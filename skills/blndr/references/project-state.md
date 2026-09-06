# Project state and helper commands

`scripts/project.py` maintains a portable `project.json` in the **asset project**, not in the skill installation. Resolve the script relative to the skill's `SKILL.md`. All artifact paths in the manifest are relative to the asset project and must stay inside it.

Initialize:

```bash
python3 /path/to/skill/scripts/project.py init /path/to/asset --name samurai
```

It creates the manifest and `references/`, `prompts/`, `models/`, `previews/`, and `exports/` folders. Initialization never creates geometry and refuses to replace a manifest. Edit the JSON as the user supplies the brief, approves decisions, or changes scope. Unknown top-level fields are preserved for project-specific notes.

## Manifest fields

- `schema_version`: `1`.
- `name`: asset name; `phase`: current working phase.
- `brief`: `description`, `style`, `intended_use`, `delivery_mode` (`static`, `rigged`, `animated`), `scale`, `target`, `constraints`, `deliverable_formats`.
- `concept`: a `views` map with `front`, `back`, `side`, and `three_quarter`.
- `components`: nonempty list of objects with a unique `id`, `description`, `views` map for all six directions, and optional `details`/`attachments` notes.
- `animations`: clip specifications for animated mode. Each has unique `name`, `description`, positive `fps`, `frame_start`, `frame_end`, boolean `loop`, and `root_motion` (`in_place`, `traveling`, or `not_applicable`). No clips are required for static or rigged-only delivery.
- `pose_references`: optional list of image entries when pose sheets were agreed.
- `approvals`: populated by the helper with statements, source locators, timestamps, and input fingerprints.
- `deliverables`, `validation`: lists maintained during implementation and delivery. Record file paths, what was tested, actual results, limitations, and Blender version; do not fabricate tests.

An image entry looks like:

```json
{
  "path": "references/head-v2.png",
  "panel": "top row, left panel: front",
  "reviewed": true
}
```

`panel` is required (use `full image` for a single view). If one file is used for multiple views, give each a distinct real panel description. Review the entire sheet visually; a checksum cannot verify its geometry. Images must decode as PNG, JPEG, or WebP. Sidecar prompts/metadata should stay beside the images or in `prompts/`.

## Check and record decisions

```bash
python3 /path/to/skill/scripts/project.py check /path/to/asset
python3 /path/to/skill/scripts/project.py approve /path/to/asset --stage concept --statement-file /path/to/user-reply.txt --source "conversation message identifier"
python3 /path/to/skill/scripts/project.py approve /path/to/asset --stage scope --statement-file /path/to/user-reply.txt --source "conversation message identifier"
python3 /path/to/skill/scripts/project.py approve /path/to/asset --stage references --statement-file /path/to/user-reply.txt --source "conversation message identifier"
python3 /path/to/skill/scripts/project.py check /path/to/asset --ready-to-model
python3 /path/to/skill/scripts/project.py start-modeling /path/to/asset
```

Use the actual user reply, only for the scope it explicitly approves. `approve` is a record-writing helper, not an independent source of permission. It validates that the stage's prerequisites exist. It does not generate approval text. Store reply files in the private asset project, not in this repository.

The approval fingerprints include relevant manifest fields and referenced image bytes. Replacing a file at the same filename, changing a component, or changing the animation brief invalidates affected approval. Validation reports missing views, unreviewed images, malformed clip specifications, and stale/missing approval. `start-modeling` refuses to advance until ready.

These are workflow guardrails, not a security sandbox around Blender. A user can explicitly authorize a different process, but an agent must not bypass the gate just to get a passing result. Document intentional departures and their authorization separately; do not edit the validator or manufacture approval to conceal them.
