from __future__ import annotations

import os
from pathlib import Path

from tsao_researcher.io import clear_json_cache, load_json


def test_json_cache_invalidates_same_size_replacement_with_preserved_mtime(tmp_path: Path) -> None:
    path = tmp_path / "record.json"
    path.write_text('{"value":1}', encoding="utf-8")
    clear_json_cache()
    original = path.stat()
    assert load_json(path) == {"value": 1}

    replacement = tmp_path / "replacement.json"
    replacement.write_text('{"value":2}', encoding="utf-8")
    assert replacement.stat().st_size == original.st_size
    os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
    os.replace(replacement, path)

    current = path.stat()
    assert current.st_size == original.st_size
    assert current.st_mtime_ns == original.st_mtime_ns
    # Path+mtime+size alone is therefore ambiguous; file identity must invalidate the cache.
    assert (current.st_dev, current.st_ino, current.st_ctime_ns) != (
        original.st_dev,
        original.st_ino,
        original.st_ctime_ns,
    )
    assert load_json(path) == {"value": 2}


def test_json_cache_still_hits_when_file_identity_is_unchanged(tmp_path: Path, monkeypatch) -> None:
    from tsao_researcher import io as io_module

    path = tmp_path / "record.json"
    path.write_text('{"items":[1]}', encoding="utf-8")
    clear_json_cache()
    original_read = io_module.read_text
    calls = 0

    def counted(source, **kwargs):
        nonlocal calls
        calls += 1
        return original_read(source, **kwargs)

    monkeypatch.setattr(io_module, "read_text", counted)
    first = load_json(path)
    second = load_json(path)
    assert first == second == {"items": [1]}
    assert first is not second
    assert calls == 1
