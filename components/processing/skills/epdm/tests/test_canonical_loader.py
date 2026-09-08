from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from types import MappingProxyType

import pytest

from skills.epdm.canonical_loader import (
    CANONICAL_PROJECT_SCHEMA,
    LOADER_VERSION,
    CanonicalLoadIssue,
    CanonicalProjectLoadError,
    load_canonical_project,
    load_canonical_project_file,
    load_canonical_project_json,
    parse_project_json,
)
from skills.epdm.contracts import (
    CatalystFamily,
    EvidenceStatus,
    ModelQualification,
    StateDefinition,
)
from skills.epdm.validation_v2 import GateDecision, validate_v2_project

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/v2_phase_a1_reference_project.json"


def _project() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_project_builds_complete_immutable_typed_snapshot() -> None:
    snapshot = load_canonical_project(_project())

    assert snapshot.project_id == "EPDM-V2-PHASE-A1-TUTORIAL"
    assert snapshot.schema_version == "2.0.0"
    assert snapshot.loader_version == LOADER_VERSION
    assert snapshot.migration.steps == ("IDENTITY_2_0_0",)
    assert snapshot.migration.evidence_fabricated is False
    assert len(snapshot.registry.evidence) == 7
    assert len(snapshot.registry.applicability_domains) == 1
    assert len(snapshot.registry.catalysts) == 1
    assert len(snapshot.registry.dienes) == 1
    assert len(snapshot.registry.rate_laws) == 1
    assert len(snapshot.registry.kinetic_parameters) == 2
    assert len(snapshot.registry.thermo_passports) == 1
    assert len(snapshot.registry.datasets) == 2
    assert len(snapshot.state_definitions) == 1
    assert len(snapshot.calibration_plans) == 1
    assert isinstance(snapshot.qualification, ModelQualification)
    assert isinstance(next(iter(snapshot.state_definitions.values())), StateDefinition)
    assert next(iter(snapshot.registry.evidence.values())).status is EvidenceStatus.QUALIFIED
    assert next(iter(snapshot.registry.catalysts.values())).family is CatalystFamily.METALLOCENE


def test_file_json_and_object_entrypoints_publish_identical_snapshot() -> None:
    from_object = load_canonical_project(_project())
    from_json = load_canonical_project_json(FIXTURE.read_text(encoding="utf-8"))
    from_file = load_canonical_project_file(FIXTURE)

    assert from_object.publication_sha256 == from_json.publication_sha256
    assert from_json.publication_sha256 == from_file.publication_sha256
    assert from_object.registry.content_sha256 == from_file.registry.content_sha256
    assert from_object.to_json() == from_json.to_json() == from_file.to_json()


def test_input_and_returned_snapshot_are_isolated_from_mutation() -> None:
    project = _project()
    snapshot = load_canonical_project(project)
    catalyst_id = project["catalyst_passports"][0]["catalyst_id"]  # type: ignore[index]

    project["catalyst_passports"][0]["display_name"] = "MUTATED"  # type: ignore[index]
    catalyst = snapshot.registry.catalysts[catalyst_id]
    assert catalyst.display_name != "MUTATED"

    with pytest.raises(TypeError):
        snapshot.registry.catalysts[catalyst_id] = catalyst  # type: ignore[index]
    with pytest.raises(TypeError):
        snapshot.canonical_project["project_id"] = "MUTATED"  # type: ignore[index]
    assert isinstance(snapshot.canonical_project, MappingProxyType)
    assert isinstance(snapshot.canonical_project["catalyst_passports"], tuple)


def test_registry_hash_is_independent_of_project_list_order() -> None:
    original = _project()
    reordered = copy.deepcopy(original)
    reordered["evidence_ledger"].reverse()  # type: ignore[union-attr]
    reordered["datasets"].reverse()  # type: ignore[union-attr]

    first = load_canonical_project(original)
    second = load_canonical_project(reordered)

    assert first.registry.content_sha256 == second.registry.content_sha256
    assert first.source_sha256 != second.source_sha256
    assert first.publication_sha256 != second.publication_sha256


def test_extensions_are_source_bound_but_do_not_change_core_registry_identity() -> None:
    original = _project()
    extended = copy.deepcopy(original)
    extended["catalyst_passports"][0]["extensions"] = {  # type: ignore[index]
        "vendor_note": "non-core metadata"
    }

    first = load_canonical_project(original)
    second = load_canonical_project(extended)

    assert first.registry.content_sha256 == second.registry.content_sha256
    assert first.source_sha256 != second.source_sha256


def test_manifest_is_deterministic_and_keeps_approval_boundaries_closed() -> None:
    snapshot = load_canonical_project(_project())
    manifest = json.loads(snapshot.to_json())

    assert manifest["schema"] == CANONICAL_PROJECT_SCHEMA
    assert manifest["publication_sha256"] == snapshot.publication_sha256
    assert manifest["registry_content_sha256"] == snapshot.registry.content_sha256
    assert manifest["scientific_technical_approval"] == "NOT_EVALUATED"
    assert manifest["engineering_design_approval"] == "NOT_EVALUATED"
    assert manifest["customer_qualification"] == "NOT_EVALUATED"
    assert manifest["industrial_performance_guarantee"] == "NOT_EVALUATED"
    assert snapshot.to_json() == load_canonical_project(_project()).to_json()


def test_registry_snapshot_lookup_is_explicit_and_fail_closed() -> None:
    snapshot = load_canonical_project(_project())
    evidence_id = next(iter(snapshot.registry.evidence))

    assert snapshot.registry.require("evidence", evidence_id).reference.evidence_id == evidence_id
    with pytest.raises(KeyError, match="unknown registry"):
        snapshot.registry.require("unknown", evidence_id)
    with pytest.raises(KeyError, match="unresolved evidence"):
        snapshot.registry.require("evidence", "EV-MISSING")


@pytest.mark.parametrize("version", [None, "1.0.0", "2.1.0", "3.0.0"])
def test_version_migration_rejects_missing_or_unknown_versions(version: object) -> None:
    project = _project()
    if version is None:
        project.pop("schema_version")
    else:
        project["schema_version"] = version

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "version_migration"
    assert caught.value.issue.path == "$.schema_version"


def test_json_parser_rejects_duplicate_object_keys() -> None:
    with pytest.raises(CanonicalProjectLoadError) as caught:
        parse_project_json('{"schema_version":"2.0.0","schema_version":"2.0.0"}')
    assert caught.value.issue.phase == "json_parse"
    assert "duplicate JSON object key" in caught.value.issue.message


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_json_parser_rejects_nonfinite_tokens(token: str) -> None:
    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project_json(f'{{"schema_version":"2.0.0","x":{token}}}')
    assert caught.value.issue.phase == "json_parse"
    assert "non-finite" in caught.value.issue.message


def test_object_loader_rejects_nonfinite_numbers_before_publication() -> None:
    project = _project()
    project["diene_passports"][0]["molecular_weight"]["value"] = math.nan  # type: ignore[index]

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "input"
    assert "finite JSON-compatible" in caught.value.issue.message


def test_schema_type_confusion_fails_before_dataclass_publication() -> None:
    project = _project()
    project["diene_passports"][0]["terminal_model_supported"] = "true"  # type: ignore[index]

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "schema_validation"
    assert "boolean" in caught.value.issue.message


def test_dataclass_contract_can_reject_schema_valid_but_semantically_empty_text() -> None:
    project = _project()
    project["evidence_ledger"][0]["locator"] = "   "  # type: ignore[index]

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "dataclass_construction"
    assert "locator must not be empty" in caught.value.issue.message


def test_duplicate_id_fails_without_mutating_caller_payload() -> None:
    project = _project()
    duplicate = copy.deepcopy(project["datasets"][0])  # type: ignore[index]
    project["datasets"].append(duplicate)  # type: ignore[union-attr]
    original = copy.deepcopy(project)

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert project == original
    assert "duplicate" in caught.value.issue.message


def test_cross_registry_reference_failure_prevents_publication() -> None:
    project = _project()
    project["thermo_passports"][0]["validation_dataset_ids"] = ["DS-MISSING"]  # type: ignore[index]

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "reference_validation"
    assert "DS-MISSING" in caught.value.issue.message


def test_parameter_must_reference_rate_law_inside_its_own_parameter_set() -> None:
    project = _project()
    project["kinetic_parameter_sets"][0]["parameters"][0]["rate_law_id"] = (  # type: ignore[index]
        "RL-MISSING"
    )

    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(project)
    assert caught.value.issue.phase == "reference_validation"
    assert "outside its parameter set" in caught.value.issue.message


def test_missing_schema_registry_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(CanonicalProjectLoadError) as caught:
        load_canonical_project(_project(), schema_dir=tmp_path)
    assert caught.value.issue.phase == "schema_validation"
    assert "FileNotFoundError" in caught.value.issue.message


def test_public_validation_path_invokes_canonical_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skills.epdm import validation_v2

    def fail_publication(*args: object, **kwargs: object) -> object:
        raise CanonicalProjectLoadError(
            CanonicalLoadIssue("test_phase", "$.test", "forced publication failure")
        )

    monkeypatch.setattr(validation_v2, "load_canonical_project", fail_publication)
    result = validate_v2_project(_project())

    assert result.decision == GateDecision.FAIL
    assert any("forced publication failure" in issue.message for issue in result.errors)


def test_reference_fixture_remains_valid_through_public_validation() -> None:
    result = validate_v2_project(_project())
    assert result.decision == GateDecision.PASS, result.as_dict()


def test_module_contract_registers_canonical_loader() -> None:
    payload = json.loads((ROOT / "data/module_contracts_v2.json").read_text(encoding="utf-8"))
    indexed = {item["module"]: item for item in payload["items"]}
    contract = indexed["canonical_loader.py"]
    assert contract["phase"] == "A1"
    assert contract["status"] == "TRANSACTIONAL_CANONICAL_PUBLICATION_IMPLEMENTED"
    assert contract["numerical_execution"] is False
