from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..errors import SecurityError

_PORTABLE_ENVIRONMENT_KEYS = ("PATH", "HOME", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE")
_WINDOWS_ENVIRONMENT_KEYS = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "SYSTEMDRIVE",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
)
_SAFE_OVERRIDE_KEYS = frozenset(
    {
        "CUDA_VISIBLE_DEVICES",
        "HIP_VISIBLE_DEVICES",
        "ROCR_VISIBLE_DEVICES",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    }
)
_READ_ONLY_PROBE_ARGUMENTS = frozenset(
    {
        ("--version",),
        ("-version",),
        ("version",),
        ("info",),
        ("info", "--version"),
        ("-v",),
        ("-h",),
        ("--help",),
        ("-help",),
        ("mdrun", "-h"),
    }
)
_MAX_PROBE_OUTPUT_CHARS = 65_536

_PROBE_ARGUMENTS: dict[str, frozenset[tuple[str, ...]]] = {
    "nvidia-smi": frozenset(
        {
            (
                "--query-gpu=index,name,memory.total,compute_cap",
                "--format=csv,noheader,nounits",
            ),
            (
                "--query-gpu=index,name,memory.total",
                "--format=csv,noheader,nounits",
            ),
        }
    ),
    "rocminfo": frozenset({()}),
    "sycl-ls": frozenset({()}),
    "clinfo": frozenset({("-l",)}),
}
_PYTHON_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_PROCESS_EXECUTION_PERMIT = object()


def _override_allowed(key: str) -> bool:
    normalized = key.upper()
    return (
        normalized in _SAFE_OVERRIDE_KEYS
        or normalized in _PORTABLE_ENVIRONMENT_KEYS
        or normalized in _WINDOWS_ENVIRONMENT_KEYS
        or normalized.startswith("TSAO_")
    )


def _subprocess_environment(
    overrides: Mapping[str, str] | None = None,
    *,
    parent: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> dict[str, str]:
    source = os.environ if parent is None else parent
    platform = os.name if platform_name is None else platform_name
    allowed = _PORTABLE_ENVIRONMENT_KEYS + (_WINDOWS_ENVIRONMENT_KEYS if platform == "nt" else ())
    if platform == "nt":
        source_by_name = {str(key).casefold(): str(value) for key, value in source.items()}
        merged = {
            name: source_by_name[name.casefold()]
            for name in allowed
            if name.casefold() in source_by_name
        }
    else:
        merged = {name: str(source[name]) for name in allowed if name in source}
    merged.setdefault("PATH", "")
    merged["LANG"] = "C.UTF-8"
    if overrides:
        unsafe = sorted(str(key) for key in overrides if not _override_allowed(str(key)))
        if unsafe:
            raise SecurityError(f"unsafe subprocess environment overrides: {unsafe}")
        for raw_key, raw_value in overrides.items():
            key = str(raw_key)
            value = str(raw_value)
            if not value or "\x00" in value:
                raise SecurityError(f"invalid subprocess environment value: {key}")
            if platform == "nt":
                for existing in tuple(merged):
                    if existing.casefold() == key.casefold():
                        del merged[existing]
            merged[key] = value
    return merged


def _validated_cwd(cwd: Path) -> Path:
    try:
        resolved = cwd.expanduser().resolve(strict=True)
    except OSError as error:
        raise SecurityError(f"working directory does not exist: {cwd}") from error
    if not resolved.is_dir():
        raise SecurityError(f"working directory does not exist: {cwd}")
    return resolved


def _validated_executable(executable: str) -> Path:
    if not isinstance(executable, str) or not executable or "\x00" in executable:
        raise SecurityError("executable must be a non-empty string")
    candidate = Path(executable).expanduser()
    found = str(candidate) if candidate.is_absolute() else shutil.which(executable)
    if not found:
        raise SecurityError(f"executable not detected: {executable}")
    try:
        resolved = Path(found).resolve(strict=True)
    except OSError as error:
        raise SecurityError(f"executable not detected: {executable}") from error
    if not resolved.is_file() or (os.name != "nt" and not os.access(resolved, os.X_OK)):
        raise SecurityError(f"executable is not runnable: {executable}")
    return resolved


def _run_prepared(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    environment: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    if not argv or any(not isinstance(item, str) or not item or "\x00" in item for item in argv):
        raise SecurityError("argv must be a non-empty sequence of non-empty strings")
    if timeout <= 0 or timeout > 86400:
        raise SecurityError("timeout must be within (0, 86400] seconds")
    if any(
        not key or not value or "\x00" in key or "\x00" in value
        for key, value in environment.items()
    ):
        raise SecurityError("prepared subprocess environment contains invalid entries")
    return subprocess.run(
        tuple(argv),
        cwd=_validated_cwd(cwd),
        env=dict(environment),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,  # nosec B603
    )


def _run_sanitized(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run_prepared(
        argv,
        cwd=cwd,
        timeout=timeout,
        environment=_subprocess_environment(env),
    )


def safe_run(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 300.0,
    env: Mapping[str, str] | None = None,
    allow_process_execution: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Compatibility entrypoint that always denies direct process execution.

    External computation must use :func:`tsao_computation.execution.run_plan` with a
    matching hash-bound authorization. The legacy boolean is intentionally ignored
    as an authorization mechanism.
    """

    del argv, cwd, timeout, allow_process_execution
    if env:
        _subprocess_environment(env)
    raise SecurityError(
        "direct process execution is disabled; use run_plan with hash-bound authorization"
    )


def _issue_process_execution_permit() -> object:
    return _PROCESS_EXECUTION_PERMIT


def _authorized_run(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 300.0,
    environment: Mapping[str, str],
    permit: object,
) -> subprocess.CompletedProcess[str]:
    if permit is not _PROCESS_EXECUTION_PERMIT:
        raise SecurityError("internal process execution permit is invalid")
    return _run_prepared(
        argv,
        cwd=cwd,
        timeout=timeout,
        environment=environment,
    )


def probe_command_output(executable: str, arguments: tuple[str, ...]) -> str:
    """Run one allowlisted, read-only hardware discovery command."""

    resolved = _validated_executable(executable)
    slug = resolved.stem.casefold()
    allowed = _PROBE_ARGUMENTS.get(slug)
    if allowed is None or arguments not in allowed:
        raise SecurityError(f"unsupported read-only probe command: {resolved.name} {arguments}")
    try:
        result = _run_sanitized(
            (str(resolved), *arguments),
            cwd=Path.cwd(),
            timeout=8.0,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def probe_python_modules(executable: str, modules: tuple[str, ...]) -> tuple[str, ...]:
    """Check module discoverability using a fixed script and sanitized environment."""

    if not modules:
        return ()
    if any(not isinstance(name, str) or _PYTHON_MODULE.fullmatch(name) is None for name in modules):
        raise SecurityError("Python module probe names must be dotted identifiers")
    resolved = _validated_executable(executable)
    name = resolved.stem.casefold()
    current = Path(sys.executable).resolve(strict=True)
    if not name.startswith(("python", "pypy")) and resolved != current:
        raise SecurityError("Python module probes require a Python interpreter")
    script = (
        "import importlib.util,json,sys;"
        "missing=[name for name in sys.argv[1:] if importlib.util.find_spec(name) is None];"
        "print(json.dumps(missing));raise SystemExit(bool(missing))"
    )
    try:
        result = _run_sanitized(
            (str(resolved), "-c", script, *modules),
            cwd=Path.cwd(),
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError):
        return modules
    if result.returncode == 0:
        return ()
    try:
        payload = json.loads(result.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return modules
    return tuple(str(item) for item in payload) if isinstance(payload, list) else modules


def read_only_probe_arguments_allowed(arguments: tuple[str, ...]) -> bool:
    return arguments in _READ_ONLY_PROBE_ARGUMENTS


def probe_read_only_command_output(
    executable: str,
    arguments: tuple[str, ...],
) -> tuple[int, str, str]:
    """Run one bounded, shell-free version/help probe.

    Only a small fixed argument set is accepted. Callers remain responsible for
    ensuring that the executable is declared by an adapter registry record.
    The result is discovery evidence only and never authorizes a calculation.
    """

    if arguments not in _READ_ONLY_PROBE_ARGUMENTS:
        raise SecurityError(f"unsupported read-only executable probe arguments: {arguments}")
    resolved = _validated_executable(executable)
    try:
        result = _run_sanitized(
            (str(resolved), *arguments),
            cwd=Path.cwd(),
            timeout=8.0,
        )
    except (OSError, subprocess.SubprocessError):
        return 127, "", ""
    return (
        result.returncode,
        result.stdout[:_MAX_PROBE_OUTPUT_CHARS],
        result.stderr[:_MAX_PROBE_OUTPUT_CHARS],
    )
