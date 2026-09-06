# Codex built-in image generation

When the current Codex environment has both the image tool and an installed `imagegen` skill, use that skill as the preferred path. Discover it through the host's skill catalog, read its actual `SKILL.md`, and follow current generation/editing rules. Do not hard-code a user's installation path or copy the system skill into this package.

For new whole-model proposals, generate a coherent multi-view sheet. For component views, supply the accepted master design as a reference. For revisions, supply the image being edited and preserve invariants; inspect local edit targets with the host's image viewer first. Use the built-in tool's supported image-reference mechanism.

The built-in path does not need `OPENAI_API_KEY`. Do not invoke this repository's API helper merely for output-path control. Generate with the built-in tool, then copy selected project-bound files into the user's asset project and preserve their alpha. Keep the prompt/provider metadata alongside them. Version edits rather than overwriting approved references.

Show outputs inline when supported, inspect the views, and update coverage. A failed/unavailable built-in tool is a missing capability, not permission to spend on an API. Explain the configured alternatives and use one only when selected by the user. If the user explicitly chooses the installed imagegen skill's own CLI fallback, follow that skill's bundled CLI instructions instead of substituting another client.
