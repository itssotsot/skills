# It's Sotsot Skills

A collection of reusable agent skills for **Codex and Claude Code**. Each folder in `skills/` is one independently installable skill, including its own instructions, references, and helpers.

## Skills

| Skill | What it does |
| --- | --- |
| [blndr](skills/blndr/SKILL.md) | Takes an idea through approved concepts, all-angle references for every component, Blender modeling, optional rigging and animation, and export review. |

The Blender workflow uses Codex's installed imagegen skill when available, or an explicitly configured OpenAI or Google Nano Banana image API. Image providers create references; Blender creates the editable geometry and animation.

## Install

After this repository is published to GitHub, install the Blender skill into both agents using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add itssotsot/itssotsotskills --skill blndr --agent codex claude-code --global
```

Browse the collection without installing:

```bash
npx skills add itssotsot/itssotsotskills --list
```

For a local checkout, replace `itssotsot/itssotsotskills` with `.`. Alternatively, copy the **entire** `skills/blndr/` folder into your agent's personal skills directory: `~/.codex/skills/` for Codex or `~/.claude/skills/` for Claude Code. Do not install only `SKILL.md`.

Invoke `$blndr` in Codex or `/blndr` in Claude Code, followed by your request. Example:

> Create a stylized samurai for a game. Help me approve the design and all component references before building. I need a rig, an idle loop, and a sword attack.

The agent asks only about missing requirements. Concept approval, final additions, and approval of the complete component reference pack happen before Blender modeling. Static, rigged, and animated assets are different delivery modes of this **one skill**.

## Requirements

- Codex or Claude Code with local file access and command execution; this is not a standalone model generator.
- Python 3.10+ for the shared helpers. Install their dependency in an environment you control:

  ```bash
  python3 -m venv .venv
  .venv/bin/python -m pip install -r skills/blndr/requirements.txt
  ```

- Blender 4.5+ for modeling helpers; the actual Blender version and validation evidence are recorded in each project. Helper smoke tests have been exercised on Blender 5.2.0 LTS.
- An image provider: Codex built-in generation needs no API key. The API paths use `OPENAI_API_KEY` or `GEMINI_API_KEY` from the process environment and incur separate provider charges. Never commit credentials. See [provider setup](skills/blndr/providers/README.md).

Keep generated images, `.blend` files, exports, and project state in the **user's asset project**, outside the installed skill. No private machine paths or credentials belong in this repository.

## Development

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

Run the real Blender smoke test when Blender is available:

```bash
python3 tests/blender_smoke.py --blender blender
```

Tests use local fixtures and mocked HTTP responses. They do not call paid image APIs. A passing structural validator is not evidence that an arbitrary character will model or animate well: inspect actual references, geometry, deformation, and exported clips on each project.

To add another skill, add a self-contained `skills/<name>/SKILL.md` with `name` and `description` frontmatter, include only its necessary resources, and add it to the catalog above. Keep helpers within that skill's folder so individual installation works. CI discovers skill folders automatically.

## Distribution

GitHub hosts the collection; no npm package or server is required. Individual installation does not need a Claude plugin marketplace. A marketplace can be added later without changing the shared skill's source. Contributions are covered by the repository's MIT license; users must separately check rights for any third-party references or assets they supply.
