#!/usr/bin/env python3
"""Closed compute-campaign configuration contract and explicit legacy migration."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = SKILL_ROOT.parents[1] if len(SKILL_ROOT.parents) > 1 else SKILL_ROOT
CANONICAL_SCHEMA_PATH = SKILL_ROOT / "templates" / "compute-qualification-campaign.schema.json"
LEGACY_SCHEMA_PATH = SKILL_ROOT / "templates" / "compute-qualification-campaign-v1.0.schema.json"
ROOT_SCHEMA_MIRROR_PATH = REPOSITORY_ROOT / "templates" / "compute-qualification-campaign.schema.json"
TEMPLATE_PATH = SKILL_ROOT / "templates" / "compute-qualification-campaign.yaml"
CANONICAL_SCHEMA_VERSION = "1.1"
LEGACY_SCHEMA_VERSION = "1.0"
CANONICAL_SCHEMA_ID = "https://github.com/SUNHAOJUN22/TsaoDFT_skill/compute-qualification-campaign.schema.json"
LEGACY_SCHEMA_ID = "https://github.com/SUNHAOJUN22/TsaoDFT_skill/compute-qualification-campaign-v1.0.schema.json"
CANONICAL_CONTRACT = "canonical-compute-campaign-v1.1"
LEGACY_CONTRACT = "legacy-compute-campaign-v1.0"
NO_EVIDENCE_PROMOTION = "NO_EVIDENCE_PROMOTION"
ROLES = {"scientific-reference", "acceleration-candidate"}
ENGINES = {"gaussian", "vasp", "quantum-espresso", "cp2k", "generic", "ml-surrogate"}


class CampaignContractError(ValueError):
    """Raised when a campaign configuration cannot be interpreted without guessing."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise CampaignContractError("campaign mapping keys must be scalar and hashable") from exc
        if duplicate:
            raise CampaignContractError(f"duplicate campaign mapping key is forbidden: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _reject_constant(value: str) -> None:
    raise CampaignContractError(f"non-finite JSON constant is forbidden: {value}")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CampaignContractError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise CampaignContractError(f"duplicate campaign mapping key is forbidden: {key!r}")
        mapping[key] = value
    return mapping


def _require_finite_tree(value: Any, path: str = "<root>") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CampaignContractError(f"{path}: non-finite numeric value is forbidden")
    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_tree(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_tree(item, f"{path}[{index}]")


def load_mapping(path: Path) -> dict[str, Any]:
    """Load JSON or YAML without duplicate keys, non-finite values, or non-mapping roots."""
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            loaded = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_constant,
                parse_float=_parse_finite_float,
            )
        else:
            loader = _UniqueKeySafeLoader(text)
            try:
                loaded = loader.get_single_data()
            finally:
                loader.dispose()
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, CampaignContractError) as exc:
        raise CampaignContractError(f"cannot load {path.name}: {exc}") from exc
    if type(loaded) is not dict:
        raise CampaignContractError(f"{path.name} root must be a mapping")
    _require_finite_tree(loaded)
    return cast(dict[str, Any], loaded)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def schema_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return [f"schema is not valid Draft 2020-12: {exc.message}"]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    return [f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}" for error in errors]


def canonical_schema() -> dict[str, Any]:
    return load_mapping(CANONICAL_SCHEMA_PATH)


def legacy_schema() -> dict[str, Any]:
    return load_mapping(LEGACY_SCHEMA_PATH)


def approved_schema_kind(schema: dict[str, Any]) -> str:
    schema_id = schema.get("$id")
    version = ((schema.get("properties") or {}).get("schema_version") or {}).get("const")
    if schema_id == CANONICAL_SCHEMA_ID and version == CANONICAL_SCHEMA_VERSION:
        return CANONICAL_CONTRACT
    if schema_id == LEGACY_SCHEMA_ID and version == LEGACY_SCHEMA_VERSION:
        return LEGACY_CONTRACT
    return "custom-nonqualifying"


def detect_contract(record: Any) -> str:
    if type(record) is not dict:
        raise CampaignContractError("campaign root must be a mapping")
    _require_finite_tree(record)
    version = record.get("schema_version")
    has_legacy = bool({"reference_candidate_id", "candidate_ids"} & set(record))
    has_canonical = "participants" in record
    if has_legacy and has_canonical:
        raise CampaignContractError("mixed legacy and canonical campaign fields are forbidden")
    if version == CANONICAL_SCHEMA_VERSION:
        if has_legacy or not has_canonical:
            raise CampaignContractError("canonical campaign v1.1 requires participants and forbids legacy role fields")
        return CANONICAL_CONTRACT
    if version == LEGACY_SCHEMA_VERSION:
        if has_canonical or not has_legacy:
            raise CampaignContractError(
                "legacy campaign v1.0 requires reference_candidate_id and candidate_ids and forbids participants"
            )
        return LEGACY_CONTRACT
    raise CampaignContractError(
        f"unsupported compute-campaign schema_version: {version!r}; supported versions are "
        f"{LEGACY_SCHEMA_VERSION} and {CANONICAL_SCHEMA_VERSION}"
    )


def _validate_or_raise(record: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = schema_errors(record, schema)
    if errors:
        raise CampaignContractError(f"{label} validation failed: {'; '.join(errors)}")


def _semantic_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("campaign_id", "benchmark_plan_id"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty non-whitespace string")
    if record.get("engine") not in ENGINES:
        errors.append(f"engine must be one of {sorted(ENGINES)}")

    repeats = record.get("minimum_repeats")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 3:
        errors.append("minimum_repeats must be an integer >= 3")
    ratio = record.get("minimum_reference_over_candidate_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(float(ratio)) or ratio <= 1:
        errors.append("minimum_reference_over_candidate_ratio must be finite and > 1")

    participants = record.get("participants")
    if not isinstance(participants, list):
        errors.append("participants must be a list")
        participants = []
    identities: list[str] = []
    references = 0
    candidates = 0
    for index, participant in enumerate(participants):
        if not isinstance(participant, dict):
            errors.append(f"participants.{index} must be a mapping")
            continue
        candidate_id = participant.get("candidate_id")
        role = participant.get("role")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            errors.append(f"participants.{index}.candidate_id must be non-empty and non-whitespace")
        else:
            identities.append(candidate_id)
        if role == "scientific-reference":
            references += 1
        elif role == "acceleration-candidate":
            candidates += 1
        elif role not in ROLES:
            errors.append(f"participants.{index}.role must be one of {sorted(ROLES)}")
    if len(identities) != len(set(identities)):
        errors.append("participant candidate_id values must be globally unique across roles")
    if references != 1:
        errors.append("campaign must declare exactly one scientific-reference participant")
    if candidates < 1:
        errors.append("campaign must declare at least one acceleration-candidate participant")

    tolerances = record.get("numerical_tolerances")
    if not isinstance(tolerances, dict) or not tolerances:
        errors.append("numerical_tolerances must be a non-empty mapping")
    else:
        for name, tolerance in tolerances.items():
            if not isinstance(name, str) or not name.strip():
                errors.append("numerical_tolerances keys must be non-empty non-whitespace strings")
                continue
            if type(tolerance) is not dict or set(tolerance) != {"absolute", "relative"}:
                errors.append(f"numerical_tolerances.{name} must contain only absolute and relative")
                continue
            for field in ("absolute", "relative"):
                value = tolerance[field]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or value < 0
                ):
                    errors.append(f"numerical_tolerances.{name}.{field} must be finite and >= 0")
    return errors


def _legacy_to_canonical(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_or_raise(record, legacy_schema(), "legacy compute campaign v1.0")
    reference = record["reference_candidate_id"]
    candidates = record["candidate_ids"]
    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "campaign_id": record["campaign_id"],
        "benchmark_plan_id": record["benchmark_plan_id"],
        "engine": record["engine"],
        "participants": [
            {"candidate_id": reference, "role": "scientific-reference"},
            *({"candidate_id": candidate_id, "role": "acceleration-candidate"} for candidate_id in candidates),
        ],
        "minimum_repeats": record["minimum_repeats"],
        "minimum_reference_over_candidate_ratio": record["minimum_reference_over_candidate_ratio"],
        "numerical_tolerances": copy.deepcopy(record["numerical_tolerances"]),
    }
    semantic_errors = _semantic_errors(canonical)
    if semantic_errors:
        raise CampaignContractError(
            f"legacy compute campaign v1.0 semantic validation failed: {'; '.join(semantic_errors)}"
        )
    _validate_or_raise(canonical, canonical_schema(), "migrated canonical compute campaign v1.1")
    return canonical, {
        "source_contract": LEGACY_CONTRACT,
        "target_contract": CANONICAL_CONTRACT,
        "migration": "reference-and-candidate-fields-to-explicit-participants",
        "qualification_impact": NO_EVIDENCE_PROMOTION,
        "defaults_applied": [],
        "evidence_fields_added": [],
    }


def normalize_campaign(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = detect_contract(record)
    if contract == LEGACY_CONTRACT:
        return _legacy_to_canonical(record)
    canonical = copy.deepcopy(record)
    _validate_or_raise(canonical, canonical_schema(), "canonical compute campaign v1.1")
    semantic_errors = _semantic_errors(canonical)
    if semantic_errors:
        raise CampaignContractError(
            f"canonical compute campaign v1.1 semantic validation failed: {'; '.join(semantic_errors)}"
        )
    return canonical, {
        "source_contract": CANONICAL_CONTRACT,
        "target_contract": CANONICAL_CONTRACT,
        "migration": "none",
        "qualification_impact": "none",
        "defaults_applied": [],
        "evidence_fields_added": [],
    }


def freeze_tree(value: Any) -> Any:
    """Recursively freeze JSON-compatible data into mapping proxies and tuples."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_tree(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_tree(item) for item in value)
    if value is None or type(value) in {str, bool, int, float}:
        return value
    raise CampaignContractError(f"campaign contract contains a non-JSON value: {type(value).__name__}")


def thaw_tree(value: Any) -> Any:
    """Return a detached mutable JSON-compatible copy of frozen contract data."""
    if isinstance(value, Mapping):
        return {str(key): thaw_tree(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw_tree(item) for item in value]
    if value is None or type(value) in {str, bool, int, float}:
        return value
    raise CampaignContractError(f"frozen campaign contract contains a non-JSON value: {type(value).__name__}")


class CampaignVersion(str):
    """String-compatible schema version carrying validated migration metadata."""

    campaign_migration: dict[str, Any]

    def __new__(cls, value: str, migration: dict[str, Any]) -> CampaignVersion:
        instance = cast(CampaignVersion, super().__new__(cls, value))
        instance.campaign_migration = migration
        return instance


def _validated_migration(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise CampaignContractError("campaign migration metadata must be a mapping")
    expected = {
        "source_contract",
        "target_contract",
        "migration",
        "qualification_impact",
        "defaults_applied",
        "evidence_fields_added",
    }
    if set(value) != expected:
        raise CampaignContractError("campaign migration metadata fields are invalid")
    if value.get("target_contract") != CANONICAL_CONTRACT:
        raise CampaignContractError("campaign migration target must be canonical v1.1")
    if value.get("defaults_applied") != [] or value.get("evidence_fields_added") != []:
        raise CampaignContractError("campaign migration must not apply defaults or add evidence fields")
    source = value.get("source_contract")
    if source == CANONICAL_CONTRACT:
        if value.get("migration") != "none" or value.get("qualification_impact") != "none":
            raise CampaignContractError("canonical campaign migration metadata is contradictory")
    elif source == LEGACY_CONTRACT:
        if value.get("migration") != "reference-and-candidate-fields-to-explicit-participants":
            raise CampaignContractError("legacy campaign migration identifier is invalid")
        if value.get("qualification_impact") != NO_EVIDENCE_PROMOTION:
            raise CampaignContractError("legacy campaign migration must not promote evidence")
    else:
        raise CampaignContractError("campaign migration source contract is unsupported")
    return cast(dict[str, Any], thaw_tree(value))


@dataclass(frozen=True)
class CampaignConfig:
    """Immutable typed view of one canonical compute-campaign v1.1 configuration."""

    source: str
    record: Mapping[str, Any]
    migration: Mapping[str, Any]

    @property
    def schema_version(self) -> str:
        return str(self.record["schema_version"])

    @property
    def campaign_id(self) -> str:
        return str(self.record["campaign_id"])

    @property
    def benchmark_plan_id(self) -> str:
        return str(self.record["benchmark_plan_id"])

    @property
    def engine(self) -> str:
        return str(self.record["engine"])

    @property
    def participants(self) -> tuple[Mapping[str, Any], ...]:
        return cast(tuple[Mapping[str, Any], ...], self.record["participants"])

    @property
    def reference_candidate_id(self) -> str:
        return next(
            str(participant["candidate_id"])
            for participant in self.participants
            if participant["role"] == "scientific-reference"
        )

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(
            str(participant["candidate_id"])
            for participant in self.participants
            if participant["role"] == "acceleration-candidate"
        )

    @property
    def minimum_repeats(self) -> int:
        return int(self.record["minimum_repeats"])

    @property
    def minimum_reference_over_candidate_ratio(self) -> float:
        return float(self.record["minimum_reference_over_candidate_ratio"])

    @property
    def numerical_tolerances(self) -> Mapping[str, Mapping[str, float]]:
        return cast(Mapping[str, Mapping[str, float]], self.record["numerical_tolerances"])

    @property
    def expected_roles(self) -> Mapping[str, str]:
        return MappingProxyType(
            {str(participant["candidate_id"]): str(participant["role"]) for participant in self.participants}
        )

    def to_dict(self) -> dict[str, Any]:
        value = cast(dict[str, Any], thaw_tree(self.record))
        value["schema_version"] = CampaignVersion(
            str(value["schema_version"]),
            self.migration_dict(),
        )
        return value

    def migration_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], thaw_tree(self.migration))


def prepare_campaign(record: dict[str, Any], *, source: str = "<memory>") -> CampaignConfig:
    version = record.get("schema_version") if isinstance(record, dict) else None
    preserved_migration = getattr(version, "campaign_migration", None)
    raw_record = dict(record)
    if preserved_migration is not None:
        raw_record["schema_version"] = str(version)
    canonical, migration = normalize_campaign(raw_record)
    if preserved_migration is not None:
        migration = _validated_migration(preserved_migration)
    return CampaignConfig(
        source=source,
        record=cast(Mapping[str, Any], freeze_tree(canonical)),
        migration=cast(Mapping[str, Any], freeze_tree(migration)),
    )


def load_campaign(path: Path) -> CampaignConfig:
    return prepare_campaign(load_mapping(path), source=path.as_posix())


def _explicit_diagnostics(record: Any) -> list[str]:
    if type(record) is not dict:
        return ["campaign root must be a mapping"]
    errors: list[str] = []
    repeats = record.get("minimum_repeats")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 3:
        errors.append("minimum_repeats must be an integer >= 3")
    ratio = record.get("minimum_reference_over_candidate_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(float(ratio)) or ratio <= 1:
        errors.append("minimum_reference_over_candidate_ratio must be finite and > 1")
    return errors


def validate_campaign(record: Any) -> list[str]:
    raw = record.to_dict() if isinstance(record, CampaignConfig) else record
    errors = _explicit_diagnostics(raw)
    try:
        if isinstance(record, CampaignConfig):
            prepare_campaign(record.to_dict(), source=record.source)
        elif type(record) is dict:
            prepare_campaign(record)
        else:
            raise CampaignContractError("campaign root must be a mapping")
    except (CampaignContractError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return list(dict.fromkeys(errors))


def _default_paths(value: Any, path: str = "<root>") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        if "default" in value:
            paths.append(path)
        for key, item in value.items():
            paths.extend(_default_paths(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_default_paths(item, f"{path}[{index}]"))
    return paths


def contract_report() -> dict[str, Any]:
    errors: list[str] = []
    canonical_text = ""
    canonical: dict[str, Any] = {}
    legacy: dict[str, Any] = {}
    template: CampaignConfig | None = None
    try:
        canonical_text = CANONICAL_SCHEMA_PATH.read_text(encoding="utf-8")
        canonical = canonical_schema()
        legacy = legacy_schema()
        if approved_schema_kind(canonical) != CANONICAL_CONTRACT:
            errors.append("canonical campaign schema identity or version is invalid")
        if approved_schema_kind(legacy) != LEGACY_CONTRACT:
            errors.append("legacy campaign schema identity or version is invalid")
        if schema_errors({}, canonical) == []:
            errors.append("canonical campaign schema accepts an empty document")
        defaults = [*_default_paths(canonical), *_default_paths(legacy)]
        if defaults:
            errors.append(f"campaign schemas must not define defaults: {sorted(defaults)}")
        template = load_campaign(TEMPLATE_PATH)
        if template.schema_version != CANONICAL_SCHEMA_VERSION:
            errors.append("repository campaign template is not canonical v1.1")
        if template.migration.get("migration") != "none":
            errors.append("repository campaign template unexpectedly requires migration")
        if ROOT_SCHEMA_MIRROR_PATH.is_file():
            if ROOT_SCHEMA_MIRROR_PATH.read_text(encoding="utf-8") != canonical_text:
                errors.append("root compute-campaign schema mirror differs from the Skill authority")
        elif REPOSITORY_ROOT != SKILL_ROOT:
            errors.append("root compute-campaign schema mirror is missing")
    except (OSError, UnicodeError, CampaignContractError) as exc:
        errors.append(str(exc))
    return {
        "ok": not errors,
        "canonical_contract": CANONICAL_CONTRACT,
        "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
        "canonical_schema_path": CANONICAL_SCHEMA_PATH.as_posix(),
        "canonical_schema_id": canonical.get("$id"),
        "canonical_schema_sha256": sha256_text(canonical_text) if canonical_text else None,
        "root_mirror_path": ROOT_SCHEMA_MIRROR_PATH.as_posix(),
        "root_mirror_synchronized": not any("root compute-campaign schema mirror" in item for item in errors),
        "legacy_contract": LEGACY_CONTRACT,
        "legacy_schema_id": legacy.get("$id"),
        "template_campaign_id": template.campaign_id if template else None,
        "template_source_contract": template.migration.get("source_contract") if template else None,
        "migration_policy": {
            LEGACY_CONTRACT: "central explicit role expansion; no defaults and no evidence creation",
            CANONICAL_CONTRACT: "native closed-schema validation",
            "unknown_or_mixed": "fail-closed",
        },
        "migration_qualification_impact": NO_EVIDENCE_PROMOTION,
        "defaults_applied": [],
        "benchmark_result_contract_boundary": "independent-canonical-nested-v1.1",
        "external_engine_invoked": False,
        "performance_ratio_published": False,
        "errors": errors,
    }
