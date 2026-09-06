"""Run through Blender: write a read-only diagnostic scene inventory."""
import argparse
import json
import sys
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.output.exists():
        raise ValueError("Inspection output exists; choose a versioned filename")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = []
    for obj in bpy.context.scene.objects:
        item = {"name": obj.name, "type": obj.type, "location": list(obj.location),
                "rotation": list(obj.rotation_euler), "scale": list(obj.scale),
                "dimensions": list(obj.dimensions), "hide_render": obj.hide_render,
                "parent": obj.parent.name if obj.parent else None,
                "active_action": obj.animation_data.action.name
                if obj.animation_data and obj.animation_data.action else None,
                "nla_tracks": [track.name for track in obj.animation_data.nla_tracks]
                if obj.animation_data else [],
                "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers]}
        if obj.type == "MESH":
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                mesh.calc_loop_triangles()
                item.update({"vertices": len(mesh.vertices), "triangles": len(mesh.loop_triangles),
                             "materials": [m.name if m else None for m in obj.data.materials],
                             "vertex_groups": [g.name for g in obj.vertex_groups]})
            finally:
                evaluated.to_mesh_clear()
        if obj.type == "ARMATURE":
            item["bones"] = [{"name": b.name, "parent": b.parent.name if b.parent else None,
                              "deform": b.use_deform} for b in obj.data.bones]
        objects.append(item)
    images = []
    for image in bpy.data.images:
        if image.source in {"VIEWER", "GENERATED"}:
            continue
        path = bpy.path.abspath(image.filepath, library=image.library)
        packed = bool(image.packed_file or getattr(image, "packed_files", None))
        images.append({"name": image.name, "source": image.source, "path": image.filepath,
                       "packed": packed, "exists": bool(path and Path(path).is_file()),
                       "note": "Sequence and UDIM dependencies need per-file inspection"
                       if image.source in {"SEQUENCE", "TILED"} else None})
    report = {"blender_version": bpy.app.version_string, "source_blend": bpy.data.filepath,
              "frame": bpy.context.scene.frame_current,
              "fps": bpy.context.scene.render.fps / bpy.context.scene.render.fps_base,
              "units": bpy.context.scene.unit_settings.system,
              "scale_length": bpy.context.scene.unit_settings.scale_length,
              "objects": objects, "images": images,
              "actions": [{"name": a.name, "frame_range": list(a.frame_range),
                           "slots": [s.identifier for s in getattr(a, "slots", [])]}
                          for a in bpy.data.actions],
              "limitations": ["Inventory does not verify visual quality, rig deformation, or clip playback.",
                              "Triangle counts are per object, not expanded instance totals."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"ok": True, "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
