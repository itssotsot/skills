---
name: blndr
description: Design and build editable Blender assets through user-approved concepts and all-angle component references, with optional rigging, animation, and export validation. Use for new assets or substantial visual redesigns; routine Blender fixes do not need a new concept workflow.
---

# blndr

Guide a user from an idea to an editable Blender asset, with a project website for generated assets and interactive model inspection. This is one skill for Codex and Claude Code. Use the tools actually available; do not invent image-generation or Blender capabilities.

## Begin or resume

Read the user's existing prompt and project state before asking questions. Keep project artifacts outside this installed skill. Resolve helper paths relative to this `SKILL.md`; do not assume an installation directory, shell, or agent-specific tool name.

- New project: use [project-state.md](references/project-state.md) and `scripts/project.py init <project-dir> --name <asset-name>`.
- Existing project: inspect `project.json`, current references, approvals, and last `.blend` checkpoint. Confirm state against files before continuing. A change to approved inputs invalidates the affected approval fingerprints.
- Routine edits to an existing asset: preserve the authorized scope. Do not force an entire redesign or claim new approvals. Use the modeling/animation references as relevant.

For a new project, read [project-website.md](references/project-website.md) and **create and open the project website before generating the first asset**. Provide separate **Assets** and **Interactive Preview** pages from the start. Populate Assets incrementally as files are generated; activate the interactive page when actual model geometry is available. Do not wait for images, a complete reference pack, or a finished model to create the website. On resume, reuse and update the existing site.

Use [design-and-approval.md](references/design-and-approval.md) during briefing and review. Ask compact questions only about missing decisions that affect the outcome: appearance, proportions, materials, required parts, intended use, scale, deliverables, and **static / rigged / animated** mode. For animated work, read [animation.md](references/animation.md) now to establish clips and movement constraints before references or geometry.

## Required order for a new model

1. **Brief and website.** Record the user's requirements and agreed defaults. Do not invent extras from an example such as “samurai.” Initialize and open the website with empty states before asset generation. Check local Python/Blender and provider availability without creating geometry or invoking paid generation.
2. **Whole-model concept.** Choose a provider with [providers/README.md](providers/README.md). Generate or accept front, side, back, and three-quarter concept views of one coherent design. Show the images, label them as concepts, and revise the existing design until the user approves it.
3. **Final additions.** Show the accepted design and proposed component/deliverable list. Ask whether anything should be added or changed before building. A reply that already says “nothing else, proceed” satisfies this step. Record scope approval and update the list if needed.
4. **Complete component reference pack.** Before **any Blender modeling, including blockout**, follow [component-references.md](references/component-references.md). Generate front, back, left, right, top, and bottom references for **every planned component**. Add attachment details and animation pose sheets where useful. Finish the entire pack before moving to Blender; do not generate missing parts just in time during construction.
5. **Reference review.** Inspect every image for coverage and consistency, resolve contradictions, and show the entire pack in manageable review groups. Apply requested revisions. Obtain explicit approval of the completed pack and permission to proceed. Record the actual user statement, never an inferred or invented approval.
6. **Modeling gate.** Run `scripts/project.py check <project-dir> --ready-to-model`, then `scripts/project.py start-modeling <project-dir>`. Both require current concept, scope, and complete-pack approvals. The check verifies files and fingerprints, not visual correctness or the truth of a quoted statement; the agent remains responsible for those.
7. **Build and inspect.** Read [blender-workflow.md](references/blender-workflow.md). Build proportions first, then detail, materials, and topology. Inspect **actual Blender renders** against the approved references at useful milestones. For rigged/animated delivery, follow [animation.md](references/animation.md); validate the rig before creating the agreed clips.
8. **Deliver.** Save versioned `.blend` checkpoints, dependencies, requested exports, and previews. Finish both website pages, including the interactive model viewer and complete asset gallery. Reopen outputs and test relevant behavior, browser controls, and asset links. Update `deliverables` and `validation` in state, including known limitations. Claim completion only when the agreed deliverables have actually been checked.

Do not equate silence, successful image generation, or an agent's own inspection with user approval. User instructions can explicitly change the workflow; record the change rather than silently weakening it. The supplied gate deliberately has no automatic “skip references” switch.

## Images and construction

- Image providers supply concept/reference images and, when appropriate, texture sources. They do not produce editable Blender geometry or skeletal animation through this skill.
- Use approved whole-model images as inputs for component generation; when editing, supply the current target and explicitly preserve unchanged features. Do not regenerate each view from text alone.
- Named reference components are a planning breakdown, not a command to create disconnected body meshes. Choose construction that supports shape, assembly, and required deformation.
- Generated views are not exact CAD projections. Check silhouette, proportions, left/right identity, material boundaries, and connections before using them as specifications.
- Keep image-provider changes explicit. Native Codex generation is preferred when its installed imagegen skill is available. Read that skill and follow its current instructions. API fallback is a separately configured path, never an automatic substitute for a failed built-in call.
- Never present a generated concept image as a render of the built model, or an AI video as editable Blender animation.

## Tool use and boundaries

Helpers provide bookkeeping, image API access, rendering, and scene inspection. They are not universal automatic character modeling, rigging, retopology, or animation algorithms. Write task-specific Blender Python or use an available Blender connection, inspect results, and state limitations honestly. Do not replace the requested style with primitives and call it complete.

Normal scripts require Python 3.10+ and the skill's [requirements.txt](requirements.txt). Blender scripts run through Blender's bundled Python; they do not require Pillow. Use `--python-exit-code 1` so Python failures reach the caller. Check the installed Blender version and consult matching official docs for version-dependent APIs.

Keep prompts, images, metadata, approvals, and checkpoints in the user's project. Use versioned filenames; do not overwrite approved assets. Preview all user-facing images with the host's available viewer. If image tools, credentials, Blender, or a required viewer are missing, explain the exact missing capability and continue only work that does not depend on it. Never pretend the entire workflow ran.
