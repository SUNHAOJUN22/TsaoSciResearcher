from __future__ import annotations

import math
from pathlib import Path

import pytest

from scripts import common
from scripts.common import atomic_write_text, read_jsonl, write_json

ROOT = Path(__file__).resolve().parents[1]


def test_json_rejects_nan(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_json(tmp_path / "value.json", {"value": math.nan})


def test_jsonl_rejects_non_object_and_non_finite(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        read_jsonl(path)
    path.write_text('{"value": NaN}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        read_jsonl(path)


def test_atomic_write_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("original", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("TSR-007: platform does not permit symlink creation")
    with pytest.raises(ValueError, match="symbolic"):
        atomic_write_text(link, "replacement")
    assert target.read_text(encoding="utf-8") == "original"


def test_atomic_write_preserves_old_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    target.write_text("old\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"simulated replace failure: {source} -> {destination}")

    monkeypatch.setattr(common.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        atomic_write_text(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".state.json.*")) == []
