from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    path = ROOT / "scripts/install.py"
    spec = importlib.util.spec_from_file_location("tsao_installer_transaction", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = load_installer()

    def test_marker_failure_rolls_back_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            skill = self.installer.AVAILABLE[0]
            destination = target / skill
            target.mkdir(parents=True)
            destination.mkdir()
            (destination / "foreign.txt").write_text("original", encoding="utf-8")
            marker_dir = target / self.installer.OWNERSHIP_DIR
            marker_dir.mkdir()
            source = (self.installer.SKILLS_DIR / skill).resolve()
            self.installer.write_marker(
                target,
                skill,
                {
                    "schema_version": self.installer.MARKER_SCHEMA,
                    "repository": self.installer.REPOSITORY,
                    "skill": skill,
                    "version": "test",
                    "method": "copy",
                    "source": str(source),
                    "destination": str(destination),
                    "source_digest": "x",
                    "installed_digest": self.installer.tree_digest(destination),
                    "backup": None,
                },
            )
            with (
                patch.object(self.installer, "write_marker", side_effect=OSError("marker failed")),
                self.assertRaises(OSError),
            ):
                self.installer.install_skill(target, skill, "copy", force=True, backup_existing=True, dry_run=False)
            self.assertTrue((destination / "foreign.txt").is_file())
            self.assertFalse(destination.with_name(destination.name + ".backup").exists())

    def test_concurrent_install_lock_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            lock = target / self.installer.INSTALL_LOCK
            lock.write_text("busy", encoding="utf-8")
            with self.assertRaises(self.installer.InstallSafetyError), self.installer.install_lock(target):
                pass


if __name__ == "__main__":
    unittest.main()
