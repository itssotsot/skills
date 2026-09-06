import copy
import contextlib
import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/blndr/scripts"


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


project = module("project", "project.py")


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        Image.new("RGB", (64, 64), "navy").save(self.root / "fixture.png")
        self.state = project.initial_state("test-fixture")
        self.state["brief"].update(description="Offline test asset", style="simple", intended_use="test",
                                     scale="one meter", target="Blender")
        self.state["concept"]["views"] = self.views(project.CONCEPT_VIEWS)
        self.state["components"] = [{"id": "body", "description": "The test body", "views": self.views(project.VIEWS)}]

    def views(self, views):
        # Synthetic labels are test fixtures, never evidence for an actual user's asset.
        return {v: {"path": "fixture.png", "panel": f"fixture panel {v}", "reviewed": True} for v in views}

    def approve_all(self):
        for stage in project.STAGES:
            project.approve(self.root, self.state, stage, "TEST ONLY: approved fixture", "unit test")

    def cli(self, arguments):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return project.main(arguments)

    def test_initial_state_cannot_start_modeling(self):
        project.save(self.root, project.initial_state("new"))
        self.assertEqual(self.cli(["start-modeling", str(self.root)]), 1)
        self.assertEqual(project.load(self.root)["phase"], "brief")

    def test_approved_pack_can_start_modeling(self):
        self.approve_all()
        self.assertEqual(project.ready_errors(self.root, self.state), [])
        self.assertEqual(self.cli(["start-modeling", str(self.root)]), 0)
        self.assertEqual(project.load(self.root)["phase"], "modeling")

    def test_every_component_requires_every_view(self):
        self.state["components"].append({"id": "helmet", "description": "second component", "views": self.views(project.VIEWS)})
        for component in self.state["components"]:
            for view in project.VIEWS:
                changed = copy.deepcopy(self.state)
                part = next(p for p in changed["components"] if p["id"] == component["id"])
                del part["views"][view]
                with self.subTest(component=component["id"], view=view):
                    self.assertTrue(any(view in error for error in project.validation_errors(self.root, changed)))

    def test_scope_can_be_approved_before_component_images_exist(self):
        self.state["components"][0]["views"] = {}
        project.approve(self.root, self.state, "concept", "TEST fixture", "unit test")
        project.approve(self.root, self.state, "scope", "TEST fixture", "unit test")
        with self.assertRaises(ValueError):
            project.approve(self.root, self.state, "references", "TEST fixture", "unit test")

    def test_reference_approval_requires_prior_decisions(self):
        with self.assertRaisesRegex(ValueError, "missing explicit user approval"):
            project.approve(self.root, self.state, "references", "TEST fixture", "unit test")

    def test_same_filename_changed_bytes_invalidates_approval(self):
        self.approve_all()
        Image.new("RGB", (64, 64), "red").save(self.root / "fixture.png")
        errors = project.ready_errors(self.root, self.state)
        self.assertIn("stale user approval: concept", errors)
        self.assertIn("stale user approval: references", errors)

    def test_added_part_invalidates_scope_and_pack(self):
        self.approve_all()
        self.state["components"].append({"id": "new-part", "description": "new scope", "views": self.views(project.VIEWS)})
        errors = project.approval_errors(self.root, self.state)
        self.assertIn("stale user approval: scope", errors)
        self.assertIn("stale user approval: references", errors)

    def test_unreviewed_or_missing_image_blocks(self):
        self.state["components"][0]["views"]["front"]["reviewed"] = False
        self.state["components"][0]["views"]["top"]["path"] = "missing.png"
        errors = project.validation_errors(self.root, self.state)
        self.assertTrue(any("not been visually reviewed" in e for e in errors))
        self.assertTrue(any("missing artifact" in e for e in errors))

    def test_invalid_image_and_escaped_path_block(self):
        (self.root / "invalid.png").write_text("not an image")
        self.assertTrue(project.image_errors(self.root, {"path": "invalid.png", "panel": "full image", "reviewed": True}, "bad"))
        with self.assertRaisesRegex(ValueError, "escapes"):
            project.artifact(self.root, "../outside.png")

    def test_duplicate_panel_cannot_count_as_multiple_views(self):
        self.state["components"][0]["views"]["back"] = self.state["components"][0]["views"]["front"]
        self.assertTrue(any("own image or sheet panel" in e for e in project.validation_errors(self.root, self.state)))

    def test_animation_contract_required_and_hashed(self):
        self.state["brief"]["delivery_mode"] = "animated"
        self.assertTrue(any("agreed animation clips" in e for e in project.validation_errors(self.root, self.state)))
        self.state["animations"] = [{"name": "idle", "description": "Idle loop", "fps": 24,
                                     "frame_start": 1, "frame_end": 25, "loop": True, "root_motion": "in_place"}]
        self.approve_all()
        self.state["animations"][0]["frame_end"] = 49
        self.assertIn("stale user approval: scope", project.approval_errors(self.root, self.state))

    def test_bad_clip_values_rejected(self):
        self.state["brief"]["delivery_mode"] = "animated"
        self.state["animations"] = [{"name": "bad", "fps": float("nan"), "frame_start": 1,
                                     "frame_end": 1, "loop": "yes", "root_motion": "unknown"}]
        self.assertGreaterEqual(len(project.validation_errors(self.root, self.state)), 5)

    def test_output_bookkeeping_does_not_invalidate_design(self):
        self.approve_all()
        self.state["deliverables"].append({"path": "models/model-v1.blend"})
        self.state["validation"].append({"status": "pending"})
        self.assertEqual(project.ready_errors(self.root, self.state), [])

    def test_no_overwrite_on_initialization(self):
        project.save(self.root, self.state)
        before = (self.root / "project.json").read_bytes()
        self.assertEqual(self.cli(["init", str(self.root), "--name", "replacement"]), 1)
        self.assertEqual((self.root / "project.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
