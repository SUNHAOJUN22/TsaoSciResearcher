from __future__ import annotations

import unittest

from scripts.audit_repository import audit


class TestRepositoryAudit(unittest.TestCase):
    def test_repository_audit(self) -> None:
        result = audit()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["checks"]["capabilities"]["loaded"], 158)
        self.assertEqual(result["checks"]["capabilities"]["v2_loaded"], 340)
        self.assertEqual(result["checks"]["workflows"]["count"], 15)
        self.assertEqual(result["checks"]["schemas"]["total"], 15)
        self.assertEqual(result["checks"]["domain_packs"]["count"], 7)


if __name__ == "__main__":
    unittest.main()
