"""Run through Blender: render six orthographic views plus a three-quarter view."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution", type=int, default=768)
    parser.add_argument("--frame", type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not 64 <= args.resolution <= 4096:
        raise ValueError("resolution must be between 64 and 4096")
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty/new preview directory to preserve prior evidence")
    scene = bpy.context.scene
    if args.frame is not None:
        scene.frame_set(args.frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for instance in depsgraph.object_instances:
        obj = instance.object
        if obj.type == "MESH" and not obj.hide_render and obj.original.visible_get():
            points.extend(instance.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise ValueError("No visible mesh geometry to frame")
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    radius = max((high - low).length / 2, 0.01)
    camera_data = bpy.data.cameras.new("SotsotPreviewCamera")
    camera = bpy.data.objects.new("SotsotPreviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "WORLD"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("SotsotPreviewWorld")
    scene.world.color = (0.18, 0.18, 0.18)
    scene.render.resolution_x = scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    # Model faces -Y, +Z is up: anatomical left is +X.
    directions = {"front": (0, -1, 0), "back": (0, 1, 0),
                  "left": (1, 0, 0), "right": (-1, 0, 0),
                  "top": (0, 0, 1), "bottom": (0, 0, -1),
                  "three_quarter": (1, -1, 0.7)}
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"blender_version": bpy.app.version_string, "source_blend": bpy.data.filepath,
                "frame": scene.frame_current, "engine": scene.render.engine,
                "orientation": "+Z up, front faces -Y, anatomical left +X",
                "bounds": {"min": list(low), "max": list(high)}, "views": {}}
    for name, direction in directions.items():
        camera.location = center + Vector(direction).normalized() * radius * 4
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera_data.type = "ORTHO"
        camera_data.clip_start = max(radius / 1000, 0.0001)
        camera_data.clip_end = radius * 10
        bpy.context.view_layer.update()
        local = [camera.matrix_world.inverted() @ point for point in points]
        span = max(max(p[i] for p in local) - min(p[i] for p in local) for i in (0, 1))
        camera_data.ortho_scale = max(span, 0.01) * 1.18
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        manifest["views"][name] = {"path": f"{name}.png", "projection": "orthographic",
                                   "location": list(camera.location),
                                   "rotation": list(camera.rotation_euler),
                                   "ortho_scale": camera_data.ortho_scale}
    (out / "views.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_dir": str(out), "views": list(directions)}))


if __name__ == "__main__":
    main()
