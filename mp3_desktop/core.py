"""Streaming HTTPS MP3 transfers."""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable


class DownloadError(Exception):
    pass


class Cancelled(DownloadError):
    pass


class Paused(DownloadError):
    pass


@dataclass
class Progress:
    name: str
    received: int
    total: int | None
    speed: float
    resumable: bool


def validate_url(url: str, *, allow_http: bool = False) -> str:
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        _ = parsed.port
    except ValueError as exc:
        raise DownloadError("URL inválida.") from exc
    if parsed.scheme not in ({"https", "http"} if allow_http else {"https"}):
        raise DownloadError("Use uma URL HTTPS direta.")
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or any(c.isspace() for c in url)
    ):
        raise DownloadError("URL inválida ou com credenciais.")
    return url.strip()


def safe_name(raw: str) -> str:
    name = urllib.parse.unquote(raw).replace("\\", "/").split("/")[-1]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    reserved = (
        {"CON", "PRN", "AUX", "NUL"}
        | {f"COM{i}" for i in range(1, 10)}
        | {f"LPT{i}" for i in range(1, 10)}
    )
    if not name or name.split(".")[0].upper() in reserved:
        name = "audio"
    name = name[:170].rstrip(" .")
    if not name.lower().endswith(".mp3"):
        name = f"{name.rsplit('.', 1)[0]}.mp3" if "." in name else f"{name}.mp3"
    return name


def _filename(headers, url: str) -> str:
    disposition = headers.get("Content-Disposition", "")
    match = re.search(
        r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)", disposition, re.I
    )
    raw = (
        (match.group(1) or match.group(2)) if match else urllib.parse.urlsplit(url).path
    )
    return safe_name(raw or "audio.mp3")


def _is_mp3(data: bytes) -> bool:
    return data.startswith(b"ID3") or (
        len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
    )


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allow_http: bool):
        self.allow_http = allow_http

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, allow_http=self.allow_http)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Download:
    def __init__(
        self,
        url: str,
        folder: Path,
        *,
        max_bytes: int = 500 * 1024 * 1024,
        allow_http: bool = False,
    ):
        self.url = validate_url(url, allow_http=allow_http)
        self.folder = folder
        self.max_bytes = max_bytes
        self.allow_http = allow_http
        self.cancel = Event()
        self.pause = Event()
        self.partial = folder / f".mp3-desktop-{uuid.uuid4().hex}.part"
        self.received = 0
        self.total: int | None = None
        self.etag: str | None = None
        self.resumable = False
        self.name: str | None = None

    def run(self, on_progress: Callable[[Progress], None]) -> Path:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DownloadError("Não foi possível criar a pasta de destino.") from exc
        paused = False
        opener = urllib.request.build_opener(_SafeRedirect(self.allow_http))
        headers = {"User-Agent": "MP3Desktop/0.1"}
        if self.received:
            headers["Range"] = f"bytes={self.received}-"
            if self.etag:
                headers["If-Range"] = self.etag
        req = urllib.request.Request(self.url, headers=headers)
        try:
            with opener.open(req, timeout=20) as response:
                status = response.status
                if self.received:
                    expected = f"bytes {self.received}-"
                    if status != 206 or not response.headers.get(
                        "Content-Range", ""
                    ).startswith(expected):
                        raise DownloadError(
                            "Servidor não confirmou a retomada; inicie um novo download."
                        )
                elif status != 200:
                    raise DownloadError(f"Resposta HTTP inesperada: {status}.")
                content_type = response.headers.get_content_type().lower()
                if content_type not in {
                    "audio/mpeg",
                    "audio/mp3",
                    "application/octet-stream",
                }:
                    raise DownloadError(f"Conteúdo não é MP3: {content_type}.")
                self.name = self.name or _filename(response.headers, response.url)
                self.etag = response.headers.get("ETag") or self.etag
                self.resumable = (
                    response.headers.get("Accept-Ranges", "").lower() == "bytes"
                    or status == 206
                )
                size = response.headers.get("Content-Length")
                self.total = (
                    self.received + int(size) if size and size.isdecimal() else None
                )
                if self.total is not None and self.total > self.max_bytes:
                    raise DownloadError("Arquivo excede o limite configurado.")
                started = time.monotonic()
                baseline = self.received
                with self.partial.open("ab" if self.received else "xb") as output:
                    while True:
                        if self.cancel.is_set():
                            raise Cancelled("Download cancelado.")
                        if self.pause.is_set() and self.resumable:
                            raise Paused("Download pausado.")
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        if self.received == 0 and not _is_mp3(chunk):
                            raise DownloadError(
                                "O arquivo recebido não parece ser MP3."
                            )
                        self.received += len(chunk)
                        if self.received > self.max_bytes:
                            raise DownloadError("Arquivo excede o limite configurado.")
                        output.write(chunk)
                        elapsed = max(time.monotonic() - started, 0.001)
                        on_progress(
                            Progress(
                                self.name,
                                self.received,
                                self.total,
                                (self.received - baseline) / elapsed,
                                self.resumable,
                            )
                        )
                if self.total is not None and self.received != self.total:
                    raise DownloadError("Download incompleto.")
                if self.received < 3:
                    raise DownloadError("Arquivo MP3 vazio ou incompleto.")
                target = self.folder / self.name
                stem = target.stem
                for index in range(1000):
                    candidate = (
                        target if index == 0 else self.folder / f"{stem} ({index}).mp3"
                    )
                    try:
                        os.link(self.partial, candidate)
                        self.partial.unlink()
                        return candidate
                    except FileExistsError:
                        continue
                raise DownloadError("Há arquivos demais com esse nome na pasta.")
        except Paused:
            paused = True
            raise
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise DownloadError(
                f"Falha de rede ou arquivo: {type(exc).__name__}."
            ) from exc
        finally:
            if not paused:
                self.partial.unlink(missing_ok=True)
