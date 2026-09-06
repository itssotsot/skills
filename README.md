# Skills

**[blndr](skills/blndr/SKILL.md)** is currently the only skill in this repository. It helps **Codex and Claude Code** create editable Blender models, with optional rigging and animation.

## How blndr works

Describe what you want to create. The agent asks focused questions about missing details, uses your answers to identify any remaining gaps, and repeats until the requirements are clear. This covers appearance, required parts, intended use, movement, and deliverables. It builds on earlier answers rather than asking the same questions again.

Once those details are settled, the agent develops a concept and component references for your review. You can request changes and repeat the review until you approve them. Only then does modeling begin in Blender, followed by checks of the finished asset and its controls.

A local website opens before generation starts. Its **Assets** page fills as images and files are created. A separate **Interactive Preview** page becomes a 3D viewer when model geometry is available, with the agreed rig or animation controls.

[Read the full blndr workflow →](skills/blndr/SKILL.md)

## Install blndr

Install it globally for Codex and Claude Code using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add itssotsot/skills --skill blndr --agent codex claude-code --global
```

## Use blndr

Type `$blndr` in Codex or `/blndr` in Claude Code, followed by your request.

## Examples

### Ferrari-inspired Formula One car

The starting request was:

> I want to create a red F1 Ferrari formula.

The agent clarified the delivery mode:

| Stage | Agent's question | User's answer |
| --- | --- | --- |
| Delivery mode | What should the Ferrari F1 model be prepared for? | Rigged model with steering and rotating wheels |

The options offered were:

1. Static display model with an editable `.blend` file (Recommended)
2. **Rigged model with steering and rotating wheels — selected**
3. Animated model—describe the motion you want

The result was an editable red Formula One car with front-wheel steering, independent wheel rotation, and a cockpit steering wheel that follows the front wheels. The project includes a gallery of generated concepts, component references, and model renders, plus an interactive 3D preview to orbit, zoom, steer, and spin the wheels.

## What you need

- Codex or Claude Code with local file and command access.
- Blender 4.5+ and Python 3.10+ with the [helper dependencies](skills/blndr/requirements.txt).
- Codex built-in image generation, or a configured OpenAI or Google Nano Banana API. API usage has separate costs; see [provider setup](skills/blndr/providers/README.md).

The generated files stay in your asset project folder.

[MIT License](LICENSE)
