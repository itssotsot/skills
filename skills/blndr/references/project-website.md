# Project website

Create the website during project setup, **before the first image or other asset is generated**. Open it immediately with useful empty states, then keep it current throughout the workflow. The website and its files belong in the asset project. Serve it locally by default using the available tools; public deployment is a separate user request. Reuse an existing project site when resuming work.

## Two separate pages

- **Assets:** the initial landing page. Start with an empty gallery explaining that generated assets will appear here. Add each saved artifact or small generation batch as it becomes available, without waiting for a complete reference pack or the model. Include concepts, component references, revisions, textures, model renders, animation previews, and downloadable model/export files as applicable. Group by stage, component, and version; show which version is current and retain access to earlier versions. Images need readable thumbnails and full-size viewing. Other files need clear labels and working download links.
- **Interactive Preview:** create this page and its navigation link at setup too. Until actual geometry exists, show a clear “Model not ready yet” state and a link to Assets. Once Blender modeling is authorized and a usable checkpoint exists, load an export of the actual model and label its version and work-in-progress status. Replace it with the validated final model when ready.

Keep navigation between the two pages available throughout. The Assets page must remain usable when the interactive model is pending or fails to load. Label concepts, references, and actual model renders accurately; a generated image is not an interactive 3D model. Gallery presence and review status do not constitute user approval. Continue the existing concept, scope, and complete-reference approval workflow.

## Interactive model behavior

Provide orbit, zoom, pan, useful camera views, and reset. For rigged models, expose the agreed rig controls where the browser can support them; for animated models, provide playback and clip selection for the agreed animations. Verify moving parts, axes, pivots, and clips against Blender. A successful geometry export does not prove that Blender drivers or constraints work in the browser: reproduce or bake the needed behavior and test it.

Keep the editable `.blend` authoritative. Create the browser export from a checkpoint or isolated copy and keep materials and dependencies portable. State material approximations and any control limitations. Show loading progress and actionable load errors inside the preview page.

## State and delivery

Record the site entry path, page paths, local URL, startup command, and current preview version in a top-level `website` field in `project.json`. Use project-relative artifact paths. This is output bookkeeping; do not change approved design inputs merely to update the website. The existing project helper preserves this field but does not build or validate the website for you.

Check that both pages open before generation, that a newly saved asset appears with a working full-size or download link, and that the empty preview does not prevent asset browsing. After adding the model, inspect actual browser geometry and exercise the relevant controls. Include the website, browser export, dependencies, and startup instructions in the final deliverables; record observed checks and limitations in `validation`.
