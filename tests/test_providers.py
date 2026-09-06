import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from test_workflow import module

generation = module("generation", "generate_reference.py")


class ProviderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "prompt.txt").write_text("Show the approved helmet from all six angles.")
        image = io.BytesIO()
        Image.new("RGBA", (32, 32), (24, 50, 90, 128)).save(image, format="PNG")
        self.image = image.getvalue()
        self.encoded = base64.b64encode(self.image).decode()
        (self.root / "reference.png").write_bytes(self.image)

    def args(self, provider="openai", *extra):
        return generation.parser().parse_args(["--provider", provider, "--prompt-file", str(self.root / "prompt.txt"),
                                              "--out", str(self.root / "output.png"), *extra])

    def test_dry_run_never_calls_transport_or_creates_output(self):
        with patch.object(generation, "request_json") as transport, patch.dict(os.environ, {}, clear=True):
            result = generation.run(self.args())
        transport.assert_not_called()
        self.assertTrue(result["dry_run"])
        self.assertFalse((self.root / "output.png").exists())

    def test_openai_generation_and_edit_endpoints_and_file_bytes(self):
        args = self.args()
        generation.validate_args(args)
        url, body, content_type = generation.build_request(args, "test", [])
        self.assertTrue(url.endswith("/images/generations"))
        self.assertEqual(json.loads(body)["n"], 1)
        ref = generation.read_reference(self.root / "reference.png")
        url, body, content_type = generation.build_request(args, "keep armor", [ref])
        self.assertTrue(url.endswith("/images/edits"))
        self.assertIn(b'name="image[]"', body)
        self.assertIn(self.image, body)
        self.assertNotIn(b"input_fidelity", body)
        self.assertIn("multipart/form-data", content_type)

    def test_nano_banana_reference_payload(self):
        args = self.args("nano-banana", "--aspect-ratio", "3:2")
        generation.validate_args(args)
        ref = generation.read_reference(self.root / "reference.png")
        url, body, _ = generation.build_request(args, "test", [ref])
        payload = json.loads(body)
        self.assertIn("gemini-3.1-flash-image:generateContent", url)
        self.assertEqual(payload["contents"][0]["parts"][1]["inlineData"]["data"], self.encoded)
        self.assertEqual(payload["generationConfig"]["responseFormat"]["image"]["aspectRatio"], "3:2")

    def test_nano_banana_skips_thought_images(self):
        response = {"candidates": [{"content": {"parts": [
            {"thought": True, "inlineData": {"data": "invalid-hidden-image"}},
            {"text": "result"}, {"inlineData": {"mimeType": "image/png", "data": self.encoded}}
        ]}}]}
        output = generation.decode_image("nano-banana", response)
        with Image.open(io.BytesIO(output)) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 128)

    def test_execute_saves_image_metadata_and_no_secret(self):
        response = {"data": [{"b64_json": self.encoded}], "usage": {"total_tokens": 12}}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-secret"}), \
                patch.object(generation, "request_json", return_value=(response, "test-request")) as transport:
            result = generation.run(self.args("openai", "--execute"))
        self.assertFalse(result["dry_run"])
        transport.assert_called_once()
        metadata = (self.root / "output.json").read_text()
        self.assertNotIn("unit-test-secret", metadata)
        self.assertEqual(json.loads(metadata)["usage"]["total_tokens"], 12)
        self.assertTrue((self.root / "output.png").exists())
        self.assertFalse((self.root / "output.request.lock").exists())

    def test_existing_output_prevents_billable_request(self):
        (self.root / "output.png").write_bytes(self.image)
        with patch.object(generation, "request_json") as transport:
            with self.assertRaisesRegex(ValueError, "already exists"):
                generation.run(self.args("openai", "--execute"))
        transport.assert_not_called()

    def test_uncertain_request_is_not_retried_and_leaves_marker(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unit-test-secret"}), \
                patch.object(generation, "request_json", side_effect=RuntimeError("uncertain")) as transport:
            with self.assertRaises(RuntimeError):
                generation.run(self.args("nano-banana", "--execute"))
        transport.assert_called_once()
        self.assertTrue((self.root / "output.request.lock").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            generation.run(self.args("nano-banana", "--execute"))

    def test_missing_credentials_do_not_call_transport(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(generation, "request_json") as transport:
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
                generation.run(self.args("nano-banana", "--execute"))
        transport.assert_not_called()

    def test_invalid_options_fail_before_network(self):
        cases = [("openai", "--size", "0x1024"), ("openai", "--intent", "edit"),
                 ("openai", "--aspect-ratio", "1:1"), ("nano-banana", "--quality", "high"),
                 ("nano-banana", "--model", "../../wrong")]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                generation.run(self.args(*args))

    def test_blocked_and_multi_output_responses_fail(self):
        for response in ({}, {"candidates": [{"content": {"parts": [{"text": "No image"}]}}]},
                         {"candidates": [{"content": {"parts": [{"inlineData": {"data": self.encoded}}]}}] * 2}):
            with self.subTest(response=response), self.assertRaises(ValueError):
                generation.decode_image("nano-banana", response)


if __name__ == "__main__":
    unittest.main()
