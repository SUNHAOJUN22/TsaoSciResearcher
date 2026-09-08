from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..errors import SecurityError
from ..hashing import canonical_json_sha256, file_sha256, text_sha256
from ..security.process import (
    _authorized_run,
    _issue_process_execution_permit,
    _subprocess_environment,
)
from .typing_compat import CommandPlanLike

_AUTHORIZATION_SEAL = object()


def _has_explicit_relative_prefix(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith("./") or normalized.startswith("../")


def _search_exact_path_entry(argv0: str, search_path: str) -> str | None:
    """Resolve an exact filename from the immutable plan PATH.

    ``shutil.which`` follows Windows ``PATHEXT`` rules and therefore ignores an
    extensionless executable fixture. Command-plan identity, however, binds the
    exact file bytes selected from the declared PATH. This bounded fallback
    checks only literal PATH entries and never consults the ambient process PATH.
    """

    if not search_path:
        return None
    for raw_entry in search_path.split(os.pathsep):
        entry = raw_entry.strip().strip('"')
        if not entry:
            continue
        candidate = Path(entry).expanduser() / argv0
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def _resolve_executable(argv0: str, cwd: Path, *, search_path: str) -> Path:
    if not isinstance(argv0, str) or not argv0 or "\x00" in argv0:
        raise SecurityError("command plan executable must be a non-empty string")
    candidate = Path(argv0).expanduser()
    explicit_relative = candidate.parent != Path(".") or _has_explicit_relative_prefix(argv0)
    found: str | None
    if candidate.is_absolute():
        found = str(candidate)
    elif explicit_relative:
        found = str(cwd / candidate)
    else:
        found = shutil.which(argv0, path=search_path)
        if found is None:
            found = _search_exact_path_entry(argv0, search_path)
    if not found:
        raise SecurityError(f"command plan executable is unavailable: {argv0}")
    try:
        resolved = Path(found).resolve(strict=True)
    except OSError as error:
        raise SecurityError(f"command plan executable is unavailable: {argv0}") from error
    if not resolved.is_file() or (os.name != "nt" and not os.access(resolved, os.X_OK)):
        raise SecurityError(f"command plan executable is not runnable: {argv0}")
    return resolved


def _input_binding(plan: CommandPlanLike, cwd: Path) -> tuple[str | None, str | None]:
    raw_path = getattr(plan, "input_path", None)
    declared_sha256 = getattr(plan, "input_sha256", None)
    if raw_path is None:
        if declared_sha256 is not None:
            raise SecurityError("command plan declares an input hash without an input path")
        return None, None
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SecurityError(f"command plan input file is unavailable: {raw_path}") from error
    if not resolved.is_file():
        raise SecurityError(f"command plan input file is unavailable: {raw_path}")
    actual_sha256 = file_sha256(resolved)
    if declared_sha256 is not None and declared_sha256 != actual_sha256:
        raise SecurityError("command plan input file does not match its declared SHA-256")
    return str(resolved), actual_sha256


def _bound_plan(
    plan: CommandPlanLike,
) -> tuple[str, str, str, str | None, Mapping[str, str], Path]:
    if not plan.argv or any(
        not isinstance(item, str) or not item or "\x00" in item for item in plan.argv
    ):
        raise SecurityError("command plan argv must contain non-empty strings")
    try:
        cwd = plan.cwd.expanduser().resolve(strict=True)
    except OSError as error:
        raise SecurityError(f"command plan working directory is unavailable: {plan.cwd}") from error
    if not cwd.is_dir():
        raise SecurityError(f"command plan working directory is unavailable: {plan.cwd}")
    normalized_environment = _subprocess_environment(plan.environment)
    executable = _resolve_executable(
        plan.argv[0], cwd, search_path=normalized_environment.get("PATH", "")
    )
    executable_sha256 = file_sha256(executable)
    input_path, input_sha256 = _input_binding(plan, cwd)
    normalized_argv = [str(executable), *plan.argv[1:]]
    payload = {
        "argv": normalized_argv,
        "cwd": str(cwd),
        "environment": dict(sorted(normalized_environment.items())),
        "adapter_slug": getattr(plan, "adapter_slug", None),
        "executable_sha256": executable_sha256,
        "input_path": input_path,
        "input_sha256": input_sha256,
    }
    digest = canonical_json_sha256(payload)
    return (
        digest,
        str(executable),
        executable_sha256,
        input_sha256,
        normalized_environment,
        cwd,
    )


def plan_sha256(plan: CommandPlanLike) -> str:
    return _bound_plan(plan)[0]


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    plan_sha256: str
    executable_sha256: str
    input_sha256: str | None
    authorized_by: str
    purpose: str
    explicit_authorization: bool
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _AUTHORIZATION_SEAL:
            raise SecurityError("execution authorizations must be created by authorize_plan")

    @property
    def authorization_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "plan_sha256": self.plan_sha256,
                "executable_sha256": self.executable_sha256,
                "input_sha256": self.input_sha256,
                "authorized_by": self.authorized_by,
                "purpose": self.purpose,
                "explicit_authorization": self.explicit_authorization,
            }
        )


def authorize_plan(
    plan: CommandPlanLike,
    *,
    authorized_by: str,
    purpose: str,
    explicit_authorization: bool,
) -> ExecutionAuthorization:
    if explicit_authorization is not True:
        raise SecurityError("explicit process execution authorization must be boolean true")
    if not isinstance(authorized_by, str) or not authorized_by.strip():
        raise SecurityError("authorized_by must be a non-empty identity")
    if not isinstance(purpose, str) or not purpose.strip():
        raise SecurityError("authorization purpose must be a non-empty string")
    digest, _, executable_sha256, input_sha256, _, _ = _bound_plan(plan)
    return ExecutionAuthorization(
        digest,
        executable_sha256,
        input_sha256,
        authorized_by.strip(),
        purpose.strip(),
        True,
        _AUTHORIZATION_SEAL,
    )


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    argv: tuple[str, ...]
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    started_at: str
    completed_at: str
    completed: bool
    plan_sha256: str
    authorization_sha256: str
    authorized_by: str
    executable_sha256: str
    input_sha256: str | None


def run_plan(
    plan: CommandPlanLike,
    *,
    authorization: ExecutionAuthorization | None = None,
    timeout: float = 300.0,
) -> ExecutionRecord:
    if authorization is None:
        raise SecurityError("external process execution is plan-only until explicitly authorized")
    digest, executable, executable_sha256, input_sha256, environment, cwd = _bound_plan(plan)
    if authorization.explicit_authorization is not True or authorization.plan_sha256 != digest:
        raise SecurityError("execution authorization does not match the immutable command plan")
    if authorization.executable_sha256 != executable_sha256:
        raise SecurityError("authorized executable content changed before execution")
    if authorization.input_sha256 != input_sha256:
        raise SecurityError("authorized input content changed before execution")
    started = datetime.now(timezone.utc).isoformat()
    argv = (executable, *plan.argv[1:])
    result = _authorized_run(
        argv,
        cwd=cwd,
        timeout=timeout,
        environment=environment,
        permit=_issue_process_execution_permit(),
    )
    completed_at = datetime.now(timezone.utc).isoformat()
    return ExecutionRecord(
        tuple(argv),
        result.returncode,
        text_sha256(result.stdout),
        text_sha256(result.stderr),
        started,
        completed_at,
        result.returncode == 0,
        digest,
        authorization.authorization_sha256,
        authorization.authorized_by,
        executable_sha256,
        input_sha256,
    )
