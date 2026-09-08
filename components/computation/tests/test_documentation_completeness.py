from __future__ import annotations

from pathlib import Path

from scripts.build_adapter_docs import REQUIRED_HEADINGS as ADAPTER_HEADINGS
from scripts.build_workflow_docs import REQUIRED_HEADINGS as WORKFLOW_HEADINGS
from tsao_computation.registries import adapters, workflows

ROOT = Path(__file__).resolve().parents[1]


def test_root_skill_contains_intake_and_contract_policy() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "## Intake questions",
        "## Calculation contract",
        "## Routing and progressive loading",
        "## State and acceptance policy",
        "## Required gates",
        "validate-contract <file> --strict",
        "completed ≠ parsed ≠ converged ≠ validated ≠ accepted",
    ):
        assert phrase in text


def test_every_adapter_document_has_required_sections() -> None:
    for record in adapters():
        path = ROOT / "adapters" / str(record["slug"]) / "ADAPTER.md"
        text = path.read_text(encoding="utf-8")
        for heading in ADAPTER_HEADINGS:
            assert heading in text, f"{path}: missing {heading}"


def test_every_workflow_document_has_required_sections() -> None:
    for record in workflows():
        path = ROOT / "skills" / "workflows" / str(record["slug"]) / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        for heading in WORKFLOW_HEADINGS:
            assert heading in text, f"{path}: missing {heading}"


def test_uploaded_catalog_traceability_is_documented() -> None:
    text = (ROOT / "docs" / "coverage-matrix.md").read_text(encoding="utf-8")
    for phrase in ("322", "164", "32", "27 core adapters", "11 catalog engines"):
        assert phrase in text
