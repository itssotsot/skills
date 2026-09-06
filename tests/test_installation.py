import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IndependentInstallTest(unittest.TestCase):
    def test_skill_works_when_copied_without_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "installed-skill"
            shutil.copytree(ROOT / "skills/blndr", skill)
            asset = root / "asset-project"
            initialized = subprocess.run([sys.executable, str(skill / "scripts/project.py"), "init", str(asset),
                                          "--name", "isolated-fixture"], cwd=root, capture_output=True, text=True)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            gate = subprocess.run([sys.executable, str(skill / "scripts/project.py"), "check", str(asset),
                                   "--ready-to-model"], cwd=root, capture_output=True, text=True)
            self.assertEqual(gate.returncode, 1)
            self.assertFalse(json.loads(gate.stdout)["ok"])
            prompt = asset / "prompts/concept.txt"
            prompt.write_text("A test asset concept, for a dry run only.")
            for provider in ("openai", "nano-banana"):
                result = subprocess.run([sys.executable, str(skill / "scripts/generate_reference.py"),
                                         "--provider", provider, "--prompt-file", str(prompt),
                                         "--out", str(asset / "references/concept.png")],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)["dry_run"])


if __name__ == "__main__":
    unittest.main()
