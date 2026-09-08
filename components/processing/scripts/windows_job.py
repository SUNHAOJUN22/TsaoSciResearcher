from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

_CREATE_PROCESS_LOCK = threading.Lock()
_CREATE_SUSPENDED = 0x00000004
_KILL_ON_JOB_CLOSE = 0x00002000


class WindowsKillJob:
    """Unnamed kill-on-close Job Object owned by one CI command."""

    def __init__(self, handle: int) -> None:
        self.handle = handle
        self.bound = False
        self.closed = False


def _kernel32() -> Any:
    import ctypes

    return ctypes.WinDLL("kernel32", use_last_error=True)


def _close_handle(handle: int) -> str | None:
    if os.name != "nt" or not handle:
        return None

    import ctypes
    from ctypes import wintypes

    close_handle = _kernel32().CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    if close_handle(handle):
        return None
    return f"cannot close Windows handle {handle}: winerror {ctypes.get_last_error()}"


def _create_kill_job() -> tuple[WindowsKillJob | None, list[str]]:
    if os.name != "nt":
        return None, []

    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = _kernel32()
    create_job = kernel32.CreateJobObjectW
    create_job.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    create_job.restype = wintypes.HANDLE
    set_information = kernel32.SetInformationJobObject
    set_information.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    set_information.restype = wintypes.BOOL

    handle = create_job(None, None)
    if not handle:
        return None, [f"cannot create Windows Job Object: winerror {ctypes.get_last_error()}"]

    information = ExtendedLimitInformation()
    information.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
    if set_information(handle, 9, ctypes.byref(information), ctypes.sizeof(information)):
        return WindowsKillJob(int(handle)), []

    error = ctypes.get_last_error()
    issues = [f"cannot configure Windows Job Object: winerror {error}"]
    close_issue = _close_handle(int(handle))
    if close_issue:
        issues.append(close_issue)
    return None, issues


def _restricted_process_handle(pid: int) -> tuple[int | None, str | None]:
    import ctypes
    from ctypes import wintypes

    open_process = _kernel32().OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    handle = open_process(0x00001000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if handle:
        return int(handle), None
    return (
        None,
        f"cannot open restricted process handle for PID {pid}: winerror {ctypes.get_last_error()}",
    )


def _assign(
    job: WindowsKillJob, process_handle: int, pid: int, test_fault: str | None
) -> list[str]:
    import ctypes
    from ctypes import wintypes

    issues: list[str] = []
    assignment_handle = process_handle
    restricted_handle: int | None = None
    if test_fault == "assign_access_denied":
        restricted_handle, issue = _restricted_process_handle(pid)
        if issue:
            return [issue]
        assert restricted_handle is not None
        assignment_handle = restricted_handle
    elif test_fault is not None:
        return [f"unsupported Windows Job Object test fault: {test_fault}"]

    assign = _kernel32().AssignProcessToJobObject
    assign.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    assign.restype = wintypes.BOOL
    if assign(job.handle, assignment_handle):
        job.bound = True
        if test_fault == "assign_access_denied":
            issues.append("restricted-handle assignment unexpectedly succeeded")
    else:
        issues.append(
            f"cannot bind PID {pid} to Windows Job Object: winerror {ctypes.get_last_error()}"
        )

    if restricted_handle is not None:
        close_issue = _close_handle(restricted_handle)
        if close_issue:
            issues.append(close_issue)
    return issues


def _resume(thread_handle: int, pid: int) -> str | None:
    import ctypes
    from ctypes import wintypes

    resume = _kernel32().ResumeThread
    resume.argtypes = [wintypes.HANDLE]
    resume.restype = wintypes.DWORD
    previous_count = resume(thread_handle)
    if previous_count == 0xFFFFFFFF:
        return f"cannot resume suspended PID {pid}: winerror {ctypes.get_last_error()}"
    if previous_count == 0:
        return f"PID {pid} was not suspended before Job Object binding"
    return None


def popen_in_kill_job(
    command: list[str],
    *,
    cwd: Path,
    log: Any,
    test_fault: str | None = None,
) -> tuple[subprocess.Popen[object], WindowsKillJob | None, list[str]]:
    """Create suspended, bind before first instruction, then resume."""
    if os.name != "nt":
        raise RuntimeError("Windows Job Object launcher requires Windows")

    import _winapi

    job, issues = _create_kill_job()
    if job is None:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return process, None, issues

    launch_issues = list(issues)

    try:
        with _CREATE_PROCESS_LOCK:
            # Capture the native function only after acquiring the process-wide lock.
            # Capturing it earlier lets a concurrent caller retain another caller's
            # temporary wrapper, causing nested assignment/resume and a false cleanup
            # failure even though the child is correctly contained.
            original_create_process = _winapi.CreateProcess

            def create_suspended(
                application_name: Any,
                command_line: Any,
                process_attributes: Any,
                thread_attributes: Any,
                inherit_handles: Any,
                creation_flags: int,
                environment: Any,
                current_directory: Any,
                startup_info: Any,
            ) -> tuple[int, int, int, int]:
                process_handle, thread_handle, pid, thread_id = original_create_process(
                    application_name,
                    command_line,
                    process_attributes,
                    thread_attributes,
                    inherit_handles,
                    creation_flags | _CREATE_SUSPENDED,
                    environment,
                    current_directory,
                    startup_info,
                )
                binding_issues = _assign(job, int(process_handle), int(pid), test_fault)
                if binding_issues:
                    launch_issues.extend(binding_issues)
                    try:
                        _winapi.TerminateProcess(process_handle, 125)
                    except OSError as exc:
                        launch_issues.append(f"cannot terminate uncontained PID {pid}: {exc}")
                        resume_issue = _resume(int(thread_handle), int(pid))
                        if resume_issue:
                            launch_issues.append(resume_issue)
                    return process_handle, thread_handle, pid, thread_id

                resume_issue = _resume(int(thread_handle), int(pid))
                if resume_issue:
                    launch_issues.append(resume_issue)
                    try:
                        _winapi.TerminateProcess(process_handle, 125)
                    except OSError as exc:
                        launch_issues.append(f"cannot terminate unresumable PID {pid}: {exc}")
                return process_handle, thread_handle, pid, thread_id

            _winapi.CreateProcess = create_suspended
            try:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            finally:
                _winapi.CreateProcess = original_create_process
    except BaseException:
        close_issue = _close_handle(job.handle)
        job.closed = True
        if close_issue:
            launch_issues.append(close_issue)
        raise
    return process, job, launch_issues


def _member_handles(job: WindowsKillJob) -> tuple[list[tuple[int, int]], list[str]]:
    import ctypes
    from ctypes import wintypes

    if not job.bound or job.closed:
        return [], []

    kernel32 = _kernel32()
    query = kernel32.QueryInformationJobObject
    query.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    query.restype = wintypes.BOOL
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE

    capacity = 64
    process_ids: list[int] = []
    while capacity <= 4096:
        pointer_size = ctypes.sizeof(ctypes.c_size_t)
        buffer = ctypes.create_string_buffer(8 + capacity * pointer_size)
        returned = wintypes.DWORD()
        if query(job.handle, 3, buffer, len(buffer), ctypes.byref(returned)):
            count = wintypes.DWORD.from_buffer(buffer, 4).value
            process_ids = [
                int(ctypes.c_size_t.from_buffer(buffer, 8 + index * pointer_size).value)
                for index in range(min(count, capacity))
            ]
            break
        error = ctypes.get_last_error()
        if error != 234:  # ERROR_MORE_DATA
            return [], [f"cannot query Windows Job Object members: winerror {error}"]
        capacity *= 2
    else:
        return [], ["Windows Job Object exceeded the 4096-process cleanup limit"]

    handles: list[tuple[int, int]] = []
    issues: list[str] = []
    for pid in sorted(set(process_ids)):
        if pid <= 0 or pid == os.getpid():
            continue
        handle = open_process(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            handles.append((pid, int(handle)))
        else:
            error = ctypes.get_last_error()
            if error not in {87, 1168}:
                issues.append(f"cannot capture Windows Job Object PID {pid}: winerror {error}")
    return handles, issues


def close_kill_job(job: WindowsKillJob | None) -> list[str]:
    """Close last job handle, triggering kill-on-close, and verify members exit."""
    if os.name != "nt" or job is None or job.closed:
        return []

    import ctypes
    from ctypes import wintypes

    process_handles, issues = _member_handles(job)
    close_issue = _close_handle(job.handle)
    job.closed = True
    if close_issue:
        issues.append(close_issue)

    wait = _kernel32().WaitForSingleObject
    wait.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    wait.restype = wintypes.DWORD
    deadline = time.monotonic() + 5.0
    for pid, handle in process_handles:
        remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
        result = wait(handle, remaining_ms)
        if result == 0x00000102:
            issues.append(f"Windows Job Object PID {pid} did not exit after handle close")
        elif result == 0xFFFFFFFF:
            issues.append(
                f"cannot wait for Windows Job Object PID {pid}: winerror {ctypes.get_last_error()}"
            )
        handle_issue = _close_handle(handle)
        if handle_issue:
            issues.append(handle_issue)
    return sorted(set(issues))
