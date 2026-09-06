# OpenAI Images API

This adapter supports generation and reference-based editing through OpenAI's Images API. The initial model is `gpt-image-2`; override it explicitly with `--model` or `SOTSOT_OPENAI_IMAGE_MODEL` when the user chooses another model. Never silently downgrade after failure.

Requires `OPENAI_API_KEY` in the calling process and separate API billing. Configure credentials privately when running the skill; do not paste them into chat, pass them as CLI arguments, or store them in the skill. No credential is needed for dry runs or mocked repository tests.

```bash
python3 /path/to/skill/scripts/generate_reference.py --provider openai --prompt-file /path/to/asset/prompts/head.txt --reference /path/to/asset/references/master.png --out /path/to/asset/references/head-v1.png
```

After checking the request and authorized usage, add `--execute`. Revisions use `--intent edit --reference /path/to/current-head.png` first, then any supporting reference images.

Requests without images use `POST /v1/images/generations`. Requests with images use `POST /v1/images/edits`, including new reference-guided angles; the prompt still distinguishes new generation from a targeted edit. Input images are sent as multipart `image[]` files. The helper requests one PNG and decodes `data[0].b64_json`.

OpenAI-only options: `--size` (default `auto`) and `--quality` (default `auto`). The helper checks GPT Image 2 dimensions before execution: multiples of 16, maximum edge 3840, ratio at most 3:1, and area 655360–8294400 pixels. It does not set `input_fidelity`, a transparency parameter, or legacy response-format flags. The helper has no mask interface; use a separately authorized tool if precise mask support is required.

Preserve the exact prompt and image invariants across edits. This API path is not Codex's built-in image tool. Native generation remains preferred in Codex unless the user selects the API path.

Documentation checked 2026-09-06: [image generation and edits](https://developers.openai.com/api/docs/guides/image-generation), [Images API reference](https://developers.openai.com/api/reference/resources/images). Consult current model documentation before changing model-specific options.
