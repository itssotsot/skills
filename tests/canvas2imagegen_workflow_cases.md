# Canvas2ImageGen conversation checks

Forward-test `skills/canvas2imagegen/SKILL.md` using an independent evaluator with mocked browser, attachment, and image-generation tools. Supply each user turn in order. Record chosen tools, the generation prompt, reference identity, and whether execution waits. No provider calls or real user approvals are part of these tests. Give the evaluator the user turns and available capabilities before comparing its trace with the checks below.

## Brief, then a Use sketch click

1. User: `$canvas2imagegen I want a watercolor lighthouse on a rocky island, with the tower on the left and sunset behind it.`
2. Mock helper returns a URL and a session file; two bounded waiter calls return `status: "waiting"`.
3. User clicks Use sketch, without sending a chat message. The next wait returns a submission with a local PNG path, matching hash, and sequence `1`.

Check that the agent opens the canvas and stays active through both expired waits. It inspects the exact submitted PNG, loads imagegen, and generates using the original brief without another skill mention or confirmation. A repeated event with sequence `1` must not generate again; subsequent redraw waits use `--after 1`.

## Brief, then an image-only reply

1. User: `$canvas2imagegen I want a watercolor lighthouse on a rocky island, with the tower on the left and sunset behind it.`
2. User: attachment `lighthouse-sketch.png`, with no text.

Check that the first turn opens the sketchpad and waits. The second loads imagegen and generates using the supplied attachment and the original watercolor/composition brief, without another skill mention or confirmation.

## Completion text without an attachment

1. Same lighthouse request.
2. User: `done`, with no attachment.

Check that the agent tells the user to click Use sketch or attach the PNG and continues bounded waiting. It does not generate, read the clipboard, or inspect the browser canvas to guess completion.

## Existing sketch, then a text refinement

1. User: `$canvas2imagegen turn this attached sketch into a polished clay render`, with `chair-sketch.png` attached.
2. Mock imagegen returns `chair-render.png`.
3. User: `Make the chair blue.`

Check that the first turn generates from the supplied sketch without opening an unnecessary canvas. The refinement edits the generated chair image using imagegen in the same conversation, preserving the requested clay style and other content.

## Drawing-only scope

1. User: `$canvas2imagegen just open the canvas; I only need a PNG today.`
2. User: a sketch attachment, without a new generation request.

Check that the agent opens the sketchpad and supports PNG delivery but does not invoke a generation provider.

## Generation unavailable

1. The environment has neither imagegen nor a built-in image-generation tool; no API provider has been selected.
2. User requests a generated image from a supplied sketch using `$canvas2imagegen`.

Check that the agent identifies the unavailable generation capability, keeps sketchpad/export access available, and does not silently select a paid fallback or claim a generated result.

## Waiting is unavailable

1. The environment cannot keep the agent active across shell waits.
2. User requests the sketch-to-image flow.

Check that the agent explains that Use sketch can save a queued reference but cannot wake a completed turn. It offers copy/paste or attachment and never promises automatic continuation after ending its turn.
