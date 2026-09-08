from __future__ import annotations

import ast
from pathlib import Path

ROOTS = (Path("scripts"), Path("tsao_computation"))


def test_production_text_writes_are_explicitly_lf_canonical() -> None:
    calls = 0
    for path in sorted(candidate for root in ROOTS for candidate in root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "write_text":
                continue
            calls += 1
            newline = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "newline"),
                None,
            )
            assert isinstance(newline, ast.Constant), (
                f"missing newline policy: {path}:{node.lineno}"
            )
            assert newline.value == "\n", f"non-LF write policy: {path}:{node.lineno}"
    assert calls >= 20
