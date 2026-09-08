from __future__ import annotations

import pytest

from tsao_computation.accelerators import probe as probe_module


def test_posix_memory_probe_is_covered_on_every_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {"SC_PHYS_PAGES": 4 * 1024 * 1024, "SC_PAGE_SIZE": 4096}
    monkeypatch.setattr(probe_module.os, "name", "posix")
    monkeypatch.setattr(probe_module.os, "sysconf", lambda key: values[key], raising=False)
    assert probe_module._memory_gib() == 16.0


def test_posix_memory_probe_fails_closed_on_sysconf_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: str) -> int:
        raise OSError("unavailable")

    monkeypatch.setattr(probe_module.os, "name", "posix")
    monkeypatch.setattr(probe_module.os, "sysconf", fail, raising=False)
    assert probe_module._memory_gib() is None


def test_posix_memory_probe_rejects_nonpositive_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(probe_module.os, "name", "posix")
    monkeypatch.setattr(probe_module.os, "sysconf", lambda _: 0, raising=False)
    assert probe_module._memory_gib() is None
