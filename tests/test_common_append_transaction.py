from __future__ import annotations

from pathlib import Path

import pytest

from scripts.common import append_jsonl, read_jsonl
from tsao_researcher import io as io_module


def test_script_helper_rolls_back_short_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "records.jsonl"
    append_jsonl(target, {"existing": "中文"})
    original = target.read_bytes()
    write = io_module.os.write

    def shortened(fd: int, payload: bytes) -> int:
        if b'"new":true' in payload:
            return write(fd, payload[:5])
        return write(fd, payload)

    monkeypatch.setattr(io_module.os, "write", shortened)
    with pytest.raises(OSError, match="short JSONL write"):
        append_jsonl(target, {"new": True})
    assert target.read_bytes() == original
    assert read_jsonl(target) == [{"existing": "中文"}]


@pytest.mark.parametrize("record", [None, [], "text", 3])
def test_script_helper_rejects_nonobject(tmp_path: Path, record: object) -> None:
    with pytest.raises(ValueError, match="object"):
        append_jsonl(tmp_path / "events.jsonl", record)


def test_nonfinite_append_preserves_prior_record(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    append_jsonl(target, {"existing": True})
    original = target.read_bytes()
    with pytest.raises(ValueError):
        append_jsonl(target, {"value": float("nan")})
    assert target.read_bytes() == original
