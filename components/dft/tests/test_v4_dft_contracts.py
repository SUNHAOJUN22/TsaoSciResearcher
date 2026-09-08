from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/tsao-dft-hpc-provenance/scripts"


def load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


parser = load("engine_parser_v4")
tst = load("tst_standard_state")
ml = load("ml_provenance_contract")


@pytest.mark.parametrize(
    "engine,text",
    [
        ("gaussian", "Entering Gaussian System\nNormal termination\nError termination via Lnk1e"),
        ("vasp", "vasp.6\nreached required accuracy\nGeneral timing and accounting informations\nZBRENT: fatal error"),
        ("qe", "Program PWSCF\nconvergence has been achieved\nJOB DONE\nError in routine cdiaghg"),
        ("cp2k", "PROGRAM STARTED AT\nPROGRAM ENDED AT\n*** ABORT"),
    ],
)
def test_fatal_after_success_is_never_accepted(engine: str, text: str) -> None:
    record = parser.parse_engine_output(engine, text)
    assert record.parser_accepted is False
    assert record.exit_code != 0
    assert record.status.startswith("FAILED")


@pytest.mark.parametrize(
    "engine,text",
    [
        ("gaussian", "Entering Gaussian System\nError termination\nEntering Gaussian System\nNormal termination"),
        ("qe", "Program PWSCF\nError in routine x\nProgram PWSCF\nJOB DONE"),
        ("cp2k", "PROGRAM STARTED AT\n*** ABORT\nPROGRAM STARTED AT\nPROGRAM ENDED AT"),
    ],
)
def test_independent_later_complete_job_can_be_accepted(engine: str, text: str) -> None:
    record = parser.parse_engine_output(engine, text)
    assert record.parser_accepted is True
    assert record.status == "ACCEPTED"
    assert len(record.segments) == 2


def test_nonconvergence_dominates_success() -> None:
    assert (
        parser.parse_engine_output("qe", "Program PWSCF\nJOB DONE\nconvergence NOT achieved").parser_accepted is False
    )
    assert (
        parser.parse_engine_output(
            "cp2k", "PROGRAM STARTED AT\nPROGRAM ENDED AT\nSCF run NOT converged"
        ).parser_accepted
        is False
    )


def test_truncated_and_chunk_boundaries_are_fail_closed() -> None:
    chunks = ["Program PW", "SCF\nJOB ", "DONE\n"]
    assert parser.parse_engine_stream("qe", chunks).parser_accepted is True
    limited = parser.parse_engine_stream("qe", ["Program PWSCF\n" + "x" * 100], max_bytes=10)
    assert limited.status == "TRUNCATED_BY_LIMIT" and not limited.parser_accepted
    incomplete = parser.parse_engine_output("gaussian", "Entering Gaussian System\nSCF Done")
    assert incomplete.status == "INCOMPLETE"


def test_tst_first_order_analytical_value_and_unit() -> None:
    result = tst.eyring_rate(50, barrier_unit="kJ/mol", temperature_K=298.15)
    expected = tst.BOLTZMANN * 298.15 / tst.PLANCK * math.exp(-50000 / (tst.GAS_CONSTANT * 298.15))
    assert result.rate_constant == pytest.approx(expected)
    assert result.rate_unit == "s^-1"


def test_bimolecular_requires_standard_state_and_scales_correctly() -> None:
    with pytest.raises(tst.TSTContractError):
        tst.eyring_rate(50, barrier_unit="kJ/mol", temperature_K=298.15, molecularity=2)
    one_m = tst.eyring_rate(
        50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=tst.StandardState(1, "M", "ideal dilute activity"),
    )
    two_m = tst.eyring_rate(
        50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=tst.StandardState(2, "M", "ideal dilute activity"),
    )
    assert one_m.rate_unit == "M^-1 s^-1"
    assert two_m.rate_constant == pytest.approx(one_m.rate_constant / 2)


def test_kcal_and_kj_barriers_are_equivalent() -> None:
    kj = tst.eyring_rate(41.84, barrier_unit="kJ/mol", temperature_K=300)
    kcal = tst.eyring_rate(10, barrier_unit="kcal/mol", temperature_K=300)
    assert kj.rate_constant == pytest.approx(kcal.rate_constant)


@pytest.mark.parametrize("bad", [True, math.nan, math.inf])
def test_tst_rejects_bool_and_nonfinite(bad: object) -> None:
    with pytest.raises(tst.TSTContractError):
        tst.eyring_rate(bad, barrier_unit="kJ/mol", temperature_K=300)


def test_training_consumes_checksum_bound_pass_artifact(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("id,y\na,1\nb,2\n", encoding="utf-8")
    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
    artifact = ml.DatasetValidationArtifact.from_mapping(
        {
            "status": "PASS",
            "dataset_sha256": digest,
            "schema_version": "dft.dataset.v2",
            "validator_sha256": "1" * 64,
            "sample_count": 2,
            "method_fingerprints": ["PBE-PAW-v1"],
            "split_sha256": "2" * 64,
        }
    )
    receipt = ml.authorize_training(dataset, artifact, expected_schema="dft.dataset.v2")
    assert receipt["model_output_ceiling"] == "BASELINE_GENERATED"
    dataset.write_text("id,y\na,1\nb,3\n", encoding="utf-8")
    with pytest.raises(ml.MLProvenanceError, match="checksum"):
        ml.authorize_training(dataset, artifact, expected_schema="dft.dataset.v2")


def test_model_card_cannot_self_accept_without_ad_uq_holdout_and_approval() -> None:
    base = {
        "status": "ACCEPTED",
        "dataset_sha256": "1" * 64,
        "model_sha256": "2" * 64,
        "code_sha256": "3" * 64,
        "environment_sha256": "4" * 64,
        "metrics": {"mae": 1.0},
    }
    with pytest.raises(ml.MLProvenanceError):
        ml.validate_model_card(base)
    complete = {
        **base,
        "applicability_domain": {"method": "distance", "threshold": 1.0},
        "calibrated_uncertainty": {"method": "conformal", "coverage": 0.9},
        "holdout_validation": {"n": 20, "mae": 1.1},
        "independent_approval": {
            "issuer": "reviewer",
            "role": "qualified-scientist",
            "scope": "model-use",
            "artifact_sha256": "5" * 64,
            "signature": "sig",
            "issued_at": "2026-08-12T00:00:00Z",
        },
    }
    assert ml.validate_model_card(complete)["predictive_use_allowed"] is True
