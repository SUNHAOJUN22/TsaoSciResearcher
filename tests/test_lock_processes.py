from __future__ import annotations

import json
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tsao_researcher.errors import LockTimeoutError
from tsao_researcher.io import exclusive_lock


def _hold_lock(path: str, ready: object, release: object) -> None:
    with exclusive_lock(path, timeout=2, stale_after=10):
        ready.set()  # type: ignore[attr-defined]
        release.wait(5)  # type: ignore[attr-defined]


def _acquire_competing_lock(path: str, ready: object, entered: object, timeout: float = 15) -> None:
    ready.set()  # type: ignore[attr-defined]
    with exclusive_lock(path, timeout=timeout, stale_after=0.01):
        entered.set()  # type: ignore[attr-defined]


def test_concurrent_stale_lock_recovery_never_enters_two_critical_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = tmp_path / "stale-race.lock"
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    dead_pid = child.pid
    child.wait(timeout=5)
    lock.write_text(
        json.dumps({"pid": dead_pid, "host": socket.gethostname(), "token": "stale"}),
        encoding="utf-8",
    )
    old = time.time() - 60
    os.utime(lock, (old, old))

    unlink_checked = threading.Event()
    release_unlink = threading.Event()
    fast_inside = threading.Event()
    active_lock = threading.Lock()
    active = 0
    max_active = 0
    acquired: set[str] = set()
    errors: list[BaseException] = []
    original_unlink = Path.unlink

    def interleaved_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if (
            path == lock
            and threading.current_thread().name == "late-reclaimer"
            and not unlink_checked.is_set()
        ):
            unlink_checked.set()
            if not release_unlink.wait(3):
                raise RuntimeError("test did not release the paused reclaimer")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", interleaved_unlink)

    def contend(name: str) -> None:
        nonlocal active, max_active
        try:
            with exclusive_lock(lock, timeout=2, stale_after=0.01):
                with active_lock:
                    active += 1
                    max_active = max(max_active, active)
                    acquired.add(name)
                    if name == "fast-reclaimer":
                        fast_inside.set()
                time.sleep(0.15)
                with active_lock:
                    active -= 1
        except BaseException as exc:
            errors.append(exc)

    late = threading.Thread(target=contend, args=("late-reclaimer",), name="late-reclaimer")
    fast = threading.Thread(target=contend, args=("fast-reclaimer",), name="fast-reclaimer")
    late.start()
    try:
        reached_unlink = unlink_checked.wait(2)
        if reached_unlink:
            fast.start()
            # The unprotected implementation lets this contender remove the stale
            # lock and enter while the first contender is paused after its check.
            fast_entered_before_release = fast_inside.wait(0.5)
    finally:
        release_unlink.set()
    late.join(3)
    if fast.ident is not None:
        fast.join(3)

    assert not late.is_alive() and not fast.is_alive()
    assert reached_unlink, f"the stale reclaimer did not reach unlink; thread errors: {errors!r}"
    assert fast_entered_before_release is False
    assert errors == []
    assert acquired == {"late-reclaimer", "fast-reclaimer"}
    assert max_active == 1


def test_stale_lock_recovery_guard_serializes_separate_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = tmp_path / "stale-process-race.lock"
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    dead_pid = child.pid
    child.wait(timeout=5)
    lock.write_text(
        json.dumps({"pid": dead_pid, "host": socket.gethostname(), "token": "stale"}),
        encoding="utf-8",
    )
    old = time.time() - 60
    os.utime(lock, (old, old))

    unlink_checked = threading.Event()
    release_unlink = threading.Event()
    errors: list[BaseException] = []
    original_unlink = Path.unlink

    def pause_before_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == lock and threading.current_thread().name == "paused-reclaimer":
            unlink_checked.set()
            if not release_unlink.wait(10):
                raise RuntimeError("test did not release the paused reclaimer")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", pause_before_unlink)

    def reclaim() -> None:
        try:
            with exclusive_lock(lock, timeout=15, stale_after=0.01):
                time.sleep(0.2)
        except BaseException as exc:
            errors.append(exc)

    late = threading.Thread(target=reclaim, name="paused-reclaimer")
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    entered = context.Event()
    contender = context.Process(target=_acquire_competing_lock, args=(str(lock), ready, entered))
    late.start()
    try:
        reached_unlink = unlink_checked.wait(5)
        if reached_unlink:
            contender.start()
            contender_ready = ready.wait(10)
            entered_before_release = entered.wait(0.5) if contender_ready else False
        else:
            contender_ready = False
            entered_before_release = False
    finally:
        release_unlink.set()
        late.join(16)
        if contender.pid is not None:
            contender.join(16)
            if contender.is_alive():
                contender.terminate()
                contender.join()

    assert reached_unlink, f"the stale reclaimer did not reach unlink; thread errors: {errors!r}"
    assert contender_ready, "the competing process did not start"
    assert entered_before_release is False
    assert not late.is_alive()
    assert contender.exitcode == 0
    assert entered.is_set()
    assert errors == []


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is unavailable on this platform")
def test_fork_waits_for_recovery_and_child_can_acquire_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = tmp_path / "stale-fork-race.lock"
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    dead_pid = child.pid
    child.wait(timeout=5)
    lock.write_text(
        json.dumps({"pid": dead_pid, "host": socket.gethostname(), "token": "stale"}),
        encoding="utf-8",
    )
    old = time.time() - 60
    os.utime(lock, (old, old))

    unlink_checked = threading.Event()
    release_unlink = threading.Event()
    original_unlink = Path.unlink

    def pause_before_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == lock and threading.current_thread().name == "fork-blocking-reclaimer":
            unlink_checked.set()
            if not release_unlink.wait(5):
                raise RuntimeError("test did not release the paused reclaimer")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", pause_before_unlink)
    errors: list[BaseException] = []
    fork_calling = threading.Event()
    fork_returned = threading.Event()
    child_exit_codes: list[int] = []
    real_fork = os.fork

    def signal_then_fork() -> int:
        fork_calling.set()
        return real_fork()

    monkeypatch.setattr(os, "fork", signal_then_fork)

    def reclaim() -> None:
        try:
            with exclusive_lock(lock, timeout=5, stale_after=0.01):
                time.sleep(0.2)
        except BaseException as exc:
            errors.append(exc)

    late = threading.Thread(target=reclaim, name="fork-blocking-reclaimer")

    def fork_and_wait() -> None:
        child_pid = os.fork()
        if child_pid == 0:
            try:
                with exclusive_lock(lock, timeout=5, stale_after=0.01):
                    pass
            except BaseException:
                os._exit(1)
            os._exit(0)
        fork_returned.set()
        _, status = os.waitpid(child_pid, 0)
        child_exit_codes.append(os.waitstatus_to_exitcode(status))

    forker = threading.Thread(target=fork_and_wait, name="fork-contender")
    late.start()
    contender_started = False
    try:
        assert unlink_checked.wait(2), "the stale reclaimer did not reach the compare/unlink window"
        forker.start()
        contender_started = True
        assert fork_calling.wait(2), "the forking thread did not reach os.fork"
        fork_returned_during_recovery = fork_returned.wait(0.2)
    finally:
        release_unlink.set()
        late.join(6)
        if contender_started:
            forker.join(10)

    assert not late.is_alive()
    assert contender_started and not forker.is_alive()
    assert fork_returned_during_recovery is False
    assert child_exit_codes == [0]
    assert errors == []


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
