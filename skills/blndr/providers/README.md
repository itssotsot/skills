# Image providers

Select an available provider before generating. Keep the selected provider, model, prompts, and reference lineage in each asset project. Provider selection is portable across Codex and Claude Code; never infer capability solely from the agent name.

| Provider | Requires | Guide |
| --- | --- | --- |
| Codex built-in | Built-in image tool and installed imagegen skill | [codex-imagegen.md](codex-imagegen.md) |
| OpenAI Images API | `OPENAI_API_KEY`, explicitly selected API usage | [openai.md](openai.md) |
| Google Nano Banana | `GEMINI_API_KEY`, explicitly selected API usage | [nano-banana.md](nano-banana.md) |

If no generation provider is usable, state the dependency and help the user configure one or accept user-supplied images. Do not create placeholder reference images and continue to Blender. A skill file does not supply a generation engine or credentials.

## Shared API helper

`scripts/generate_reference.py` is a reusable, agent-independent API client for the two configured API providers. It is separate from Codex's built-in imagegen tool. It never routes a failed built-in request to an API automatically.

Use `--provider openai` or `--provider nano-banana`, `--prompt-file`, `--out` (PNG), and repeat `--reference` for input images. `--intent edit` requires a reference; the first image must be the edit target, described as such in the prompt. With `--intent generate`, references can anchor a new angle or component.

The default is a **dry run**: it validates local inputs and prints request metadata without sending images or reading credentials. `--execute` makes one API request; use it only after the user has chosen that provider and authorized its use/cost. Existing authorization persists; do not ask on every image within the approved scope. Keys are read from environment variables, never command-line arguments or repository configuration. The helper does not provision keys or load arbitrary `.env` files.

Save prompts in the asset project's `prompts/` folder. The output includes a PNG and `.json` sidecar with prompt, model, input hashes, output hash, timestamp, and available usage/request metadata. Inspect the result and register it in `project.json`; successful generation never marks it approved. Container conversion to PNG preserves alpha and does not remove provenance marks.

Outputs are exclusive/versioned: choose a new filename for revisions. One request produces one deliverable; separate components require separate requests. The client does not automatically retry requests or switch models/providers, because a timed-out request may already have incurred a charge. Check provider state or ask before retrying an uncertain result. Provider error responses are not printed verbatim to avoid leaking credentials or private response content.

Do not promise API availability, pricing, exact projection consistency, texture readiness, or model access from a successful dry run. Routine repository tests mock API transport; live access is verified only when an actual authorized request succeeds.
