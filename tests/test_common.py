from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import atomic_write_text, read_jsonl, write_json  # noqa: E402


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
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symbolic"):
        atomic_write_text(link, "replacement")
    assert target.read_text(encoding="utf-8") == "original"
