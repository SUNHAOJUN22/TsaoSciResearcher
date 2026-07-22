from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_researcher.vnext import handoff, init, route, transition, verify

ROOT = Path(__file__).resolve().parents[1]


def test_v2_router_semantics() -> None:
    assert route("做 PRISMA 系统综述")["primary_workflow"] == "systematic-review"
    assert route("只解释已有 GROMACS 轨迹, 不运行模拟")["primary_workflow"] == "data-analysis"
    assert route("帮我处理事情")["primary_workflow"] == "unknown"


def test_v2_state_chain_and_approval(tmp_path: Path) -> None:
    state_root = init("x", "what is tested?", tmp_path)
    transition(state_root, "planned", "approved plan")
    transition(state_root, "running", "start")
    assert verify(state_root)["valid"] is True
    with pytest.raises(ValueError, match="illegal transition"):
        transition(state_root, "accepted", "skip validation")


def test_v2_handoff_has_unique_id_and_checksum(tmp_path: Path) -> None:
    state_root = init("x", "what is tested?", tmp_path)
    (state_root / "data/a.txt").write_text("x", encoding="utf-8")
    first = handoff(
        state_root,
        "computation/a.json",
        "real question",
        "energy",
        "quantum",
        ["DFT"],
        ["data/a.txt"],
    )
    second = handoff(
        state_root,
        "computation/b.json",
        "real question",
        "energy",
        "quantum",
        ["DFT"],
        ["data/a.txt"],
    )
    assert first["handoff_id"] != second["handoff_id"]
    assert len(first["inputs"][0]["sha256"]) == 64


def test_v2_capability_count() -> None:
    index = json.loads((ROOT / "capabilities/v2/index.json").read_text(encoding="utf-8"))
    assert index["total"] == 340
    assert index["workbook_named_total"] == 322
    assert index["domain_named"] == 164
    assert index["generic_domain_slots"] == 0
