from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from scripts import audit_repository_legacy, run_mutation_smoke, validate_structure
from scripts.audit_repository import audit


class TestRepositoryAudit(unittest.TestCase):
    def test_repository_audit(self) -> None:
        result = audit()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["checks"]["capabilities"]["loaded"], 158)
        self.assertEqual(result["checks"]["capabilities"]["v2_base_loaded"], 340)
        self.assertEqual(result["checks"]["capabilities"]["v2_extension_loaded"], 1)
        self.assertEqual(result["checks"]["capabilities"]["v2_loaded"], 341)
        self.assertEqual(result["checks"]["workflows"]["count"], 15)
        self.assertEqual(result["checks"]["schemas"]["total"], 20)
        self.assertEqual(result["checks"]["domain_packs"]["count"], 7)


@pytest.mark.parametrize("environment", [".venv", "venv"])
def test_source_audit_excludes_generated_virtual_environments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    source = tmp_path / "tsao_researcher" / "example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    dependency = tmp_path / environment / "lib" / "example.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("GENERATED_DEPENDENCY = 1\n", encoding="utf-8")
    monkeypatch.setattr(audit_repository_legacy, "ROOT", tmp_path)

    assert audit_repository_legacy._source_files() == [source]


@pytest.mark.parametrize("environment", [".venv", "venv"])
def test_structure_validation_excludes_generated_environments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    dependency = tmp_path / environment / "lib" / "dependency.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("PLACEHOLDER" + "_CONTENT\n", encoding="utf-8")
    monkeypatch.setattr(validate_structure, "REQUIRED", set())
    monkeypatch.setattr(validate_structure, "capability_index", lambda: {"total": 158})
    monkeypatch.setattr(validate_structure, "load_capabilities", lambda: [{}] * 158)

    assert validate_structure.validate_structure(tmp_path) == []


@pytest.mark.parametrize("environment", [".venv", "venv"])
def test_mutation_copy_excludes_generated_environments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    dependency = source / environment / "lib" / "dependency.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("DEPENDENCY = 1\n", encoding="utf-8")
    monkeypatch.setattr(run_mutation_smoke, "ROOT", source)

    destination = tmp_path / "isolated"
    run_mutation_smoke._copy_repository(destination)
    assert (destination / "module.py").is_file()
    assert not (destination / environment).exists()


if __name__ == "__main__":
    unittest.main()
