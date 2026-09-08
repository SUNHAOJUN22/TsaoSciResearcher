from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tsao_computation.repository_audit import _parse_project_version


def test_project_version_parser_uses_static_project_table() -> None:
    text = """[tool.example]
version = "99.0"

[project]
name = "demo"
version = "3.0.0" # release
"""
    assert _parse_project_version(text) == "3.0.0"


def test_project_version_parser_accepts_controlled_version_file() -> None:
    text = """[project]
name = "demo"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {file = ["VERSION"]}
"""
    assert _parse_project_version(text) == "VERSION"
    assert _parse_project_version(text, "3.0.1") == "3.0.1"


def test_project_version_parser_accepts_single_quotes_and_table_comment() -> None:
    text = "[project] # package metadata\nversion = '3.0.0'\n"
    assert _parse_project_version(text) == "3.0.0"


@pytest.mark.parametrize(
    "text",
    (
        "",
        "[project]\nname = 'demo'\n",
        "[project]\nversion = 3\n",
        "[project]\ndynamic = ['version']\n",
        "[project]\ndynamic = ['version']\n[tool.setuptools.dynamic]\nversion = {attr = 'x'}\n",
    ),
)
def test_project_version_parser_rejects_invalid_values(text: str) -> None:
    with pytest.raises(ValueError, match="version"):
        _parse_project_version(text)


def test_repository_audit_source_is_python310_compatible() -> None:
    source = Path("tsao_computation/repository_audit.py").read_text(encoding="utf-8")
    ast.parse(source, filename="repository_audit.py", feature_version=(3, 10))
    assert "tomllib" not in source
