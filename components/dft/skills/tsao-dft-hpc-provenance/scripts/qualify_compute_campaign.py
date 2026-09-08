#!/usr/bin/env python3
"""Qualify reproducible CPU/accelerator campaigns from canonical or explicit legacy evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import benchmark_contract as contract  # noqa: E402 -- standalone Skill import contract
import compute_campaign_contract as campaign_policy  # noqa: E402 -- standalone Skill import contract
import performance_evidence as performance  # noqa: E402 -- standalone Skill import contract

ROOT = SCRIPT_PATH.parents[3] if len(SCRIPT_PATH.parents) > 3 else Path.cwd()
DEFAULT_SCHEMA = contract.CANONICAL_SCHEMA_PATH
MAX_WORKERS = 8
EXTERNAL_HOLD = "EXTERNAL_HOLD"
UNQUALIFIED = "UNQUALIFIED"
QUALIFIED_FOR_REVIEW = "QUALIFIED_FOR_REVIEW"
GPU_BACKENDS = {"cuda", "openacc", "hip", "sycl", "metal"}
STANDARD_RESULTS = {
    "energy_ev": "energy",
    "forces_ev_per_angstrom": "forces",
    "stress_gpa": "stress",
}
PROJECTION_STATUS = "RETAINED_DIAGNOSTIC_NOT_ELIGIBLE"
CAMPAIGN_CONTRACT = campaign_policy.CANONICAL_CONTRACT
CAMPAIGN_SCHEMA_VERSION = campaign_policy.CANONICAL_SCHEMA_VERSION


class QualificationLoadError(ValueError):
    """Raised when campaign or evidence documents cannot be decoded safely."""


@dataclass(frozen=True)
class CampaignDocument:
    """Immutable typed access to one centrally normalized canonical nested v1.1 result."""

    source: str
    record: Mapping[str, Any]
    migration: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "record",
            cast(Mapping[str, Any], campaign_policy.freeze_tree(self.record)),
        )
        object.__setattr__(
            self,
            "migration",
            cast(Mapping[str, Any], campaign_policy.freeze_tree(self.migration)),
        )
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    @property
    def schema_version(self) -> str:
        return str(self.record["schema_version"])

    @property
    def benchmark_plan_id(self) -> str:
        return str(self.record["benchmark_plan_id"])

    @property
    def candidate_id(self) -> str:
        return str(self.record["candidate_id"])

    @property
    def role(self) -> str:
        return str(self.record["role"])

    @property
    def repeat_index(self) -> int:
        return int(self.record["repeat_index"])

    @property
    def engine_name(self) -> str:
        return str(cast(Mapping[str, Any], self.record["engine"])["name"])

    @property
    def engine_version(self) -> str:
        return str(cast(Mapping[str, Any], self.record["engine"])["version"])

    @property
    def engine_executable(self) -> str:
        return str(cast(Mapping[str, Any], self.record["engine"])["executable"])

    @property
    def build_fingerprint_id(self) -> str:
        return str(cast(Mapping[str, Any], self.record["engine"])["build_fingerprint_id"])

    @property
    def hardware_fingerprint_id(self) -> str:
        return str(cast(Mapping[str, Any], self.record["hardware"])["hardware_fingerprint_id"])

    @property
    def site_id(self) -> str:
        return str(cast(Mapping[str, Any], self.record["execution"])["site_id"])

    @property
    def run_id(self) -> str:
        return str(cast(Mapping[str, Any], self.record["execution"])["run_id"])

    @property
    def input_sha256(self) -> str:
        return str(cast(Mapping[str, Any], self.record["scientific"])["input_sha256"])

    @property
    def method_fingerprint_id(self) -> str:
        return str(cast(Mapping[str, Any], self.record["scientific"])["method_fingerprint_id"])

    @property
    def evidence_kind(self) -> str:
        return str(cast(Mapping[str, Any], self.record["evidence_source"])["kind"])

    @property
    def missing_fields(self) -> tuple[str, ...]:
        evidence = cast(Mapping[str, Any], self.record["evidence_source"])
        return tuple(str(item) for item in cast(Sequence[Any], evidence["missing_fields"]))

    @property
    def parser_accepted(self) -> bool:
        return cast(Mapping[str, Any], self.record["scientific"])["parser_accepted"] is True

    @property
    def exit_status(self) -> int:
        return int(cast(Mapping[str, Any], self.record["execution"])["exit_status"])

    @property
    def wall_time_s(self) -> float:
        return float(cast(Mapping[str, Any], self.record["performance"])["wall_time_s"])

    @property
    def accelerator_backend(self) -> str:
        software = cast(Mapping[str, Any], self.record["software"])
        return _backend_from_runtime(software["accelerator_runtime"])

    @property
    def gpu_uuids(self) -> tuple[str, ...]:
        hardware = cast(Mapping[str, Any], self.record["hardware"])
        return tuple(str(item) for item in cast(Sequence[Any], hardware["gpu_uuids"]))

    @property
    def all_artifacts_verified(self) -> bool:
        return performance.all_artifacts_verified(self.mutable_record())

    @property
    def scientific_identity(self) -> str:
        return performance.scientific_identity(self.mutable_record())

    @property
    def candidate_execution_identity(self) -> tuple[Any, ...]:
        engine = cast(Mapping[str, Any], self.record["engine"])
        software = cast(Mapping[str, Any], self.record["software"])
        hardware = cast(Mapping[str, Any], self.record["hardware"])
        return (
            engine["version"],
            engine["executable"],
            engine["build_fingerprint_id"],
            software["compiler"],
            software["mpi"],
            software["openmp_runtime"],
            software["accelerator_runtime"],
            hardware["site_id"],
            hardware["hardware_fingerprint_id"],
            hardware["nodes"],
            hardware["ranks_per_node"],
            hardware["threads_per_rank"],
            hardware["gpu_vendor"],
            hardware["gpu_model"],
            tuple(cast(Sequence[Any], hardware["gpu_uuids"])),
            hardware["gpu_memory_gb"],
            hardware["driver_version"],
            hardware["gpu_binding"],
        )

    def mutable_record(self) -> dict[str, Any]:
        return cast(dict[str, Any], campaign_policy.thaw_tree(self.record))

    def migration_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], campaign_policy.thaw_tree(self.migration))

    def scientific_observables(self) -> dict[str, Any]:
        scientific = cast(Mapping[str, Any], self.record["scientific"])
        results = cast(Mapping[str, Any], scientific["results"])
        observables = {
            key: campaign_policy.thaw_tree(value)
            for key, value in results.items()
            if key in STANDARD_RESULTS and value is not None
        }
        properties = cast(Mapping[str, Any], results.get("properties") or {})
        collisions = sorted(set(properties) & set(STANDARD_RESULTS))
        if collisions:
            raise ValueError(f"scientific properties collide with standard result fields: {collisions}")
        observables.update({str(key): campaign_policy.thaw_tree(value) for key, value in properties.items()})
        return observables


def _reject_constant(value: str) -> None:
    raise QualificationLoadError(f"non-finite JSON constant is forbidden: {value}")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise QualificationLoadError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, QualificationLoadError) as exc:
        raise QualificationLoadError(f"cannot load {path.name}: {exc}") from exc
    if type(value) is not dict:
        raise QualificationLoadError(f"{path.name} root must be a mapping")
    return value


def load_campaign_config(path: Path) -> campaign_policy.CampaignConfig:
    try:
        return campaign_policy.load_campaign(path)
    except campaign_policy.CampaignContractError as exc:
        raise QualificationLoadError(str(exc)) from exc


def load_campaign(path: Path) -> dict[str, Any]:
    """Compatibility API returning the centrally normalized canonical campaign mapping."""
    return load_campaign_config(path).to_dict()


def validate_campaign(campaign: Any) -> list[str]:
    return campaign_policy.validate_campaign(campaign)


def _prepare_campaign(
    campaign: campaign_policy.CampaignConfig | dict[str, Any],
) -> campaign_policy.CampaignConfig:
    try:
        if isinstance(campaign, campaign_policy.CampaignConfig):
            return campaign_policy.prepare_campaign(campaign.to_dict(), source=campaign.source)
        if type(campaign) is dict:
            return campaign_policy.prepare_campaign(campaign)
        raise campaign_policy.CampaignContractError("campaign root must be a mapping")
    except campaign_policy.CampaignContractError as exc:
        raise QualificationLoadError(str(exc)) from exc


def normalized_workers(workers: int | None, tasks: int) -> int:
    if isinstance(tasks, bool) or not isinstance(tasks, int) or tasks < 0:
        raise ValueError("tasks must be a non-negative integer")
    if workers is not None and (isinstance(workers, bool) or not isinstance(workers, int)):
        raise ValueError("workers must be an integer or null")
    if workers is not None and workers < 0:
        raise ValueError("workers must be non-negative")
    if tasks < 2:
        return 1
    requested = workers or min(MAX_WORKERS, os.cpu_count() or 1)
    return max(1, min(requested, MAX_WORKERS, tasks))


def _backend_from_runtime(value: Any) -> str:
    text = str(value or "none").lower()
    for backend in sorted(GPU_BACKENDS):
        if text.startswith(backend) or f"{backend};" in text:
            return backend
    return "none"


def _expected_observable_names(record: dict[str, Any]) -> set[str]:
    results = record["scientific"]["results"]
    names = {logical_name for field, logical_name in STANDARD_RESULTS.items() if results.get(field) is not None}
    names.update(str(key) for key in (results.get("properties") or {}))
    return names


def _campaign_semantic_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    results = record["scientific"]["results"]
    properties = results.get("properties") or {}
    collisions = sorted(set(properties) & set(STANDARD_RESULTS))
    if collisions:
        errors.append(f"scientific properties collide with standard result fields: {collisions}")
    if record["scientific"]["parser_accepted"] is True:
        declared = set(str(item) for item in record["scientific"]["observable_set"])
        observed = _expected_observable_names(record)
        if declared != observed:
            errors.append(
                "scientific.observable_set does not match populated canonical result fields: "
                f"declared={sorted(declared)} observed={sorted(observed)}"
            )
    return errors


def prepare_document(
    record: dict[str, Any],
    *,
    role_hint: str | None = None,
    source: str = "<memory>",
    artifact_root: Path | None = None,
) -> CampaignDocument:
    try:
        canonical, migration = contract.normalize_record(record, role_hint=role_hint)
        validated, semantic_errors, warnings = performance.validate_canonical_result(
            canonical,
            artifact_root,
        )
    except (TypeError, ValueError, contract.BenchmarkContractError) as exc:
        raise QualificationLoadError(f"{source}: benchmark contract normalization failed: {exc}") from exc
    validated.pop("validation", None)
    semantic_errors = [*semantic_errors, *_campaign_semantic_errors(validated)]
    if semantic_errors:
        raise QualificationLoadError(f"{source}: canonical semantic validation failed: {'; '.join(semantic_errors)}")
    return CampaignDocument(
        source=source,
        record=validated,
        migration=migration,
        warnings=tuple(warnings),
    )


def _load_normalized(
    path: Path,
    role_hints: Mapping[str, str],
) -> tuple[str, CampaignDocument | None, list[str]]:
    try:
        raw = load_json(path)
        candidate_id = str(raw.get("candidate_id", ""))
        document = prepare_document(
            raw,
            role_hint=role_hints.get(candidate_id),
            source=path.as_posix(),
        )
    except (QualificationLoadError, ValueError) as exc:
        return path.as_posix(), None, [str(exc)]
    return path.as_posix(), document, []


def load_results(
    paths: list[Path],
    schema: dict[str, Any],
    workers: int | None = None,
    role_hints: Mapping[str, str] | None = None,
) -> tuple[list[CampaignDocument], list[str]]:
    if contract.approved_schema_kind(schema) != "canonical-nested-v1.1":
        return [], ["compute qualification requires the authoritative nested v1.1 schema"]
    ordered = sorted((Path(path) for path in paths), key=lambda path: path.as_posix())
    hints = role_hints or {}
    count = normalized_workers(workers, len(ordered))
    if count == 1:
        loaded = [_load_normalized(path, hints) for path in ordered]
    else:
        with ThreadPoolExecutor(
            max_workers=count,
            thread_name_prefix="tsao-qualify",
        ) as executor:
            loaded = list(executor.map(lambda path: _load_normalized(path, hints), ordered))
    documents = [document for _, document, errors in loaded if document is not None and not errors]
    errors = [error for _, _, item_errors in loaded for error in item_errors]
    return documents, errors


def _role_hints(campaign: campaign_policy.CampaignConfig) -> Mapping[str, str]:
    return campaign.expected_roles


def _coerce_documents(
    campaign: campaign_policy.CampaignConfig,
    documents: Sequence[CampaignDocument | dict[str, Any]],
) -> tuple[list[CampaignDocument], list[str]]:
    prepared: list[CampaignDocument] = []
    errors: list[str] = []
    hints = campaign.expected_roles
    for index, item in enumerate(documents):
        try:
            if isinstance(item, CampaignDocument):
                checked = prepare_document(item.mutable_record(), source=item.source)
                migration = item.migration_dict()
                if migration.get("target_contract") != "canonical-nested-v1.1":
                    raise QualificationLoadError(f"{item.source}: migration target must be canonical-nested-v1.1")
                checked = CampaignDocument(
                    source=checked.source,
                    record=checked.record,
                    migration=migration,
                    warnings=checked.warnings,
                )
            elif type(item) is dict:
                candidate_id = str(item.get("candidate_id", ""))
                checked = prepare_document(
                    item,
                    role_hint=hints.get(candidate_id),
                    source=f"<memory:{index}>",
                )
            else:
                raise QualificationLoadError(f"document {index} must be a CampaignDocument or mapping")
        except (QualificationLoadError, TypeError, ValueError) as exc:
            errors.append(str(exc))
            continue
        prepared.append(checked)
    return prepared, errors


def _compare(
    reference: Any,
    candidate: Any,
    absolute: float,
    relative: float,
    path: str,
) -> list[str]:
    errors: list[str] = []
    if isinstance(reference, bool) or isinstance(candidate, bool):
        return [f"{path}: boolean scientific values are forbidden"]
    if isinstance(reference, (int, float)) and isinstance(candidate, (int, float)):
        ref = float(reference)
        value = float(candidate)
        if not math.isfinite(ref) or not math.isfinite(value):
            return [f"{path}: non-finite scientific values are forbidden"]
        limit = absolute + relative * abs(ref)
        if abs(value - ref) > limit:
            errors.append(f"{path}: numerical mismatch {value} vs {ref} exceeds {limit}")
        return errors
    if isinstance(reference, str) and isinstance(candidate, str):
        if reference != candidate:
            errors.append(f"{path}: string scientific result mismatch")
        return errors
    if (
        isinstance(reference, Sequence)
        and not isinstance(reference, (str, bytes))
        and isinstance(candidate, Sequence)
        and not isinstance(candidate, (str, bytes))
    ):
        if len(reference) != len(candidate):
            return [f"{path}: scientific array length mismatch"]
        for index, (left, right) in enumerate(zip(reference, candidate, strict=True)):
            errors.extend(_compare(left, right, absolute, relative, f"{path}[{index}]"))
        return errors
    return [f"{path}: scientific result type mismatch"]


def _append_identity_drift(
    rows: list[CampaignDocument],
    getter: Callable[[CampaignDocument], Any],
    label: str,
    candidate_id: str,
    errors: list[str],
) -> None:
    if len({getter(row) for row in rows}) != 1:
        errors.append(f"{candidate_id}: {label} differs across repeats")


def _base_report(
    *,
    campaign: campaign_policy.CampaignConfig | None,
    errors: list[str],
    state: str,
    prepared_count: int = 0,
    holds: list[str] | None = None,
    performance_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    migration = campaign.migration_dict() if campaign else {}
    return {
        "ok": not errors,
        "state": state,
        "campaign_id": campaign.campaign_id if campaign else None,
        "campaign_contract": CAMPAIGN_CONTRACT,
        "campaign_schema_version": CAMPAIGN_SCHEMA_VERSION,
        "campaign_source_contract": migration.get("source_contract"),
        "campaign_migration": migration.get("migration"),
        "campaign_migration_qualification_impact": migration.get("qualification_impact"),
        "campaign_defaults_applied": migration.get("defaults_applied", []),
        "campaign_evidence_fields_added": migration.get("evidence_fields_added", []),
        "benchmark_result_contract": "canonical-nested-v1.1",
        "contract_boundary": "campaign-policy-independent-from-benchmark-result-evidence",
        "input_model": "canonical-nested-v1.1-typed-accessor",
        "normalization_mandatory": True,
        "native_semantic_validation": True,
        "legacy_projection_consumed": False,
        "legacy_projection_status": PROJECTION_STATUS,
        "campaign_document_immutable": True,
        "workers_bounded_by": MAX_WORKERS,
        "document_count": prepared_count,
        "performance": performance_report or {"evaluated": False, "candidates": {}},
        "holds": sorted(set(holds or [])),
        "errors": errors,
        "identity_invariants": [
            "campaign role equals canonical role",
            "global execution.run_id uniqueness",
            "single campaign site identity",
            "stable per-candidate build/software/hardware identity",
            "stable per-candidate multi-GPU UUID set",
            "single canonical scientific identity",
            "fully VERIFIED artifacts before ratio evaluation",
        ],
        "non_claims": [
            "QUALIFIED_FOR_REVIEW is not signed L3 performance qualification.",
            "Performance ratios are emitted only from accepted real-engine observations.",
            "Campaign v1.0 migration expands explicit roles but creates no execution evidence.",
            "Campaign migration cannot promote benchmark evidence or remove EXTERNAL_HOLD.",
            "Missing GPU, license, solver, build, site, hardware or artifact evidence forces EXTERNAL_HOLD.",
            "Legacy flat benchmark-result v1.0 evidence with provenance gaps remains EXTERNAL_HOLD.",
            "compute_qualification_view remains diagnostic only and is not qualification input.",
        ],
    }


def qualify(
    campaign: campaign_policy.CampaignConfig | dict[str, Any],
    documents: Sequence[CampaignDocument | dict[str, Any]],
    load_errors: list[str] | None = None,
) -> dict[str, Any]:
    try:
        config = _prepare_campaign(campaign)
    except QualificationLoadError as exc:
        return _base_report(campaign=None, errors=[str(exc)], state=UNQUALIFIED)

    prepared, coercion_errors = _coerce_documents(config, documents)
    errors = [*(load_errors or []), *coercion_errors]
    holds: list[str] = []
    if not prepared:
        holds.append("no benchmark result documents were supplied")
    expected_ids = [config.reference_candidate_id, *config.candidate_ids]
    expected_roles = config.expected_roles
    groups: dict[str, list[CampaignDocument]] = defaultdict(list)
    for document in prepared:
        groups[document.candidate_id].append(document)
    unexpected = sorted(set(groups) - set(expected_ids))
    if unexpected:
        errors.append(f"unexpected candidate_ids: {unexpected}")

    for candidate_id in expected_ids:
        rows = sorted(groups.get(candidate_id, []), key=lambda item: item.repeat_index)
        if len(rows) < config.minimum_repeats:
            holds.append(f"{candidate_id}: requires at least {config.minimum_repeats} repeats")
            continue
        indexes = [row.repeat_index for row in rows]
        if indexes != list(range(1, len(rows) + 1)):
            errors.append(f"{candidate_id}: repeat_index values must be contiguous from 1")

    run_ids = [document.run_id for document in prepared]
    if len(run_ids) != len(set(run_ids)):
        errors.append("execution.run_id values must be globally unique")

    expected_engine = "generic" if config.engine == "ml-surrogate" else config.engine
    for document in prepared:
        candidate_id = document.candidate_id
        is_real = document.evidence_kind == "real-engine"
        has_missing = bool(document.missing_fields)
        held_provenance = not is_real or has_missing
        if document.schema_version != contract.CANONICAL_SCHEMA_VERSION:
            errors.append(f"{candidate_id}: internal document is not canonical nested v1.1")
        if document.benchmark_plan_id != config.benchmark_plan_id:
            errors.append(f"{candidate_id}: benchmark_plan_id mismatch")
        if document.engine_name != expected_engine:
            errors.append(f"{candidate_id}: engine mismatch")
        if document.role != expected_roles.get(candidate_id):
            errors.append(f"{candidate_id}: canonical role does not match campaign role")
        if document.migration.get("qualification_impact") == EXTERNAL_HOLD:
            holds.append(f"{candidate_id}: source migration forces EXTERNAL_HOLD")
        if not is_real:
            holds.append(f"{candidate_id}: evidence_source.kind is not real-engine")
        if document.parser_accepted is not True or document.exit_status != 0:
            message = f"{candidate_id}: parser or exit status not accepted"
            (holds if held_provenance else errors).append(message)
        if has_missing:
            holds.append(f"{candidate_id}: evidence_source.missing_fields is not empty")
        if document.build_fingerprint_id == "MISSING":
            holds.append(f"{candidate_id}: build fingerprint is missing")
        if document.hardware_fingerprint_id == "MISSING":
            holds.append(f"{candidate_id}: hardware fingerprint is missing")
        if document.site_id == "MISSING":
            holds.append(f"{candidate_id}: site identity is missing")
        if not document.all_artifacts_verified:
            holds.append(f"{candidate_id}: artifacts are not fully VERIFIED")

        hardware = cast(Mapping[str, Any], document.record["hardware"])
        backend = document.accelerator_backend
        gpu_vendor = str(hardware["gpu_vendor"])
        gpu_uuids = document.gpu_uuids
        if document.role == "scientific-reference":
            if backend != "none" or gpu_vendor != "none" or gpu_uuids:
                message = f"{candidate_id}: reference role requires accelerator backend none and no GPU identity"
                (holds if held_provenance else errors).append(message)
        elif document.role == "acceleration-candidate" and (
            backend not in GPU_BACKENDS or gpu_vendor == "none" or not gpu_uuids
        ):
            message = f"{candidate_id}: acceleration role requires backend, vendor and GPU UUID identity"
            (holds if held_provenance else errors).append(message)

    if prepared:
        if len({document.input_sha256 for document in prepared}) != 1:
            errors.append("scientific.input_sha256 differs across campaign results")
        if len({document.method_fingerprint_id for document in prepared}) != 1:
            errors.append("scientific.method_fingerprint_id differs across campaign results")
        if len({document.scientific_identity for document in prepared}) != 1:
            errors.append("canonical scientific identity differs across campaign results")
        if len({document.site_id for document in prepared}) != 1:
            errors.append("execution.site_id differs across campaign results")

    for candidate_id, rows in groups.items():
        _append_identity_drift(
            rows,
            lambda row: row.candidate_execution_identity,
            "build, software, hardware or GPU topology identity",
            candidate_id,
            errors,
        )
        _append_identity_drift(
            rows,
            lambda row: row.hardware_fingerprint_id,
            "hardware_fingerprint_id",
            candidate_id,
            errors,
        )
        _append_identity_drift(
            rows,
            lambda row: row.gpu_uuids,
            "multi-GPU UUID set",
            candidate_id,
            errors,
        )

    reference_rows = sorted(
        groups.get(config.reference_candidate_id, []),
        key=lambda item: item.repeat_index,
    )
    if reference_rows:
        reference_results = reference_rows[0].scientific_observables()
        tolerances = config.numerical_tolerances
        for candidate_id in expected_ids:
            for row in groups.get(candidate_id, []):
                results = row.scientific_observables()
                if set(results) != set(reference_results):
                    errors.append(f"{candidate_id}: scientific observable set mismatch")
                    continue
                for name, reference_value in reference_results.items():
                    tolerance = tolerances.get(name)
                    if isinstance(reference_value, (int, float, list, tuple)) and tolerance is None:
                        errors.append(f"numerical_tolerances.{name} is required")
                        continue
                    absolute = float((tolerance or {}).get("absolute", 0.0))
                    relative = float((tolerance or {}).get("relative", 0.0))
                    errors.extend(
                        _compare(
                            reference_value,
                            results[name],
                            absolute,
                            relative,
                            f"{candidate_id}.{name}",
                        )
                    )

    performance_report: dict[str, Any] = {"evaluated": False, "candidates": {}}
    can_evaluate = not errors and not holds and bool(reference_rows)
    if can_evaluate:
        reference_median = statistics.median(row.wall_time_s for row in reference_rows)
        performance_report["evaluated"] = True
        performance_report["reference_median_wall_time_seconds"] = reference_median
        threshold = config.minimum_reference_over_candidate_ratio
        for candidate_id in config.candidate_ids:
            rows = groups[candidate_id]
            candidate_median = statistics.median(row.wall_time_s for row in rows)
            ratio = reference_median / candidate_median
            if not math.isfinite(ratio):
                errors.append(f"{candidate_id}: non-finite performance ratio")
                continue
            performance_report["candidates"][candidate_id] = {
                "median_wall_time_seconds": candidate_median,
                "reference_over_candidate_ratio": ratio,
                "threshold": threshold,
                "passes": ratio >= threshold,
            }
            if ratio < threshold:
                errors.append(f"{candidate_id}: performance threshold was not met")

    state = (
        QUALIFIED_FOR_REVIEW
        if not errors and not holds and performance_report["evaluated"]
        else EXTERNAL_HOLD
        if holds
        else UNQUALIFIED
    )
    return _base_report(
        campaign=config,
        errors=errors,
        state=state,
        prepared_count=len(prepared),
        holds=holds,
        performance_report=performance_report,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("results", nargs="*", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        campaign = load_campaign_config(args.campaign)
        schema = load_json(args.schema)
        documents, load_errors = load_results(
            args.results,
            schema,
            workers=args.workers,
            role_hints=_role_hints(campaign),
        )
        report = qualify(campaign, documents, load_errors)
    except (QualificationLoadError, ValueError) as exc:
        report = _base_report(campaign=None, errors=[str(exc)], state=UNQUALIFIED)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
