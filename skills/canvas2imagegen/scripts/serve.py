#!/usr/bin/env python3
"""Serve the sketchpad on loopback and accept explicit Use sketch submissions."""

import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets
import struct
import tempfile
import threading
import time
from urllib.parse import urlsplit
import webbrowser
import zlib

ASSETS = Path(__file__).resolve().parents[1] / "assets"
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
MAX_PNG_BYTES = 8 * 1024 * 1024


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_png(data):
    """Accept complete, bounded PNGs in the canvas's exported format."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The sketch must be a PNG image.")
    offset, header, compressed, ended = 8, None, bytearray(), False
    while offset + 12 <= len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("The PNG is incomplete.")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) != crc:
            raise ValueError("The PNG is damaged.")
        if offset == 8 and kind != b"IHDR":
            raise ValueError("The PNG header is missing.")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise ValueError("Invalid PNG header.")
            header = struct.unpack(">IIBBBBB", payload)
            width, height, depth, channels, compression, filtering, interlace = header
            if (not 1 <= width <= 4096 or not 1 <= height <= 4096 or width * height > 4194304
                    or depth != 8 or channels not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0)):
                raise ValueError("Send a supported PNG exported by this canvas.")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            ended = length == 0 and end == len(data)
            break
        offset = end
    if not header or not ended or not compressed:
        raise ValueError("The PNG is incomplete.")
    expected = (header[0] * (4 if header[3] == 6 else 3) + 1) * header[1]
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error as exc:
        raise ValueError("The PNG image data is damaged.") from exc
    if len(pixels) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid PNG image data.")


class SketchSession:
    def __init__(self, output_dir, url, resume=None):
        config = {}
        if resume:
            self.directory = Path(resume).resolve().parent
            config = json.loads(Path(resume).read_text())
            if config["session_id"] != self.directory.name:
                raise ValueError("Session identity does not match its directory.")
        else:
            output_dir = Path(output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            self.directory = Path(tempfile.mkdtemp(prefix="session-", dir=output_dir))
        self.events = self.directory / "events"
        self.events.mkdir(exist_ok=True)
        self.path = self.directory / "session.json"
        self.token = config.get("token") or secrets.token_urlsafe(32)
        self.url = url
        self.receipts = {}
        self.lock = threading.Lock()
        if resume:
            for event_file in sorted(self.events.glob("*.json")):
                event = json.loads(event_file.read_text())
                image = Path(event["path"]).resolve()
                if (event["session_id"] != self.directory.name or image.parent != self.directory
                        or hashlib.sha256(image.read_bytes()).hexdigest() != event["sha256"]):
                    raise ValueError("A submitted reference changed or belongs to another session.")
                if event["submission_id"] in self.receipts or event["seq"] <= 0:
                    raise ValueError("Invalid submission history.")
                self.receipts[event["submission_id"]] = event
        atomic_json(self.path, {"url": url, "session_id": self.directory.name, "token": self.token})
        self.path.chmod(0o600)

    def restore_draft(self, source):
        data = Path(source).read_bytes()
        if len(data) > MAX_PNG_BYTES:
            raise ValueError("Draft exceeds the canvas PNG size limit.")
        validate_png(data)
        (self.directory / "draft.png").write_bytes(data)

    def waiting(self):
        try:
            lease = json.loads((self.directory / "waiter.json").read_text())
            return lease["expires_at"] > time.time()
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def submit(self, request_id, data):
        digest = hashlib.sha256(data).hexdigest()
        with self.lock:
            existing = self.receipts.get(request_id)
            if existing:
                if existing["sha256"] != digest:
                    raise ValueError("This submission ID already belongs to a different sketch.")
                return existing
            validate_png(data)
            seq = max((event["seq"] for event in self.receipts.values()), default=0) + 1
            image = self.directory / f"sketch-{seq:04d}.png"
            image.write_bytes(data)
            receipt = {"status": "submitted", "session_id": self.directory.name,
                       "seq": seq, "submission_id": request_id, "path": str(image),
                       "sha256": digest, "bytes": len(data), "submitted_at": time.time()}
            # Publish the event only after the entire image is safely on disk.
            atomic_json(self.events / f"{seq:08d}.json", receipt)
            self.receipts[request_id] = receipt
            return receipt


class Handler(BaseHTTPRequestHandler):
    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def json_response(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        session = getattr(self.server, "sketch_session", None)
        route = urlsplit(self.path).path
        if route == "/api/session":
            self.json_response({"enabled": bool(session), "token": session.token if session else None,
                                "agent_waiting": session.waiting() if session else False,
                                "has_draft": bool(session and (session.directory / "draft.png").is_file())})
            return
        if route == "/api/draft":
            if not session or not secrets.compare_digest(self.headers.get("X-Sketch-Token", ""), session.token):
                self.send_error(403)
                return
            draft = session.directory / "draft.png"
            if not draft.is_file():
                self.send_error(404)
                return
            data = draft.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return
        self.serve_asset()

    def do_HEAD(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        self.serve_asset(head=True)

    def do_POST(self):
        session = getattr(self.server, "sketch_session", None)
        if urlsplit(self.path).path != "/api/sketch" or session is None:
            self.send_error(404)
            return
        if (not self.allowed_host() or self.headers.get("Origin") != session.url.rstrip("/")
                or not secrets.compare_digest(self.headers.get("X-Sketch-Token", ""), session.token)):
            self.json_response({"error": "Reopen this sketchpad from your chat and try again."}, 403)
            return
        request_id = self.headers.get("X-Submission-ID", "")
        if not re.fullmatch(r"[a-zA-Z0-9-]{16,80}", request_id):
            self.json_response({"error": "Invalid sketch submission ID."}, 400)
            return
        if self.headers.get("Content-Type") != "image/png":
            self.json_response({"error": "Only PNG sketches can be sent."}, 415)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if self.headers.get("Transfer-Encoding") or not 0 < length <= MAX_PNG_BYTES:
            self.json_response({"error": "The sketch is empty or too large."}, 413)
            return
        self.connection.settimeout(10)
        agent_waiting = session.waiting()
        try:
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("The sketch upload was interrupted. Try again.")
            receipt = session.submit(request_id, data)
        except (ValueError, TimeoutError) as exc:
            self.json_response({"error": str(exc)}, 400)
            return
        except OSError:
            self.json_response({"error": "The sketch could not be saved. Try again or use Download PNG."}, 500)
            return
        self.json_response({"status": receipt["status"], "seq": receipt["seq"],
                            "agent_waiting": agent_waiting or session.waiting()})

    def serve_asset(self, head=False):
        asset = FILES.get(urlsplit(self.path).path)
        if asset is None:
            self.send_error(404)
            return
        filename, content_type = asset
        data = (ASSETS / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="Local port; 0 chooses a free port")
    parser.add_argument("--open", action="store_true", help="Open the default browser")
    session_options = parser.add_mutually_exclusive_group()
    session_options.add_argument("--output-dir", type=Path, help="Enable Use sketch; save each session under this directory")
    session_options.add_argument("--resume", type=Path, help="Resume an existing session.json")
    parser.add_argument("--draft", type=Path, help="Restore a saved canvas PNG without submitting it")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if args.draft and not (args.output_dir or args.resume):
        parser.error("--draft requires --output-dir or --resume")
    if args.resume and args.port == 0:
        args.port = urlsplit(json.loads(args.resume.read_text())["url"]).port
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        details = {"url": url, "port": server.server_port}
        if args.output_dir or args.resume:
            server.sketch_session = SketchSession(args.output_dir, url, resume=args.resume)
            if args.draft:
                server.sketch_session.restore_draft(args.draft)
            details["session_file"] = str(server.sketch_session.path)
        print(json.dumps(details), flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
