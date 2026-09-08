from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StreamingStructureHashTests(unittest.TestCase):
    def test_structure_hash_streams_and_preserves_digest(self):
        script = ROOT / "scripts" / "structure_hash.py"
        validator = ROOT / "scripts" / "validate_structure_manifest.py"
        self.assertNotIn("read_bytes", script.read_text(encoding="utf-8"))
        self.assertNotIn("read_bytes", validator.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary) / "structure with 空格.xyz"
            payload.write_bytes(b"2\nlarge fixture\nH 0 0 0\nH 0 0 1\n" * 100_000)
            result = subprocess.run(
                [sys.executable, str(script), str(payload)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(result.stdout)[0]
            self.assertEqual(record["sha256"], hashlib.sha256(payload.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
