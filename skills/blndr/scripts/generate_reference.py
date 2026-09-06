#!/usr/bin/env python3
"""Generate one reference with an explicitly selected API; dry-run by default."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

DEFAULT_MODELS = {"openai": "gpt-image-2", "nano-banana": "gemini-3.1-flash-image"}
MODEL_ENVS = {"openai": "SOTSOT_OPENAI_IMAGE_MODEL", "nano-banana": "SOTSOT_GEMINI_IMAGE_MODEL"}
KEY_ENVS = {"openai": "OPENAI_API_KEY", "nano-banana": "GEMINI_API_KEY"}
MIMES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_reference(path):
    data = path.read_bytes()
    if len(data) >= 50 * 1024 * 1024:
        raise ValueError(f"Reference exceeds 50 MiB: {path.name}")
    with Image.open(io.BytesIO(data)) as im:
        mime = MIMES.get(im.format)
        if mime is None:
            raise ValueError("References must be PNG, JPEG, or WebP")
        im.verify()
    return {"path": str(path.resolve()), "sha256": sha256(data), "mime": mime, "data": data}


def validate_args(args):
    if not args.model:
        args.model = os.environ.get(MODEL_ENVS[args.provider]) or DEFAULT_MODELS[args.provider]
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", args.model):
        raise ValueError("Model must be a model identifier, not a URL or path")
    if args.intent == "edit" and not args.reference:
        raise ValueError("--intent edit requires --reference; the first image is the edit target")
    if args.out.suffix.lower() != ".png":
        raise ValueError("--out must name a PNG file")
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")
    if len(args.reference) > 16:
        raise ValueError("At most 16 reference images are supported by this helper")
    if args.provider == "openai":
        if args.aspect_ratio:
            raise ValueError("--aspect-ratio is only for Nano Banana")
        if args.size != "auto":
            match = re.fullmatch(r"(\d+)x(\d+)", args.size)
            if not match:
                raise ValueError("--size must be auto or WIDTHxHEIGHT")
            width, height = map(int, match.groups())
            if args.model == "gpt-image-2":
                if (min(width, height) <= 0 or max(width, height) > 3840 or width % 16 or height % 16
                        or max(width, height) > 3 * min(width, height)
                        or not 655360 <= width * height <= 8294400):
                    raise ValueError("Invalid GPT Image 2 dimensions; see providers/openai.md")
    elif args.size != "auto" or args.quality != "auto":
        raise ValueError("--size and --quality are OpenAI-only settings")
    if args.aspect_ratio and not re.fullmatch(r"[1-9]\d*:[1-9]\d*", args.aspect_ratio):
        raise ValueError("--aspect-ratio must have the form 3:2")


def multipart(fields, references):
    boundary = "sotsot-" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for index, ref in enumerate(references):
        # Generated filenames keep untrusted local names out of MIME headers.
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[ref["mime"]]
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; '
                       f'filename="reference-{index}.{ext}"\r\nContent-Type: {ref["mime"]}\r\n\r\n').encode())
        chunks.extend((ref["data"], b"\r\n"))
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def build_request(args, prompt, references):
    if args.provider == "openai":
        fields = {"model": args.model, "prompt": prompt, "n": 1, "size": args.size,
                  "quality": args.quality, "output_format": "png"}
        if references:
            body, mime = multipart(fields, references)
            return "https://api.openai.com/v1/images/edits", body, mime
        return "https://api.openai.com/v1/images/generations", json.dumps(fields).encode(), "application/json"
    parts = [{"text": prompt}]
    parts.extend({"inlineData": {"mimeType": ref["mime"], "data": base64.b64encode(ref["data"]).decode()}}
                 for ref in references)
    config = {"responseModalities": ["TEXT", "IMAGE"]}
    if args.aspect_ratio:
        config["responseFormat"] = {"image": {"aspectRatio": args.aspect_ratio}}
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": config}
    return (f"https://generativelanguage.googleapis.com/v1/models/{args.model}:generateContent",
            json.dumps(body).encode(), "application/json")


def request_json(url, body, headers, timeout):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response), response.headers.get("x-request-id")
    except urllib.error.HTTPError as exc:
        # Never print raw provider bodies or request headers.
        raise RuntimeError(f"Provider returned HTTP {exc.code}; no retry or model switch was attempted") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("Network request did not complete; billing may be uncertain. No retry was attempted") from None


def decode_image(provider, response):
    if provider == "openai":
        data = response.get("data", [])
        if len(data) != 1 or not data[0].get("b64_json"):
            raise ValueError("Expected exactly one base64 image from OpenAI")
        encoded = data[0]["b64_json"]
    else:
        images = []
        for candidate in response.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if part.get("thought"):
                    continue
                inline = part.get("inlineData", part.get("inline_data"))
                if inline and inline.get("data"):
                    images.append(inline["data"])
        if len(images) != 1:
            raise ValueError("Expected exactly one final image from Nano Banana; response may be blocked or text-only")
        encoded = images[0]
    raw = base64.b64decode(encoded, validate=True)
    # Normalize the image container to PNG while preserving pixels and alpha.
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        if im.format not in MIMES:
            raise ValueError("Provider returned an unsupported image format")
        if im.format == "PNG":
            return raw
        normalized = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
        output = io.BytesIO()
        normalized.save(output, format="PNG")
        return output.getvalue()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=DEFAULT_MODELS, required=True)
    p.add_argument("--model")
    p.add_argument("--intent", choices=("generate", "edit"), default="generate")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--reference", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--size", default="auto")
    p.add_argument("--quality", choices=("auto", "low", "medium", "high"), default="auto")
    p.add_argument("--aspect-ratio")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--execute", action="store_true", help="Send one request using the explicitly selected provider")
    return p


def run(args):
    validate_args(args)
    prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Prompt file is empty")
    refs = [read_reference(path) for path in args.reference]
    url, body, mime = build_request(args, prompt, refs)
    out = args.out.absolute()
    sidecar = out.with_suffix(".json")
    lock = out.with_suffix(".request.lock")
    if any(path.exists() or path.is_symlink() for path in (out, sidecar, lock)):
        raise ValueError("Output, metadata, or request lock already exists; choose a new versioned filename")
    metadata = {"provider": args.provider, "model": args.model, "intent": args.intent,
                "endpoint": url, "prompt": prompt,
                "references": [{k: v for k, v in ref.items() if k != "data"} for ref in refs],
                "settings": {"size": args.size, "quality": args.quality, "aspect_ratio": args.aspect_ratio},
                "output": str(out)}
    if not args.execute:
        return {"dry_run": True, **metadata}
    key = os.environ.get(KEY_ENVS[args.provider], "").strip()
    if not key:
        raise ValueError(f"Set {KEY_ENVS[args.provider]} privately in the process environment before --execute")
    headers = {"Content-Type": mime}
    if args.provider == "openai":
        headers["Authorization"] = f"Bearer {key}"
    else:
        headers["x-goog-api-key"] = key
    out.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the destination before a billable call; never overwrite an existing file.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"created_at": datetime.now(timezone.utc).isoformat(), "provider": args.provider}))
    try:
        if out.exists() or sidecar.exists():
            raise ValueError("Destination appeared while reserving it; choose another filename")
        response, request_id = request_json(url, body, headers, args.timeout)
        data = decode_image(args.provider, response)
        metadata.update({"created_at": datetime.now(timezone.utc).isoformat(), "request_id": request_id,
                         "sha256": sha256(data), "usage": response.get("usage", response.get("usageMetadata"))})
        with out.open("xb") as stream:
            stream.write(data)
        with sidecar.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except Exception:
        # Preserve a failed/uncertain request marker so an accidental rerun cannot rebill silently.
        raise
    else:
        lock.unlink()
    return {"dry_run": False, "output": str(out), "metadata": str(sidecar), "provider": args.provider}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        print(json.dumps(run(args), indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, Image.DecompressionBombError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
