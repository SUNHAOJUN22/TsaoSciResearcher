"""Shared fail-closed scientific contracts for the DFT Skill.

This module is intentionally standard-library-only.  The versioned public modules
in this directory are thin compatibility views over these contracts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

K_B = 1.380649e-23
H = 6.62607015e-34
R = 8.31446261815324
HARTREE_TO_EV = 27.211386245988
BOHR_TO_ANGSTROM = 0.529177210903


class DFTContractError(ValueError):
    """Raised when an input would cross a scientific trust boundary."""


class ParserContractError(DFTContractError):
    """Raised for an invalid parser quantity or engine identifier."""


class TSTContractError(DFTContractError):
    """Raised for invalid transition-state-theory inputs."""


class MLProvenanceError(DFTContractError):
    """Raised for an invalid model or dataset evidence chain."""


class ModelAcceptanceError(MLProvenanceError):
    """Raised for an invalid predictive-model acceptance chain."""


class QuantityEquivalenceError(DFTContractError):
    """Raised when a quantity record is structurally invalid."""


class KineticsUncertaintyError(TSTContractError):
    """Raised for invalid kinetics uncertainty inputs."""


def finite_real(value: object, name: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DFTContractError(f"{name} must be a non-Boolean real number")
    number = float(value)
    if not math.isfinite(number):
        raise DFTContractError(f"{name} must be finite")
    if positive and number <= 0.0:
        raise DFTContractError(f"{name} must be positive")
    if nonnegative and number < 0.0:
        raise DFTContractError(f"{name} must be non-negative")
    return number


def exact_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DFTContractError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise DFTContractError(f"{name} must be >= {minimum}")
    return value


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def require_sha256(value: object, name: str) -> str:
    if not is_sha256(value):
        raise DFTContractError(f"{name} must be a lowercase SHA-256 digest")
    return str(value)


def parse_timestamp(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DFTContractError(f"{name} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DFTContractError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise DFTContractError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def digest_mapping(value: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _hmac_digest(key: bytes, value: Mapping[str, object]) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise DFTContractError("signing key must contain at least 32 bytes")
    return hmac.new(key, canonical_json(value).encode("utf-8"), hashlib.sha256).hexdigest()


_ENGINE_ALIASES = {
    "gaussian": "gaussian",
    "vasp": "vasp",
    "qe": "qe",
    "quantum-espresso": "qe",
    "quantum_espresso": "qe",
    "cp2k": "cp2k",
}

_START_MARKERS = {
    "gaussian": re.compile(r"(?im)^\s*Entering Gaussian System"),
    "vasp": re.compile(r"(?im)^\s*vasp(?:\.|\s)"),
    "qe": re.compile(r"(?im)^\s*Program PWSCF"),
    "cp2k": re.compile(r"(?im)^\s*(?:PROGRAM STARTED AT|CP2K\|\s*version)"),
}

_SUCCESS_MARKERS = {
    "gaussian": ("normal termination",),
    "vasp": ("general timing and accounting informations", "reached required accuracy"),
    "qe": ("job done",),
    "cp2k": ("program ended at",),
}

_CONVERGENCE_MARKERS = {
    "gaussian": ("normal termination",),
    "vasp": ("reached required accuracy", "ediff is reached"),
    "qe": ("convergence has been achieved", "job done"),
    "cp2k": ("scf run converged", "program ended at"),
}

_FATAL_MARKERS = (
    "error termination",
    "fatal error",
    "error in routine",
    "*** abort",
    " abort",
    "brmix: very serious problems",
    "zbrent: fatal",
    "edddav: call to zhegv failed",
    "sub-space-matrix is not hermitian",
    "segmentation fault",
)

_NONCONVERGENCE_MARKERS = (
    "convergence not achieved",
    "scf run not converged",
    "scf not converged",
    "maximum number of electronic steps reached",
)


@dataclass(frozen=True)
class JobRecord:
    index: int
    status: str
    fatal: bool
    nonconverged: bool
    complete: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ParserRecord:
    engine: str
    status: str
    parser_accepted: bool
    exit_code: int
    reason_codes: tuple[str, ...]
    jobs: tuple[JobRecord, ...]
    truncated: bool = False

    @property
    def segments(self) -> tuple[JobRecord, ...]:
        return self.jobs


def _engine_name(engine: str) -> str:
    if not isinstance(engine, str):
        raise ParserContractError("engine must be a string")
    normalized = _ENGINE_ALIASES.get(engine.strip().casefold())
    if normalized is None:
        raise ParserContractError(f"unsupported engine: {engine}")
    return normalized


def split_jobs(engine: str, text: str) -> list[str]:
    normalized = _engine_name(engine)
    if not isinstance(text, str):
        raise ParserContractError("engine output must be text")
    generic = re.split(r"(?im)^\s*---\s*JOB START\s*---\s*$", text)
    if len(generic) > 1:
        return [segment for segment in generic if segment.strip()]
    starts = [match.start() for match in _START_MARKERS[normalized].finditer(text)]
    if len(starts) <= 1:
        return [text]
    return [
        text[start : starts[index + 1] if index + 1 < len(starts) else len(text)] for index, start in enumerate(starts)
    ]


def _job_status(engine: str, segment: str, index: int) -> JobRecord:
    folded = segment.casefold()
    fatal_view = folded
    if engine == "vasp":
        fatal_view = fatal_view.replace("aborting loop because ediff is reached", "ediff is reached")
    fatal = any(marker in fatal_view for marker in _FATAL_MARKERS)
    nonconverged = any(marker in folded for marker in _NONCONVERGENCE_MARKERS)
    success_markers = _SUCCESS_MARKERS[engine]
    convergence_markers = _CONVERGENCE_MARKERS[engine]
    complete = any(marker in folded for marker in success_markers)
    converged = any(marker in folded for marker in convergence_markers)
    if fatal:
        return JobRecord(index, "FATAL", True, nonconverged, complete, ("FATAL_MARKER_PRESENT",))
    if nonconverged:
        return JobRecord(index, "NONCONVERGED", False, True, complete, ("NONCONVERGENCE_MARKER_PRESENT",))
    if complete and converged:
        return JobRecord(index, "CONVERGED", False, False, True, ())
    return JobRecord(index, "INCOMPLETE", False, False, False, ("NORMAL_TERMINATION_MISSING",))


def parse_engine_output(
    engine: str, text: str, *, accepted_status: str = "ACCEPTED", failure_prefix: str = "FAILED_"
) -> ParserRecord:
    normalized = _engine_name(engine)
    segments = split_jobs(normalized, text)
    jobs = tuple(_job_status(normalized, segment, index) for index, segment in enumerate(segments))
    final = jobs[-1]
    if final.status == "CONVERGED":
        return ParserRecord(normalized, accepted_status, True, 0, (), jobs)
    status = final.status if failure_prefix == "" else f"{failure_prefix}{final.status}"
    return ParserRecord(normalized, status, False, 2, final.reason_codes, jobs)


def parse_engine_stream(engine: str, chunks: Iterable[str], *, max_bytes: int = 64 * 1024 * 1024) -> ParserRecord:
    limit = exact_int(max_bytes, "max_bytes", minimum=1)
    pieces: list[str] = []
    used = 0
    for chunk in chunks:
        if not isinstance(chunk, str):
            raise ParserContractError("stream chunks must be text")
        encoded = chunk.encode("utf-8")
        if used + len(encoded) > limit:
            return ParserRecord(_engine_name(engine), "TRUNCATED_BY_LIMIT", False, 2, ("MAX_BYTES_EXCEEDED",), (), True)
        pieces.append(chunk)
        used += len(encoded)
    return parse_engine_output(engine, "".join(pieces))


@dataclass(frozen=True)
class QuantityRecord:
    quantity_kind: str
    value: object
    unit: str
    shape: tuple[int, ...]
    aggregation: str
    atom_count: int | None = None
    atom_mapping: tuple[str, ...] | None = None
    component_convention: str | None = None

    def __post_init__(self) -> None:
        if self.quantity_kind == "atomic_forces_full":
            if self.aggregation != "full":
                raise ParserContractError("full atomic forces require aggregation=full")
            count = exact_int(self.atom_count, "atom_count", minimum=1)
            if self.shape != (count, 3):
                raise ParserContractError("full atomic forces require shape (atom_count, 3)")
            if self.atom_mapping is None or len(self.atom_mapping) != count:
                raise ParserContractError("full atomic forces require an exact atom mapping")
            rows = _nested_numeric(self.value, "value")
            if len(rows) != count or any(not isinstance(row, tuple) or len(row) != 3 for row in rows):
                raise ParserContractError("full atomic-force values must be N x 3")
        elif self.quantity_kind in {"stress_tensor_full", "stress_tensor"}:
            if self.aggregation != "full" or self.shape not in {(6,), (3, 3)}:
                raise ParserContractError("full stress requires Voigt-6 or 3x3 shape")
            _flatten_numeric(self.value, "value")
        else:
            _flatten_numeric(self.value, "value")


def _nested_numeric(value: object, name: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise QuantityEquivalenceError(f"{name} must be a sequence")
    output: list[object] = []
    for item in value:
        if isinstance(item, (list, tuple)):
            output.append(tuple(finite_real(entry, name) for entry in item))
        else:
            output.append(finite_real(item, name))
    return tuple(output)


def _flatten_numeric(value: object, name: str) -> tuple[float, ...]:
    if isinstance(value, (list, tuple)):
        output: list[float] = []
        for item in value:
            output.extend(_flatten_numeric(item, name))
        return tuple(output)
    return (finite_real(value, name),)


@dataclass(frozen=True)
class StandardState:
    value: float
    unit: str
    activity_convention: str

    def __post_init__(self) -> None:
        finite_real(self.value, "standard_state.value", positive=True)
        if self.unit not in {"M", "mol/L"}:
            raise TSTContractError("standard-state unit must be M or mol/L")
        if not isinstance(self.activity_convention, str) or not self.activity_convention.strip():
            raise TSTContractError("activity convention is required")


@dataclass(frozen=True)
class RateResult:
    rate_constant: float | None
    rate_unit: str
    status: str = "OK"
    reason_codes: tuple[str, ...] = ()

    @property
    def value(self) -> float | None:
        return self.rate_constant

    @property
    def unit(self) -> str:
        return self.rate_unit


def barrier_j_mol(value: object, unit: str) -> float:
    amount = finite_real(value, "barrier")
    factors = {"J/mol": 1.0, "kJ/mol": 1000.0, "kcal/mol": 4184.0}
    try:
        factor = factors[unit]
    except KeyError as exc:
        raise TSTContractError(f"unsupported barrier unit: {unit}") from exc
    converted = amount * factor
    if not math.isfinite(converted):
        raise TSTContractError("barrier conversion is non-finite")
    return converted


def eyring_rate(
    barrier: object,
    *,
    barrier_unit: str,
    temperature_K: object,
    molecularity: int = 1,
    standard_state: StandardState | None = None,
    missing_standard_state_returns_invalid: bool = False,
) -> RateResult:
    temperature = finite_real(temperature_K, "temperature_K", positive=True)
    order = exact_int(molecularity, "molecularity", minimum=1)
    try:
        energy = barrier_j_mol(barrier, barrier_unit)
    except DFTContractError as exc:
        raise TSTContractError(str(exc)) from exc
    if order > 1 and standard_state is None:
        if missing_standard_state_returns_invalid:
            return RateResult(None, "UNDEFINED", "INVALID", ("STANDARD_STATE_REQUIRED",))
        raise TSTContractError("explicit standard state is required for molecularity > 1")
    concentration = (
        1.0 if standard_state is None else finite_real(standard_state.value, "standard_state.value", positive=True)
    )
    log_rate = math.log(K_B * temperature / H) - energy / (R * temperature) + (1 - order) * math.log(concentration)
    try:
        rate = math.exp(log_rate)
    except OverflowError as exc:
        raise TSTContractError("rate overflows the finite range") from exc
    if not math.isfinite(rate):
        raise TSTContractError("rate is non-finite")
    if order == 1:
        unit = "s^-1"
    elif standard_state is not None and standard_state.unit == "mol/L":
        exponent = order - 1
        unit = f"L^{exponent} mol^-{exponent} s^-1"
    else:
        unit = f"M^{1 - order} s^-1"
    return RateResult(rate, unit)


@dataclass(frozen=True)
class DatasetValidationArtifactV4:
    status: str
    dataset_sha256: str
    schema_version: str
    validator_sha256: str
    sample_count: int
    method_fingerprints: tuple[str, ...]
    split_sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> DatasetValidationArtifactV4:
        required = {
            "status",
            "dataset_sha256",
            "schema_version",
            "validator_sha256",
            "sample_count",
            "method_fingerprints",
            "split_sha256",
        }
        if set(value) != required:
            raise MLProvenanceError("dataset validation artifact fields are incomplete")
        fingerprints = value["method_fingerprints"]
        if (
            not isinstance(fingerprints, list)
            or not fingerprints
            or not all(isinstance(item, str) and item for item in fingerprints)
        ):
            raise MLProvenanceError("method fingerprints are required")
        return cls(
            str(value["status"]),
            require_sha256(value["dataset_sha256"], "dataset_sha256"),
            str(value["schema_version"]),
            require_sha256(value["validator_sha256"], "validator_sha256"),
            exact_int(value["sample_count"], "sample_count", minimum=1),
            tuple(fingerprints),
            require_sha256(value["split_sha256"], "split_sha256"),
        )


def authorize_training_v4(
    dataset_path: Path, artifact: DatasetValidationArtifactV4, *, expected_schema: str
) -> dict[str, object]:
    if artifact.status != "PASS" or artifact.schema_version != expected_schema:
        raise MLProvenanceError("dataset validation artifact is not an exact PASS")
    digest = hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest()
    if digest != artifact.dataset_sha256:
        raise MLProvenanceError("dataset checksum does not match validation artifact")
    return {"training_authorized": True, "model_output_ceiling": "BASELINE_GENERATED", "dataset_sha256": digest}


def validate_model_card_v4(card: Mapping[str, object]) -> dict[str, object]:
    required = {
        "status",
        "dataset_sha256",
        "model_sha256",
        "code_sha256",
        "environment_sha256",
        "metrics",
        "applicability_domain",
        "calibrated_uncertainty",
        "holdout_validation",
        "independent_approval",
    }
    missing = required - set(card)
    if missing:
        raise MLProvenanceError(f"model card is missing acceptance evidence: {sorted(missing)}")
    for key in ("dataset_sha256", "model_sha256", "code_sha256", "environment_sha256"):
        require_sha256(card[key], key)
    for key in (
        "metrics",
        "applicability_domain",
        "calibrated_uncertainty",
        "holdout_validation",
        "independent_approval",
    ):
        if not isinstance(card[key], Mapping) or not card[key]:
            raise MLProvenanceError(f"{key} must be a non-empty mapping")
    return {"predictive_use_allowed": True, "truth_boundary": "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"}


def validate_labels(labels: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if len(labels) < 2:
        raise ModelAcceptanceError("at least two labels are required")
    required = {
        "sample_id",
        "parent_id",
        "quantity_kind",
        "value",
        "unit",
        "method_fingerprint",
        "engine",
        "fidelity",
        "provenance_sha256",
        "validation_status",
        "split",
    }
    samples: set[str] = set()
    train_parents: set[str] = set()
    test_parents: set[str] = set()
    methods: set[str] = set()
    values: list[float] = []
    units: set[str] = set()
    for index, label in enumerate(labels):
        if set(label) != required:
            raise ModelAcceptanceError(f"label {index} has an invalid schema")
        sample = label["sample_id"]
        parent = label["parent_id"]
        split = label["split"]
        if not isinstance(sample, str) or not sample or sample in samples:
            raise ModelAcceptanceError("sample IDs must be non-empty and unique")
        samples.add(sample)
        if not isinstance(parent, str) or not parent:
            raise ModelAcceptanceError("parent IDs are required")
        if split == "train":
            train_parents.add(parent)
        elif split in {"test", "validation"}:
            test_parents.add(parent)
        else:
            raise ModelAcceptanceError("split must be train, validation or test")
        methods.add(require_sha256(label["method_fingerprint"], "method_fingerprint"))
        require_sha256(label["provenance_sha256"], "provenance_sha256")
        if label["validation_status"] not in {"QUALIFIED", "ACCEPTED"}:
            raise ModelAcceptanceError("labels must be qualified or accepted")
        values.append(finite_real(label["value"], "label value"))
        units.add(str(label["unit"]))
        for text_key in ("quantity_kind", "engine", "fidelity"):
            if not isinstance(label[text_key], str) or not label[text_key]:
                raise ModelAcceptanceError(f"{text_key} is required")
    if train_parents & test_parents:
        raise ModelAcceptanceError("parent leakage crosses train and evaluation splits")
    if len(methods) != 1:
        raise ModelAcceptanceError("mixed method fingerprints are not allowed")
    if len(units) != 1:
        raise ModelAcceptanceError("mixed label units are not allowed")
    if max(values) == min(values):
        raise ModelAcceptanceError("constant target is not trainable")
    return {"status": "PASS", "samples": len(samples), "method_fingerprint": next(iter(methods))}


def authorize_training_v5(
    *, dataset_path: Path, validation_artifact: Mapping[str, object], labels: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    required = {"status", "dataset_sha256", "schema_version", "split_sha256"}
    if set(validation_artifact) != required or validation_artifact["status"] != "PASS":
        raise ModelAcceptanceError("validation artifact is not an exact PASS")
    if validation_artifact["schema_version"] != "tsao.dft.dataset-validation.v5":
        raise ModelAcceptanceError("validation artifact schema is not supported")
    expected = require_sha256(validation_artifact["dataset_sha256"], "dataset_sha256")
    require_sha256(validation_artifact["split_sha256"], "split_sha256")
    actual = hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest()
    if actual != expected:
        raise ModelAcceptanceError("dataset checksum changed after validation")
    validate_labels(labels)
    return {"training_authorized": True, "model_status_ceiling": "BASELINE_GENERATED", "dataset_sha256": actual}


def validate_predictive_model_card(card: Mapping[str, object], *, now: str) -> dict[str, object]:
    required = {
        "status",
        "dataset_sha256",
        "model_sha256",
        "code_sha256",
        "environment_sha256",
        "trainer_identity",
        "applicability_domain",
        "calibrated_uncertainty",
        "holdout_validation",
        "independent_approval",
    }
    if set(card) != required:
        raise ModelAcceptanceError("model card is incomplete")
    for key in ("dataset_sha256", "model_sha256", "code_sha256", "environment_sha256"):
        require_sha256(card[key], key)
    trainer = card["trainer_identity"]
    if not isinstance(trainer, str) or not trainer:
        raise ModelAcceptanceError("trainer identity is required")
    for key in ("applicability_domain", "calibrated_uncertainty", "holdout_validation"):
        if not isinstance(card[key], Mapping) or not card[key]:
            raise ModelAcceptanceError(f"{key} is required")
        _validate_finite_tree(card[key], key)
    approval = card["independent_approval"]
    if not isinstance(approval, Mapping):
        raise ModelAcceptanceError("independent approval is required")
    if approval.get("issuer") == trainer:
        raise ModelAcceptanceError("self-issued approval is forbidden")
    if approval.get("model_sha256") != card["model_sha256"]:
        raise ModelAcceptanceError("approval model hash does not match the card")
    if approval.get("role") != "qualified-scientist" or approval.get("scope") != "predictive-model-use":
        raise ModelAcceptanceError("approval role or scope is invalid")
    if not isinstance(approval.get("signature"), str) or not approval.get("signature"):
        raise ModelAcceptanceError("approval signature is required")
    current = parse_timestamp(now, "now")
    issued = parse_timestamp(str(approval.get("issued_at")), "issued_at")
    expires = parse_timestamp(str(approval.get("expires_at")), "expires_at")
    if not issued <= current < expires:
        raise ModelAcceptanceError("approval is not currently valid")
    return {"predictive_use_allowed": True, "truth_boundary": "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"}


def _validate_finite_tree(value: object, name: str) -> None:
    if isinstance(value, bool):
        raise ModelAcceptanceError(f"{name} contains a Boolean numeric value")
    if isinstance(value, (int, float)):
        finite_real(value, name)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite_tree(item, f"{name}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_finite_tree(item, f"{name}[{index}]")
    elif value is None or isinstance(value, str):
        return
    else:
        raise ModelAcceptanceError(f"{name} contains an unsupported value")


@dataclass(frozen=True)
class DatasetValidationArtifact:
    artifact_id: str
    dataset_sha256: str
    schema_sha256: str
    validator_sha256: str
    split_sha256: str
    sample_count: int
    quantity_kind: str
    unit: str
    method_fingerprint: str
    status: str
    issuer: str
    issued_at: str
    signature: str

    def __post_init__(self) -> None:
        for key in ("dataset_sha256", "schema_sha256", "validator_sha256", "split_sha256"):
            require_sha256(getattr(self, key), key)
        exact_int(self.sample_count, "sample_count", minimum=1)
        if self.status != "PASS":
            raise ModelAcceptanceError("dataset validation artifact must be PASS")


@dataclass(frozen=True)
class ModelCard:
    model_id: str
    dataset_sha256: str
    model_sha256: str
    code_sha256: str
    environment_sha256: str
    schema_sha256: str
    applicability_domain: Mapping[str, object] | None
    uncertainty_model: Mapping[str, object] | None
    holdout_metrics: Mapping[str, object] | None
    trainer_identity: str

    def __post_init__(self) -> None:
        for key in ("dataset_sha256", "model_sha256", "code_sha256", "environment_sha256", "schema_sha256"):
            require_sha256(getattr(self, key), key)
        if not self.trainer_identity:
            raise ModelAcceptanceError("trainer identity is required")
        if self.holdout_metrics is not None:
            try:
                _validate_finite_tree(self.holdout_metrics, "holdout_metrics")
            except DFTContractError as exc:
                raise ModelAcceptanceError(str(exc)) from exc


@dataclass(frozen=True)
class ModelApproval:
    approval_id: str
    model_sha256: str
    dataset_sha256: str
    scope: str
    audience: str
    approver: str
    authorized_role: str
    issued_at: str
    expires_at: str
    nonce: str
    key_id: str
    signature: str

    def unsigned(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self) if field.name != "signature"}


def sign_approval(unsigned: Mapping[str, object], key: bytes) -> str:
    return _hmac_digest(key, unsigned)


def assess_model_card(
    card: ModelCard,
    *,
    dataset_artifact: DatasetValidationArtifact,
    expected_schema_sha256: str,
    approval: ModelApproval | None,
    key_resolver: Callable[[str], bytes | None] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    expected_schema = require_sha256(expected_schema_sha256, "expected_schema_sha256")
    if card.dataset_sha256 != dataset_artifact.dataset_sha256:
        raise ModelAcceptanceError("dataset SHA does not match validation artifact")
    if dataset_artifact.schema_sha256 != expected_schema or card.schema_sha256 != dataset_artifact.split_sha256:
        raise ModelAcceptanceError("schema or split SHA does not match the validated chain")
    blockers: list[str] = []
    if not card.applicability_domain:
        blockers.append("APPLICABILITY_DOMAIN_MISSING")
    if not card.uncertainty_model:
        blockers.append("CALIBRATED_UNCERTAINTY_MISSING")
    if not card.holdout_metrics:
        blockers.append("HOLDOUT_VALIDATION_MISSING")
    if approval is None:
        blockers.append("INDEPENDENT_APPROVAL_MISSING")
    else:
        if approval.approver == card.trainer_identity:
            blockers.append("TRAINER_CANNOT_SELF_APPROVE")
        if approval.model_sha256 != card.environment_sha256 or approval.dataset_sha256 != card.dataset_sha256:
            blockers.append("APPROVAL_BINDING_MISMATCH")
        if approval.scope != "predictive-dft-model" or approval.audience != "tsao-dft":
            blockers.append("APPROVAL_SCOPE_MISMATCH")
        if approval.authorized_role != "independent_model_validator":
            blockers.append("APPROVAL_ROLE_MISMATCH")
        active_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if (
            not parse_timestamp(approval.issued_at, "issued_at")
            <= active_now
            < parse_timestamp(approval.expires_at, "expires_at")
        ):
            blockers.append("APPROVAL_NOT_CURRENT")
        if key_resolver is None:
            blockers.append("APPROVAL_KEY_UNAVAILABLE")
        else:
            key = key_resolver(approval.key_id)
            if key is None or not hmac.compare_digest(approval.signature, sign_approval(approval.unsigned(), key)):
                raise ModelAcceptanceError("approval signature is invalid")
    if blockers:
        return {"status": "HOLD", "accepted": False, "blockers": blockers}
    return {"status": "ACCEPTED", "accepted": True, "blockers": []}


@dataclass(frozen=True)
class TypedQuantity:
    quantity_kind: str
    values: object
    unit: str
    shape: tuple[int, ...]
    aggregation: str
    atom_mapping: tuple[str, ...] | None = None
    method_fingerprint: str | None = None
    periodicity: str | None = None
    component_convention: str | None = None

    def __post_init__(self) -> None:
        if self.quantity_kind == "atomic_forces_full":
            if self.aggregation != "full" or len(self.shape) != 2 or self.shape[1] != 3:
                raise QuantityEquivalenceError("full atomic forces require N x 3 shape and full aggregation")
            if self.atom_mapping is None or len(self.atom_mapping) != self.shape[0]:
                raise QuantityEquivalenceError("full atomic forces require exact atom mapping")
            nested = _nested_numeric(self.values, "values")
            if len(nested) != self.shape[0] or any(not isinstance(row, tuple) or len(row) != 3 for row in nested):
                raise QuantityEquivalenceError("full atomic-force values do not match shape")
        elif self.quantity_kind in {"stress_tensor_full", "stress_tensor"}:
            if self.aggregation != "full" or self.shape not in {(6,), (3, 3)}:
                raise QuantityEquivalenceError("full stress cannot be represented by a summary scalar")
            flattened = _flatten_numeric(self.values, "values")
            if len(flattened) not in {6, 9}:
                raise QuantityEquivalenceError("full stress requires six or nine components")
            if not self.component_convention:
                raise QuantityEquivalenceError("stress component convention is required")
        else:
            _flatten_numeric(self.values, "values")


def _unit_to_canonical(unit: str) -> float:
    factors = {
        "eV/angstrom": 1.0,
        "hartree/bohr": HARTREE_TO_EV / BOHR_TO_ANGSTROM,
        "GPa": 1.0,
    }
    try:
        return factors[unit]
    except KeyError as exc:
        raise QuantityEquivalenceError(f"unsupported quantity unit: {unit}") from exc


def equivalent(left: TypedQuantity, right: TypedQuantity, *, rel_tol: float = 1e-12, abs_tol: float = 1e-12) -> bool:
    structural = (
        left.quantity_kind == right.quantity_kind
        and left.shape == right.shape
        and left.aggregation == right.aggregation
        and left.atom_mapping == right.atom_mapping
        and left.method_fingerprint == right.method_fingerprint
        and left.periodicity == right.periodicity
        and left.component_convention == right.component_convention
    )
    if not structural:
        return False
    lvalues = _flatten_numeric(left.values, "left.values")
    rvalues = _flatten_numeric(right.values, "right.values")
    if len(lvalues) != len(rvalues):
        return False
    lf = _unit_to_canonical(left.unit)
    rf = _unit_to_canonical(right.unit)
    return all(
        math.isclose(a * lf, b * rf, rel_tol=rel_tol, abs_tol=abs_tol) for a, b in zip(lvalues, rvalues, strict=True)
    )


@dataclass(frozen=True)
class KineticsUncertaintyResult:
    rate_constant: float
    lower: float
    upper: float
    log_rate_sigma: float
    rate_unit: str
    status: str
    correlation_contribution: float

    def to_json(self) -> str:
        return canonical_json(asdict(self))


def propagate_tst_uncertainty(
    *,
    barrier: object,
    barrier_unit: str,
    temperature_K: object,
    molecularity: int = 1,
    standard_state_M: object | None = None,
    sigma_barrier: object = 0.0,
    sigma_barrier_unit: str = "kJ/mol",
    sigma_temperature_K: object = 0.0,
    relative_sigma_standard_state: object = 0.0,
    correlation_barrier_temperature: object = 0.0,
) -> KineticsUncertaintyResult:
    try:
        energy = barrier_j_mol(barrier, barrier_unit)
        temperature = finite_real(temperature_K, "temperature_K", positive=True)
        order = exact_int(molecularity, "molecularity", minimum=1)
    except DFTContractError as exc:
        raise KineticsUncertaintyError(str(exc)) from exc
    if order > 1:
        if standard_state_M is None:
            raise KineticsUncertaintyError("standard_state_M is required")
        concentration = finite_real(standard_state_M, "standard_state_M", positive=True)
    else:
        concentration = 1.0
    sigma_g = barrier_j_mol(sigma_barrier, sigma_barrier_unit)
    sigma_t = finite_real(sigma_temperature_K, "sigma_temperature_K", nonnegative=True)
    sigma_c = finite_real(relative_sigma_standard_state, "relative_sigma_standard_state", nonnegative=True)
    rho = finite_real(correlation_barrier_temperature, "correlation_barrier_temperature")
    if sigma_g < 0 or not -1.0 <= rho <= 1.0:
        raise KineticsUncertaintyError("uncertainty or correlation is outside its domain")
    base = eyring_rate(
        energy,
        barrier_unit="J/mol",
        temperature_K=temperature,
        molecularity=order,
        standard_state=StandardState(concentration, "M", "dimensionless_activity_c_over_c0") if order > 1 else None,
    )
    if base.rate_constant is None:
        raise KineticsUncertaintyError("point rate is undefined")
    d_g = -1.0 / (R * temperature)
    d_t = 1.0 / temperature + energy / (R * temperature * temperature)
    d_c = float(1 - order)
    correlation = 2.0 * rho * d_g * d_t * sigma_g * sigma_t
    variance = (d_g * sigma_g) ** 2 + (d_t * sigma_t) ** 2 + (d_c * sigma_c) ** 2 + correlation
    if variance < -1e-15:
        raise KineticsUncertaintyError("correlation produces a negative variance")
    sigma = math.sqrt(max(0.0, variance))
    lower = base.rate_constant * math.exp(-sigma)
    upper = base.rate_constant * math.exp(sigma)
    return KineticsUncertaintyResult(
        base.rate_constant,
        lower,
        upper,
        sigma,
        base.rate_unit,
        "CALCULATED_UNCERTAINTY_NOT_VALIDATED",
        correlation,
    )


@dataclass(frozen=True)
class AcceptanceV6:
    software_integrity_status: str
    external_execution_status: str
    scientific_acceptance_status: str
    reason_codes: tuple[str, ...]


def evaluate_acceptance_v6(
    *,
    parser_receipt: Mapping[str, object],
    quantity_receipt: Mapping[str, object],
    kinetics_receipt: Mapping[str, object] | None,
    model_receipt: Mapping[str, object] | None,
    external_execution_receipt: Mapping[str, object] | None,
) -> AcceptanceV6:
    if parser_receipt.get("parser_accepted") is not True or parser_receipt.get("fatal") is True:
        return AcceptanceV6("FAIL", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("PARSER_REJECTED",))
    if quantity_receipt.get("status") != "PASS":
        return AcceptanceV6("FAIL", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("QUANTITY_CONTRACT_FAILED",))
    if external_execution_receipt is None:
        return AcceptanceV6(
            "PASS", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("EXTERNAL_EXECUTION_RECEIPT_REQUIRED",)
        )
    if external_execution_receipt.get("status") != "VERIFIED_FOR_BOUND_OUTPUT" or not is_sha256(
        external_execution_receipt.get("artifact_sha256")
    ):
        return AcceptanceV6(
            "PASS", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("EXTERNAL_EXECUTION_RECEIPT_INVALID",)
        )
    ready = (
        kinetics_receipt is not None
        and kinetics_receipt.get("status") == "VALID"
        and kinetics_receipt.get("standard_state_explicit") is True
        and model_receipt is not None
        and model_receipt.get("status") == "ACCEPTED"
        and model_receipt.get("independent_approval_verified") is True
    )
    if ready:
        return AcceptanceV6(
            "PASS",
            "VERIFIED_FOR_BOUND_OUTPUT",
            "READY_FOR_INDEPENDENT_SCIENTIFIC_REVIEW",
            ("INDEPENDENT_SCIENTIFIC_REVIEW_REQUIRED",),
        )
    return AcceptanceV6("PASS", "VERIFIED_FOR_BOUND_OUTPUT", "HOLD", ("SCIENTIFIC_REVIEW_INPUTS_INCOMPLETE",))


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    issuer: str
    authorized_role: str
    engine: str
    repository_commit: str
    repository_tree: str
    executable_sha256: str
    input_sha256: str
    output_sha256: str
    method_fingerprint_sha256: str
    environment_sha256: str
    parser_record_sha256: str
    subject: str
    scope: str
    audience: str
    issued_at: str
    expires_at: str
    nonce: str
    key_id: str
    signature: str

    def unsigned(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self) if field.name != "signature"}


@dataclass(frozen=True)
class ScientificReview:
    review_id: str
    execution_receipt_sha256: str
    result_sha256: str
    claim_scope_sha256: str
    reviewer: str
    authorized_role: str
    scope: str
    audience: str
    disposition: str
    issued_at: str
    expires_at: str
    nonce: str
    key_id: str
    signature: str

    def unsigned(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self) if field.name != "signature"}


def issue_execution_receipt(*, key: bytes, **values: object) -> ExecutionReceipt:
    required = {field.name for field in fields(ExecutionReceipt)} - {"signature"}
    if set(values) != required:
        raise DFTContractError("execution receipt fields are incomplete")
    for key_name in (
        "executable_sha256",
        "input_sha256",
        "output_sha256",
        "method_fingerprint_sha256",
        "environment_sha256",
        "parser_record_sha256",
    ):
        require_sha256(values[key_name], key_name)
    for key_name in ("repository_commit", "repository_tree"):
        if not isinstance(values[key_name], str) or not re.fullmatch(r"[0-9a-f]{40}", cast(str, values[key_name])):
            raise DFTContractError(f"{key_name} must be a Git SHA-1")
    if values["authorized_role"] != "licensed-dft-runner":
        raise DFTContractError("execution receipt role is not authorized")
    issued = parse_timestamp(str(values["issued_at"]), "issued_at")
    expires = parse_timestamp(str(values["expires_at"]), "expires_at")
    if issued >= expires:
        raise DFTContractError("execution receipt expiry must follow issuance")
    signature = _hmac_digest(key, values)
    return ExecutionReceipt(
        receipt_id=str(values["receipt_id"]),
        issuer=str(values["issuer"]),
        authorized_role=str(values["authorized_role"]),
        engine=str(values["engine"]),
        repository_commit=str(values["repository_commit"]),
        repository_tree=str(values["repository_tree"]),
        executable_sha256=str(values["executable_sha256"]),
        input_sha256=str(values["input_sha256"]),
        output_sha256=str(values["output_sha256"]),
        method_fingerprint_sha256=str(values["method_fingerprint_sha256"]),
        environment_sha256=str(values["environment_sha256"]),
        parser_record_sha256=str(values["parser_record_sha256"]),
        subject=str(values["subject"]),
        scope=str(values["scope"]),
        audience=str(values["audience"]),
        issued_at=str(values["issued_at"]),
        expires_at=str(values["expires_at"]),
        nonce=str(values["nonce"]),
        key_id=str(values["key_id"]),
        signature=signature,
    )


def issue_scientific_review(*, key: bytes, **values: object) -> ScientificReview:
    required = {field.name for field in fields(ScientificReview)} - {"signature"}
    if set(values) != required:
        raise DFTContractError("scientific review fields are incomplete")
    for key_name in ("execution_receipt_sha256", "result_sha256", "claim_scope_sha256"):
        require_sha256(values[key_name], key_name)
    if values["authorized_role"] != "independent-computational-chemist":
        raise DFTContractError("scientific review role is not authorized")
    if values["disposition"] != "ACCEPTED_WITHIN_SCOPE":
        raise DFTContractError("unsupported scientific review disposition")
    issued = parse_timestamp(str(values["issued_at"]), "issued_at")
    expires = parse_timestamp(str(values["expires_at"]), "expires_at")
    if issued >= expires:
        raise DFTContractError("scientific review expiry must follow issuance")
    signature = _hmac_digest(key, values)
    return ScientificReview(
        review_id=str(values["review_id"]),
        execution_receipt_sha256=str(values["execution_receipt_sha256"]),
        result_sha256=str(values["result_sha256"]),
        claim_scope_sha256=str(values["claim_scope_sha256"]),
        reviewer=str(values["reviewer"]),
        authorized_role=str(values["authorized_role"]),
        scope=str(values["scope"]),
        audience=str(values["audience"]),
        disposition=str(values["disposition"]),
        issued_at=str(values["issued_at"]),
        expires_at=str(values["expires_at"]),
        nonce=str(values["nonce"]),
        key_id=str(values["key_id"]),
        signature=signature,
    )


def verify_execution_receipt(
    receipt: ExecutionReceipt,
    *,
    key_resolver: Callable[[str], bytes | None],
    expected_bindings: Mapping[str, object],
    allowed_issuers: set[str],
    now: datetime,
) -> str:
    if not isinstance(receipt, ExecutionReceipt):
        raise DFTContractError("execution authority must be a signed ExecutionReceipt")
    if receipt.issuer not in allowed_issuers:
        raise DFTContractError("execution receipt issuer is not allowed")
    if receipt.authorized_role != "licensed-dft-runner":
        raise DFTContractError("execution receipt role is invalid")
    for key, expected in expected_bindings.items():
        if getattr(receipt, key, None) != expected:
            raise DFTContractError(f"execution receipt binding mismatch: {key}")
    active = now.astimezone(timezone.utc)
    if (
        not parse_timestamp(receipt.issued_at, "issued_at")
        <= active
        < parse_timestamp(receipt.expires_at, "expires_at")
    ):
        raise DFTContractError("execution receipt is expired or not yet valid")
    resolved_key = key_resolver(receipt.key_id)
    if key is None or not hmac.compare_digest(
        receipt.signature, _hmac_digest(cast(bytes, resolved_key), receipt.unsigned())
    ):
        raise DFTContractError("execution receipt signature is invalid")
    return digest_mapping(asdict(receipt))


def verify_scientific_review(
    review: ScientificReview,
    *,
    key_resolver: Callable[[str], bytes | None],
    expected_execution_receipt_sha256: str,
    expected_result_sha256: str,
    expected_claim_scope_sha256: str,
    expected_scope: str,
    expected_audience: str,
    allowed_reviewers: set[str],
    now: datetime,
    execution_subject: str,
    consumed_nonces: set[str] | None = None,
    revoked_ids: set[str] | None = None,
) -> str:
    if not isinstance(review, ScientificReview):
        raise DFTContractError("scientific authority must be a signed ScientificReview")
    if revoked_ids and review.review_id in revoked_ids:
        raise DFTContractError("scientific review is revoked")
    if consumed_nonces is not None and review.nonce in consumed_nonces:
        raise DFTContractError("scientific review nonce already consumed")
    if review.reviewer not in allowed_reviewers or review.reviewer == execution_subject:
        raise DFTContractError("scientific review is not independent")
    expected = {
        "execution_receipt_sha256": expected_execution_receipt_sha256,
        "result_sha256": expected_result_sha256,
        "claim_scope_sha256": expected_claim_scope_sha256,
        "scope": expected_scope,
        "audience": expected_audience,
    }
    for key_name, expected_value in expected.items():
        if getattr(review, key_name) != expected_value:
            raise DFTContractError(f"scientific review binding mismatch: {key_name}")
    active = now.astimezone(timezone.utc)
    if not parse_timestamp(review.issued_at, "issued_at") <= active < parse_timestamp(review.expires_at, "expires_at"):
        raise DFTContractError("scientific review is expired or not yet valid")
    key = key_resolver(review.key_id)
    if key is None or not hmac.compare_digest(review.signature, _hmac_digest(key, review.unsigned())):
        raise DFTContractError("scientific review signature is invalid")
    if consumed_nonces is not None:
        consumed_nonces.add(review.nonce)
    return digest_mapping(asdict(review))


@dataclass(frozen=True)
class AcceptanceV7:
    software_integrity_status: str
    external_execution_status: str
    scientific_acceptance_status: str
    reason_codes: tuple[str, ...]
    evidence_digests: tuple[str, ...]


def evaluate_acceptance_v7(
    *,
    parser_record: Mapping[str, object],
    quantity_record: Mapping[str, object],
    execution_receipt: ExecutionReceipt | None,
    scientific_review: ScientificReview | None,
    execution_key_resolver: Callable[[str], bytes | None],
    review_key_resolver: Callable[[str], bytes | None],
    expected_execution_bindings: Mapping[str, object],
    expected_claim_scope_sha256: str,
    allowed_execution_issuers: set[str],
    allowed_reviewers: set[str],
    now: datetime,
) -> AcceptanceV7:
    if parser_record.get("parser_accepted") is not True or parser_record.get("status") != "CONVERGED":
        return AcceptanceV7("FAIL", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "FAIL", ("PARSER_REJECTED",), ())
    if parser_record.get("record_sha256") != expected_execution_bindings.get(
        "parser_record_sha256"
    ) or parser_record.get("output_sha256") != expected_execution_bindings.get("output_sha256"):
        return AcceptanceV7("FAIL", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "FAIL", ("PARSER_BINDING_MISMATCH",), ())
    if quantity_record.get("status") != "PASS" or not is_sha256(quantity_record.get("record_sha256")):
        return AcceptanceV7("FAIL", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "FAIL", ("QUANTITY_RECORD_REJECTED",), ())
    if execution_receipt is None:
        return AcceptanceV7(
            "PASS", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("SIGNED_EXECUTION_RECEIPT_REQUIRED",), ()
        )
    try:
        execution_digest = verify_execution_receipt(
            execution_receipt,
            key_resolver=execution_key_resolver,
            expected_bindings=expected_execution_bindings,
            allowed_issuers=allowed_execution_issuers,
            now=now,
        )
    except DFTContractError:
        return AcceptanceV7("PASS", "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED", "HOLD", ("EXECUTION_RECEIPT_INVALID",), ())
    if scientific_review is None:
        return AcceptanceV7(
            "PASS",
            "VERIFIED_FOR_EXACT_BOUND_OUTPUT",
            "HOLD",
            ("INDEPENDENT_SCIENTIFIC_REVIEW_REQUIRED",),
            (execution_digest,),
        )
    try:
        review_digest = verify_scientific_review(
            scientific_review,
            key_resolver=review_key_resolver,
            expected_execution_receipt_sha256=execution_digest,
            expected_result_sha256=str(expected_execution_bindings["output_sha256"]),
            expected_claim_scope_sha256=require_sha256(expected_claim_scope_sha256, "expected_claim_scope_sha256"),
            expected_scope=str(expected_execution_bindings["scope"]),
            expected_audience=str(expected_execution_bindings["audience"]),
            allowed_reviewers=allowed_reviewers,
            now=now,
            execution_subject=str(expected_execution_bindings["subject"]),
        )
    except DFTContractError:
        return AcceptanceV7(
            "PASS", "VERIFIED_FOR_EXACT_BOUND_OUTPUT", "HOLD", ("SCIENTIFIC_REVIEW_INVALID",), (execution_digest,)
        )
    return AcceptanceV7(
        "PASS",
        "VERIFIED_FOR_EXACT_BOUND_OUTPUT",
        "ACCEPTED_WITHIN_SIGNED_REVIEW_SCOPE",
        (),
        (execution_digest, review_digest),
    )
