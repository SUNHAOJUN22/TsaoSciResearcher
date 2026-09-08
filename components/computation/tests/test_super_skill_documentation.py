from __future__ import annotations

import json
from pathlib import Path

from tsao_computation.orchestration import (
    InvocationKind,
    acceleration_strategies,
    list_invocations,
    methods,
)
from tsao_computation.registries import adapters, capabilities, workflows

ROOT = Path(__file__).resolve().parents[1]


def test_super_skill_documentation_and_machine_audit_are_synchronized() -> None:
    for name in ("README.md", "README.zh-CN.md", "SKILL.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert text.count("<!-- SUPER_SKILL_ORCHESTRATION:START -->") == 1
        assert text.count("<!-- SUPER_SKILL_ORCHESTRATION:END -->") == 1
    assert (ROOT / "docs" / "orchestration.md").is_file()
    payload = json.loads(
        (ROOT / "reports" / "ULTIMATE_COMPUTATION_SUPER_SKILL_AUDIT.json").read_text(
            encoding="utf-8"
        )
    )
    architecture = payload["architecture"]
    assert architecture["methods"] == len(methods()) == 23
    assert architecture["capabilities"] == len(capabilities()) == 164
    assert architecture["adapters"] == len(adapters()) == 27
    assert architecture["workflows"] == len(workflows()) == 20
    assert architecture["acceleration_strategies"] == len(acceleration_strategies()) == 13
    assert architecture["invocation_kinds"] == sorted(item.value for item in InvocationKind)
    assert architecture["invocation_targets"] == len(list_invocations())
    assert payload["execution_policy"]["arbitrary_shell_execution"] is False
    assert payload["temporary_branch_created"] is False
    assert payload["created_pull_request"] is False
