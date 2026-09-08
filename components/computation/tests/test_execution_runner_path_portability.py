from __future__ import annotations

import os
from pathlib import Path

import pytest

from tsao_computation.execution import runner


def _literal_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"portable executable fixture\n")
    path.chmod(path.stat().st_mode | 0o111)
    return path.resolve()


def test_explicit_relative_prefix_is_separator_independent() -> None:
    assert runner._has_explicit_relative_prefix("./solver") is True
    assert runner._has_explicit_relative_prefix(".\\solver") is True
    assert runner._has_explicit_relative_prefix("../solver") is True
    assert runner._has_explicit_relative_prefix("..\\solver") is True
    assert runner._has_explicit_relative_prefix("solver") is False
    assert runner._has_explicit_relative_prefix("nested/solver") is False


def test_exact_path_entry_search_is_bounded_to_declared_path(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    executable = _literal_executable(right / "solver")

    assert runner._search_exact_path_entry("solver", "") is None
    assert runner._search_exact_path_entry("missing", str(right)) is None
    assert runner._search_exact_path_entry(
        "solver",
        os.pathsep.join((str(left), f'"{right}"')),
    ) == str(executable)


def test_exact_path_search_skips_blank_declared_entries(tmp_path: Path) -> None:
    path_bin = tmp_path / "path-bin"
    executable = _literal_executable(path_bin / "solver")
    search_path = os.pathsep.join(("", "   ", '""', str(path_bin)))

    assert runner._search_exact_path_entry("solver", search_path) == str(executable)


def test_resolver_uses_literal_immutable_path_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_bin = tmp_path / "path-bin"
    executable = _literal_executable(path_bin / "solver")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(runner.shutil, "which", lambda *_args, **_kwargs: None)

    resolved = runner._resolve_executable("solver", work, search_path=str(path_bin))

    assert resolved == executable


def test_literal_path_fallback_tolerates_unreadable_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_bin = tmp_path / "path-bin"
    executable = _literal_executable(path_bin / "solver")
    original_is_file = Path.is_file

    def guarded_is_file(path: Path) -> bool:
        if path.parent.name == "broken":
            raise OSError("fixture path failure")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    search_path = os.pathsep.join((str(tmp_path / "broken"), str(path_bin)))

    assert runner._search_exact_path_entry("solver", search_path) == str(executable)
