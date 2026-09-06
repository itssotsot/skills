# It's Sotsot Skills

A collection of reusable skills for **Codex and Claude Code**. Install each skill independently.

## Skills

| Skill | What it does |
| --- | --- |
| [blndr](skills/blndr/SKILL.md) | Creates editable Blender assets from approved visual references, with optional rigging and animation, an asset gallery, and an interactive 3D preview. |

## Install

Install `blndr` for both agents using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add itssotsot/itssotsotskills --skill blndr --agent codex claude-code --global
```

To install from a local checkout, replace `itssotsot/itssotsotskills` with `.`.

## Use

Invoke `$blndr` in Codex or `/blndr` in Claude Code, followed by your request. Example:

> Create a red F1-style car with steering and rotating wheels.

The agent helps you approve the design and complete component references before modeling in Blender.

It opens a local website **before generating any assets**. The **Assets** page fills as images and files are created. A separate **Interactive Preview** page becomes a working 3D viewer when the model is ready, with the agreed rig or animation controls.

## Requirements

- Codex or Claude Code with local file access and command execution.
- Blender 4.5+.
- Python 3.10+ with the [helper dependencies](skills/blndr/requirements.txt).
- An image provider: Codex built-in image generation, or a configured OpenAI or Google Nano Banana API. API usage has separate costs. See [provider setup](skills/blndr/providers/README.md).

Generated assets stay in your project folder, outside the installed skill.

[MIT License](LICENSE)
