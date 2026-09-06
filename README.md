# Skills

**[blndr](skills/blndr/SKILL.md)** is currently the only skill in this repository. It helps **Codex and Claude Code** create editable Blender models, with optional rigging and animation.

## How blndr works

Describe what you want to create. The agent develops a concept and component references for your approval, then builds and checks the model in Blender.

A local website opens before generation starts. Its **Assets** page fills as images and files are created. A separate **Interactive Preview** page becomes a 3D viewer when model geometry is available, with the agreed rig or animation controls.

[Read the full blndr workflow →](skills/blndr/SKILL.md)

## Install blndr

Install it globally for Codex and Claude Code using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add itssotsot/skills --skill blndr --agent codex claude-code --global
```

## Use blndr

Type `$blndr` in Codex or `/blndr` in Claude Code, followed by your request:

> Create a red F1-style car with steering and rotating wheels.

## What you need

- Codex or Claude Code with local file and command access.
- Blender 4.5+ and Python 3.10+ with the [helper dependencies](skills/blndr/requirements.txt).
- Codex built-in image generation, or a configured OpenAI or Google Nano Banana API. API usage has separate costs; see [provider setup](skills/blndr/providers/README.md).

The generated files stay in your asset project folder.

[MIT License](LICENSE)
