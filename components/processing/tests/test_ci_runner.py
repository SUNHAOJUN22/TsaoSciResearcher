from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.run_ci import RUFF_PATHS, TEST_PATHS, run


def test_ci_runner_covers_all_specialist_suites() -> None:
    expected = {
        "tests",
        "skills/process-general/tests",
        "skills/epdm/tests",
        "skills/poe/tests",
        "skills/polymer-general/tests",
    }
    assert set(TEST_PATHS) == expected
    assert {"tests", "skills/process-general", "skills/poe", "skills/polymer-general"} <= set(
        RUFF_PATHS
    )


def test_ci_runner_records_success(tmp_path: Path) -> None:
    result = run([sys.executable, "-c", "print('ok')"], cwd=tmp_path, timeout=5)
    assert result["returncode"] == 0
    assert result["timed_out"] is False
    assert result["cleanup_issues"] == []
    if os.name == "nt":
        assert result["process_control"] == "WINDOWS_JOB_OBJECT"
        assert result["job_object_bound"] is True
    else:
        assert result["process_control"] == "POSIX_PROCESS_GROUP"
        assert result["job_object_bound"] is False
    assert "ok" in result["output"]


def test_ci_runner_timeout_returns_124(tmp_path: Path) -> None:
    result = run(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        timeout=1,
    )
    assert result["returncode"] == 124
    assert result["timed_out"] is True
    assert result["cleanup_issues"] == []
    if os.name == "nt":
        assert result["process_control"] == "WINDOWS_JOB_OBJECT"
        assert result["job_object_bound"] is True
    else:
        assert result["process_control"] == "POSIX_PROCESS_GROUP"
        assert result["job_object_bound"] is False


def _gone_or_zombie(pid: int) -> bool:
    if os.name == "nt":
        status = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            text=True,
            capture_output=True,
            check=False,
        )
        return status.returncode != 0 or f'"{pid}"' not in status.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    if os.name == "posix":
        status = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            text=True,
            capture_output=True,
            check=False,
        )
        return status.returncode != 0 or status.stdout.strip().startswith("Z")
    return False


def _assert_process_gone(pid: int) -> None:
    for _ in range(100):
        if _gone_or_zombie(pid):
            return
        time.sleep(0.05)
    pytest.fail(f"descendant process remained live: {pid}")


def _posix_shell() -> str:
    shell = shutil.which("sh")
    assert shell is not None, "POSIX process-group tests require sh"
    return shell


@pytest.mark.skipif(os.name != "posix", reason="process-group assertion is POSIX-specific")
def test_ci_runner_timeout_kills_descendants(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    target = shlex.quote(str(child_pid_file))
    code = f"sleep 30 & child=$!; printf '%s' \"$child\" > {target}; wait"
    result = run([_posix_shell(), "-c", code], cwd=tmp_path, timeout=2)
    assert result["timed_out"] is True
    assert result["cleanup_issues"] == []
    assert child_pid_file.is_file(), "child PID handshake was not written before timeout"
    _assert_process_gone(int(child_pid_file.read_text()))


@pytest.mark.skipif(os.name != "posix", reason="process-group assertion is POSIX-specific")
def test_ci_runner_success_reaps_lingering_descendants(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child-success.pid"
    target = shlex.quote(str(child_pid_file))
    code = f"sleep 30 & child=$!; printf '%s' \"$child\" > {target}"
    result = run([_posix_shell(), "-c", code], cwd=tmp_path, timeout=5)
    assert result["returncode"] == 0
    assert result["cleanup_issues"] == []
    assert child_pid_file.is_file(), "child PID handshake was not written"
    _assert_process_gone(int(child_pid_file.read_text()))


@pytest.mark.skipif(os.name != "nt", reason="Windows descendant cleanup requires Win32 APIs")
def test_ci_runner_success_reaps_lingering_windows_descendants(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child-success-windows.pid"
    child_code = "import time; time.sleep(30)"
    parent_code = (
        "import subprocess, sys; "
        "from pathlib import Path; "
        f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        f"Path({str(child_pid_file)!r}).write_text(str(child.pid), encoding='utf-8')"
    )
    result = run([sys.executable, "-c", parent_code], cwd=tmp_path, timeout=5)
    assert result["returncode"] == 0, result
    assert result["process_control"] == "WINDOWS_JOB_OBJECT"
    assert result["job_object_bound"] is True
    assert result["cleanup_issues"] == []
    assert child_pid_file.is_file(), "child PID handshake was not written"
    _assert_process_gone(int(child_pid_file.read_text(encoding="utf-8")))


def _write_windows_nested_process_scripts(
    tmp_path: Path, *, parent_waits: bool
) -> tuple[Path, Path, Path]:
    child_pid_file = tmp_path / "nested-child.pid"
    grandchild_pid_file = tmp_path / "nested-grandchild.pid"
    child_script = tmp_path / "nested-child.py"
    parent_script = tmp_path / "nested-parent.py"
    child_script.write_text(
        "import subprocess, sys, time\n"
        "from pathlib import Path\n"
        "grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        f"Path({str(grandchild_pid_file)!r}).write_text(str(grandchild.pid), encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    parent_lines = [
        "import subprocess, sys, time",
        "from pathlib import Path",
        f"child = subprocess.Popen([sys.executable, {str(child_script)!r}])",
        f"Path({str(child_pid_file)!r}).write_text(str(child.pid), encoding='utf-8')",
        f"grandchild_pid_file = Path({str(grandchild_pid_file)!r})",
        "for _ in range(250):",
        "    if grandchild_pid_file.is_file():",
        "        break",
        "    time.sleep(0.02)",
        "else:",
        "    raise RuntimeError('grandchild PID handshake was not written')",
    ]
    if parent_waits:
        parent_lines.append("time.sleep(30)")
    parent_script.write_text("\n".join(parent_lines) + "\n", encoding="utf-8")
    return parent_script, child_pid_file, grandchild_pid_file


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object coverage requires Windows")
def test_ci_runner_windows_job_kills_multilevel_descendants_on_success(tmp_path: Path) -> None:
    parent_script, child_pid_file, grandchild_pid_file = _write_windows_nested_process_scripts(
        tmp_path,
        parent_waits=False,
    )
    result = run([sys.executable, str(parent_script)], cwd=tmp_path, timeout=8)
    assert result["returncode"] == 0, result
    assert result["process_control"] == "WINDOWS_JOB_OBJECT"
    assert result["job_object_bound"] is True
    assert result["cleanup_issues"] == []
    assert child_pid_file.is_file()
    assert grandchild_pid_file.is_file()
    _assert_process_gone(int(child_pid_file.read_text(encoding="utf-8")))
    _assert_process_gone(int(grandchild_pid_file.read_text(encoding="utf-8")))


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object coverage requires Windows")
def test_ci_runner_windows_job_timeout_kills_multilevel_descendants(tmp_path: Path) -> None:
    parent_script, child_pid_file, grandchild_pid_file = _write_windows_nested_process_scripts(
        tmp_path,
        parent_waits=True,
    )
    result = run([sys.executable, str(parent_script)], cwd=tmp_path, timeout=2)
    assert result["returncode"] == 124, result
    assert result["timed_out"] is True
    assert result["process_control"] == "WINDOWS_JOB_OBJECT"
    assert result["job_object_bound"] is True
    assert result["cleanup_issues"] == []
    assert child_pid_file.is_file()
    assert grandchild_pid_file.is_file()
    _assert_process_gone(int(child_pid_file.read_text(encoding="utf-8")))
    _assert_process_gone(int(grandchild_pid_file.read_text(encoding="utf-8")))


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object coverage requires Windows")
def test_ci_runner_windows_job_concurrent_launches_do_not_nest_wrappers(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def execute(index: int) -> dict[str, object]:
        return run(
            [sys.executable, "-c", f"print({index})"],
            cwd=tmp_path,
            timeout=5,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(execute, range(16)))

    assert all(result["returncode"] == 0 for result in results), results
    assert all(result["process_control"] == "WINDOWS_JOB_OBJECT" for result in results)
    assert all(result["job_object_bound"] is True for result in results)
    assert all(result["cleanup_issues"] == [] for result in results), results


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object coverage requires Windows")
def test_ci_runner_windows_job_fast_exit_has_no_leak(tmp_path: Path) -> None:
    child_pids: list[int] = []
    for index in range(8):
        child_pid_file = tmp_path / f"fast-child-{index}.pid"
        parent_code = (
            "import subprocess, sys; "
            "from pathlib import Path; "
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            f"Path({str(child_pid_file)!r}).write_text(str(child.pid), encoding='utf-8')"
        )
        result = run([sys.executable, "-c", parent_code], cwd=tmp_path, timeout=5)
        assert result["returncode"] == 0, result
        assert result["process_control"] == "WINDOWS_JOB_OBJECT"
        assert result["job_object_bound"] is True
        assert result["cleanup_issues"] == []
        assert child_pid_file.is_file()
        child_pids.append(int(child_pid_file.read_text(encoding="utf-8")))
    for pid in child_pids:
        _assert_process_gone(pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object coverage requires Windows")
def test_ci_runner_windows_job_assignment_denial_fails_closed_and_falls_back(
    tmp_path: Path,
) -> None:
    child_pid_file = tmp_path / "denied-child.pid"
    parent_code = (
        "import subprocess, sys; "
        "from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"Path({str(child_pid_file)!r}).write_text(str(child.pid), encoding='utf-8')"
    )
    result = run(
        [sys.executable, "-c", parent_code],
        cwd=tmp_path,
        timeout=5,
        _windows_job_test_fault="assign_access_denied",
    )
    assert result["returncode"] == 125, result
    assert result["timed_out"] is False
    assert result["process_control"] == "WINDOWS_TOOLHELP_FALLBACK"
    assert result["job_object_bound"] is False
    assert any(
        "cannot bind PID" in issue and "winerror 5" in issue for issue in result["cleanup_issues"]
    )
    assert not child_pid_file.exists(), "uncontained command executed after binding denial"
