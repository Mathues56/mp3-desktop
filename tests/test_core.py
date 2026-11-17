import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from mp3_desktop.core import (
    Cancelled,
    Download,
    DownloadError,
    Paused,
    safe_name,
    validate_url,
)
from mp3_desktop import storage


PAYLOAD = b"ID3" + b"a" * 200000


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/missing":
            self.send_error(404)
            return
        if self.path == "/html":
            body, kind = b"<html>oops</html>", "text/html"
        elif self.path == "/short":
            body, kind = PAYLOAD[:100], "audio/mpeg"
        else:
            body, kind = PAYLOAD, "audio/mpeg"
        start = 0
        if self.headers.get("Range") and self.path != "/no-range":
            start = int(self.headers["Range"].split("=")[1].split("-")[0])
        self.send_response(206 if start else 200)
        self.send_header("Content-Type", kind)
        self.send_header(
            "Content-Length",
            str(len(PAYLOAD) if self.path == "/short" else len(body) - start),
        )
        if self.path != "/no-range":
            self.send_header("Accept-Ranges", "bytes")
        if start:
            self.send_header(
                "Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}"
            )
        self.send_header("Content-Disposition", 'attachment; filename="song.mp3"')
        self.end_headers()
        try:
            self.wfile.write(body[start:])
        except BrokenPipeError:
            pass

    def log_message(self, *_):
        pass


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def job(self, suffix="/"):
        return Download(self.base + suffix, self.folder, allow_http=True)

    def test_url_and_filename(self):
        for url in (
            "http://example.com/x.mp3",
            "file:///x",
            "https://user:pass@example.com/a",
            "nonsense",
        ):
            with self.assertRaises(DownloadError):
                validate_url(url)
        self.assertEqual(safe_name("../CON"), "audio.mp3")
        self.assertEqual(safe_name("../../bad?.mp3"), "bad_.mp3")

    def test_download_duplicate_and_history(self):
        first = self.job().run(lambda _: None)
        second = self.job().run(lambda _: None)
        self.assertEqual(first.read_bytes(), PAYLOAD)
        self.assertEqual(second.name, "song (1).mp3")
        db = storage.connect(self.folder / "history.db")
        storage.add(first, db)
        self.assertEqual(storage.list_downloads(db)[0][0], "song.mp3")
        db.close()

    def test_cancel_and_pause_resume(self):
        cancelled = self.job()

        def stop(_):
            cancelled.cancel.set()

        with self.assertRaises(Cancelled):
            cancelled.run(stop)
        self.assertFalse(cancelled.partial.exists())
        paused = self.job()

        def pause(_):
            paused.pause.set()

        with self.assertRaises(Paused):
            paused.run(pause)
        self.assertTrue(paused.partial.exists())
        paused.pause.clear()
        self.assertEqual(paused.run(lambda _: None).read_bytes(), PAYLOAD)

    def test_errors_and_incomplete(self):
        for suffix in ("/missing", "/html", "/short"):
            job = self.job(suffix)
            with self.assertRaises(DownloadError):
                job.run(lambda _: None)
            self.assertFalse(job.partial.exists())

    def test_size_limit(self):
        with self.assertRaises(DownloadError):
            Download(self.base + "/", self.folder, max_bytes=100, allow_http=True).run(
                lambda _: None
            )

    def test_resume_rejected_cleans_partial(self):
        job = self.job("/no-range")
        job.received = 3
        job.partial.write_bytes(b"ID3")
        with self.assertRaises(DownloadError):
            job.run(lambda _: None)
        self.assertFalse(job.partial.exists())

    def test_unwritable_folder(self):
        job = self.job()
        with patch.object(Path, "mkdir", side_effect=PermissionError):
            with self.assertRaises(DownloadError):
                job.run(lambda _: None)


if __name__ == "__main__":
    unittest.main()
