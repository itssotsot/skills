#!/usr/bin/env python3
"""Validate independently installable skill folders and local Markdown links."""
import ast
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    errors, count = [], 0
    skill_root = root / "skills"
    for folder in sorted(skill_root.iterdir()):
        if not folder.is_dir():
            continue
        count += 1
        entry = folder / "SKILL.md"
        if not entry.is_file():
            errors.append(f"{folder.name}: missing SKILL.md")
            continue
        body = entry.read_text(encoding="utf-8")
        front = re.match(r"\A---\n(.*?)\n---(?:\n|$)", body, re.S)
        if not front:
            errors.append(f"{folder.name}: missing YAML frontmatter")
            continue
        try:
            metadata = yaml.safe_load(front.group(1))
            name, description = metadata.get("name"), metadata.get("description")
            if name != folder.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name or "") or len(name) >= 64:
                errors.append(f"{folder.name}: invalid or mismatched name")
            if not isinstance(description, str) or not description.strip():
                errors.append(f"{folder.name}: description is required")
        except (yaml.YAMLError, AttributeError, TypeError):
            errors.append(f"{folder.name}: invalid frontmatter")
        for md in folder.rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
                if urlsplit(target).scheme or target.startswith("#"):
                    continue
                dest = (md.parent / unquote(target.split("#")[0])).resolve()
                if not dest.is_relative_to(folder.resolve()):
                    errors.append(f"{md.relative_to(root)}: link escapes independently installed skill: {target}")
                elif not dest.exists():
                    errors.append(f"{md.relative_to(root)}: broken link: {target}")
            if re.search(r"/Users/|/home/[^/< ]+/|TODO|\[INSERT", content):
                errors.append(f"{md.relative_to(root)}: machine path or unfinished scaffold")
        ui = folder / "agents/openai.yaml"
        if ui.exists():
            try:
                config = yaml.safe_load(ui.read_text(encoding="utf-8"))
                interface = config["interface"]
                if not 25 <= len(interface["short_description"]) <= 64:
                    errors.append(f"{folder.name}: UI description must be 25–64 characters")
                if f"${folder.name}" not in interface["default_prompt"]:
                    errors.append(f"{folder.name}: default prompt must invoke the skill")
            except (yaml.YAMLError, TypeError, KeyError):
                errors.append(f"{folder.name}: invalid optional Codex UI metadata")
    if not count:
        errors.append("No skills found")
    for source in list((root / "skills").rglob("*.py")) + list((root / "scripts").rglob("*.py")) + list((root / "tests").rglob("*.py")):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"{source.relative_to(root)}: {exc}")
    return count, errors


if __name__ == "__main__":
    count, errors = validate()
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Validated {count} skill(s); {len(errors)} error(s)")
    raise SystemExit(bool(errors))
