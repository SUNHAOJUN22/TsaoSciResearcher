from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tsao  # noqa: E402
from scripts.windows_job import WindowsKillJob, close_kill_job, popen_in_kill_job  # noqa: E402

__version__ = tsao.__version__

TEST_PATHS = (
    "tests",
    "skills/process-general/tests",
    "skills/epdm/tests",
    "skills/poe/tests",
    "skills/polymer-general/tests",
)
RUFF_PATHS = (
    "tsao",
    "tests",
    "scripts",
    "skills/process-general",
    "skills/epdm",
    "skills/poe",
    "skills/polymer-general",
)
GENERATED_RELEASE_DIRECTORIES = ("build", "dist", "wheelhouse")


def _terminate_process_tree(process: subprocess.Popen[object]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        if process.poll() is None:
            try:
                process.wait(timeout=5)
                return
            except subprocess.TimeoutExpired:
                pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    elif os.name == "nt" and process.poll() is None:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    elif process.poll() is None:
        process.kill()
    if process.poll() is None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _cleanup_successful_process_group(process: subprocess.Popen[object]) -> None:
    if os.name != "posix":
        return
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _windows_descendant_pids(root_pid: int) -> list[int]:
    """Return the live Windows descendant tree for a process ID."""
    if os.name != "nt":
        return []

    import ctypes
    from ctypes import wintypes

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    create_snapshot.restype = wintypes.HANDLE
    process_first = kernel32.Process32FirstW
    process_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W)]
    process_first.restype = wintypes.BOOL
    process_next = kernel32.Process32NextW
    process_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W)]
    process_next.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    snapshot = create_snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")

    children: dict[int, list[int]] = {}
    try:
        entry = ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(ProcessEntry32W)
        if not process_first(snapshot, ctypes.byref(entry)):
            error = ctypes.get_last_error()
            if error == 18:  # ERROR_NO_MORE_FILES
                return []
            raise OSError(error, "Process32FirstW failed")
        while True:
            pid = int(entry.th32ProcessID)
            parent_pid = int(entry.th32ParentProcessID)
            children.setdefault(parent_pid, []).append(pid)
            if not process_next(snapshot, ctypes.byref(entry)):
                error = ctypes.get_last_error()
                if error != 18:  # ERROR_NO_MORE_FILES
                    raise OSError(error, "Process32NextW failed")
                break
    finally:
        close_handle(snapshot)

    descendants: list[int] = []
    queue = deque(children.get(root_pid, ()))
    seen = {root_pid}
    while queue:
        pid = queue.popleft()
        if pid in seen or pid == os.getpid():
            continue
        seen.add(pid)
        descendants.append(pid)
        queue.extend(children.get(pid, ()))
    return descendants


def _terminate_windows_pid(pid: int) -> str | None:
    if os.name != "nt":
        return None

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    terminate_process = kernel32.TerminateProcess
    terminate_process.argtypes = [wintypes.HANDLE, wintypes.UINT]
    terminate_process.restype = wintypes.BOOL
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    wait_for_single_object.restype = wintypes.DWORD
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    handle = open_process(0x0001 | 0x00100000, False, pid)  # TERMINATE | SYNCHRONIZE
    if not handle:
        error = ctypes.get_last_error()
        if error in {87, 1168}:  # invalid parameter / not found
            return None
        return f"cannot open descendant PID {pid}: winerror {error}"
    try:
        if not terminate_process(handle, 1):
            error = ctypes.get_last_error()
            if wait_for_single_object(handle, 0) != 0:  # WAIT_OBJECT_0
                return f"cannot terminate descendant PID {pid}: winerror {error}"
        wait_result = wait_for_single_object(handle, 5_000)
        if wait_result == 0x00000102:  # WAIT_TIMEOUT
            return f"descendant PID {pid} did not exit after termination"
        if wait_result == 0xFFFFFFFF:  # WAIT_FAILED
            return f"cannot wait for descendant PID {pid}: winerror {ctypes.get_last_error()}"
    finally:
        close_handle(handle)
    return None


def _cleanup_windows_descendants(root_pid: int) -> list[str]:
    """Kill descendants left behind after a Windows command exits."""
    if os.name != "nt":
        return []
    issues: list[str] = []
    for _ in range(4):
        try:
            descendants = _windows_descendant_pids(root_pid)
        except OSError as exc:
            return [f"cannot enumerate Windows descendants for PID {root_pid}: {exc}"]
        if not descendants:
            return sorted(set(issues))
        for pid in reversed(descendants):
            issue = _terminate_windows_pid(pid)
            if issue:
                issues.append(issue)
        time.sleep(0.05)
    try:
        remaining = _windows_descendant_pids(root_pid)
    except OSError as exc:
        issues.append(f"cannot verify Windows descendant cleanup for PID {root_pid}: {exc}")
    else:
        if remaining:
            issues.append(f"Windows descendants remained live for PID {root_pid}: {remaining}")
    return sorted(set(issues))


def run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 300,
    _windows_job_test_fault: str | None = None,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if _windows_job_test_fault is not None and os.name != "nt":
        raise ValueError("Windows Job Object test faults require Windows")

    started = time.perf_counter()
    cleanup_issues: list[str] = []
    process_control = "POSIX_PROCESS_GROUP" if os.name == "posix" else "DIRECT_PROCESS"
    job: WindowsKillJob | None = None
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
        if os.name == "nt":
            process, job, launch_issues = popen_in_kill_job(
                command,
                cwd=cwd,
                log=log,
                test_fault=_windows_job_test_fault,
            )
            cleanup_issues.extend(launch_issues)
            process_control = (
                "WINDOWS_JOB_OBJECT"
                if job is not None and job.bound
                else "WINDOWS_TOOLHELP_FALLBACK"
            )
        else:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=os.name == "posix",
            )
        try:
            returncode = process.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = 124
        finally:
            if os.name == "posix":
                if process.poll() is None:
                    _terminate_process_tree(process)
                if process.poll() is not None:
                    _cleanup_successful_process_group(process)
            elif os.name == "nt":
                job_was_bound = job is not None and job.bound
                job_issues = close_kill_job(job)
                cleanup_issues.extend(job_issues)
                if process.poll() is None:
                    _terminate_process_tree(process)
                if not job_was_bound or job_issues:
                    cleanup_issues.extend(_cleanup_windows_descendants(process.pid))
            elif process.poll() is None:
                _terminate_process_tree(process)
        cleanup_issues = sorted(set(cleanup_issues))
        if cleanup_issues and returncode == 0:
            returncode = 125
        log.flush()
        log.seek(0)
        output = log.read()[-20000:]
    return {
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_s": time.perf_counter() - started,
        "output": output,
        "process_control": process_control,
        "job_object_bound": bool(job is not None and job.bound),
        "cleanup_issues": cleanup_issues,
    }


def _run_command(command: list[str], root: Path) -> dict[str, Any]:
    return run(command, cwd=root)


def _remove_generated_release_directories(root: Path) -> None:
    """Start the qualification suite from a source-clean repository tree."""
    for name in GENERATED_RELEASE_DIRECTORIES:
        shutil.rmtree(root / name, ignore_errors=True)
    for path in root.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)


def main() -> int:
    root = ROOT
    _remove_generated_release_directories(root)
    checks = [
        run(
            [sys.executable, "-m", "compileall", "-q", "-j", "0", "tsao", "scripts", "skills"],
            cwd=root,
        ),
        run([sys.executable, "-m", "coverage", "erase"], cwd=root),
        run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--branch",
                "--source=skills.poe,skills.epdm,tsao.process_package,tsao.skillpacks",
                "--omit=skills/poe/scripts/*,skills/epdm/scripts/*",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *TEST_PATHS,
            ],
            cwd=root,
        ),
        run(
            [sys.executable, "-m", "coverage", "report", "--fail-under=75"],
            cwd=root,
        ),
        run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('.coverage').unlink(missing_ok=True); Path('coverage.xml').unlink(missing_ok=True)",
            ],
            cwd=root,
        ),
    ]
    parallel_commands = [
        [sys.executable, "scripts/audit_capabilities.py"],
        [sys.executable, "skills/epdm/scripts/audit_epdm.py"],
        [sys.executable, "skills/poe/scripts/audit_p0.py", "--root", "."],
        [sys.executable, "skills/poe/scripts/audit_p1.py", "--root", "."],
        [sys.executable, "-m", "tsao.cli", "doctor", "--root", ".", "--profile", "core"],
        [sys.executable, "-m", "ruff", "check", *RUFF_PATHS],
    ]
    with ThreadPoolExecutor(max_workers=len(parallel_commands)) as executor:
        checks.extend(executor.map(lambda command: _run_command(command, root), parallel_commands))

    passed = all(check["returncode"] == 0 for check in checks)
    report = {
        "version": __version__,
        "pass": passed,
        "checks": checks,
        "wall_clock_sum_s": sum(float(check["duration_s"]) for check in checks),
        "artifact_software_qualification": "PASS" if passed else "FAIL",
        "universal_process_package_status": "EXECUTABLE_ALPHA" if passed else "HOLD",
        "skillpack_delivery_status": "FOUR_SKILLS_INSTALLED_VERIFIED" if passed else "HOLD",
        "epdm_software_status": "EXECUTABLE_FLAGSHIP_ALPHA_P1_REFERENCE" if passed else "HOLD",
        "poe_software_status": ("EXECUTABLE_SPECIALIST_ALPHA_P1_REFERENCE" if passed else "HOLD"),
        "poe_scientific_execution": "UNDER_DISTILLATION",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }
    target = root / "reports/runtime/CI_RESULTS.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
