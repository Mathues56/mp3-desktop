"""Local video metadata, clip validation and sequential FFmpeg export."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class MediaError(Exception):
    pass


def _stop_process(process):
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@dataclass(frozen=True)
class Video:
    path: Path
    duration: float
    width: int
    height: int
    size: int


@dataclass(frozen=True)
class Clip:
    video_id: int
    start: float
    end: float
    title: str


PRESETS = {
    "Original": None,
    "Vertical 9:16": (1080, 1920),
    "Horizontal 16:9": (1920, 1080),
    "Quadrado 1:1": (1080, 1080),
}


def binary(name: str) -> str:
    custom = os.environ.get(f"MP3_DESKTOP_{name.upper()}")
    path = None
    if sys.platform == "darwin":
        path = os.pathsep.join(
            filter(
                None, (os.environ.get("PATH"), "/opt/homebrew/bin", "/usr/local/bin")
            )
        )
    result = custom or shutil.which(name, path=path)
    if not result:
        raise MediaError(f"{name} não encontrado. Instale FFmpeg e confira o PATH.")
    return result


def probe(path: Path, *, runner=subprocess.run) -> Video:
    if not path.is_file() or path.suffix.lower() not in {
        ".mp4",
        ".mkv",
        ".mov",
        ".webm",
        ".avi",
    }:
        raise MediaError("Escolha um arquivo de vídeo local compatível.")
    try:
        result = runner(
            [
                binary("ffprobe"),
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(result.stdout)
        stream = next(s for s in data["streams"] if s.get("codec_type") == "video")
        duration = float(data["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
        if duration <= 0 or width <= 0 or height <= 0:
            raise ValueError
        return Video(path.resolve(), duration, width, height, path.stat().st_size)
    except (
        OSError,
        subprocess.SubprocessError,
        KeyError,
        StopIteration,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise MediaError(
            "Não foi possível ler os metadados do vídeo com ffprobe."
        ) from exc


def validate_clip(clip: Clip, duration: float) -> None:
    if not (0 <= clip.start < clip.end <= duration):
        raise MediaError("O intervalo deve estar dentro da duração do vídeo.")
    if not clip.title.strip():
        raise MediaError("Informe um título para o clipe.")


def safe_title(title: str) -> str:
    from .core import safe_name

    return safe_name(title).removesuffix(".mp3") or "clipe"


def export(
    clip: Clip,
    video: Video,
    folder: Path,
    preset: str,
    quality: int,
    progress: Callable[[float], None],
    cancel: threading.Event,
    *,
    popen=subprocess.Popen,
) -> Path:
    validate_clip(clip, video.duration)
    if preset not in PRESETS or not 18 <= quality <= 32:
        raise MediaError("Preset ou qualidade inválidos.")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(folder).free < max(video.size, 100 * 1024 * 1024):
            raise MediaError("Espaço livre insuficiente para exportar.")
    except OSError as exc:
        raise MediaError("Não foi possível acessar a pasta de exportação.") from exc
    temporary = folder / f".mp3-desktop-{uuid.uuid4().hex}.mp4"
    command = [
        binary("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-ss",
        str(clip.start),
        "-i",
        str(video.path),
        "-t",
        str(clip.end - clip.start),
    ]
    if PRESETS[preset]:
        width, height = PRESETS[preset]
        command += [
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v",
            "libx264",
            "-crf",
            str(quality),
            "-preset",
            "medium",
        ]
    else:
        command += ["-c:v", "libx264", "-crf", str(quality), "-preset", "medium"]
    command += ["-c:a", "aac", "-movflags", "+faststart", "-y", str(temporary)]
    process = None
    try:
        process = popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert process.stdout is not None
        lines: queue.Queue[str | None] = queue.Queue()

        def read_progress():
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        threading.Thread(target=read_progress, daemon=True).start()
        while True:
            if cancel.is_set():
                _stop_process(process)
                raise MediaError("Exportação cancelada.")
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if line is None:
                break
            if line.startswith("out_time_ms=") or line.startswith("out_time_us="):
                micros = int(line.split("=", 1)[1])
                progress(min(100.0, micros / 1_000_000 / (clip.end - clip.start) * 100))
        if (
            process.wait() != 0
            or not temporary.is_file()
            or temporary.stat().st_size == 0
        ):
            raise MediaError("FFmpeg falhou ao exportar o clipe.")
        base = safe_title(clip.title)
        for index in range(1000):
            target = folder / (f"{base}.mp4" if index == 0 else f"{base} ({index}).mp4")
            try:
                os.link(temporary, target)
                progress(100.0)
                return target
            except FileExistsError:
                continue
        raise MediaError("Há arquivos demais com esse nome.")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise MediaError("Não foi possível executar FFmpeg.") from exc
    finally:
        if process and process.poll() is None:
            _stop_process(process)
        temporary.unlink(missing_ok=True)
