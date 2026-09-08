from __future__ import annotations

import os
import re
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..errors import ContractError, SecurityError
from ..hashing import file_sha256
from ..immutable import freeze_json
from ..security.process import probe_python_modules

_COMPLETION_SUCCESS = re.compile(
    r"\bnormal\s+termination\b|"
    r"(?:^|[;\r\n])\s*(?:(?:run|job|calculation|simulation)\s+)?"
    r"(?:finished|completed)(?:\s+successfully)?\s*(?=$|[;\r\n])|"
    r"\btotal\s+wall\s+time\b"
)

_COMPLETION_FAILURE_PATTERN = (
    r"\b(?:abnormal|error|fatal)\s+termination\b|"
    r"\b(?:run|job|calculation|simulation)\s+(?:failed|aborted)\b|"
    r"\b(?:not|never)\s+(?:finished|completed)\b|"
    r"\bcompleted\s+with\s+(?:errors?|failures?)\b|"
    r"\bfatal\s+error\b"
)
_CONVERGENCE_SUCCESS = re.compile(r"\bconverged\b|\bconvergence\s+(?:achieved|reached)\b")
_CONVERGENCE_FAILURE_PATTERN = (
    r"\bnot(?:\s+fully)?\s+converged\b|\bfailed\s+to\s+converge\b|"
    r"\bdid\s+not\s+converge\b|\bconvergence\s+(?:not\s+achieved|failed|failure)\b|"
    r"\bnon[-\s]?converged\b|\bunconverged\b"
)
_FAILURE_STATUS = re.compile(
    rf"(?P<completion>{_COMPLETION_FAILURE_PATTERN})|(?P<convergence>{_CONVERGENCE_FAILURE_PATTERN})"
)
_FAILURE_CUES = (
    "not",
    "fail",
    "error",
    "fatal",
    "abnormal",
    "abort",
    "never",
    "non-",
    "non ",
    "unconverged",
)


@dataclass(frozen=True, slots=True)
class AdapterProbe:
    slug: str
    available: bool
    executable: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class CommandPlan:
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
    claim_boundary: str
    adapter_slug: str | None = None
    input_sha256: str | None = None
    execute_allowed: bool = False
    input_path: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", tuple(str(item) for item in self.argv))
        object.__setattr__(self, "cwd", Path(self.cwd))
        object.__setattr__(
            self,
            "environment",
            MappingProxyType({str(key): str(value) for key, value in self.environment.items()}),
        )
        if self.input_path is not None:
            object.__setattr__(self, "input_path", Path(self.input_path))


def _resolve_executable(candidate: str) -> str | None:
    path = Path(candidate).expanduser()
    resolved: str | None
    if (path.is_absolute() and path.is_file()) or (path.parent != Path(".") and path.is_file()):
        resolved = str(path.resolve())
    else:
        resolved = shutil.which(candidate)
    if resolved and os.name != "nt" and not os.access(resolved, os.X_OK):
        return None
    return resolved


def _module_probe_interpreter(candidate: str, found: str) -> str:
    name = Path(found).name.casefold()
    return found if name.startswith(("python", "pypy")) else sys.executable


def _missing_python_modules(executable: str, modules: tuple[str, ...]) -> tuple[str, ...]:
    try:
        return probe_python_modules(executable, modules)
    except SecurityError:
        return modules


@dataclass(frozen=True, slots=True)
class Adapter:
    record: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record", freeze_json(dict(self.record)))

    @property
    def slug(self) -> str:
        return str(self.record["slug"])

    @property
    def python_modules(self) -> tuple[str, ...]:
        raw = self.record.get("python_modules", [])
        return tuple(str(item) for item in raw) if isinstance(raw, list) else ()

    def _probe_candidate(self, candidate: str) -> AdapterProbe:
        found = _resolve_executable(candidate)
        if not found:
            return AdapterProbe(self.slug, False, None, f"executable not detected: {candidate}")
        interpreter = _module_probe_interpreter(candidate, found)
        missing = _missing_python_modules(interpreter, self.python_modules)
        if missing:
            return AdapterProbe(
                self.slug,
                False,
                found,
                f"detected {candidate}, but required Python modules are missing from {interpreter}: {', '.join(missing)}",
            )
        reason = f"detected {candidate}"
        if self.python_modules:
            reason += f" with modules in {interpreter}: {', '.join(self.python_modules)}"
        return AdapterProbe(self.slug, True, found, reason)

    def probe(self) -> AdapterProbe:
        reasons: list[str] = []
        for executable in self.record.get("executables", []):
            result = self._probe_candidate(str(executable))
            if result.available:
                return result
            reasons.append(result.reason)
        return AdapterProbe(
            self.slug,
            False,
            None,
            "; ".join(reasons) if reasons else "no declared executable detected",
        )

    def _explicit_probe(self, executable: str) -> AdapterProbe:
        requested = _resolve_executable(executable)
        declared = {
            found
            for candidate in self.record.get("executables", [])
            if (found := _resolve_executable(str(candidate))) is not None
        }
        if requested is None or requested not in declared:
            return AdapterProbe(
                self.slug,
                False,
                requested,
                "explicit executable is not a declared adapter executable",
            )
        return self._probe_candidate(executable)

    def build_command(self, input_path: Path, *, executable: str | None = None) -> CommandPlan:
        try:
            source = input_path.expanduser().resolve(strict=True)
        except OSError as error:
            raise ContractError(f"input file does not exist: {input_path}") from error
        if not source.is_file():
            raise ContractError(f"input file does not exist: {input_path}")
        probe = self.probe() if executable is None else self._explicit_probe(executable)
        if not probe.available or not probe.executable:
            raise ContractError(
                f"adapter {self.slug} is not runnable in the current environment: {probe.reason}"
            )
        return CommandPlan(
            argv=(probe.executable, source.name),
            cwd=source.parent,
            environment={},
            claim_boundary="Command prepared only; execution requires hash-bound authorization and scientific acceptance requires separate evidence.",
            adapter_slug=self.slug,
            input_sha256=file_sha256(source),
            execute_allowed=False,
            input_path=source,
        )

    def parse(self, output: str) -> dict[str, Any]:
        folded = output.casefold()
        completion_failed = convergence_failed = False
        if any(cue in folded for cue in _FAILURE_CUES):
            for match in _FAILURE_STATUS.finditer(folded):
                completion_failed |= match.lastgroup == "completion"
                convergence_failed |= match.lastgroup == "convergence"
                if completion_failed and convergence_failed:
                    break
        completed = not completion_failed and _COMPLETION_SUCCESS.search(folded) is not None
        converged = (
            completed and not convergence_failed and _CONVERGENCE_SUCCESS.search(folded) is not None
        )
        return {
            "completed": completed,
            "converged": converged,
            "raw_length": len(output),
            "validated": False,
        }
