from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

import pytest

from tsao_researcher.errors import LockTimeoutError
from tsao_researcher.io import exclusive_lock


def _hold_lock(path: str, ready: object, release: object) -> None:
    with exclusive_lock(path, timeout=2, stale_after=10):
        ready.set()  # type: ignore[attr-defined]
        release.wait(5)  # type: ignore[attr-defined]


def test_old_mtime_does_not_reclaim_a_live_process_lock(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    lock = tmp_path / "active.lock"
    owner = context.Process(target=_hold_lock, args=(str(lock), ready, release))
    owner.start()
    try:
        assert ready.wait(5)
        old = time.time() - 1000
        os.utime(lock, (old, old))
        with pytest.raises(LockTimeoutError), exclusive_lock(lock, timeout=0.1, stale_after=0.01):
            pass
        assert owner.is_alive()
    finally:
        release.set()
        owner.join(5)
        if owner.is_alive():
            owner.terminate()
            owner.join()
    assert owner.exitcode == 0


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is unavailable on this platform")
def test_forked_child_cannot_release_parent_lock(tmp_path: Path) -> None:
    lock = tmp_path / "fork.lock"
    manager = exclusive_lock(lock)
    manager.__enter__()
    pid = os.fork()
    if pid == 0:
        manager.__exit__(None, None, None)
        os._exit(0)
    try:
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0
        assert lock.exists()
    finally:
        manager.__exit__(None, None, None)
    assert not lock.exists()
