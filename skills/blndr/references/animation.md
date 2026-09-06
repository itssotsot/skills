# Rigging and animation

Read this during briefing for rigged/animated work, and again when implementation reaches the rig. Animation is an optional branch of the same skill, not a required extra package.

## Plan before references and modeling

Choose static, rigged-only, or animated delivery. For rigged/animated assets, establish anatomy/mechanics, rest pose, control expectations, weapon/prop attachments, facial requirements, and any target skeleton. For animation, agree the actual clip list, style/timing, frame rate, loops, root motion, and target engine/application. For rigid mechanisms or camera/prop motion, use object animation rather than forcing a humanoid skeleton.

Pose-reference sheets can clarify anticipation, contact, weight transfer, and recovery. Use the approved character and avoid redesigning it between poses. Pose images supplement the mandatory six-angle component pack; they do not replace it. Generate agreed pose references before building and include them in reference approval. Do not require a generated video or six-angle sheet for every animation frame.

The scope should say whether mocap/retargeting or an external asset source is wanted. Do not silently subscribe to services, import unlicensed animations, or assume a generic humanoid retarget will match the character.

## Rig and deformation

- Build the skeleton/control setup appropriate to the model. Keep a documented rest pose, axes, root, stable bone names, and attachment points.
- Weight flexible geometry so joints bend without collapsing; keep rigid plates and weapons rigid where intended. Automatic weights are only a starting point.
- Test bends, twists, raised arms, crouches, hand grips, and the most demanding agreed poses before producing clips. Inspect all sides for deformation and collisions.
- Confirm IK/FK or other controls behave as intended and that the export can represent the result. Bake constraint-driven motion when required by the destination format.
- Keep the editable control rig in the `.blend`, even when export requires a simplified/baked deformation skeleton.

## Clips and review

Create each agreed movement as an identifiable Blender action/clip. Record frame ranges, frame rate, loop behavior, root motion, and important contact/event frames in project state. Blender action APIs differ across versions; inspect the installed version before creating or assigning actions/slots.

Use clear key poses, then refine transitions and timing. Render **actual Blender motion previews**, view them with the available video tool, and sample critical frames when needed. If full playback inspection is unavailable, disclose that limitation and show contact sheets; do not claim fluid motion was verified from a single still.

Check:

- Foot/hand contact, weight, balance, foot sliding, grip stability, and prop attachment.
- Armor/cloth clearance throughout movement; no sudden joint collapse or unintended intersections.
- Loop seams in position, orientation, and velocity; check across the boundary, not only identical endpoint poses.
- Consistent root-motion conventions and scale across clips.
- User-requested transitions where they are part of scope. Creating isolated clips does not implement a game's animation state machine.

Show previews for user review and make scoped revisions. Do not regenerate design references for ordinary timing changes. Changes to appearance, anatomy, or required components return to the affected reference/approval stages.

## Export and handoff

For GLB/glTF, validate action selection and names, baked transforms, skeleton/weights, shape-key behavior if used, clip duration, and root motion. Unsupported Blender-only features must be baked/converted where possible or documented. Reimport exports and play every required clip; compare key poses with the source. If a target engine is available, test there too.

Deliver the editable rig and actions in the `.blend`, agreed exports, clip manifest, and actual previews. A rendered video is a preview, not the editable animation deliverable. Never claim “game-ready” from a successful export alone.

Sources: [Blender skinning](https://docs.blender.org/manual/en/latest/animation/armatures/skinning/parenting.html), [Blender actions](https://docs.blender.org/manual/en/latest/animation/actions.html), [glTF animation](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html).
