# Design and approval

## Brief without an interrogation

Summarize answered requirements first. Ask one compact group of missing questions, with suggested defaults when useful. Establish:

- Visual style, proportions, palette, materials, must-have/must-avoid features, supplied references.
- Use: game/runtime, cinematic render, illustration, printing, or another purpose; target engine or application if known.
- Scale, modeling detail, performance/triangle/texture constraints when relevant.
- Delivery mode: static, rigged, or animated. Required file formats and dependencies.
- For movement: clips, timing/style, contact points, clothing and rigid-part clearance; see [animation.md](animation.md).

Do not demand technical numbers from a user who only knows the desired appearance. Propose appropriate constraints and record assumptions. Do not generate a large reference pack while the basic direction remains unsettled.

## Whole-model concept

Use a single master design with front, side, back, and three-quarter views. A sheet is useful for a first proposal, but check that each panel describes the same object. For an asymmetric model, distinguish anatomical left/right from the viewer's left/right. Use a neutral background and lighting that reveals form, with a consistent neutral/rest pose.

Save the prompt and selected images as versions in the asset project. Label input roles: approved master, edit target, material reference, or supporting detail. Keep requested revisions narrow and restate the invariants. Show the result; ask for design approval only after there is something concrete to approve.

## Approval stages

1. **Concept**: the appearance and whole-model views are accepted.
2. **Scope**: the user has had the chance to add requirements and accepts the planned parts and deliverables. The question is: “Before I start building, is there anything else you want to add or change?” Clarify that the complete part references still come first.
3. **References**: all component views are present, inspected, consistent, and accepted; the user has authorized starting Blender work.

These are persisted decisions, not an obligation to ask the same question repeatedly. One explicit statement may satisfy multiple stages when the user has actually seen the corresponding artifacts and scope. A “looks good” about the whole-model concept does not approve unseen component references. Review the complete pack in batches if necessary, then summarize what is approved and what remains.

Use `project.py approve` only after receiving the relevant user statement. Store its exact wording and a message locator (message ID, timestamp, or an unambiguous description). The helper records fingerprints but cannot authenticate the speaker. Do not auto-approve artifacts in scripts, after elapsed time, or because a test fixture says approved.

If revisions change an approved decision, refresh only affected approvals. Updated part images invalidate the complete reference pack; a changed component list or animation requirement also invalidates scope. If the user requests changes after modeling begins, preserve the old checkpoint, revise the affected inputs, and recheck before continuing work that depends on them.
