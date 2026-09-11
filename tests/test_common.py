from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import pytest

from scripts import common
from scripts.common import atomic_write_text, read_jsonl, write_json
from tsao_researcher import io as io_module
from tsao_researcher.errors import ValidationError
from tsao_researcher.io import clear_json_cache, load_json, sha256_file

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


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "prepared", "outputs": [{"hash": "original"}]},
        [{"items": [1, {"approved": False}]}],
        {"nested": {"items": [{"label": "原始数据"}]}},
        [],
        {},
    ],
)
def test_json_cache_returns_detached_containers(tmp_path: Path, payload: Any) -> None:
    path = tmp_path / "record.json"
    text = json.dumps(payload, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    clear_json_cache()
    first = load_json(path)
    second = load_json(path)
    assert first is not second

    # Mutate every nested list and object; no container may belong to the cache.
    pending = [first]
    while pending:
        current = pending.pop()
        children = list(current.values()) if isinstance(current, dict) else list(current)
        pending.extend(child for child in children if isinstance(child, (dict, list)))
        if isinstance(current, dict):
            current["caller_only"] = True
        else:
            current.append("caller_only")
    assert second == payload
    assert load_json(path) == payload
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize("payload", [None, True, False, 0, 1.25, "原始数据"])
def test_json_cache_preserves_scalar_types(tmp_path: Path, payload: Any) -> None:
    path = tmp_path / "scalar.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    clear_json_cache()
    for _ in range(2):
        result = load_json(path)
        assert type(result) is type(payload)
        assert result == payload


def test_json_cache_isolation_preserves_cache_and_size_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "record.json"
    path.write_text('{"items":[1]}', encoding="utf-8")
    clear_json_cache()
    original = io_module.read_text
    calls: list[Path] = []

    def counted(source: str | Path, **kwargs: Any) -> str:
        calls.append(Path(source))
        return original(source, **kwargs)

    monkeypatch.setattr(io_module, "read_text", counted)
    first = load_json(path)
    first["items"].append(2)
    assert load_json(path) == {"items": [1]}
    assert len(calls) == 1
    with pytest.raises(ValidationError, match="exceeds"):
        load_json(path, max_bytes=1)
    assert len(calls) == 1
    clear_json_cache()
    assert load_json(path) == {"items": [1]}
    assert len(calls) == 2


def test_json_cache_detaches_deeply_nested_decoded_arrays(tmp_path: Path) -> None:
    path = tmp_path / "deep.json"
    depth = 600
    path.write_text("[" * depth + "0" + "]" * depth, encoding="utf-8")
    clear_json_cache()
    first = load_json(path)
    cursor = first
    for _ in range(depth - 1):
        cursor = cursor[0]
    cursor[0] = 99
    second = load_json(path)
    for _ in range(depth):
        second = second[0]
    assert second == 0


@pytest.mark.parametrize("chunk_bytes", [0, -1, True, False, 1.0, "1", None, math.nan, math.inf])
def test_checksum_rejects_invalid_read_sizes(tmp_path: Path, chunk_bytes: Any) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"non-empty evidence")
    with pytest.raises(ValidationError, match="chunk_bytes"):
        sha256_file(path, chunk_bytes=chunk_bytes)


@pytest.mark.parametrize("chunk_bytes", [1, 7, 1024 * 1024, 10**100])
def test_checksum_bounds_reads_and_preserves_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, chunk_bytes: int
) -> None:
    payload = b"original evidence" * 3
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    requested: list[int] = []

    class BoundedStream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            assert 0 < size <= 1024 * 1024
            requested.append(size)
            return super().read(size)

    stream = BoundedStream(payload)

    def open_stream(_path: Path, *args: Any, **kwargs: Any) -> BoundedStream:
        return stream

    monkeypatch.setattr(Path, "open", open_stream)
    assert sha256_file(path, chunk_bytes=chunk_bytes) == hashlib.sha256(payload).hexdigest()
    assert requested
    assert stream.closed


def test_checksum_empty_and_nonempty_files_are_distinct(tmp_path: Path) -> None:
    empty = tmp_path / "empty.bin"
    full = tmp_path / "full.bin"
    empty.write_bytes(b"")
    full.write_bytes(b"evidence")
    assert sha256_file(empty) == hashlib.sha256(b"").hexdigest()
    assert sha256_file(full) == hashlib.sha256(b"evidence").hexdigest()
    assert sha256_file(empty) != sha256_file(full)


@pytest.mark.parametrize("loader", ["json", "jsonl", "runtime-jsonl", "script-json"])
@pytest.mark.parametrize(
    "text",
    [
        '{"accepted": false, "accepted": true}',
        '{"a": 1, "a": 1}',
        '{"outer": {"rate": 0.1, "rate": 0.2}}',
        '{"rows": [{"unit": "Pa", "unit": "MPa"}]}',
        '{"a": 1, "\\u0061": 2}',
    ],
)
def test_json_readers_reject_duplicate_members(tmp_path: Path, loader: str, text: str) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(text + "\n", encoding="utf-8")
    read = {
        "json": load_json,
        "jsonl": read_jsonl,
        "runtime-jsonl": io_module.read_jsonl,
        "script-json": common.load_data,
    }[loader]
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read(path)


@pytest.mark.parametrize("loader", ["json", "jsonl", "runtime-jsonl", "script-json"])
@pytest.mark.parametrize("number", ["1e400", "-1e400", "1.8e308", "NaN", "Infinity", "-Infinity"])
def test_json_readers_reject_nonfinite_numbers(tmp_path: Path, loader: str, number: str) -> None:
    path = tmp_path / "overflow.json"
    path.write_text('{"outer": [{"value": ' + number + "}]}\n", encoding="utf-8")
    read = {
        "json": load_json,
        "jsonl": read_jsonl,
        "runtime-jsonl": io_module.read_jsonl,
        "script-json": common.load_data,
    }[loader]
    with pytest.raises(ValueError, match="non-finite JSON number"):
        read(path)


@pytest.mark.parametrize("text", ["1e400", "[-1e400]", '[{"x": 1, "x": 2}]'])
def test_json_reader_rejects_invalid_top_level_values(tmp_path: Path, text: str) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(path)


@pytest.mark.parametrize("loader", ["json", "jsonl", "runtime-jsonl", "script-json"])
def test_strict_json_preserves_valid_values_and_independent_scopes(tmp_path: Path, loader: str) -> None:
    text = '{"left": {"x": 1}, "right": {"x": 2}, "large": 1e308, "small": 5e-324, "zero": -0.0, "flag": true, "none": null, "integer": 123456789012345678901234567890, "text": "1e400"}'
    path = tmp_path / "valid.json"
    path.write_text(text + "\n", encoding="utf-8")
    read = {
        "json": load_json,
        "jsonl": read_jsonl,
        "runtime-jsonl": io_module.read_jsonl,
        "script-json": common.load_data,
    }[loader]
    decoded = read(path)
    value = decoded[0] if loader.endswith("jsonl") else decoded
    assert value == json.loads(text)
    assert type(value["integer"]) is int
    assert type(value["flag"]) is bool
    assert math.copysign(1, value["zero"]) == -1
    json.dumps(value, allow_nan=False)


def test_rejected_json_is_not_cached_and_replacement_is_readable(tmp_path: Path) -> None:
    path = tmp_path / "mutable.json"
    path.write_text('{"x": 1, "x": 2}', encoding="utf-8")
    clear_json_cache()
    with pytest.raises(ValueError, match="duplicate"):
        load_json(path)
    path.write_text('{"x": 3}', encoding="utf-8")
    assert load_json(path) == {"x": 3}


def test_jsonl_checks_later_lines_without_merging_objects(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"x": 1}\n\n{"x": 2, "x": 3}\n', encoding="utf-8")
    rows = io_module.iter_jsonl(path)
    assert next(rows) == {"x": 1}
    with pytest.raises(ValueError, match="duplicate"):
        next(rows)
