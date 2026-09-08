from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SKILL = "tsao-dft-suite"


class InstallerSecurityTests(unittest.TestCase):
    def run_installer(self, target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--agent",
                "codex",
                "--scope",
                "project",
                "--target",
                str(target),
                "--skill",
                SKILL,
                *arguments,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_copy_install_records_ownership_and_uninstalls(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            installed = self.run_installer(target)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            destination = target / SKILL
            marker = target / ".tsao-skill-ownership" / f"{SKILL}.json"
            self.assertTrue((destination / "SKILL.md").is_file())
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(payload["skill"], SKILL)
            self.assertEqual(payload["method"], "copy")
            removed = self.run_installer(target, "--uninstall")
            self.assertEqual(removed.returncode, 0, removed.stdout + removed.stderr)
            self.assertFalse(destination.exists())
            self.assertFalse(marker.exists())

    def test_force_refuses_foreign_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            destination = target / SKILL
            destination.mkdir(parents=True)
            sentinel = destination / "FOREIGN_DATA.txt"
            sentinel.write_text("must survive\n", encoding="utf-8")
            result = self.run_installer(target, "--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unowned destination", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must survive\n")

    def test_uninstall_refuses_foreign_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            destination = target / SKILL
            destination.mkdir(parents=True)
            sentinel = destination / "FOREIGN_DATA.txt"
            sentinel.write_text("must survive\n", encoding="utf-8")
            result = self.run_installer(target, "--uninstall")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unowned destination", result.stderr)
            self.assertTrue(sentinel.is_file())

    def test_modified_copy_requires_backup_before_force_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            self.assertEqual(self.run_installer(target).returncode, 0)
            destination = target / SKILL
            local_note = destination / "LOCAL_NOTE.txt"
            local_note.write_text("preserve me\n", encoding="utf-8")
            refused = self.run_installer(target, "--force")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("owned copy was modified", refused.stderr)
            self.assertTrue(local_note.is_file())

            replaced = self.run_installer(target, "--force", "--backup-existing")
            self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
            backup = target / f"{SKILL}.backup"
            self.assertEqual((backup / "LOCAL_NOTE.txt").read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse((destination / "LOCAL_NOTE.txt").exists())
            self.assertTrue((destination / "SKILL.md").is_file())

    def test_uninstall_of_modified_owned_copy_requires_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            self.assertEqual(self.run_installer(target).returncode, 0)
            destination = target / SKILL
            (destination / "LOCAL_NOTE.txt").write_text("modified\n", encoding="utf-8")
            refused = self.run_installer(target, "--uninstall")
            self.assertNotEqual(refused.returncode, 0)
            self.assertTrue(destination.exists())
            forced = self.run_installer(target, "--uninstall", "--force")
            self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
            self.assertFalse(destination.exists())

    def test_changed_symlink_target_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "skills"
            installed = self.run_installer(target, "--method", "symlink")
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            destination = target / SKILL
            foreign = root / "foreign"
            foreign.mkdir()
            destination.unlink()
            destination.symlink_to(foreign, target_is_directory=True)
            refused = self.run_installer(target, "--uninstall", "--force")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("symlink target changed", refused.stderr)
            self.assertEqual(destination.resolve(), foreign.resolve())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            result = self.run_installer(target, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(target.exists())

    def test_home_directory_is_not_a_valid_target_root(self):
        result = self.run_installer(Path.home())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe target root refused", result.stderr)


if __name__ == "__main__":
    unittest.main()
