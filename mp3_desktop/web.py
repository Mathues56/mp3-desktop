"""Local browser interface for the existing download and media services."""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import closing
from pathlib import Path
from tkinter import Tk, filedialog
from urllib.parse import parse_qs, urlsplit

from . import storage
from .core import Cancelled, Download, DownloadError, Paused, validate_url
from .media import (
    Clip,
    MediaError,
    PRESETS,
    Video,
    export,
    probe,
    validate_clip,
)


ASSETS = Path(__file__).with_name("web_assets")


def _mac_dialog(kind: str):
    if kind == "videos":
        script = """try
 set chosenItems to choose file with multiple selections allowed with prompt "Importar vídeos"
on error number -128
 return ""
end try
set itemPaths to {}
repeat with selectedItem in chosenItems
 set end of itemPaths to POSIX path of selectedItem
end repeat
set AppleScript's text item delimiters to character id 31
return itemPaths as text"""
    else:
        script = """try
 set selectedFolder to choose folder with prompt "Escolher pasta"
on error number -128
 return ""
end try
return POSIX path of selectedFolder"""
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise OSError("O seletor nativo do macOS não pôde ser aberto.")
    output = result.stdout.removesuffix("\n").removesuffix("\r")
    if kind == "videos":
        return output.split("\x1f") if output else []
    return output


class StudioService:
    def __init__(self):
        with closing(storage.connect()):
            pass
        self.lock = threading.RLock()
        self.dialog_lock = threading.Lock()
        self.download: Download | None = None
        self.download_worker: threading.Thread | None = None
        self.closing = False
        self.download_state = {
            "status": "idle",
            "received": 0,
            "total": None,
            "speed": 0,
            "resumable": False,
            "message": "",
        }
        self.export_cancel = threading.Event()
        self.export_progress = 0.0
        self.export_id: int | None = None
        self.export_worker: threading.Thread | None = None
        self.export_requested = False
        self._start_next_export()

    def _db(self):
        return sqlite3.connect(storage.DATA_DIR / "history.db", timeout=30)

    def state(self):
        with closing(self._db()) as db:
            videos = storage.list_videos(db)
            projects = storage.list_projects(db)
            clips = {
                str(row[0]): [
                    dict(id=c[0], start=c[1], end=c[2], title=c[3])
                    for c in storage.list_clips(row[0], db)
                ]
                for row in videos
            }
            result = {
                "settings": {
                    "folder": str(Path.home() / "Music"),
                    "limit_mb": 500,
                    **storage.load_settings(),
                },
                "downloads": [
                    dict(name=r[0], path=r[1], size=r[2], date=r[3])
                    for r in storage.list_downloads(db)
                ],
                "videos": [
                    dict(
                        id=r[0],
                        path=r[1],
                        name=Path(r[1]).name,
                        duration=r[2],
                        width=r[3],
                        height=r[4],
                        size=r[5],
                    )
                    for r in videos
                ],
                "projects": [
                    {
                        "id": r[0],
                        "name": r[1],
                        "description": r[2],
                        "created_at": r[3],
                        "video_count": r[4],
                        "videos": [
                            dict(
                                id=v[0],
                                path=v[1],
                                name=Path(v[1]).name,
                                duration=v[2],
                                width=v[3],
                                height=v[4],
                                size=v[5],
                            )
                            for v in storage.list_project_videos(r[0], db)
                        ],
                    }
                    for r in projects
                ],
                "clips": clips,
                "exports": [
                    dict(id=r[0], title=r[1], status=r[2], result=r[3])
                    for r in storage.list_exports(db)
                ],
                "presets": list(PRESETS),
            }
        with self.lock:
            result["download"] = self.download_state.copy()
            result["export"] = {"id": self.export_id, "progress": self.export_progress}
        return result

    def choose(self, kind: str):
        if kind not in {"videos", "download_folder", "export_folder"}:
            raise ValueError("Seleção inválida.")
        with self.dialog_lock:
            if sys.platform == "darwin":
                return _mac_dialog(kind)
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                if kind == "videos":
                    paths = filedialog.askopenfilenames(
                        parent=root,
                        title="Importar vídeos",
                        filetypes=[("Vídeos", "*.mp4 *.mkv *.mov *.webm *.avi")],
                    )
                    return list(paths)
                return filedialog.askdirectory(parent=root, title="Escolher pasta")
            finally:
                root.destroy()

    def import_videos(self, paths, project_id=None):
        if not isinstance(paths, list) or not paths or len(paths) > 100:
            raise ValueError("Escolha até 100 vídeos locais.")
        imported, errors = [], []
        with closing(self._db()) as db:
            if project_id is not None:
                project_id = int(project_id)
                if not db.execute(
                    "SELECT 1 FROM projects WHERE id=?", (project_id,)
                ).fetchone():
                    raise ValueError("Projeto não encontrado.")
            for raw in paths:
                try:
                    video = probe(Path(raw))
                    video_id = storage.add_video(video, db)
                    if project_id is not None:
                        storage.add_video_to_project(project_id, video_id, db)
                    imported.append(video_id)
                except (MediaError, OSError) as exc:
                    errors.append(f"{Path(raw).name}: {exc}")
        return {"imported": imported, "errors": errors}

    def project_action(self, action, data):
        project_id = int(data.get("id", 0)) if action != "create" else None
        if action == "delete":
            with closing(self._db()) as db:
                storage.delete_project(project_id, db)
            return
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name or len(name) > 120 or len(description) > 2000:
            raise ValueError(
                "Informe um nome (até 120 caracteres) e uma descrição de até 2000 caracteres."
            )
        with closing(self._db()) as db:
            if action == "create":
                return storage.add_project(name, description, db)
            if action == "update":
                storage.update_project(project_id, name, description, db)
                return project_id
        raise ValueError("Ação inválida.")

    def start_download(self, data):
        url = validate_url(str(data.get("url", "")))
        folder = Path(str(data.get("folder", ""))).expanduser()
        if not str(data.get("folder", "")).strip():
            raise ValueError("Escolha a pasta de destino.")
        limit = int(data.get("limit", 500))
        if not 1 <= limit <= 10240:
            raise ValueError("O limite deve ficar entre 1 e 10240 MB.")
        with self.lock:
            if self.closing:
                raise ValueError("O Media Studio está sendo encerrado.")
            if self.download_state["status"] in {"running", "paused"}:
                raise ValueError("Já existe um download ativo.")
            self.download = Download(url, folder, max_bytes=limit * 1024 * 1024)
            self.download_state = {
                "status": "running",
                "received": 0,
                "total": None,
                "speed": 0,
                "resumable": False,
                "message": "Conectando…",
            }
            self._start_download_worker()

    def _start_download_worker(self):
        self.download_worker = threading.Thread(target=self._run_download, daemon=True)
        self.download_worker.start()

    def _run_download(self):
        job = self.download
        if job is None:
            return
        try:

            def progress(p):
                with self.lock:
                    self.download_state.update(
                        received=p.received,
                        total=p.total,
                        speed=p.speed,
                        resumable=p.resumable,
                        message=p.name,
                    )

            path = job.run(progress)
            with closing(self._db()) as db:
                storage.add(path, db)
            with self.lock:
                self.download_state.update(status="done", message=f"Salvo em {path}")
                self.download = None
        except Paused:
            with self.lock:
                self.download_state.update(status="paused", message="Download pausado.")
        except (Cancelled, DownloadError, OSError) as exc:
            with self.lock:
                self.download_state.update(status="error", message=str(exc))
                self.download = None

    def download_action(self, action):
        with self.lock:
            if self.closing:
                raise ValueError("O Media Studio está sendo encerrado.")
            job = self.download
            status = self.download_state["status"]
            if job is None:
                raise ValueError("Nenhum download ativo.")
            if (
                action == "pause"
                and status == "running"
                and self.download_state["resumable"]
            ):
                job.pause.set()
            elif action == "resume" and status == "paused":
                job.pause.clear()
                self.download_state["status"] = "running"
                self._start_download_worker()
            elif action == "cancel" and status in {"running", "paused"}:
                if status == "paused":
                    job.partial.unlink(missing_ok=True)
                    self.download = None
                    self.download_state.update(
                        status="error", message="Download cancelado."
                    )
                else:
                    job.cancel.set()
            else:
                raise ValueError("Ação indisponível no estado atual.")

    def _video(self, video_id: int, db):
        row = db.execute(
            "SELECT id,path,duration,width,height,size FROM videos WHERE id=?",
            (video_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Selecione um vídeo importado.")
        return Video(Path(row[1]), row[2], row[3], row[4], row[5])

    def media_path(self, video_id: int) -> Path:
        with closing(self._db()) as db:
            video = self._video(video_id, db)
        if not video.path.is_file():
            raise ValueError("O arquivo de vídeo não está disponível.")
        return video.path

    def clip_action(self, action, data):
        with closing(self._db()) as db:
            if action == "delete":
                clip_id = int(data.get("id", 0))
                if not db.execute(
                    "SELECT 1 FROM clips WHERE id=?", (clip_id,)
                ).fetchone():
                    raise ValueError("Selecione um clipe.")
                storage.delete_clip(clip_id, db)
                return
            video_id = int(data.get("video_id", 0))
            video = self._video(video_id, db)
            clip = Clip(
                video_id,
                float(data.get("start", 0)),
                float(data.get("end", 0)),
                str(data.get("title", "")).strip(),
            )
            validate_clip(clip, video.duration)
            if action == "add":
                storage.add_clip(clip, db)
            elif action == "update":
                clip_id = int(data.get("id", 0))
                if not db.execute(
                    "SELECT 1 FROM clips WHERE id=? AND video_id=?", (clip_id, video_id)
                ).fetchone():
                    raise ValueError("Selecione um clipe deste vídeo.")
                db.execute(
                    "UPDATE clips SET start=?,end=?,title=? WHERE id=?",
                    (clip.start, clip.end, clip.title, clip_id),
                )
                db.commit()
            else:
                raise ValueError("Ação inválida.")

    def enqueue(self, data):
        clip_id = int(data.get("clip_id", 0))
        folder = Path(str(data.get("folder", ""))).expanduser()
        preset = str(data.get("preset", ""))
        quality = int(data.get("quality", 23))
        if (
            not str(data.get("folder", "")).strip()
            or preset not in PRESETS
            or not 18 <= quality <= 32
        ):
            raise ValueError("Confira pasta, proporção e qualidade (18 a 32).")
        with closing(self._db()) as db:
            row = db.execute(
                "SELECT c.video_id,c.start,c.end,c.title FROM clips c WHERE c.id=?",
                (clip_id,),
            ).fetchone()
            if not row:
                raise ValueError("Selecione um clipe antes de exportar.")
            video = self._video(row[0], db)
            validate_clip(Clip(*row), video.duration)
            storage.enqueue(clip_id, folder, preset, quality, db)
        self._start_next_export()

    def _start_next_export(self):
        with self.lock:
            if self.closing:
                return
            self.export_requested = True
            if self.export_worker and self.export_worker.is_alive():
                return
            self.export_requested = False
            self.export_worker = threading.Thread(target=self._run_exports, daemon=True)
            self.export_worker.start()

    def _run_exports(self):
        while True:
            with self.lock:
                if self.closing:
                    break
                self.export_requested = False
            with closing(self._db()) as db:
                row = storage.next_export(db)
                if not row:
                    with self.lock:
                        if self.closing or not self.export_requested:
                            break
                    continue
                (
                    export_id,
                    clip_id,
                    folder,
                    preset,
                    quality,
                    video_id,
                    start,
                    end,
                    title,
                    path,
                    duration,
                    width,
                    height,
                    size,
                ) = row
                storage.update_export(export_id, "running", None, db)
            with self.lock:
                stopping = self.closing
                if not stopping:
                    self.export_cancel.clear()
                    self.export_id = export_id
                    self.export_progress = 0
            if stopping:
                with closing(self._db()) as db:
                    storage.update_export(export_id, "interrupted", None, db)
                break
            try:
                result = export(
                    Clip(video_id, start, end, title),
                    Video(Path(path), duration, width, height, size),
                    Path(folder),
                    preset,
                    quality,
                    self._set_export_progress,
                    self.export_cancel,
                )
                status, message = "done", str(result)
            except (MediaError, OSError) as exc:
                status = "cancelled" if self.export_cancel.is_set() else "error"
                message = str(exc)
            with closing(self._db()) as db:
                storage.update_export(export_id, status, message, db)
            with self.lock:
                self.export_id = None
                self.export_progress = 0
        with self.lock:
            self.export_worker = None
            restart = self.export_requested and not self.closing
        if restart:
            self._start_next_export()

    def _set_export_progress(self, value):
        with self.lock:
            self.export_progress = value

    def open_folder(self, data):
        path = Path(str(data.get("path", ""))).expanduser()
        if not path.is_dir():
            raise ValueError("Pasta não encontrada.")
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(
                ["/usr/bin/open" if sys.platform == "darwin" else "xdg-open", str(path)]
            )

    def settings(self, data):
        folder = str(data.get("folder", "")).strip()
        limit = int(data.get("limit_mb", 500))
        if not folder or not 1 <= limit <= 10240:
            raise ValueError("Informe uma pasta e um limite entre 1 e 10240 MB.")
        storage.save_settings({"folder": folder, "limit_mb": limit})

    def close(self):
        with self.lock:
            self.closing = True
            if self.download is not None:
                self.download.cancel.set()
            self.export_cancel.set()
            workers = [self.download_worker, self.export_worker]
        for worker in workers:
            if worker and worker is not threading.current_thread():
                worker.join(timeout=22)


def make_handler(service: StudioService, token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _send(self, code, content, mime="application/json; charset=utf-8"):
            payload = (
                content
                if isinstance(content, bytes)
                else json.dumps(content, ensure_ascii=False).encode("utf-8")
            )
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

        def _is_local_request(self):
            try:
                host = urlsplit("//" + self.headers.get("Host", ""))
                port = self.server.server_port
                if (
                    host.hostname not in {"127.0.0.1", "localhost"}
                    or host.port not in {None, port}
                    or host.username is not None
                    or host.password is not None
                ):
                    return False
                origin = self.headers.get("Origin")
                if origin:
                    parsed_origin = urlsplit(origin)
                    if (
                        parsed_origin.scheme != "http"
                        or parsed_origin.hostname not in {"127.0.0.1", "localhost"}
                        or parsed_origin.port not in {None, port}
                    ):
                        return False
                return True
            except ValueError:
                return False

        def _send_media(self, path):
            size = path.stat().st_size
            range_header = self.headers.get("Range")
            start, end, status = 0, size - 1, 200
            if range_header:
                try:
                    unit, value = range_header.split("=", 1)
                    if unit != "bytes" or "," in value or size == 0:
                        raise ValueError
                    first, last = value.split("-", 1)
                    if not first:
                        suffix = int(last)
                        if suffix <= 0:
                            raise ValueError
                        start = max(size - suffix, 0)
                    else:
                        start = int(first)
                        end = int(last) if last else size - 1
                    if start < 0 or start >= size or end < start:
                        raise ValueError
                    end = min(end, size - 1)
                    status = 206
                except (ValueError, TypeError):
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

            length = max(0, end - start + 1)
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD":
                return
            with path.open("rb") as media:
                media.seek(start)
                remaining = length
                while remaining:
                    block = media.read(min(64 * 1024, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)

        def do_GET(self):
            if not self._is_local_request():
                return self._send(403, {"error": "Origem local inválida."})
            request = urlsplit(self.path)
            if request.path == "/":
                page = (
                    (ASSETS / "index.html")
                    .read_text(encoding="utf-8")
                    .replace("__LOCAL_TOKEN__", token)
                )
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if request.path in {"/app.css", "/app.js"}:
                suffix = request.path[1:]
                mime = (
                    "text/css; charset=utf-8"
                    if suffix.endswith("css")
                    else "text/javascript; charset=utf-8"
                )
                return self._send(200, (ASSETS / suffix).read_bytes(), mime)
            if (
                request.path == "/api/state"
                and self.headers.get("X-Local-Token") == token
            ):
                return self._send(200, service.state())
            if request.path.startswith("/media/"):
                media_id = request.path.removeprefix("/media/")
                query = parse_qs(request.query)
                if query.get("token", [""])[0] != token:
                    return self._send(403, {"error": "Acesso negado."})
                if not media_id.isdecimal():
                    return self._send(404, {"error": "Vídeo não encontrado."})
                try:
                    path = service.media_path(int(media_id))
                except (ValueError, OSError):
                    return self._send(404, {"error": "Vídeo não encontrado."})
                return self._send_media(path)
            self._send(404, {"error": "Não encontrado."})

        def do_HEAD(self):
            if not self._is_local_request():
                return self._send(403, {"error": "Origem local inválida."})
            request = urlsplit(self.path)
            if not request.path.startswith("/media/"):
                return self._send(404, {"error": "Não encontrado."})
            media_id = request.path.removeprefix("/media/")
            query = parse_qs(request.query)
            if query.get("token", [""])[0] != token:
                return self._send(403, {"error": "Acesso negado."})
            if not media_id.isdecimal():
                return self._send(404, {"error": "Vídeo não encontrado."})
            try:
                path = service.media_path(int(media_id))
            except (ValueError, OSError):
                return self._send(404, {"error": "Vídeo não encontrado."})
            return self._send_media(path)

        def do_POST(self):
            if not self._is_local_request():
                return self._send(403, {"error": "Origem local inválida."})
            if self.headers.get("X-Local-Token") != token:
                return self._send(403, {"error": "Acesso negado."})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self._send(415, {"error": "Envie JSON."})
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                return self._send(413, {"error": "Pedido muito grande."})
            try:
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Pedido inválido.")
                action = self.path.removeprefix("/api/")
                should_shutdown = False
                if action == "choose":
                    result = service.choose(str(data.get("kind", "")))
                elif action == "import":
                    result = service.import_videos(
                        data.get("paths"), data.get("project_id")
                    )
                elif action in {
                    "project/create",
                    "project/update",
                    "project/delete",
                }:
                    result = service.project_action(action.split("/")[1], data)
                elif action == "download":
                    service.start_download(data)
                    result = None
                elif action in {"pause", "resume", "cancel"}:
                    service.download_action(action)
                    result = None
                elif action in {"clip/add", "clip/update", "clip/delete"}:
                    service.clip_action(action.split("/")[1], data)
                    result = None
                elif action == "enqueue":
                    service.enqueue(data)
                    result = None
                elif action == "cancel-export":
                    if service.export_id is None:
                        raise ValueError("Nenhuma exportação em andamento.")
                    service.export_cancel.set()
                    result = None
                elif action == "open-folder":
                    service.open_folder(data)
                    result = None
                elif action == "settings":
                    service.settings(data)
                    result = None
                elif action == "shutdown":
                    result = None
                    should_shutdown = True
                else:
                    return self._send(404, {"error": "Ação não encontrada."})
                self._send(200, {"ok": True, "result": result})
                if should_shutdown:
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
            except (
                ValueError,
                TypeError,
                DownloadError,
                MediaError,
                OSError,
                sqlite3.Error,
            ) as exc:
                self._send(400, {"error": str(exc)})

    return Handler


def main():
    service = StudioService()
    token = secrets.token_urlsafe(32)
    port = int(os.environ.get("MP3_DESKTOP_PORT", "0"))
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(service, token))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"MP3 Desktop: {url}", flush=True)
    if os.environ.get("MP3_DESKTOP_NO_BROWSER") != "1":
        webbrowser.open(url)

    def terminate(_signum, _frame):
        raise KeyboardInterrupt

    previous_sigterm = signal.signal(signal.SIGTERM, terminate)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()
        signal.signal(signal.SIGTERM, previous_sigterm)
