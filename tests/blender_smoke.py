#!/usr/bin/env python3
"""Exercise render/inventory helpers and animated GLB roundtrip with a local fixture."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/blndr/scripts"

BUILD = '''
import bpy, json, math, sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index("--") + 1])
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 24
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1))
mesh = bpy.context.object
mesh.name = "FixtureBody"
mesh.scale = (0.5, 0.3, 1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
material = bpy.data.materials.new("FixtureBlue")
material.diffuse_color = (0.06, 0.3, 0.8, 1)
mesh.data.materials.append(material)
bpy.ops.object.armature_add(location=(0, 0, 0))
rig = bpy.context.object
rig.name = "FixtureRig"
bone = rig.data.bones[0]
group = mesh.vertex_groups.new(name=bone.name)
group.add(list(range(len(mesh.data.vertices))), 1, "REPLACE")
modifier = mesh.modifiers.new("FixtureArmature", "ARMATURE")
modifier.object = rig
mesh.parent = rig
pose = rig.pose.bones[0]
pose.rotation_mode = "XYZ"
for frame, angle in [(1, 0), (12, 0.6), (24, 0)]:
    pose.rotation_euler.y = angle
    pose.keyframe_insert(data_path="rotation_euler", frame=frame)
rig.animation_data.action.name = "fixture-wave"
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 24
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(root / "fixture.blend"))
bpy.ops.export_scene.gltf(filepath=str(root / "fixture.glb"), export_format="GLB", export_animations=True)
'''

ROUNDTRIP = '''
import bpy, json, sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index("--") + 1])
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root / "fixture.glb"))
rigs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.visible_get() and not o.hide_render]
assert rigs and meshes, "GLB lost skeleton or mesh"
assert len(bpy.data.actions) > 0, "GLB lost animation"
samples = []
for frame in (1, 12, 24):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    coords = []
    for obj in meshes:
        evaluated = obj.evaluated_get(graph)
        evaluated_mesh = evaluated.to_mesh()
        coords.extend(evaluated.matrix_world @ v.co for v in evaluated_mesh.vertices)
        evaluated.to_mesh_clear()
    samples.append([min(p[i] for p in coords) for i in range(3)] + [max(p[i] for p in coords) for i in range(3)])
assert max(abs(a-b) for a,b in zip(samples[0], samples[1])) > 0.05, "Exported pose did not animate"
assert max(abs(a-b) for a,b in zip(samples[0], samples[2])) < 0.01, "Loop endpoint changed"
report = {"ok": True, "blender_version": bpy.app.version_string, "actions": [a.name for a in bpy.data.actions], "pose_bounds": samples}
(root / "roundtrip.json").write_text(json.dumps(report, indent=2))
'''


def run(blender, root):
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("Smoke output directory must be empty")
    (root / "build_fixture.py").write_text(BUILD)
    (root / "roundtrip.py").write_text(ROUNDTRIP)

    def blender_run(name, arguments):
        result = subprocess.run([blender, "--background", "--factory-startup", *arguments],
                                capture_output=True, text=True, timeout=180)
        (root / f"{name}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"Blender {name} failed; see {root / (name + '.log')}")

    blender_run("build", ["--python-exit-code", "1", "--python", str(root / "build_fixture.py"), "--", str(root)])
    blender_run("render", [str(root / "fixture.blend"), "--python-exit-code", "1", "--python",
                           str(SCRIPTS / "render_views.py"), "--", "--output-dir", str(root / "views"), "--resolution", "192"])
    blender_run("inspect", [str(root / "fixture.blend"), "--python-exit-code", "1", "--python",
                            str(SCRIPTS / "inspect_scene.py"), "--", "--output", str(root / "scene.json")])
    blender_run("roundtrip", ["--python-exit-code", "1", "--python", str(root / "roundtrip.py"), "--", str(root)])
    manifest = json.loads((root / "views/views.json").read_text())
    assert len(manifest["views"]) == 7
    for view in manifest["views"]:
        with Image.open(root / "views" / f"{view}.png") as im:
            assert im.size == (192, 192)
            assert max(ImageStat.Stat(im.convert("RGB")).stddev) > 3, f"Blank {view} preview"
    inventory = json.loads((root / "scene.json").read_text())
    mesh = next(obj for obj in inventory["objects"] if obj["name"] == "FixtureBody")
    assert mesh["triangles"] == 12
    assert any(obj.get("bones") for obj in inventory["objects"])
    assert any(a["name"] == "fixture-wave" for a in inventory["actions"])
    print(json.dumps({"ok": True, "blender_version": inventory["blender_version"],
                      "checks": ["seven nonblank renders", "mesh and rig inventory", "animated GLB roundtrip"],
                      "evidence": str(root)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir:
        run(args.blender, args.output_dir.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="sotsot-blender-smoke-") as directory:
            run(args.blender, Path(directory))
