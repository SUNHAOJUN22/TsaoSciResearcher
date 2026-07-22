from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tsao_researcher.capabilities import load_capabilities, search_capabilities

ROOT = Path(__file__).resolve().parents[1]


def test_v2_catalog_contains_322_named_contracts_and_no_generic_slots() -> None:
    rows = load_capabilities()
    index = json.loads((ROOT / "capabilities/v2/index.json").read_text(encoding="utf-8"))

    assert len(rows) == 340
    assert len({row["id"] for row in rows}) == 340
    assert len({row["slug"] for row in rows}) == 340
    assert index["workbook_named_total"] == 322
    assert index["core_added"] == 18
    assert index["generic_domain_slots"] == 0

    workbook_rows = [
        row
        for row in rows
        if any(
            lineage.get("source") == "ai-for-science-workbook-322"
            for lineage in row.get("source_lineage", [])
            if isinstance(lineage, dict)
        )
    ]
    assert len(workbook_rows) == 322
    assert not [row["slug"] for row in rows if re.search(r"-capability-[0-9]+$", row["slug"])]


@pytest.mark.parametrize(
    ("query", "expected_slug"),
    [
        ("UMAP", "publication-quality-plot"),
        ("DCCM", "contact-map-analysis"),
        ("free-energy landscape", "pca-free-energy"),
        ("molecular weight distribution", "population-balance"),
        ("image splicing", "image-manipulation-detector"),
        ("research question tree", "research-question-formulator"),
        ("hypothesis matrix", "hypothesis-generator"),
        ("research team analysis", "citation-network-analyzer"),
        ("time series", "scientific-feature-engineering"),
        ("journal format adaptation", "reference-formatter"),
    ],
)
def test_design_terms_resolve_to_named_capabilities(query: str, expected_slug: str) -> None:
    results = search_capabilities(query, limit=20)
    assert any(row["slug"] == expected_slug for row in results)
