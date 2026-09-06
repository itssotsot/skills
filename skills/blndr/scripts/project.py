#!/usr/bin/env python3
"""Portable project state and an explicit reference-approval gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

VIEWS = ("front", "back", "left", "right", "top", "bottom")
CONCEPT_VIEWS = ("front", "back", "side", "three_quarter")
STAGES = ("concept", "scope", "references")


def now():
    return datetime.now(timezone.utc).isoformat()


def initial_state(name):
    return {
        "schema_version": 1, "name": name, "phase": "brief",
        "brief": {"description": "", "style": "", "intended_use": "",
                  "delivery_mode": "static", "scale": "", "target": "",
                  "constraints": [], "deliverable_formats": ["blend"]},
        "concept": {"views": {}}, "components": [], "animations": [],
        "pose_references": [], "approvals": {}, "approval_history": [],
        "deliverables": [], "validation": [],
    }


def load(root):
    state = json.loads((root / "project.json").read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Expected a project object with schema_version 1")
    return state


def save(root, state):
    path = root / "project.json"
    temporary = root / f".project-{uuid.uuid4().hex}.json"
    try:
        temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def artifact(root, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("artifact path must be a nonempty relative string")
    rel = Path(value)
    if rel.is_absolute():
        raise ValueError("artifact paths must be relative to the project")
    result = (root / rel).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("artifact path escapes the project")
    if not result.is_file():
        raise ValueError(f"missing artifact: {value}")
    return result


def image_errors(root, entry, label):
    if not isinstance(entry, dict):
        return [f"{label}: missing image entry"]
    errors = []
    if entry.get("reviewed") is not True:
        errors.append(f"{label}: image has not been visually reviewed")
    if not isinstance(entry.get("panel"), str) or not entry["panel"].strip():
        errors.append(f"{label}: identify the panel, or use 'full image'")
    try:
        path = artifact(root, entry.get("path"))
        with Image.open(path) as im:
            if im.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("expected PNG, JPEG, or WebP")
            im.verify()
    except (ValueError, OSError, Image.DecompressionBombError) as exc:
        errors.append(f"{label}: {exc}")
    return errors


def view_errors(root, views, required, label):
    if not isinstance(views, dict):
        return [f"{label}: views must be an object"]
    errors, panels = [], set()
    for view in required:
        entry = views.get(view)
        errors.extend(image_errors(root, entry, f"{label}.{view}"))
        if isinstance(entry, dict):
            key = (str(entry.get("path")), str(entry.get("panel")))
            if key in panels:
                errors.append(f"{label}.{view}: a view must identify its own image or sheet panel")
            panels.add(key)
    return errors


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validation_errors(root, state, stage="references"):
    errors = []
    if not nonempty(state.get("name")):
        errors.append("name is required")
    brief = state.get("brief")
    if not isinstance(brief, dict):
        return errors + ["brief must be an object"]
    for key in ("description", "style", "intended_use"):
        if not nonempty(brief.get(key)):
            errors.append(f"brief.{key} is required")
    mode = brief.get("delivery_mode")
    if mode not in ("static", "rigged", "animated"):
        errors.append("brief.delivery_mode must be static, rigged, or animated")
    concept = state.get("concept", {})
    errors.extend(view_errors(root, concept.get("views") if isinstance(concept, dict) else None,
                              CONCEPT_VIEWS, "concept"))
    if stage == "concept":
        return errors
    for key in ("scale", "target"):
        if not nonempty(brief.get(key)):
            errors.append(f"brief.{key} is required; record an agreed default or 'not applicable'")
    formats = brief.get("deliverable_formats")
    if not isinstance(formats, list) or not formats or not all(nonempty(x) for x in formats):
        errors.append("brief.deliverable_formats must be a nonempty list of strings")
    parts = state.get("components")
    if not isinstance(parts, list) or not parts:
        errors.append("components must contain the complete planned part list")
        parts = []
    ids = set()
    for part in parts:
        if not isinstance(part, dict):
            errors.append("each component must be an object")
            continue
        part_id = part.get("id")
        if not isinstance(part_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", part_id):
            errors.append("component id must be a lowercase slug")
        elif part_id in ids:
            errors.append(f"duplicate component id: {part_id}")
        else:
            ids.add(part_id)
        if not nonempty(part.get("description")):
            errors.append(f"component {part_id}: description is required")
        if stage == "references":
            errors.extend(view_errors(root, part.get("views"), VIEWS, f"component {part_id}"))
    clips = state.get("animations", [])
    if not isinstance(clips, list):
        errors.append("animations must be a list")
        clips = []
    if mode == "animated" and not clips:
        errors.append("animated delivery requires agreed animation clips")
    if mode != "animated" and clips:
        errors.append("animation clips require animated delivery mode")
    names = set()
    for clip in clips:
        if not isinstance(clip, dict):
            errors.append("animation clip must be an object")
            continue
        name = clip.get("name")
        if not nonempty(name) or name in names:
            errors.append("animation names must be nonempty and unique")
        else:
            names.add(name)
        if not nonempty(clip.get("description")):
            errors.append(f"animation {name}: description is required")
        fps = clip.get("fps")
        if not finite_number(fps) or fps <= 0:
            errors.append(f"animation {name}: fps must be positive")
        start, end = clip.get("frame_start"), clip.get("frame_end")
        if not finite_number(start) or not finite_number(end) or end <= start:
            errors.append(f"animation {name}: frame_end must exceed frame_start")
        if not isinstance(clip.get("loop"), bool):
            errors.append(f"animation {name}: loop must be a boolean")
        if clip.get("root_motion") not in ("in_place", "traveling", "not_applicable"):
            errors.append(f"animation {name}: root_motion is required")
    poses = state.get("pose_references", [])
    if not isinstance(poses, list):
        errors.append("pose_references must be a list")
    elif stage == "references":
        for index, entry in enumerate(poses):
            errors.extend(image_errors(root, entry, f"pose_references[{index}]"))
    return errors


def with_hashes(root, obj):
    if isinstance(obj, dict):
        result = {key: with_hashes(root, value) for key, value in obj.items()}
        if "path" in obj:
            result["sha256"] = hashlib.sha256(artifact(root, obj["path"]).read_bytes()).hexdigest()
        return result
    if isinstance(obj, list):
        return [with_hashes(root, value) for value in obj]
    return obj


def fingerprint(root, state, stage):
    if stage == "concept":
        brief = state["brief"]
        inputs = {"name": state["name"], "brief": {k: brief.get(k) for k in
                  ("description", "style", "intended_use", "delivery_mode", "constraints")},
                  "concept": with_hashes(root, state["concept"])}
    elif stage == "scope":
        inputs = {"name": state["name"], "brief": state["brief"],
                  "components": [{k: v for k, v in part.items() if k != "views"}
                                 for part in state["components"]],
                  "animations": state.get("animations", [])}
    else:
        inputs = {"concept": fingerprint(root, state, "concept"),
                  "scope": fingerprint(root, state, "scope"),
                  "components": with_hashes(root, state["components"]),
                  "pose_references": with_hashes(root, state.get("pose_references", []))}
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def approval_errors(root, state, stages=STAGES):
    errors = []
    approvals = state.get("approvals", {})
    if not isinstance(approvals, dict):
        return ["approvals must be an object"]
    for stage in stages:
        entry = approvals.get(stage)
        if not isinstance(entry, dict) or not nonempty(entry.get("statement")) or not nonempty(entry.get("source")):
            errors.append(f"missing explicit user approval: {stage}")
        else:
            try:
                if entry.get("fingerprint") != fingerprint(root, state, stage):
                    errors.append(f"stale user approval: {stage}")
            except (ValueError, KeyError, TypeError, OSError):
                errors.append(f"cannot verify approval inputs: {stage}")
    return errors


def ready_errors(root, state):
    return validation_errors(root, state) + approval_errors(root, state)


def approve(root, state, stage, statement, source):
    if not nonempty(statement) or not nonempty(source):
        raise ValueError("Approval requires the actual user statement and its message locator")
    errors = validation_errors(root, state, stage)
    errors += approval_errors(root, state, STAGES[:STAGES.index(stage)])
    if errors:
        raise ValueError("\n".join(errors))
    approvals = state.setdefault("approvals", {})
    if stage in approvals:
        state.setdefault("approval_history", []).append({"stage": stage, **approvals[stage]})
    approvals[stage] = {"statement": statement.strip(), "source": source.strip(),
                        "recorded_at": now(), "fingerprint": fingerprint(root, state, stage)}
    save(root, state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("project", type=Path)
    init.add_argument("--name", required=True)
    check = sub.add_parser("check")
    check.add_argument("project", type=Path)
    check.add_argument("--ready-to-model", action="store_true")
    approval = sub.add_parser("approve")
    approval.add_argument("project", type=Path)
    approval.add_argument("--stage", choices=STAGES, required=True)
    approval.add_argument("--statement-file", type=Path, required=True)
    approval.add_argument("--source", required=True)
    start = sub.add_parser("start-modeling")
    start.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    root = args.project.resolve()
    try:
        if args.command == "init":
            if not args.name.strip():
                raise ValueError("name must be nonempty")
            root.mkdir(parents=True, exist_ok=True)
            with (root / "project.json").open("x", encoding="utf-8") as stream:
                json.dump(initial_state(args.name), stream, indent=2)
                stream.write("\n")
            for directory in ("references", "prompts", "models", "previews", "exports"):
                (root / directory).mkdir(exist_ok=True)
        else:
            state = load(root)
            if args.command == "approve":
                approve(root, state, args.stage, args.statement_file.read_text(encoding="utf-8"), args.source)
            else:
                require_ready = args.command == "start-modeling" or args.ready_to_model
                errors = ready_errors(root, state) if require_ready else validation_errors(root, state)
                if errors:
                    print(json.dumps({"ok": False, "errors": errors}, indent=2))
                    return 1
                if args.command == "start-modeling":
                    state["phase"] = "modeling"
                    state["modeling_started_at"] = now()
                    save(root, state)
        print(json.dumps({"ok": True, "command": args.command, "project": str(root)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
