import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRelease(unittest.TestCase):
    def test_release_archive(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                [sys.executable, 'scripts/package_release.py', '--out', td],
                cwd=ROOT,
                check=True,
                env={'PATH': __import__('os').environ.get('PATH', ''), 'PYTHONDONTWRITEBYTECODE': '1'},
            )
            version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
            archive = Path(td) / f'TsaoSciResearcher-v{version}.zip'
            self.assertTrue(archive.exists())
            checksum_line = (Path(td) / 'SHA256SUMS').read_text(encoding='utf-8').strip()
            self.assertEqual(checksum_line.split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
            for required in [
                'TsaoSciResearcher/SKILL.md',
                'TsaoSciResearcher/manifest.json',
                'TsaoSciResearcher/capability-index/capabilities.json',
                'TsaoSciResearcher/scripts/run_tests.py',
            ]:
                self.assertIn(required, names)


if __name__ == '__main__':
    unittest.main()
