#!/usr/bin/env python3
"""Wait for an explicit Use sketch event; never inspect the canvas or clipboard."""

import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid


def wait_for_sketch(session_file, after=0, timeout=55):
    session_file = Path(session_file).resolve()
    config = json.loads(session_file.read_text(encoding="utf-8"))
    directory = session_file.parent
    lease = directory / "waiter.json"
    waiter_id = uuid.uuid4().hex
    deadline = time.monotonic() + timeout
    try:
        while True:
            temporary = directory / f"waiter-{waiter_id}.tmp"
            temporary.write_text(json.dumps({"id": waiter_id, "expires_at": time.time() + 5}))
            temporary.replace(lease)
            for path in sorted((directory / "events").glob("*.json")):
                event = json.loads(path.read_text(encoding="utf-8"))
                if event["seq"] <= after:
                    continue
                image = Path(event["path"]).resolve()
                if event["session_id"] != config["session_id"] or image.parent != directory:
                    raise ValueError("Sketch event does not belong to this drawing session.")
                if hashlib.sha256(image.read_bytes()).hexdigest() != event["sha256"]:
                    raise ValueError("The submitted sketch changed on disk.")
                return event
            if time.monotonic() >= deadline:
                return {"status": "waiting", "session_id": config["session_id"], "after": after}
            time.sleep(min(0.25, max(0, deadline - time.monotonic())))
    finally:
        try:
            if json.loads(lease.read_text())["id"] == waiter_id:
                lease.unlink()
        except (OSError, ValueError, KeyError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, type=Path, help="session_file returned by serve.py")
    parser.add_argument("--after", type=int, default=0, help="Last submission sequence already handled")
    parser.add_argument("--timeout", type=float, default=55, help="Wait in seconds, at most 55")
    args = parser.parse_args()
    if args.after < 0 or not 0 <= args.timeout <= 55:
        parser.error("--after must be nonnegative; --timeout must be between 0 and 55")
    print(json.dumps(wait_for_sketch(args.session, args.after, args.timeout)), flush=True)


if __name__ == "__main__":
    main()
