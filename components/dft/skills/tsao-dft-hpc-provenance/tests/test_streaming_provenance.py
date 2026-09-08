from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StreamingProvenanceTests(unittest.TestCase):
    def test_large_file_hash_is_exact_without_read_bytes(self):
        source = ROOT / "scripts" / "collect_provenance.py"
        self.assertNotIn("read_bytes", source.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "large-output.bin"
            payload.write_bytes(b"TsaoDFT-streaming-hash\n" * 250_000)
            output = root / "provenance.json"
            result = subprocess.run(
                [sys.executable, str(source), str(payload), "--out", str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(output.read_text(encoding="utf-8"))["files"][0]
            self.assertEqual(record["sha256"], hashlib.sha256(payload.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
