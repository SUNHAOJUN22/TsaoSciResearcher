import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestCLIContracts(unittest.TestCase):
    def run_ok(self, *args):
        return subprocess.run([sys.executable, *args], cwd=ROOT, check=True, text=True, capture_output=True)

    def test_installer_dry_run_and_uninstall(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'skill'
            dry = self.run_ok('scripts/install.py', '--target', str(target), '--dry-run', '--validate')
            self.assertIn('Would install', dry.stdout)
            self.assertFalse(target.exists())
            self.run_ok('scripts/install.py', '--target', str(target), '--validate')
            self.assertTrue((target / 'SKILL.md').exists())
            self.run_ok('scripts/install.py', '--target', str(target), '--uninstall')
            self.assertFalse(target.exists())

    def test_capability_search(self):
        result = self.run_ok('scripts/capability_search.py', '科研绘图')
        self.assertTrue(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()
