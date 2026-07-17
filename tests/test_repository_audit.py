from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_repository import audit

ROOT = Path(__file__).resolve().parents[1]


class TestRepositoryAudit(unittest.TestCase):
    def test_repository_audit(self) -> None:
        result = audit()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["checks"]["capabilities"]["loaded"], 158)
        self.assertEqual(result["checks"]["workflows"]["count"], 15)
        self.assertEqual(result["checks"]["schemas"]["count"], 8)


if __name__ == "__main__":
    unittest.main()
