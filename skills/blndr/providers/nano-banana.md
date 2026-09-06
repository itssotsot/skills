# Google Nano Banana

Nano Banana is Google's Gemini image-generation family. This adapter uses the documented `generateContent` REST endpoint for generation and image-conditioned editing. The initial model is Nano Banana 2, `gemini-3.1-flash-image`; select another explicitly with `--model` or `SOTSOT_GEMINI_IMAGE_MODEL`. Model availability depends on the user's account.

Requires `GEMINI_API_KEY` in the calling process and separate Google API billing. Keep it out of chat, command-line arguments, repository files, and generated metadata.

```bash
python3 /path/to/skill/scripts/generate_reference.py --provider nano-banana --prompt-file /path/to/asset/prompts/head.txt --reference /path/to/asset/references/master.png --out /path/to/asset/references/head-v1.png
```

The command previews the request locally. Add `--execute` only for authorized API usage. For an edit, add `--intent edit` and put the current image first in the `--reference` inputs. Describe each input's role and the features to preserve.

The helper sends text and inline image data to `https://generativelanguage.googleapis.com/v1/models/<model>:generateContent` with the key in the `x-goog-api-key` header. It requests image/text output, skips any `thought` image parts, and requires exactly one final image. It saves provider usage metadata when present. No video, web-search grounding, or batch job is requested.

`--aspect-ratio` is an optional Nano Banana setting, passed as `generationConfig.responseFormat.image.aspectRatio`. Leave it unset if the chosen model doesn't support it. OpenAI's size and quality flags are rejected rather than ignored. Image inputs provide the context for each new request; the helper does not maintain a conversational session or claim exact cross-view consistency.

Inspect image identity, labels, proportions, and all requested views after every call. Preserve provider provenance/watermarks. Do not auto-switch from Nano Banana to OpenAI or to a different Gemini model after failure.

Documentation checked 2026-09-06: [Nano Banana generateContent guide](https://ai.google.dev/gemini-api/docs/generate-content/image-generation), [Gemini image models](https://ai.google.dev/gemini-api/docs/models). Google also exposes other API surfaces; changing this adapter's endpoint/payload requires verifying that surface's schema.
