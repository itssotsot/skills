"""The sketchpad must work when installed without any sibling skills."""

import importlib.util
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import struct
import time
import unittest
import zlib
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class Canvas2ImageGenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.skill = Path(cls.temporary.name) / "installed-skill"
        shutil.copytree(ROOT / "skills/canvas2imagegen", cls.skill)
        source = cls.skill / "scripts/serve.py"
        spec = importlib.util.spec_from_file_location("sketch_server", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module
        waiter_spec = importlib.util.spec_from_file_location("sketch_waiter", cls.skill / "scripts/wait_for_sketch.py")
        cls.waiter = importlib.util.module_from_spec(waiter_spec)
        waiter_spec.loader.exec_module(cls.waiter)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    def setUp(self):
        self.session = self.module.SketchSession(Path(self.temporary.name) / "submissions", self.url + "/")
        self.server.sketch_session = self.session

    @staticmethod
    def png(shade=255, width=1200, height=900):
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        pixels = (b"\x00" + bytes([shade, shade, shade, 255]) * width) * height
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")

    def post_sketch(self, data, request_id="fixture-request-0001", **headers):
        supplied = {"Content-Type": "image/png", "Origin": self.url,
                    "X-Sketch-Token": self.session.token, "X-Submission-ID": request_id}
        supplied.update(headers)
        with urlopen(Request(self.url + "/api/sketch", data=data, headers=supplied, method="POST"), timeout=5) as response:
            return json.load(response)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temporary.cleanup()

    def test_isolated_install_serves_exact_assets(self):
        for route, filename, mime in [
            ("/", "index.html", "text/html"),
            ("/index.html", "index.html", "text/html"),
            ("/style.css", "style.css", "text/css"),
            ("/app.js", "app.js", "text/javascript"),
        ]:
            with self.subTest(route=route), urlopen(self.url + route, timeout=5) as response:
                self.assertEqual(response.read(), (self.skill / "assets" / filename).read_bytes())
                self.assertEqual(response.headers.get_content_type(), mime)

    def test_does_not_expose_skill_files_or_directory_listings(self):
        for path in ["/SKILL.md", "/scripts/serve.py", "/../SKILL.md", "/%2e%2e/SKILL.md", "/assets/"]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as raised:
                urlopen(self.url + path, timeout=5)
            self.assertEqual(raised.exception.code, 404)

    def test_has_no_arbitrary_upload_endpoint(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(Request(self.url + "/", data=b"test-fixture-not-a-user-reference", method="POST"), timeout=5)
        self.assertEqual(raised.exception.code, 404)

    def test_use_sketch_delivers_exact_png_to_waiter(self):
        data = self.png()
        response = self.post_sketch(data)
        event = self.waiter.wait_for_sketch(self.session.path, timeout=0)
        self.assertEqual(response["seq"], event["seq"])
        self.assertEqual(event["status"], "submitted")
        self.assertEqual(Path(event["path"]).read_bytes(), data)
        self.assertEqual(event["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(self.waiter.wait_for_sketch(self.session.path, after=event["seq"], timeout=0)["status"], "waiting")

    def test_responsive_canvas_aspects_are_preserved_in_handoff(self):
        for seq, (width, height) in enumerate([(1200, 600), (600, 1200), (800, 800)], start=1):
            with self.subTest(width=width, height=height):
                data = self.png(width=width, height=height)
                self.post_sketch(data, request_id=f"responsive-fixture-{seq:04d}")
                event = self.waiter.wait_for_sketch(self.session.path, after=seq - 1, timeout=0)
                self.assertEqual(Path(event["path"]).read_bytes(), data)

    def test_excessive_canvas_dimensions_are_rejected(self):
        with self.assertRaises(HTTPError) as raised:
            self.post_sketch(self.png(width=4097, height=1))
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(list(self.session.events.glob("*.json")), [])

    def test_retry_of_same_click_does_not_duplicate_reference(self):
        data = self.png()
        first = self.post_sketch(data)
        second = self.post_sketch(data)
        self.assertEqual(first["seq"], second["seq"])
        self.assertEqual(len(list(self.session.events.glob("*.json"))), 1)
        self.assertEqual(len(list(self.session.directory.glob("*.png"))), 1)

    def test_reusing_click_id_for_different_pixels_is_rejected(self):
        self.post_sketch(self.png())
        with self.assertRaises(HTTPError) as raised:
            self.post_sketch(self.png(0))
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(len(list(self.session.events.glob("*.json"))), 1)

    def test_submissions_are_ordered_and_after_skips_handled_reference(self):
        self.post_sketch(self.png())
        self.post_sketch(self.png(0), request_id="fixture-request-0002")
        self.assertEqual(self.waiter.wait_for_sketch(self.session.path, timeout=0)["seq"], 1)
        event = self.waiter.wait_for_sketch(self.session.path, after=1, timeout=0)
        self.assertEqual(event["seq"], 2)
        self.assertEqual(Path(event["path"]).read_bytes(), self.png(0))

    def test_waiter_unblocks_on_button_submission(self):
        results = []
        thread = threading.Thread(target=lambda: results.append(self.waiter.wait_for_sketch(self.session.path, timeout=3)))
        thread.start()
        deadline = time.monotonic() + 2
        while not self.session.waiting() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(self.session.waiting())
        self.post_sketch(self.png())
        thread.join(timeout=4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]["status"], "submitted")
        self.assertFalse(self.session.waiting())

    def test_wrong_origin_or_token_does_not_submit(self):
        for headers in [{"Origin": "https://unrelated.example"}, {"X-Sketch-Token": "wrong-token"}]:
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as raised:
                self.post_sketch(self.png(), **headers)
            self.assertEqual(raised.exception.code, 403)
        self.assertEqual(list(self.session.events.glob("*.json")), [])

    def test_invalid_and_truncated_images_do_not_submit(self):
        for data in [b"not-a-png", self.png()[:-12], self.png() + b"trailing data"]:
            with self.subTest(size=len(data)), self.assertRaises(HTTPError) as raised:
                self.post_sketch(data)
            self.assertEqual(raised.exception.code, 400)
        self.assertEqual(list(self.session.events.glob("*.json")), [])

    def test_wrong_content_type_or_oversize_request_is_rejected(self):
        for headers, status in [({"Content-Type": "text/plain"}, 415),
                                ({"Content-Length": str(self.module.MAX_PNG_BYTES + 1)}, 413)]:
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as raised:
                self.post_sketch(b"fixture", **headers)
            self.assertEqual(raised.exception.code, status)

    def test_waiter_rejects_modified_reference(self):
        self.post_sketch(self.png())
        (self.session.directory / "sketch-0001.png").write_bytes(self.png(0))
        with self.assertRaisesRegex(ValueError, "changed on disk"):
            self.waiter.wait_for_sketch(self.session.path, timeout=0)

    def test_drawing_without_submission_never_creates_reference_event(self):
        (self.session.directory / "unsubmitted-draft.png").write_bytes(self.png())
        self.assertEqual(self.waiter.wait_for_sketch(self.session.path, timeout=0)["status"], "waiting")

    def test_resume_preserves_token_submission_identity_and_sequence(self):
        data = self.png()
        first = self.post_sketch(data)
        token = self.session.token
        restored = self.module.SketchSession(None, self.url + "/", resume=self.session.path)
        self.assertEqual(restored.token, token)
        self.server.sketch_session = restored
        self.assertEqual(self.post_sketch(data)["seq"], first["seq"])
        self.assertEqual(self.post_sketch(self.png(0), request_id="fixture-request-0002")["seq"], first["seq"] + 1)
        self.assertEqual(len(list(restored.events.glob("*.json"))), 2)

    def test_resume_rejects_changed_submitted_reference(self):
        self.post_sketch(self.png())
        (self.session.directory / "sketch-0001.png").write_bytes(self.png(0))
        with self.assertRaisesRegex(ValueError, "reference changed"):
            self.module.SketchSession(None, self.url + "/", resume=self.session.path)

    def test_restored_draft_is_private_and_does_not_submit(self):
        source = self.session.directory / "fixture.png"
        source.write_bytes(self.png(80))
        self.session.restore_draft(source)
        with urlopen(self.url + "/api/session", timeout=5) as response:
            self.assertTrue(json.load(response)["has_draft"])
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.url + "/api/draft", timeout=5)
        self.assertEqual(raised.exception.code, 403)
        request = Request(self.url + "/api/draft", headers={"X-Sketch-Token": self.session.token})
        with urlopen(request, timeout=5) as response:
            self.assertEqual(response.read(), source.read_bytes())
        self.assertEqual(self.waiter.wait_for_sketch(self.session.path, timeout=0)["status"], "waiting")

    def test_invalid_draft_does_not_replace_existing_drawing(self):
        source = self.session.directory / "fixture.png"
        source.write_bytes(self.png(80))
        self.session.restore_draft(source)
        source.write_bytes(b"invalid PNG")
        with self.assertRaises(ValueError):
            self.session.restore_draft(source)
        self.assertEqual((self.session.directory / "draft.png").read_bytes(), self.png(80))

    def test_head_matches_asset_length_without_body(self):
        with urlopen(Request(self.url + "/app.js?check=1", method="HEAD"), timeout=5) as response:
            self.assertEqual(response.read(), b"")
            self.assertEqual(int(response.headers["Content-Length"]), (self.skill / "assets/app.js").stat().st_size)

    def test_cli_announces_the_actual_available_loopback_port(self):
        process = subprocess.Popen([sys.executable, str(self.skill / "scripts/serve.py")],
                                   cwd=self.temporary.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # A bounded reader avoids hanging the suite if startup breaks.
            lines = []
            reader = threading.Thread(target=lambda: lines.append(process.stdout.readline()), daemon=True)
            reader.start()
            reader.join(timeout=5)
            self.assertTrue(lines, "Server did not announce a URL within five seconds")
            details = json.loads(lines[0])
            self.assertGreater(details["port"], 0)
            self.assertEqual(details["url"], f'http://127.0.0.1:{details["port"]}/')
            with urlopen(details["url"], timeout=5) as response:
                self.assertEqual(response.status, 200)
        finally:
            process.terminate()
            process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
