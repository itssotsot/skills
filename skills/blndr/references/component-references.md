# Complete component references

## Inventory

Decompose the accepted design into meaningful modeling components. For a humanoid this may include head, torso, arms, hands, legs, feet, clothing layers, armor, hair, and accessories. Record left/right variants when they differ. For a prop, use its actual assemblies instead of anatomical categories. Do not turn every tiny bolt into a separate component unless it needs a distinct design decision.

Every inventoried component needs **front, back, left, right, top, and bottom** views before any Blender modeling. A six-view sheet may satisfy this if all panels are readable and inspected; map each view to its actual panel in project state. Do not claim one unlabelled angle covers six views. Bilateral symmetry may be documented, but do not silently omit a side from the required pack.

Add close-ups for hidden/interior geometry, grips, fastenings, joints, underside details, and attachment surfaces when the six views leave construction ambiguous. References do not have to be separate PNGs, but all requested coverage must exist.

## Keep the set coherent

- Supply the accepted whole-model design and relevant neighboring parts to each request.
- State the component's identity, scale relative to the whole, pose, orientation, palette, materials, and approved details.
- Use consistent view order and scale. Define “left/right” as the subject's left/right. Keep top/bottom views oriented consistently and label the intended front direction.
- Separate body, clothing, and armor references where needed to reveal underlying shape. Do not accidentally redesign occluded parts without review.
- Keep attachment dimensions/proportions compatible across neighbors. Add an assembled check sheet when needed; do not model missing details to discover what they should look like.
- Inspect identities across all views: count plates, match seams, compare lengths, distinguish front/back and both sides, verify accessories and any approved asymmetry.
- Resolve conflicts in generated images using targeted edits. The whole-model design is the anchor; images are design guides rather than measured engineering drawings.

## Prompt recipe

Use the selected provider's generation/edit conventions. Adapt this recipe rather than adding unrequested style:

```text
Use case: stylized-concept
Asset type: Blender component reference sheet
Input images: Image 1 is the approved whole-model design; Image 2 is the current component edit target, if present.
Primary request: Show [component] from front, back, anatomical left, anatomical right, top, and bottom.
Subject: [approved component appearance and attachment relationships]
Composition: Six separated, clearly identified views, neutral background, matching scale, no perspective exaggeration. Reveal the entire component in each view.
Lighting: Neutral, readable form and material boundaries; avoid dramatic shadows that hide geometry.
Constraints: Preserve approved proportions, colors, materials, silhouette, and asymmetry. Keep attachment points compatible with [neighbors]. No additional accessories or design changes.
For an edit: Change only [requested change]; keep [specific invariants] unchanged.
```

For complex components, separate calls per view can improve readability. Each call must use the same accepted reference inputs. More images are not proof of consistency.

## Coverage and review

Save each chosen artifact and its prompt/provider metadata in the asset project. Inspect with the host's image viewer before setting `reviewed: true` in `project.json`. The flag means the agent checked the image, not that the user approved it. Register panel locations for sheets. Keep discarded versions out of the active manifest without destroying them.

Run `project.py check` to report missing files/views while the pack is being built. Finish every component, review the completed pack with the user, then record reference approval. No geometry, armatures, blockouts, or material implementation should start while any planned reference remains unresolved.
