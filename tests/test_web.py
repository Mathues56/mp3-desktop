"""Smoke tests for the local HTML interface and its API boundary."""

import json
import re
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mp3_desktop import storage
from mp3_desktop.media import Video
from mp3_desktop.web import StudioService, make_handler
from http.server import ThreadingHTTPServer


class WebTests(unittest.TestCase):
    def test_application_entry_point_imports(self):
        import app

        self.assertTrue(callable(app.web_main))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(storage, "DATA_DIR", Path(self.temp.name))
        self.data_patch.start()
        self.service = StudioService()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.service, "test-token")
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.data_patch.stop()
        self.temp.cleanup()

    def request(self, path, data=None, token=True):
        headers = {"X-Local-Token": "test-token"} if token else {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path,
            json.dumps(data).encode() if data is not None else None,
            headers=headers,
        )
        return urllib.request.urlopen(request, timeout=3)

    def test_assets_and_empty_state(self):
        with self.request("/") as response:
            page = response.read().decode()
        self.assertIn("test-token", page)
        self.assertIn('id="page-editor"', page)
        with self.request("/app.css") as response:
            self.assertIn(b"#04222b", response.read().lower())
        with self.request("/api/state") as response:
            state = json.load(response)
        self.assertEqual(state["videos"], [])
        self.assertEqual(state["download"]["status"], "idle")

    def test_web_controls_and_routes_have_matching_targets(self):
        assets = Path(__file__).parents[1] / "mp3_desktop" / "web_assets"
        page = (assets / "index.html").read_text(encoding="utf-8")
        script = (assets / "app.js").read_text(encoding="utf-8")
        ids = set(re.findall(r'\bid="([^"]+)"', page))
        required_ids = set(re.findall(r'\$\("([^"]+)"\)', script))
        self.assertTrue(required_ids <= ids, required_ids - ids)
        pages = set(re.findall(r'\bid="page-([^"]+)"', page))
        routes = set(re.findall(r'data-page="([^"]+)"', page))
        self.assertTrue(routes <= pages, routes - pages)

    def test_api_requires_token_and_rejects_missing_video(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/state", token=False)
        self.assertEqual(error.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(
                "/api/clip/add",
                {"video_id": 0, "start": 0, "end": 10, "title": "Teste"},
            )
        self.assertEqual(error.exception.code, 400)

    def test_local_server_rejects_untrusted_hosts_and_origins(self):
        request = urllib.request.Request(
            self.base + "/", headers={"Host": "attacker.example"}
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 403)

        request = urllib.request.Request(
            self.base + "/api/state",
            headers={
                "Host": f"127.0.0.1:{self.server.server_port}",
                "Origin": "https://attacker.example",
                "X-Local-Token": "test-token",
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 403)

    def test_mac_native_dialogs_and_folder_open(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/tmp/one.mp4\x1f/tmp/two.mov\n", stderr=""
        )
        with (
            patch("mp3_desktop.web.sys", SimpleNamespace(platform="darwin")),
            patch("mp3_desktop.web.subprocess.run", return_value=completed) as run,
        ):
            self.assertEqual(
                self.service.choose("videos"), ["/tmp/one.mp4", "/tmp/two.mov"]
            )
            self.assertEqual(run.call_args.args[0][0], "/usr/bin/osascript")
            self.assertIn("choose file", run.call_args.args[0][2])

            run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="/tmp/output\n", stderr=""
            )
            self.assertEqual(self.service.choose("export_folder"), "/tmp/output")
            self.assertIn("choose folder", run.call_args.args[0][2])

            with patch("mp3_desktop.web.subprocess.Popen") as popen:
                self.service.open_folder({"path": self.temp.name})
            popen.assert_called_once_with(["/usr/bin/open", self.temp.name])

    def test_mac_data_directory_uses_application_support(self):
        home = Path(self.temp.name)
        with (
            patch("mp3_desktop.storage.sys", SimpleNamespace(platform="darwin")),
            patch("mp3_desktop.storage.Path.home", return_value=home),
        ):
            self.assertEqual(
                storage._default_data_dir(),
                home / "Library" / "Application Support" / "MediaStudio",
            )

    def test_shutdown_requires_token_and_stops_server(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/shutdown", {}, token=False)
        self.assertEqual(error.exception.code, 403)
        with self.request("/api/shutdown", {}) as response:
            self.assertEqual(response.status, 200)
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def test_media_endpoint_requires_token_and_supports_byte_ranges(self):
        path = Path(self.temp.name) / "source.mp4"
        payload = b"0123456789-media-bytes"
        path.write_bytes(payload)
        with patch(
            "mp3_desktop.web.probe",
            return_value=Video(path, 30.0, 1920, 1080, len(payload)),
        ):
            video_id = self.service.import_videos([str(path)])["imported"][0]

        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(
                self.base + f"/media/{video_id}?token=wrong", timeout=3
            )
        self.assertEqual(error.exception.code, 403)

        request = urllib.request.Request(
            self.base + f"/media/{video_id}?token=test-token",
            headers={"Range": "bytes=2-6"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(
                response.headers["Content-Range"], f"bytes 2-6/{len(payload)}"
            )
            self.assertEqual(response.read(), payload[2:7])

        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(
                self.base + f"/media/{video_id + 999}?token=test-token", timeout=3
            )
        self.assertEqual(error.exception.code, 404)

    def test_import_clip_and_queue_flow(self):
        path = Path(self.temp.name) / "video.mp4"
        path.write_bytes(b"sample")
        with patch(
            "mp3_desktop.web.probe", return_value=Video(path, 30.0, 1920, 1080, 6)
        ):
            imported = self.service.import_videos([str(path)])
        video_id = imported["imported"][0]
        self.service.clip_action(
            "add", {"video_id": video_id, "start": 2, "end": 8, "title": "Trecho"}
        )
        clip_id = self.service.state()["clips"][str(video_id)][0]["id"]
        with patch.object(self.service, "_start_next_export"):
            self.service.enqueue(
                {
                    "clip_id": clip_id,
                    "folder": self.temp.name,
                    "preset": "Original",
                    "quality": 23,
                }
            )
        self.assertEqual(self.service.state()["exports"][0]["title"], "Trecho")

    def test_project_creation_editing_and_video_membership(self):
        project_id = self.service.project_action(
            "create", {"name": "Lançamento", "description": "Vídeos do evento"}
        )
        path = Path(self.temp.name) / "source.mp4"
        path.write_bytes(b"sample")
        with patch(
            "mp3_desktop.web.probe", return_value=Video(path, 30.0, 1920, 1080, 6)
        ):
            imported = self.service.import_videos([str(path)], project_id)
        self.assertEqual(len(imported["imported"]), 1)
        project = self.service.state()["projects"][0]
        self.assertEqual(project["name"], "Lançamento")
        self.assertEqual(project["video_count"], 1)
        self.assertEqual(project["videos"][0]["name"], "source.mp4")
        self.service.project_action(
            "update", {"id": project_id, "name": "Evento", "description": ""}
        )
        self.service.project_action("delete", {"id": project_id})
        state = self.service.state()
        self.assertEqual(state["projects"], [])
        self.assertEqual(len(state["videos"]), 1)


if __name__ == "__main__":
    unittest.main()
