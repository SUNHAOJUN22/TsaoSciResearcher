from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from scripts.route_task import MAX_ROUTE_CHARS, normalize, route

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("帮我从宽泛方向形成可证伪科学问题", "research-question"),
        ("做PRISMA系统综述", "systematic-review"),
        ("进行meta-analysis", "systematic-review"),
        ("做正交实验和响应面", "experiment-design"),
        ("进行ANOVA和回归诊断", "data-analysis"),
        ("绘制论文多panel图", "scientific-figure"),
        ("写论文摘要和引言", "scientific-writing"),
        ("模拟同行审稿", "peer-review"),
        ("生成技术报告", "technical-report"),
        ("制定科研项目里程碑", "project-management"),
        ("做专利地图和现有技术检索", "patent-and-transfer"),
        ("检查科研图像是否重复拼接", "research-integrity"),
        ("生成实验SOP和样品编码", "laboratory"),
        ("用Gaussian优化分子", "computation-handoff"),
        ("用GROMACS做100ns MD", "computation-handoff"),
        ("使用Aspen做流程模拟", "computation-handoff"),
    ],
)
def test_intents(text: str, expected: str) -> None:
    assert route(text)["workflow"] == expected


def test_duplicate_keywords_do_not_double_count() -> None:
    rules = {
        "first": {"weight": 1, "keywords": ["alpha", "alpha"]},
        "second": {"weight": 1, "keywords": ["alpha"]},
    }
    result = route("alpha", rules=rules)
    assert result["workflow"] == "first"
    assert result["matched"] == ["alpha"]
    assert result["alternatives"] == [{"workflow": "second", "score": 1}]


def test_ascii_tokens_respect_word_boundaries() -> None:
    assert (
        route(
            "subplotter",
            rules={
                "plotting": {"weight": 3, "keywords": ["plot"]},
                "default": {"weight": 1, "keywords": ["research"]},
            },
        )["workflow"]
        == "research-question"
    )


def test_stable_tie_break_uses_rule_order() -> None:
    assert (
        route(
            "x", rules={"alpha": {"weight": 1, "keywords": ["x"]}, "zeta": {"weight": 1, "keywords": ["x"]}}
        )["workflow"]
        == "alpha"
    )


def test_rejects_oversized_input() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        route("x" * (MAX_ROUTE_CHARS + 1))


@given(st.text(max_size=1000))
def test_normalization_is_idempotent(text: str) -> None:
    normalized = normalize(text)
    assert normalize(normalized) == normalized


@given(st.text(max_size=1000))
def test_router_never_returns_unknown_workflow(text: str) -> None:
    result = route(text)
    assert isinstance(result["workflow"], str)
    assert result["read_first"].endswith("/WORKFLOW.md")
    assert 0.0 <= result["confidence"] <= 1.0
