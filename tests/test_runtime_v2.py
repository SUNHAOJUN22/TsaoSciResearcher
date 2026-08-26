from __future__ import annotations

import json
import os
import time
from pathlib import Path

import jsonschema
import pytest
import yaml

from tsao_researcher.capabilities import load_capabilities, search_capabilities
from tsao_researcher.errors import IntegrityError, LockTimeoutError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import canonical_json, exclusive_lock, load_json, new_id, read_jsonl, sha256_file
from tsao_researcher.router import MAX_ROUTE_CHARS, clear_rule_cache, load_rules, route
from tsao_researcher.state import initialize, load_project, transition, verify

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_is_complete_unique_and_defensively_copied() -> None:
    first = load_capabilities()
    second = load_capabilities()
    assert len(first) == 341
    assert len({row["id"] for row in first}) == 341
    assert len({row["slug"] for row in first}) == 341
    first[0]["slug"] = "mutated"
    assert second[0]["slug"] != "mutated"


def test_capability_search_is_ranked_and_filterable() -> None:
    rows = search_capabilities("polymer molecular dynamics", domains={"molecular-dynamics-multiscale"})
    assert rows
    assert rows == sorted(rows, key=lambda row: (-row["score"], row["slug"]))
    assert all("molecular-dynamics-multiscale" in row["domains"] for row in rows)


def test_capability_search_indexes_named_engine_triggers() -> None:
    rows = search_capabilities("GROMACS", domains={"molecular-dynamics-multiscale"})
    assert rows
    assert all("molecular-dynamics-multiscale" in row["domains"] for row in rows)


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
def test_capability_search_supports_design_aliases(query: str, expected_slug: str) -> None:
    rows = search_capabilities(query, limit=20)
    assert any(row["slug"] == expected_slug for row in rows)


def test_capability_search_rejects_unbounded_limit() -> None:
    with pytest.raises(ValidationError):
        search_capabilities("polymer", limit=1000)


def test_router_rules_are_cached_and_reloaded_on_change(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"a": {"weight": 2, "positive": ["alpha"]}}), encoding="utf-8")
    first = load_rules(path)
    assert first is load_rules(path)
    time.sleep(0.002)
    path.write_text(json.dumps({"b": {"weight": 2, "positive": ["beta"]}}), encoding="utf-8")
    os.utime(path, None)
    second = load_rules(path)
    assert second != first
    clear_rule_cache()


def test_router_unicode_boundaries_and_negative_semantics() -> None:
    assert route("做聚合反应的 Aspen 实际动态模拟")["primary_workflow"] == "computation-handoff"
    assert (
        route("从统计物理和量子力学提出第一性原理计算策略, 不运行求解器")["primary_workflow"]
        == "computation-handoff"
    )
    assert route("只分析已有 GROMACS 轨迹, 不运行")["primary_workflow"] == "data-analysis"
    assert route("请审核引用真实性和科研诚信")["primary_workflow"] == "research-integrity"
    assert route("ordinary")["primary_workflow"] == "unknown"


def test_router_rejects_unbounded_input() -> None:
    with pytest.raises(ValidationError):
        route("x" * (MAX_ROUTE_CHARS + 1))


def test_router_applies_negation_only_to_the_local_english_clause() -> None:
    measurement = route("Do not use DFT; I only need experimental measurements.")
    assert measurement["primary_workflow"] == "laboratory"
    assert all(row["workflow"] != "computation-handoff" for row in measurement["matched"])

    mixed = route("Do not use DFT, but run LAMMPS for 10 ns.")
    assert mixed["primary_workflow"] == "computation-handoff"
    computation = next(row for row in mixed["matched"] if row["workflow"] == "computation-handoff")
    assert "lammps" in computation["positive"]
    assert "dft" in computation["negated_positive"]


def test_router_applies_negation_only_to_the_local_chinese_clause() -> None:
    measurement = route("不要使用 DFT，只要实验测量。")  # noqa: RUF001
    assert measurement["primary_workflow"] == "laboratory"
    assert all(row["workflow"] != "computation-handoff" for row in measurement["matched"])

    mixed = route("不要使用 DFT，但运行 LAMMPS 完成分子动力学。")  # noqa: RUF001
    assert mixed["primary_workflow"] == "computation-handoff"


def test_project_full_lifecycle_and_hash_chain(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    for state in ("planned", "running", "completed", "checked", "validated"):
        transition(root, state, f"move to {state}")
    transition(root, "accepted", "approved result", approvals=["APR-1"])
    result = verify(root)
    assert result["valid"] is True
    assert result["events"] == 7
    assert result["status"] == "accepted"


def test_project_chain_detects_tampering(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    events = root / "state/events.jsonl"
    rows = events.read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    payload["reason"] = "tampered"
    rows[0] = canonical_json(payload)
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        verify(root)


def test_accepted_state_requires_approval(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    for state in ("planned", "running", "completed", "checked", "validated"):
        transition(root, state, f"move to {state}")
    with pytest.raises(ValueError, match="approval"):
        transition(root, "accepted", "accept without approval")


def test_initialize_refuses_unmanaged_replacement(tmp_path: Path) -> None:
    root = tmp_path / ".tsao-research"
    root.mkdir()
    (root / "private.txt").write_text("do not delete", encoding="utf-8")
    with pytest.raises(ValidationError, match="unmanaged"):
        initialize("study", "what mechanism is tested?", tmp_path, force=True)


def test_lock_timeout_and_stale_lock_recovery(tmp_path: Path) -> None:
    lock = tmp_path / "x.lock"
    with exclusive_lock(lock), pytest.raises(LockTimeoutError), exclusive_lock(lock, timeout=0.01):
        pass
    lock.write_text("stale", encoding="utf-8")
    old = time.time() - 1000
    os.utime(lock, (old, old))
    with exclusive_lock(lock, timeout=0.1, stale_after=10):
        assert lock.exists()


def test_handoff_validates_paths_and_ready_inputs(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    with pytest.raises(ValidationError, match="verified input"):
        create_handoff(root, "computation/empty.json", "question", "energy", "DFT", ["PBE"], [])
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(ValidationError, match="escapes"):
        create_handoff(root, "computation/bad.json", "question", "energy", "DFT", ["PBE"], ["../outside.txt"])


def test_handoff_schema_validation(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    data = root / "data/input.dat"
    data.write_bytes(b"123")
    handoff = create_handoff(
        root, "computation/handoff.json", "question", "energy", "DFT", ["PBE"], ["data/input.dat"]
    )
    schema = load_json(ROOT / "schemas/v2/handoff.schema.json")
    jsonschema.Draft202012Validator(schema).validate(handoff)
    assert handoff["inputs"][0]["sha256"] == sha256_file(data)
    assert handoff["scale"] == "multiscale"
    assert handoff["evidence_level"] == "prepared"
    assert handoff["evaluation_metrics"] == ["energy"]
    assert handoff["expected_outputs"] == ["validated artifact for energy"]
    project = load_project(root)
    assert project["computation_handoffs"] == ["computation/handoff.json"]
    artifacts = read_jsonl(root / "artifacts.jsonl")
    assert artifacts[-1]["artifact_type"] == "computation-handoff"
    assert artifacts[-1]["path"] == "computation/handoff.json"
    assert verify(root)["valid"] is True


def test_project_schema_validation(tmp_path: Path) -> None:
    root = initialize("study", "what mechanism is tested?", tmp_path)
    schema = load_json(ROOT / "schemas/v2/project.schema.json")
    jsonschema.Draft202012Validator(schema).validate(load_project(root))


def test_ids_are_collision_resistant() -> None:
    values = {new_id("TSR") for _ in range(2000)}
    assert len(values) == 2000


def test_workflow_contracts_and_gates_match() -> None:
    schema = load_json(ROOT / "schemas/v2/workflow.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    for directory in sorted((ROOT / "workflows").iterdir()):
        if not directory.is_dir():
            continue
        contract = load_json(directory / "workflow.yaml.json")
        validator.validate(contract)
        assert contract["slug"] == directory.name
        gates = yaml.safe_load((directory / "gates.yaml").read_text(encoding="utf-8"))
        assert all(gates[key] for key in ("entry", "blocking", "completion"))


def _clear_capability_caches() -> None:
    from tsao_researcher import capabilities as capability_module

    capability_module._catalog.cache_clear()
    capability_module._merged_catalog.cache_clear()
    capability_module._single_search_index.cache_clear()
    capability_module._merged_search_index.cache_clear()


def test_custom_catalog_path_is_loaded_without_default_extensions(tmp_path: Path) -> None:
    from tsao_researcher.capabilities import load_capabilities, search_capabilities

    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "id": "CUSTOM-1",
                    "slug": "custom-method",
                    "name_en": "Custom Method",
                    "description": "custom searchable method",
                }
            ]
        ),
        encoding="utf-8",
    )
    assert [row["id"] for row in load_capabilities(custom)] == ["CUSTOM-1"]
    assert search_capabilities("custom searchable", path=custom)[0]["slug"] == "custom-method"


def test_missing_extension_catalog_falls_back_to_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tsao_researcher import capabilities as capability_module

    monkeypatch.setattr(capability_module, "EXTENSIONS_PATH", tmp_path / "missing-extensions.json")
    _clear_capability_caches()
    try:
        assert len(capability_module.load_capabilities()) == 340
        assert capability_module.search_capabilities("polymer", limit=1)
    finally:
        _clear_capability_caches()


def test_non_file_extension_catalog_falls_back_to_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tsao_researcher import capabilities as capability_module

    extension_directory = tmp_path / "extensions"
    extension_directory.mkdir()
    monkeypatch.setattr(capability_module, "EXTENSIONS_PATH", extension_directory)
    _clear_capability_caches()
    try:
        assert len(capability_module.load_capabilities()) == 340
        assert capability_module.search_capabilities("polymer", limit=1)
    finally:
        _clear_capability_caches()


def test_duplicate_extension_capability_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tsao_researcher import capabilities as capability_module

    duplicate = capability_module.load_capabilities(capability_module.CATALOG_PATH)[0]
    extension = tmp_path / "extensions.json"
    extension.write_text(json.dumps([duplicate]), encoding="utf-8")
    monkeypatch.setattr(capability_module, "EXTENSIONS_PATH", extension)
    _clear_capability_caches()
    try:
        with pytest.raises(ValidationError, match="across catalogs"):
            capability_module.load_capabilities()
    finally:
        _clear_capability_caches()
