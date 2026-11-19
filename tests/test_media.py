import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mp3_desktop import storage
from mp3_desktop.media import (
    Clip,
    MediaError,
    Video,
    binary,
    export,
    probe,
    validate_clip,
)


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "sample.mp4"
        self.source.write_bytes(b"video sample")
        self.video = Video(self.source, 120.0, 1920, 1080, self.source.stat().st_size)

    @patch("mp3_desktop.media.binary", return_value="ffprobe")
    def test_probe(self, _):
        class Result:
            stdout = json.dumps(
                {
                    "format": {"duration": "120"},
                    "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
                }
            )

        video = probe(self.source, runner=lambda *args, **kwargs: Result())
        self.assertEqual((video.duration, video.width, video.height), (120, 1920, 1080))
        with self.assertRaises(MediaError):
            probe(self.folder / "missing.mp4")

    def test_clip_validation_and_persistence(self):
        db = storage.connect(self.folder / "studio.db")
        video_id = storage.add_video(self.video, db)
        valid = Clip(video_id, 10, 20, "Trecho")
        validate_clip(valid, self.video.duration)
        clip_id = storage.add_clip(valid, db)
        job_id = storage.enqueue(clip_id, self.folder, "Original", 23, db)
        self.assertEqual(storage.next_export(db)[0], job_id)
        storage.update_export(job_id, "running", None, db)
        db.close()
        db = storage.connect(self.folder / "studio.db")
        self.assertEqual(storage.list_exports(db)[0][2], "interrupted")
        self.assertEqual(storage.list_clips(video_id, db)[0][3], "Trecho")
        db.close()
        for start, end in ((-1, 2), (20, 20), (10, 121)):
            with self.assertRaises(MediaError):
                validate_clip(Clip(video_id, start, end, "x"), 120)

    @patch("mp3_desktop.media.binary", return_value="ffmpeg")
    def test_export_and_duplicate(self, _):
        class Process:
            def __init__(self, command, **kwargs):
                Path(command[-1]).write_bytes(b"mp4 output")
                self.stdout = iter(["out_time_us=5000000\n"])

            def wait(self, timeout=None):
                return 0

            def poll(self):
                return 0

        clip = Clip(1, 0, 10, "Trecho")
        values = []
        first = export(
            clip,
            self.video,
            self.folder,
            "Vertical 9:16",
            23,
            values.append,
            threading.Event(),
            popen=Process,
        )
        second = export(
            clip,
            self.video,
            self.folder,
            "Original",
            23,
            values.append,
            threading.Event(),
            popen=Process,
        )
        self.assertEqual(first.name, "Trecho.mp4")
        self.assertEqual(second.name, "Trecho (1).mp4")
        self.assertIn(50.0, values)
        self.assertEqual(values[-1], 100)

    @patch("mp3_desktop.media.binary", return_value="ffmpeg")
    def test_cancel_cleans_temp(self, _):
        class Process:
            def __init__(self, command, **kwargs):
                Path(command[-1]).write_bytes(b"temp")
                self.stdout = iter(["out_time_us=1000000\n"])

            def terminate(self):
                pass

            def wait(self, timeout=None):
                return 1

            def poll(self):
                return None

        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(MediaError):
            export(
                Clip(1, 0, 10, "x"),
                self.video,
                self.folder,
                "Original",
                23,
                lambda _: None,
                cancel,
                popen=Process,
            )
        self.assertEqual(list(self.folder.glob(".mp3-desktop-*.mp4")), [])

    def test_cancel_kills_ffmpeg_if_terminate_times_out(self):
        class Process:
            killed = False
            stdout = iter(())

            def poll(self):
                return 1 if self.killed else None

            def terminate(self):
                pass

            def wait(self, timeout=None):
                if timeout is not None:
                    raise subprocess.TimeoutExpired("ffmpeg", timeout)
                return 1

            def kill(self):
                self.killed = True

        process = Process()
        cancel = threading.Event()
        cancel.set()
        with patch("mp3_desktop.media.binary", return_value="ffmpeg"):
            with self.assertRaises(MediaError):
                export(
                    Clip(1, 0, 10, "x"),
                    self.video,
                    self.folder,
                    "Original",
                    23,
                    lambda _: None,
                    cancel,
                    popen=lambda *_args, **_kwargs: process,
                )
        self.assertTrue(process.killed)
        self.assertEqual(list(self.folder.glob(".mp3-desktop-*.mp4")), [])

    def test_macos_ffmpeg_lookup_includes_homebrew_prefixes(self):
        with (
            patch("mp3_desktop.media.sys", SimpleNamespace(platform="darwin")),
            patch.dict(os.environ, {"PATH": "/usr/bin"}),
            patch(
                "mp3_desktop.media.shutil.which",
                return_value="/opt/homebrew/bin/ffmpeg",
            ) as which,
        ):
            self.assertEqual(binary("ffmpeg"), "/opt/homebrew/bin/ffmpeg")
        search_path = which.call_args.kwargs["path"].split(os.pathsep)
        self.assertIn("/opt/homebrew/bin", search_path)
        self.assertIn("/usr/local/bin", search_path)


if __name__ == "__main__":
    unittest.main()
