from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from ..errors import ContractError, SecurityError
from ..hashing import canonical_json_sha256, file_sha256, text_sha256
from ..registries import accelerators as accelerator_records
from ..registries import adapters as adapter_records
from ..security.process import (
    probe_python_modules,
    probe_read_only_command_output,
    read_only_probe_arguments_allowed,
)

_MAX_VERSION_EXCERPT_CHARS = 4096
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_QUALIFICATION_STATUSES = frozenset(
    {
        "candidate-only",
        "detected-incomplete",
        "fingerprinted-unqualified",
        "version-probed-unqualified",
    }
)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ContractError(f"{field_name} must be an array")
    parsed = tuple(_required_string(item, field_name) for item in value)
    if len(set(parsed)) != len(parsed):
        raise ContractError(f"{field_name} must contain unique values")
    return parsed


def _record(slug: str, records: Iterable[Mapping[str, object]], kind: str) -> Mapping[str, object]:
    normalized = _required_string(slug, "adapter_slug")
    for record in records:
        if str(record.get("slug", "")) == normalized:
            return record
    raise KeyError(f"unknown {kind}: {normalized}")


def _resolve_executable(candidate: str, which: Callable[[str], str | None]) -> Path | None:
    path = Path(candidate).expanduser()
    found = str(path) if path.is_absolute() or path.parent != Path(".") else which(candidate)
    if not found:
        return None
    try:
        resolved = Path(found).resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_file() or (os.name != "nt" and not os.access(resolved, os.X_OK)):
        return None
    return resolved


def _probe_interpreter(executable: Path) -> str:
    name = executable.name.casefold()
    return str(executable) if name.startswith(("python", "pypy")) else sys.executable


def _matching_probe_arguments(
    executable: Path,
    declared_name: str,
    raw_hints: object,
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(raw_hints, list):
        return ()
    expected_names = {Path(declared_name).name.casefold(), executable.name.casefold()}
    results: list[tuple[str, ...]] = []
    for raw in raw_hints:
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            tokens = shlex.split(raw, posix=True)
        except ValueError:
            continue
        if len(tokens) < 2 or Path(tokens[0]).name.casefold() not in expected_names:
            continue
        arguments = tuple(tokens[1:])
        if read_only_probe_arguments_allowed(arguments) and arguments not in results:
            results.append(arguments)
    return tuple(results)


def _version_text(stdout: str, stderr: str) -> str:
    parts = [part.strip().replace("\r\n", "\n").replace("\r", "\n") for part in (stdout, stderr)]
    return "\n".join(part for part in parts if part)


@dataclass(frozen=True, slots=True)
class SolverCapabilityEvidence:
    adapter_slug: str
    declared_executables: tuple[str, ...]
    detected: bool
    executable_name: str | None = None
    executable_path: str | None = None
    executable_sha256: str | None = None
    executable_size_bytes: int | None = None
    required_python_modules: tuple[str, ...] = ()
    missing_python_modules: tuple[str, ...] = ()
    version_arguments: tuple[str, ...] = ()
    version_returncode: int | None = None
    version_text_sha256: str | None = None
    version_excerpt: str | None = None
    qualification_status: str = "candidate-only"
    reason: str = "no declared executable detected"
    claim_boundary: str = (
        "Executable presence, content hashing, module discovery and bounded version/help output are "
        "environment evidence only. They do not prove backend support, numerical equivalence, "
        "convergence, speedup, physical validity, applicability, licensing, or authorization."
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "adapter_slug", _required_string(self.adapter_slug, "adapter_slug")
        )
        for field_name in (
            "declared_executables",
            "required_python_modules",
            "missing_python_modules",
            "version_arguments",
        ):
            object.__setattr__(
                self,
                field_name,
                _string_tuple(getattr(self, field_name), field_name),
            )
        if not isinstance(self.detected, bool):
            raise ContractError("detected must be a boolean")
        if self.executable_size_bytes is not None and (
            isinstance(self.executable_size_bytes, bool)
            or not isinstance(self.executable_size_bytes, int)
        ):
            raise ContractError("executable_size_bytes must be an integer or null")
        if self.version_returncode is not None and (
            isinstance(self.version_returncode, bool)
            or not isinstance(self.version_returncode, int)
        ):
            raise ContractError("version_returncode must be an integer or null")

        for field_name in (
            "executable_name",
            "executable_path",
            "executable_sha256",
            "version_text_sha256",
            "version_excerpt",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_string(value, field_name))
        for field_name in ("executable_sha256", "version_text_sha256"):
            value = getattr(self, field_name)
            if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
                raise ContractError(f"{field_name} must be a lowercase SHA-256 digest")
        if (
            self.version_excerpt is not None
            and len(self.version_excerpt) > _MAX_VERSION_EXCERPT_CHARS
        ):
            raise ContractError("version_excerpt exceeds the bounded evidence limit")

        status = _required_string(self.qualification_status, "qualification_status")
        if status not in _QUALIFICATION_STATUSES:
            raise ContractError(f"unsupported qualification_status: {status}")
        object.__setattr__(self, "qualification_status", status)
        object.__setattr__(self, "reason", _required_string(self.reason, "reason"))
        object.__setattr__(
            self,
            "claim_boundary",
            _required_string(self.claim_boundary, "claim_boundary"),
        )

        required_modules = set(self.required_python_modules)
        missing_modules = set(self.missing_python_modules)
        if not missing_modules.issubset(required_modules):
            raise ContractError(
                "missing_python_modules must be a subset of required_python_modules"
            )
        if bool(self.version_arguments) != (self.version_returncode is not None):
            raise ContractError("version arguments and return code must be recorded together")
        if (self.version_text_sha256 is None) != (self.version_excerpt is None):
            raise ContractError("version text SHA-256 and excerpt must be recorded together")
        if self.version_returncode is None and self.version_text_sha256 is not None:
            raise ContractError("version text requires a completed version probe")

        executable_evidence = (
            self.executable_name,
            self.executable_path,
            self.executable_sha256,
            self.executable_size_bytes,
        )
        version_evidence = (
            self.version_arguments,
            self.version_returncode,
            self.version_text_sha256,
            self.version_excerpt,
        )
        if self.detected:
            if any(value is None for value in executable_evidence):
                raise ContractError(
                    "detected solver evidence requires name, path, SHA-256 and size"
                )
            if self.executable_size_bytes is None or self.executable_size_bytes < 1:
                raise ContractError("detected solver evidence requires a positive executable size")
            if status == "candidate-only":
                raise ContractError("detected solver evidence cannot be candidate-only")
        else:
            if any(
                value is not None and value != ()
                for value in (*executable_evidence, *version_evidence)
            ):
                raise ContractError("undetected solver evidence cannot contain executable evidence")
            if self.missing_python_modules:
                raise ContractError("undetected solver evidence cannot report missing modules")
            if status != "candidate-only":
                raise ContractError("undetected solver evidence must be candidate-only")

        if status == "detected-incomplete":
            if not self.detected or not self.missing_python_modules:
                raise ContractError(
                    "detected-incomplete evidence requires detected solver and missing modules"
                )
        elif status == "version-probed-unqualified":
            if self.missing_python_modules:
                raise ContractError("version-probed evidence cannot report missing Python modules")
            if (
                not self.detected
                or self.version_returncode != 0
                or self.version_text_sha256 is None
            ):
                raise ContractError(
                    "version-probed evidence requires successful bounded version output"
                )
        elif status == "fingerprinted-unqualified":
            if not self.detected or self.missing_python_modules:
                raise ContractError(
                    "fingerprinted evidence requires a detected solver with complete modules"
                )
            if self.version_returncode == 0 and self.version_text_sha256 is not None:
                raise ContractError(
                    "successful version output must use version-probed-unqualified status"
                )

    def _identity_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["declared_executables"] = list(self.declared_executables)
        payload["required_python_modules"] = list(self.required_python_modules)
        payload["missing_python_modules"] = list(self.missing_python_modules)
        payload["version_arguments"] = list(self.version_arguments)
        return payload

    @property
    def evidence_sha256(self) -> str:
        return canonical_json_sha256(self._identity_dict())

    def to_dict(self) -> dict[str, object]:
        payload = self._identity_dict()
        payload["evidence_sha256"] = self.evidence_sha256
        return payload

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> SolverCapabilityEvidence:
        if not isinstance(value, Mapping):
            raise ContractError("solver capability evidence must be an object")
        allowed = {
            "adapter_slug",
            "declared_executables",
            "detected",
            "executable_name",
            "executable_path",
            "executable_sha256",
            "executable_size_bytes",
            "required_python_modules",
            "missing_python_modules",
            "version_arguments",
            "version_returncode",
            "version_text_sha256",
            "version_excerpt",
            "qualification_status",
            "reason",
            "claim_boundary",
            "evidence_sha256",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ContractError(f"unknown solver evidence fields: {unknown}")
        required = {"adapter_slug", "declared_executables", "detected"}
        missing = sorted(required - set(value))
        if missing:
            raise ContractError(f"missing solver evidence fields: {missing}")

        size = value.get("executable_size_bytes")
        if size is not None and (isinstance(size, bool) or not isinstance(size, int)):
            raise ContractError("executable_size_bytes must be an integer or null")
        returncode = value.get("version_returncode")
        if returncode is not None and (
            isinstance(returncode, bool) or not isinstance(returncode, int)
        ):
            raise ContractError("version_returncode must be an integer or null")
        detected = value["detected"]
        if not isinstance(detected, bool):
            raise ContractError("detected must be a boolean")

        def optional_string(field_name: str) -> str | None:
            raw = value.get(field_name)
            return None if raw is None else _required_string(raw, field_name)

        default_boundary = (
            "Executable presence, content hashing, module discovery and bounded version/help output "
            "are environment evidence only. They do not prove backend support, numerical "
            "equivalence, convergence, speedup, physical validity, applicability, licensing, or "
            "authorization."
        )
        evidence = cls(
            adapter_slug=_required_string(value["adapter_slug"], "adapter_slug"),
            declared_executables=_string_tuple(
                value["declared_executables"], "declared_executables"
            ),
            detected=detected,
            executable_name=optional_string("executable_name"),
            executable_path=optional_string("executable_path"),
            executable_sha256=optional_string("executable_sha256"),
            executable_size_bytes=size,
            required_python_modules=_string_tuple(
                value.get("required_python_modules", ()), "required_python_modules"
            ),
            missing_python_modules=_string_tuple(
                value.get("missing_python_modules", ()), "missing_python_modules"
            ),
            version_arguments=_string_tuple(
                value.get("version_arguments", ()), "version_arguments"
            ),
            version_returncode=returncode,
            version_text_sha256=optional_string("version_text_sha256"),
            version_excerpt=optional_string("version_excerpt"),
            qualification_status=_required_string(
                value.get("qualification_status", "candidate-only"),
                "qualification_status",
            ),
            reason=_required_string(
                value.get("reason", "no declared executable detected"),
                "reason",
            ),
            claim_boundary=_required_string(
                value.get("claim_boundary", default_boundary),
                "claim_boundary",
            ),
        )
        supplied_digest = value.get("evidence_sha256")
        if supplied_digest is not None:
            digest = _required_string(supplied_digest, "evidence_sha256")
            if digest != evidence.evidence_sha256:
                raise ContractError("solver evidence SHA-256 does not match its content")
        return evidence


def load_solver_capability_evidence(path: Path) -> SolverCapabilityEvidence:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read solver capability evidence: {path}") from error
    if not isinstance(payload, Mapping):
        raise ContractError("solver capability evidence must be an object")
    return SolverCapabilityEvidence.from_mapping(payload)


def probe_solver_capability(
    adapter_slug: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[[str, tuple[str, ...]], tuple[int, str, str]] = (
        probe_read_only_command_output
    ),
    module_probe: Callable[[str, tuple[str, ...]], tuple[str, ...]] = probe_python_modules,
    adapters_loader: Callable[[], Iterable[Mapping[str, object]]] = adapter_records,
    accelerators_loader: Callable[[], Iterable[Mapping[str, object]]] = accelerator_records,
) -> SolverCapabilityEvidence:
    adapter = _record(adapter_slug, adapters_loader(), "adapter")
    accelerator = _record(adapter_slug, accelerators_loader(), "accelerator profile")
    declared = _string_tuple(adapter.get("executables", []), "executables")
    required_modules = _string_tuple(adapter.get("python_modules", []), "python_modules")
    reasons: list[str] = []

    for candidate in declared:
        executable = _resolve_executable(candidate, which)
        if executable is None:
            reasons.append(f"executable not detected: {candidate}")
            continue
        missing_modules: tuple[str, ...]
        try:
            missing_modules = module_probe(_probe_interpreter(executable), required_modules)
        except SecurityError:
            missing_modules = required_modules
        executable_sha256 = file_sha256(executable)
        size_bytes = executable.stat().st_size
        version_arguments: tuple[str, ...] = ()
        version_returncode: int | None = None
        version_text_sha256: str | None = None
        version_excerpt: str | None = None
        probe_reason = "no safe declared version/help probe was available"

        for arguments in _matching_probe_arguments(
            executable,
            candidate,
            accelerator.get("probe_hints", []),
        ):
            try:
                returncode, stdout, stderr = runner(str(executable), arguments)
            except SecurityError:
                continue
            version_arguments = arguments
            version_returncode = returncode
            text = _version_text(stdout, stderr)
            if text:
                version_text_sha256 = text_sha256(text)
                version_excerpt = text[:_MAX_VERSION_EXCERPT_CHARS]
            probe_reason = (
                "bounded declared version/help probe completed"
                if returncode == 0 and text
                else f"declared version/help probe returned {returncode} without qualifying evidence"
            )
            break

        if missing_modules:
            status = "detected-incomplete"
            reason = (
                f"detected {candidate}, but required Python modules are missing: "
                f"{', '.join(missing_modules)}; {probe_reason}"
            )
        elif version_returncode == 0 and version_text_sha256 is not None:
            status = "version-probed-unqualified"
            reason = f"detected and fingerprinted {candidate}; {probe_reason}"
        else:
            status = "fingerprinted-unqualified"
            reason = f"detected and fingerprinted {candidate}; {probe_reason}"

        return SolverCapabilityEvidence(
            adapter_slug=_required_string(adapter_slug, "adapter_slug"),
            declared_executables=declared,
            detected=True,
            executable_name=executable.name,
            executable_path=str(executable),
            executable_sha256=executable_sha256,
            executable_size_bytes=size_bytes,
            required_python_modules=required_modules,
            missing_python_modules=missing_modules,
            version_arguments=version_arguments,
            version_returncode=version_returncode,
            version_text_sha256=version_text_sha256,
            version_excerpt=version_excerpt,
            qualification_status=status,
            reason=reason,
        )

    return SolverCapabilityEvidence(
        adapter_slug=_required_string(adapter_slug, "adapter_slug"),
        declared_executables=declared,
        detected=False,
        required_python_modules=required_modules,
        qualification_status="candidate-only",
        reason="; ".join(reasons) if reasons else "no declared executable detected",
    )


fingerprint_solver = probe_solver_capability
