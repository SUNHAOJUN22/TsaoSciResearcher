"""Non-destructive owner queries and descriptor cleanup across supported systems."""

from __future__ import annotations

import ctypes
import errno
import json
import multiprocessing as mp
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tsao_researcher import io, state
from tsao_researcher.errors import LockTimeoutError


def _short_lock(path: str | Path) -> Any:
    return io.exclusive_lock(path, timeout=0.15, stale_after=0.01)


def _paused_transition(root: str, entered: Any, release: Any, result: Any) -> None:
    state.exclusive_lock = _short_lock
    original = state._event_payload

    def pause(*args: Any, **kwargs: Any) -> dict[str, Any]:
        event = original(*args, **kwargs)
        entered.set()
        if not release.wait(15):
            raise RuntimeError("fixture did not release the transaction")
        return event

    state._event_payload = pause
    try:
        result.send(state.transition(root, "planned", "live owner")["status"])
    finally:
        result.close()


def test_public_transition_protects_a_live_owner_and_preserves_the_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = state.initialize("owner query", "Is the live transaction preserved?", tmp_path)
    context = mp.get_context("spawn")
    entered, release = context.Event(), context.Event()
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(target=_paused_transition, args=(str(root), entered, release, sender))
    worker.start()
    sender.close()
    try:
        assert entered.wait(10)
        time.sleep(0.04)
        monkeypatch.setattr(state, "exclusive_lock", _short_lock)
        with pytest.raises(LockTimeoutError):
            state.transition(root, "planned", "contender must wait")
        assert worker.is_alive()
    finally:
        release.set()
        worker.join(10)
        if worker.is_alive():
            worker.terminate()  # Only this fixture's own subprocess.
            worker.join(5)
            pytest.fail("fixture child did not exit")
    try:
        assert worker.exitcode == 0 and receiver.poll(1)
        assert receiver.recv() == "planned"
    finally:
        receiver.close()
    assert state.verify(root)["events"] == 2
    assert [row["reason"] for row in io.read_jsonl(root / "state/events.jsonl")] == [
        "project initialized",
        "live owner",
    ]
    state.transition(root, "running", "next transaction")
    assert state.verify(root)["events"] == 3


def _owner_file(path: Path, pid: int) -> None:
    path.write_text(
        json.dumps({"pid": pid, "host": socket.gethostname(), "token": "fixture"}), encoding="utf-8"
    )


def test_windows_dispatch_never_calls_the_signal_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock = tmp_path / "owner.lock"
    _owner_file(lock, 12345)
    queried: list[int] = []

    def query(pid: int) -> bool:
        queried.append(pid)
        return True

    def forbidden(*args: Any) -> None:
        pytest.fail("a Windows liveness query must not call os.kill")

    monkeypatch.setattr(io, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(io, "_windows_process_is_alive", query)
    monkeypatch.setattr(io.os, "kill", forbidden)
    assert io._lock_owner_is_alive(lock)
    assert queried == [12345]


@pytest.mark.parametrize("exit_code", [0, 259])
def test_owned_process_remains_alive_then_its_exit_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    lock = tmp_path / "owned.lock"

    def forbidden(*args: Any) -> None:
        pytest.fail("Windows process observation signaled the child")

    if sys.platform == "win32":
        monkeypatch.setattr(io.os, "kill", forbidden)
    with subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; print('ready', flush=True); sys.stdin.read(1); sys.exit(int(sys.argv[1]))",
            str(exit_code),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    ) as child:
        assert child.stdout is not None and child.stdout.readline().strip() == "ready"
        _owner_file(lock, child.pid)
        assert io._lock_owner_is_alive(lock)
        assert child.poll() is None
        child.communicate("x", timeout=10)
        assert child.returncode == (exit_code if sys.platform == "win32" else exit_code % 256)
        assert not io._lock_owner_is_alive(lock)
        old = time.time() - 60
        os.utime(lock, (old, old))
        with io.exclusive_lock(lock, timeout=0.1, stale_after=0.01):
            assert lock.exists()


@pytest.mark.parametrize(
    "payload",
    [b"", b"broken", b"\xff", b"{}", b'{"pid":true}', b'{"pid":123,"host":"foreign.invalid"}'],
)
def test_unknown_or_foreign_ownership_does_not_query_a_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    lock = tmp_path / "unknown.lock"
    lock.write_bytes(payload)

    def forbidden(*args: Any) -> None:
        pytest.fail("unknown ownership must stay protected without a process query")

    monkeypatch.setattr(io.os, "kill", forbidden)
    monkeypatch.setattr(io, "_windows_process_is_alive", forbidden)
    assert io._lock_owner_is_alive(lock)
    assert lock.read_bytes() == payload


@pytest.mark.parametrize("pid", [0, -1])
def test_nonpositive_lock_pid_stays_protected(tmp_path: Path, pid: int) -> None:
    lock = tmp_path / "nonpositive-owner.lock"
    _owner_file(lock, pid)
    payload = lock.read_bytes()
    old = time.time() - 60
    os.utime(lock, (old, old))

    with pytest.raises(LockTimeoutError), io.exclusive_lock(lock, timeout=0.05, stale_after=0.01):
        pytest.fail("unknown process ownership must not authorize lock recovery")

    assert lock.read_bytes() == payload


def _mock_windows_api(
    monkeypatch: pytest.MonkeyPatch,
    *,
    handle: int | None = (1 << 40) + 7,
    owner_pid: int = 123,
    wait_result: int = 258,
    error_code: int = 0,
    failure: str | None = None,
) -> list[tuple[str, tuple[Any, ...]]]:
    calls: list[tuple[str, tuple[Any, ...]]] = []

    def call(name: str, value: Any, *args: Any) -> Any:
        calls.append((name, args))
        if name == failure:
            raise OSError("injected process query failure")
        return value

    api = SimpleNamespace(
        OpenProcess=lambda *args: call("OpenProcess", handle, *args),
        GetProcessId=lambda *args: call("GetProcessId", owner_pid, *args),
        WaitForSingleObject=lambda *args: call("WaitForSingleObject", wait_result, *args),
        CloseHandle=lambda *args: call("CloseHandle", True, *args),
    )
    monkeypatch.setattr(io, "_windows_process_api", lambda: api)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: error_code, raising=False)
    return calls


@pytest.mark.parametrize(
    ("handle", "owner_pid", "wait_result", "error_code", "expected"),
    [
        (None, 0, 0, 87, False),
        (None, 0, 0, 5, True),
        ((1 << 40) + 7, 123, 0, 0, False),
        ((1 << 40) + 7, 123, 258, 0, True),
        ((1 << 40) + 7, 123, 0xFFFFFFFF, 0, True),
        ((1 << 40) + 7, 999, 0, 0, True),
    ],
    ids=["absent", "denied", "exited", "live", "wait-failed", "identity-mismatch"],
)
def test_windows_queries_validate_identity_wait_without_delay_and_close_handles(
    monkeypatch: pytest.MonkeyPatch,
    handle: int | None,
    owner_pid: int,
    wait_result: int,
    error_code: int,
    expected: bool,
) -> None:
    calls = _mock_windows_api(
        monkeypatch, handle=handle, owner_pid=owner_pid, wait_result=wait_result, error_code=error_code
    )
    assert io._windows_process_is_alive(123) is expected
    assert calls[0] == ("OpenProcess", (0x00101000, False, 123))
    if handle:
        assert calls[-1] == ("CloseHandle", (handle,))
        if owner_pid == 123:
            assert ("WaitForSingleObject", (handle, 0)) in calls
    else:
        assert len(calls) == 1


@pytest.mark.parametrize("pid", [0, -1, 1 << 40])
def test_windows_process_identity_cannot_be_truncated(monkeypatch: pytest.MonkeyPatch, pid: int) -> None:
    calls = _mock_windows_api(monkeypatch)
    assert io._windows_process_is_alive(pid)
    assert calls == []


@pytest.mark.parametrize("failure", ["GetProcessId", "WaitForSingleObject", "CloseHandle"])
def test_process_query_errors_keep_the_lock_occupied_and_attempt_handle_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    lock = tmp_path / "query-failure.lock"
    _owner_file(lock, 123)
    calls = _mock_windows_api(monkeypatch, failure=failure)
    monkeypatch.setattr(io, "sys", SimpleNamespace(platform="win32"))
    assert io._lock_owner_is_alive(lock)
    assert calls[-1][0] == "CloseHandle"
    assert sum(name == "OpenProcess" for name, _ in calls) == sum(name == "CloseHandle" for name, _ in calls)


def test_failed_append_descriptor_inspection_closes_file_and_preserves_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "records.jsonl"
    target.write_text('{"id":1}\n', encoding="utf-8")
    original = target.read_bytes()
    opened: list[int] = []
    injected: set[int] = set()
    real_open, real_stat = os.open, os.fstat

    def track_open(path: Any, flags: int, mode: int = 0o777) -> int:
        fd = real_open(path, flags, mode)
        if Path(path) == target:
            opened.append(fd)
        return fd

    def inspect(fd: int) -> os.stat_result:
        if fd in opened and fd not in injected:
            injected.add(fd)
            raise OSError("injected append descriptor inspection failure")
        return real_stat(fd)

    with monkeypatch.context() as patch:
        patch.setattr(io.os, "open", track_open)
        patch.setattr(io.os, "fstat", inspect)
        with pytest.raises(OSError, match="append descriptor inspection failure"):
            io.append_jsonl(target, {"id": 2})
    assert len(opened) == 1
    closed_error = None
    try:
        os.fstat(opened[0])
    except OSError as exc:
        closed_error = exc.errno
    else:
        os.close(opened[0])
    assert closed_error == errno.EBADF
    assert target.read_bytes() == original
    io.append_jsonl(target, {"id": 2})
    assert io.read_jsonl(target) == [{"id": 1}, {"id": 2}]
