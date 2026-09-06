# Blender construction and delivery

## Start after reference approval

Complete the project readiness check before creating a blockout or other model geometry. Locate Blender through the user's configuration or `PATH`; record `blender --version`. The supplied helpers target Blender 4.5+ and are tested on 5.2 LTS. Check version-specific APIs when authoring task scripts.

Use local Blender Python as the shared default for Codex and Claude Code. An already available Blender connection is also acceptable. Save scripts, `.blend` checkpoints, and evidence in the asset project. Never reset an existing scene with factory settings unless the user authorized a fresh scene or you are working in an isolated new file.

## Construction

1. Establish units, dimensions, axes, neutral pose, and component names. The render helper assumes +Z up and a front-facing direction of -Y; align the model or account for this before comparison.
2. Build the overall silhouette and relative proportions. Use real geometry with thickness, back surfaces, and appropriate connections; do not substitute image planes for requested volumetric assets.
3. Inspect orthographic front/back/side/top/bottom renders against the references before fine detail.
4. Develop components and materials. Separate rigid parts when useful; retain connected deformation-friendly topology where the body or cloth needs it. Reference component boundaries need not equal mesh boundaries.
5. Implement UVs/textures, topology budgets, print constraints, or animation topology according to the brief. A generated material swatch is not automatically a seamless texture or calibrated PBR map; inspect seams, lighting baked into color, and map interpretation.
6. For rigged/animated delivery, continue with [animation.md](animation.md). For static assets, validate the agreed pose and geometry directly.

## Helper commands

Run a task-specific build script with reliable error reporting:

```bash
blender --background --python-exit-code 1 --python /path/to/asset/build_model.py
```

Render six orthographic views and one three-quarter view from a saved scene:

```bash
blender --background /path/to/asset/models/model-v1.blend --python-exit-code 1 --python /path/to/skill/scripts/render_views.py -- --output-dir /path/to/asset/previews/model-v1 --resolution 768
```

The helper frames visible evaluated mesh geometry at the current frame, uses a consistent workbench material-color preview, and writes a camera manifest. It does not modify the saved `.blend`. Pass `--frame 20` for another pose. Use a fresh output directory for each version. For final material/texture assessment, also render with the project's intended Eevee/Cycles lighting: the helper's workbench images cannot prove final shader quality.

Write a scene inventory:

```bash
blender --background /path/to/asset/models/model-v1.blend --python-exit-code 1 --python /path/to/skill/scripts/inspect_scene.py -- --output /path/to/asset/previews/model-v1/scene.json
```

The inventory includes transforms, evaluated triangle counts, bones, actions/frame ranges, materials, and external image dependencies. It is diagnostic evidence, not a quality certificate. Bounds include all visible meshes, so isolate the asset from unrelated scene geometry for reference renders.

## Delivery checks

- Reopen the actual `.blend`; ensure intended objects, modifiers, materials, and dependencies are present.
- Inspect the silhouette and details from every relevant side. Check normals, unwanted intersections, disconnected pieces, shading, scale, and origins according to intended use.
- For games, measure evaluated triangles and actual exported asset cost. For printing, check manifold/watertight geometry and physical wall thickness. Do not impose print constraints on every game mesh.
- Include textures as packed data or portable relative files. Verify no user-specific absolute path is needed to open the delivery.
- Export the format the user requested. Use current Blender export settings; include animations only when requested. Reimport the output into a fresh scene and inspect it. Test the target application when available; disclose if only Blender reimport was verified.
- For animation, check the actual exported clips using [animation.md](animation.md), not just the original rig.
- Deliver the editable `.blend`, dependencies, requested exports, actual model previews, and a short list of tested behavior and remaining limitations. Update the project manifest.

Primary documentation: [Blender Python API](https://docs.blender.org/api/current/), [command line](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html), [glTF export](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html). Consult the version matching the installed Blender before using changed API fields.
