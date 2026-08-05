from __future__ import annotations

from pathlib import Path
from re import Pattern
from typing import cast

import pytest

from scripts import route_task
from tsao_researcher import capabilities, router, strategy
from tsao_researcher.capabilities import load_capabilities, search_capabilities
from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.state import initialize


def test_legacy_router_compiles_default_rules_once(monkeypatch: pytest.MonkeyPatch) -> None:
    route_task._compiled_default_rules.cache_clear()
    calls = 0
    original = route_task._compile_rules

    def counted(rules: dict[str, dict[str, object]]) -> tuple[route_task._Rule, ...]:
        nonlocal calls
        calls += 1
        return original(rules)  # type: ignore[arg-type]

    monkeypatch.setattr(route_task, "_compile_rules", counted)
    assert route_task.route("use GROMACS for MD")["workflow"] == "computation-handoff"
    assert route_task.route("use GROMACS for MD")["workflow"] == "computation-handoff"
    assert calls == 1
    route_task._compiled_default_rules.cache_clear()


def test_legacy_router_normalized_duplicates_are_counted_once() -> None:
    result = route_task.route(
        "alpha",
        rules={
            "first": {"weight": 2, "keywords": ["alpha", "\uff21\uff2c\uff30\uff28\uff21", "Alpha"]},
            "second": {"weight": 1, "keywords": ["alpha"]},
        },
    )
    assert result["workflow"] == "first"
    assert result["matched"] == ["alpha"]
    assert result["alternatives"] == [{"workflow": "second", "score": 1}]


def test_capability_catalog_and_search_results_are_deeply_isolated() -> None:
    first = load_capabilities()
    original_name = first[0]["name_en"]
    first[0]["name_en"] = "mutated"
    first[0]["domains"].append("mutated-domain")
    first[0]["source_lineage"][0]["source"] = "mutated-source"
    first[0]["human_approval"]["points"].append("mutated-approval")
    first[0]["computation_handoff"]["mode"] = "mutated-mode"

    second = load_capabilities()
    assert second[0]["name_en"] == original_name
    assert "mutated-domain" not in second[0]["domains"]
    assert second[0]["source_lineage"][0]["source"] != "mutated-source"
    assert "mutated-approval" not in second[0]["human_approval"]["points"]
    assert second[0]["computation_handoff"]["mode"] != "mutated-mode"

    result = search_capabilities("polymer", limit=1)
    assert result
    result[0]["domains"].append("mutated-domain")
    again = search_capabilities("polymer", limit=1)
    assert "mutated-domain" not in again[0]["domains"]


def test_search_index_precomputes_slug_and_domain_metadata() -> None:
    indexed = capabilities._search_rows(capabilities.CATALOG_PATH)
    row, _haystack, _tokens, normalized_slug, domains = indexed[0]
    assert normalized_slug == str(row["slug"]).casefold()
    assert domains == frozenset(row["domains"])


def test_strategy_trigger_compilation_is_cached() -> None:
    strategy._compiled_trigger.cache_clear()
    first = strategy.advise_computation_strategy(
        "How should polymer charge transport be modelled?",
        ["space charge", "conductivity"],
        ["30 C", "20 kV/mm"],
    )
    after_first = strategy._compiled_trigger.cache_info()
    second = strategy.advise_computation_strategy(
        "How should polymer charge transport be modelled?",
        ["space charge", "conductivity"],
        ["30 C", "20 kV/mm"],
    )
    after_second = strategy._compiled_trigger.cache_info()
    assert first == second
    assert after_first.misses > 0
    assert after_second.hits > after_first.hits


def test_trigger_literal_prefilters_avoid_unnecessary_regex_work() -> None:
    class ExplodingPattern:
        def search(self, text: str) -> None:
            raise AssertionError(f"regex should not run for absent literal: {text}")

    pattern = cast(Pattern[str], ExplodingPattern())
    assert strategy._compiled_trigger_matches("unrelated text", "target", pattern) is False
    assert router.Trigger("target", pattern).matches("unrelated text") is False
    assert route_task._Keyword("target", "target", pattern, 0).matches("unrelated text") is False


def test_strategy_trigger_prefilter_preserves_literal_and_word_boundaries() -> None:
    assert strategy._contains_trigger("unrelated text", "target") is False
    assert strategy._contains_trigger("a target value", "target") is True
    assert strategy._contains_trigger("targeted value", "target") is False
    assert strategy._contains_trigger("高分子结晶过程", "结晶") is True


def test_capsule_prunes_repository_metadata_and_streams_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = initialize("study", "does the model conserve charge?", tmp_path)
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("secret-ish repository metadata", encoding="utf-8")
    cache_dir = root / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "cached.pyc").write_bytes(b"cache")
    payload = root / "reports" / "large.bin"
    payload.write_bytes(b"x" * (2 * 1024 * 1024))

    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path == payload:
            raise AssertionError("capsule export must stream project files")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    capsule = tmp_path / "capsule.zip"
    result = export_capsule(root, capsule, mode="full")
    assert result["valid"] is True
    verified = verify_capsule(capsule)
    assert verified["valid"] is True

    import zipfile

    with zipfile.ZipFile(capsule) as handle:
        names = set(handle.namelist())
    assert "capsule/project/reports/large.bin" in names
    assert "capsule/project/.git/config" not in names
    assert "capsule/project/__pycache__/cached.pyc" not in names
