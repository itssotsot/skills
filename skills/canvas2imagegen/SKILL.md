---
name: canvas2imagegen
description: Turn the user's sketch into a generated image in one conversation. Open a drawing canvas, receive its Use sketch submission without copy/paste, then automatically use imagegen to generate and refine the image. Use when the user mentions canvas2imagegen or wants to sketch a visual reference for image generation.
---

# Canvas2ImageGen

Own the complete sketch-to-image flow. The user mentions **$canvas2imagegen once**; this skill opens the sketchpad and automatically uses **imagegen** after the user supplies their drawing. Do not require a second skill mention or a separate request to start generation.

Carry the user's original description, requested style, and constraints across turns. The user does the drawing; do not substitute an agent-created sketch. If the user already supplied a sketch and a usable brief, go directly to generation. If they explicitly want only the drawing tool, honor that scope.

## Open the sketchpad

When the user still needs to draw, open the bundled app immediately. Keep any image brief they already provided; they can add details with the sketch instead of answering a questionnaire before the canvas opens.

Resolve this skill's installed directory from this file's location. Run the bundled Python 3 helper in a persistent shell session:

```bash
python3 "<skill-directory>/scripts/serve.py" --output-dir "<workspace>/output/canvas2imagegen"
```

The first stdout line is JSON containing the loopback `url`, selected `port`, and an absolute `session_file`. Use those returned values; the helper chooses a free port and a new session directory. Keep the server alive while the user draws. Reuse the server and session file opened for this request instead of replacing the user's tab. Do not reuse another task's drawing session.

If that helper must restart, `--resume "<session_file>"` retains its port, token, and submission history. Before refreshing a tab with an unsaved drawing, download its PNG; `--draft "<saved-PNG>"` restores that image when the refreshed page loads. This restores the drawing as one undoable image, fitting it without distortion when the viewport changes; the original per-stroke undo history is not retained. A restored draft is not a submission: wait for the user's Use sketch click as usual.

If Codex's `open_in_codex` tool is available, open the URL with `target: {type: "browser", url: "<returned-url>"}`. Otherwise use the environment's browser-opening tool, or start the helper with `--open` to open the default browser. Always provide a clickable URL as well.

The app in [assets/index.html](assets/index.html), [assets/style.css](assets/style.css), and [assets/app.js](assets/app.js) is plain HTML, CSS, and JavaScript. The helper uses only Python's standard library. Use sketch sends a PNG to this loopback helper, which saves the reference and a submission event under the returned session directory. It does not call a generation provider or insert a user message into the chat.

Without `--output-dir`, the helper provides drawing/copy/download only. A plain static host also supports those alternatives; direct handoff requires the local helper and an active agent wait. Follow the user's hosting scope rather than silently publishing the app.

## Receive the sketch

Tell the user: **Draw, then click Use sketch. I'll receive the drawing and generate the image here using your description.** Keep Copy image and Download PNG available as alternatives. Copy alone does not submit a reference. The unsent draft lives in the browser tab; submitted PNGs are saved in the workspace.

For a drawing-to-image invocation, **stay active while the user draws; do not end the turn after opening the canvas.** Run the bundled waiter in a shell tool:

```bash
python3 "<skill-directory>/scripts/wait_for_sketch.py" --session "<returned-session-file>" --after 0 --timeout 55
```

Use a yielding shell session so the user can keep interacting. A `status: "waiting"` result means only that the bounded wait expired: repeat the wait while the user is drawing. A `status: "submitted"` result contains the exact PNG `path`, `sha256`, and `seq`; proceed to imagegen immediately with that reference and the original brief. Remember the latest handled sequence and use `--after <seq>` if the user redraws in the same session. Repeated reads of a handled sequence do not authorize duplicate generation. Honor cancellation or changed scope from the user.

The waiter reads only explicit submission events, verifies the saved image's hash, and never inspects the canvas or clipboard. A file merely appearing elsewhere, a browser draft, or text saying "done" is not a submission. If the user supplies an attachment instead, continue with it without a separate imagegen mention. If no reference has arrived, keep waiting or explain the copy/attachment alternative. Test fixtures are never real user references or approvals.

If the current environment cannot keep the agent active across a wait, explain that Use sketch can save a queued reference but cannot wake a completed turn. Offer copy/paste instead of promising automatic continuation. When the user requests only a canvas or PNG, use the drawing-only mode and do not wait for or initiate generation.

## Generate and refine with imagegen

1. Resolve **imagegen** from the current environment's skill catalog, read its `SKILL.md` if not already loaded, and follow it automatically. Resolve the installed location dynamically; do not assume a sibling skill or a particular home directory. Imagegen owns provider selection, generation/edit workflow, output inspection, and delivery.
2. Use the user's actual sketch as an image input through the current tool's supported reference mechanism. For a supplied local file, inspect it with `view_image` first. For an attachment, include that conversation image in the generation call. Do not replace the reference with a text description, a screenshot of the drawing page, or a test fixture.
3. Build the generation prompt from the existing brief and the sketch's intended role. Preserve requested composition, object placement, proportions, and other stated constraints; use the requested visual style rather than assuming the rough pen marks are the final style. Ask a focused question only if missing meaning or direction materially blocks generation.
4. Generate using imagegen's built-in tool path by default. Mentioning this skill does not select a paid API/CLI provider. If imagegen is not installed but the built-in image-generation tool is available, use that tool directly with the same brief and reference. If neither is available, explain that generation is unavailable in this environment; keep the sketchpad usable and follow the user's provider choice rather than silently switching to a paid fallback.
5. Show the generated image and deliver/save it according to imagegen and the user's intended use. Continue requested refinements through imagegen in the same conversation. Reopen the sketchpad only if the user wants to redraw; do not send them through the drawing stage again for an ordinary text revision.

The agent performs generation after receiving the explicit Use sketch event or a user-supplied attachment. The page sends only its canvas PNG to the local helper; it never calls a model or attaches clipboard contents by itself.

## Runtime details

- Copy writes an opaque PNG from the canvas during the user's click. Browser clipboard rules require a secure context and may require permission; the helper uses loopback HTTP. On an unsupported embedded browser, offer the same URL in a normal browser or PNG download.
- The drawing surface fills the area below the toolbar without gutters. PNG dimensions follow its aspect ratio, with the longest side at 1200 pixels. Resizing fits existing artwork without stretching it; the entire surface remains drawable. The white background is included in the PNG; toolbar and page chrome are excluded.
- Pen, eraser, fill bucket (F), line, rectangle, ellipse, colors, stroke size, undo, redo, and undoable clearing are included. Fill colors the connected area under a click using the selected ink; close outlines to contain it. Mouse, touch, and stylus use pointer events.
- Do not rebuild the interface on every invocation. Edit the bundled app only when the user requests a change or a reproduced failure needs a fix.
