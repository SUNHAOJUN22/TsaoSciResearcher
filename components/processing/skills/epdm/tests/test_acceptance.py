from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills.epdm import acceptance as acceptance_module
from skills.epdm.acceptance import (
    ACCEPTANCE_SCHEMA,
    MAX_ANALYTIC_ABSOLUTE_ERROR,
    MAX_MEDIAN_LOAD_SECONDS,
    MAX_PEAK_LOAD_BYTES,
    build_canonical_execution_bundle,
    execute_canonical_acceptance,
    qualify_acceptance,
    write_acceptance_report,
)
from skills.epdm.canonical_loader import load_canonical_project_file
from skills.epdm.contracts import ContractValidationError, GateDecision
from tsao.cli import main

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "fixtures/v2_phase_a1_reference_project.json"
UNIT_TEST_LOAD_SAMPLES = 3


def test_bundle_requires_canonical_snapshot() -> None:
    with pytest.raises(TypeError, match="CanonicalProjectSnapshot"):
        build_canonical_execution_bundle({})  # type: ignore[arg-type]


def test_canonical_bundle_binds_a2_a3_a4_to_publication() -> None:
    snapshot = load_canonical_project_file(PROJECT)
    bundle = build_canonical_execution_bundle(snapshot)

    assert bundle.publication_sha256 == snapshot.publication_sha256
    assert bundle.state_definition.source_state_definition_id in snapshot.state_definitions
    assert bundle.reaction_network.generated_state_definition_id == (
        bundle.state_definition.generated_state_definition_id
    )
    assert bundle.reaction_network_audit.decision == GateDecision.PASS
    assert bundle.rate_package_audit.decision == GateDecision.PASS
    assert bundle.rate_package_audit.metrics["binding_count"] == 41
    assert bundle.parameter_basis == "SYNTHETIC_REFERENCE_NOT_PROJECT_CALIBRATION"


def test_canonical_acceptance_matches_analytic_reference() -> None:
    snapshot = load_canonical_project_file(PROJECT)
    bundle = build_canonical_execution_bundle(snapshot)
    result = execute_canonical_acceptance(bundle)

    assert result.decision == GateDecision.PASS
    assert result.reason_code == "A15_ADAPTIVE_INTEGRATION_COMPLETE"
    assert result.conservation["time_monotonic"] is True
    assert result.maximum_conservation_residual <= 1.0e-12


def test_acceptance_qualification_closes_all_software_checks() -> None:
    result = qualify_acceptance(PROJECT, load_samples=UNIT_TEST_LOAD_SAMPLES)

    assert result.pass_ is True, result.as_dict()
    assert all(result.checks.values())
    assert result.metrics["canonical_loader_median_seconds"] <= MAX_MEDIAN_LOAD_SECONDS
    assert result.metrics["canonical_loader_peak_bytes"] <= MAX_PEAK_LOAD_BYTES
    assert result.metrics["analytic_absolute_error"] <= MAX_ANALYTIC_ABSOLUTE_ERROR
    assert result.integration["decision"] == "PASS"
    assert result.errors == ()
    assert result.holds


def test_acceptance_report_is_valid_json_and_keeps_approvals_closed(tmp_path: Path) -> None:
    output = tmp_path / "acceptance.json"
    result = write_acceptance_report(output, PROJECT, load_samples=UNIT_TEST_LOAD_SAMPLES)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert result.pass_
    assert payload["schema"] == ACCEPTANCE_SCHEMA
    assert payload["pass"] is True
    assert payload["artifact_software_qualification"] == "PASS"
    for field in (
        "scientific_technical_approval",
        "engineering_design_approval",
        "hse_approval",
        "customer_qualification",
        "industrial_performance_guarantee",
    ):
        assert payload[field] == "NOT_EVALUATED"


def test_acceptance_rejects_project_without_catalyst(tmp_path: Path) -> None:
    payload = json.loads(PROJECT.read_text(encoding="utf-8"))
    payload["catalyst_passports"] = []
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises((ContractValidationError, ValueError)):
        snapshot = load_canonical_project_file(path)
        build_canonical_execution_bundle(snapshot)


def test_cli_acceptance_writes_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "cli-acceptance.json"
    rc = main(
        [
            "epdm",
            "qualify-acceptance",
            "--project",
            str(PROJECT),
            "--output",
            str(output),
            "--load-samples",
            str(UNIT_TEST_LOAD_SAMPLES),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert output.is_file()
    assert json.loads(captured.out)["pass"] is True


def test_loader_timing_is_isolated_from_tracemalloc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_publication = load_canonical_project_file(PROJECT).publication_sha256
    tracing = {"active": False}
    traced_loads: list[bool] = []
    original_loader = acceptance_module.load_canonical_project_file

    def tracked_loader(path: Path):
        traced_loads.append(tracing["active"])
        return original_loader(path)

    def start_tracing() -> None:
        assert tracing["active"] is False
        tracing["active"] = True

    def stop_tracing() -> None:
        assert tracing["active"] is True
        tracing["active"] = False

    def traced_memory() -> tuple[int, int]:
        assert tracing["active"] is True
        return 0, 1234

    monkeypatch.setattr(
        acceptance_module,
        "load_canonical_project_file",
        tracked_loader,
    )
    monkeypatch.setattr(acceptance_module.tracemalloc, "start", start_tracing)
    monkeypatch.setattr(acceptance_module.tracemalloc, "stop", stop_tracing)
    monkeypatch.setattr(
        acceptance_module.tracemalloc,
        "get_traced_memory",
        traced_memory,
    )

    median, peak, publication = acceptance_module._loader_resource_metrics(
        PROJECT,
        3,
    )

    assert traced_loads == [False, False, False, True]
    assert tracing["active"] is False
    assert median >= 0.0
    assert peak == 1234
    assert publication == expected_publication


def test_load_samples_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        qualify_acceptance(PROJECT, load_samples=0)
