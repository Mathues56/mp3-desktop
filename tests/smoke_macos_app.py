"""Exercise the packaged macOS app without browser or user interaction."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(url, token=None, data=None):
    headers = {}
    body = None
    if token:
        headers["X-Local-Token"] = token
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    with urlopen(Request(url, body, headers), timeout=5) as response:
        return (
            json.loads(response.read())
            if body is not None or "/api/" in url
            else response.read()
        )


def main():
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"Executável do app ausente: {executable}")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} não está disponível no PATH do runner.")

    with tempfile.TemporaryDirectory(prefix="media-studio-macos-smoke-") as temp:
        root = Path(temp)
        source = root / "synthetic.mp4"
        output = root / "exports"
        output.mkdir()
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=teal:s=320x240:r=24:d=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=44100:duration=3",
                "-shortest",
                "-c:v",
                "mpeg4",
                "-q:v",
                "4",
                "-c:a",
                "aac",
                str(source),
            ],
            check=True,
        )

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env.update(
            MP3_DESKTOP_PORT=str(port),
            MP3_DESKTOP_NO_BROWSER="1",
            MP3_DESKTOP_DATA_DIR=str(root / "app-data"),
        )
        process = subprocess.Popen(
            [str(executable)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 30
            page = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"O app encerrou durante a inicialização: {process.returncode}"
                    )
                try:
                    page = request(base + "/")
                    break
                except (URLError, TimeoutError):
                    time.sleep(0.25)
            if page is None:
                raise RuntimeError("O servidor local não iniciou em 30 segundos.")
            match = re.search(rb'<meta name="local-token" content="([^"]+)"', page)
            if not match:
                raise RuntimeError("A interface não publicou o token local da sessão.")
            token = match.group(1).decode("ascii")

            try:
                request(base + "/api/state")
            except HTTPError as error:
                if error.code != 404:
                    raise RuntimeError(
                        f"Estado sem token retornou HTTP {error.code}."
                    ) from error
            else:
                raise RuntimeError("A API aceitou uma solicitação sem token.")

            project = request(
                base + "/api/project/create",
                token,
                {"name": "Smoke macOS", "description": "Projeto gerado no runner."},
            )["result"]
            imported = request(
                base + "/api/import",
                token,
                {"paths": [str(source)], "project_id": project},
            )["result"]["imported"]
            if len(imported) != 1:
                raise RuntimeError("O app empacotado não importou o vídeo sintético.")
            video_id = imported[0]
            request(
                base + "/api/clip/add",
                token,
                {"video_id": video_id, "start": 0.25, "end": 1.75, "title": "Smoke"},
            )
            state = request(base + "/api/state", token)
            clip_id = state["clips"][str(video_id)][0]["id"]
            request(
                base + "/api/enqueue",
                token,
                {
                    "clip_id": clip_id,
                    "folder": str(output),
                    "preset": "Original",
                    "quality": 23,
                },
            )
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                state = request(base + "/api/state", token)
                export = state["exports"][0]
                if export["status"] in {"error", "interrupted", "cancelled"}:
                    raise RuntimeError(
                        f"A exportação FFmpeg falhou: {export['result']}"
                    )
                if export["status"] == "done":
                    result = Path(export["result"])
                    if not result.is_file() or result.stat().st_size == 0:
                        raise RuntimeError("A exportação não criou um MP4 válido.")
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("A exportação FFmpeg não terminou em 90 segundos.")

            request(base + "/api/shutdown", token, {})
            if process.wait(timeout=25) != 0:
                raise RuntimeError(f"O app encerrou com código {process.returncode}.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    print(
        "macOS app smoke test passed: startup, local auth, projects, import, clips, FFmpeg export, shutdown."
    )


if __name__ == "__main__":
    main()
