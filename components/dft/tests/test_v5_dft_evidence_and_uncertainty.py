from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from pathlib import Path
from typing import Protocol, cast

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


kinetics = load("kinetics_uncertainty_v5")
models = load("model_acceptance_v5")
quantities = load("quantity_equivalence_v5")


class QuantityLike(Protocol):
    quantity_kind: str
    values: object
    unit: str
    shape: tuple[int, ...]
    aggregation: str
    atom_mapping: tuple[str, ...] | None
    periodicity: str | None


def _labels() -> list[dict[str, object]]:
    method = "1" * 64
    provenance = "2" * 64
    return [
        {
            "sample_id": "s-train-1",
            "parent_id": "p1",
            "quantity_kind": "energy",
            "value": -1.0,
            "unit": "eV",
            "method_fingerprint": method,
            "engine": "VASP",
            "fidelity": "PBE-PAW",
            "provenance_sha256": provenance,
            "validation_status": "QUALIFIED",
            "split": "train",
        },
        {
            "sample_id": "s-test-1",
            "parent_id": "p2",
            "quantity_kind": "energy",
            "value": -2.0,
            "unit": "eV",
            "method_fingerprint": method,
            "engine": "VASP",
            "fidelity": "PBE-PAW",
            "provenance_sha256": provenance,
            "validation_status": "ACCEPTED",
            "split": "test",
        },
    ]


def test_tst_uncertainty_zero_sigma_reduces_to_point_rate() -> None:
    result = kinetics.propagate_tst_uncertainty(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
    )
    expected = kinetics.K_B * 298.15 / kinetics.H * math.exp(-50_000 / (kinetics.R * 298.15))
    assert result.rate_constant == pytest.approx(expected)
    assert result.lower == pytest.approx(expected)
    assert result.upper == pytest.approx(expected)
    assert result.log_rate_sigma == 0
    assert result.status == "CALCULATED_UNCERTAINTY_NOT_VALIDATED"
    assert "NaN" not in result.to_json()


def test_bimolecular_standard_state_and_sigma_scale_are_dimensionally_explicit() -> None:
    one = kinetics.propagate_tst_uncertainty(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=300,
        molecularity=2,
        standard_state_M=1.0,
        sigma_barrier=1.0,
        sigma_barrier_unit="kJ/mol",
        relative_sigma_standard_state=0.1,
    )
    half = kinetics.propagate_tst_uncertainty(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=300,
        molecularity=2,
        standard_state_M=0.5,
        sigma_barrier=1.0,
        sigma_barrier_unit="kJ/mol",
        relative_sigma_standard_state=0.1,
    )
    assert half.rate_constant == pytest.approx(2 * one.rate_constant)
    assert one.rate_unit == "M^-1 s^-1"
    assert one.upper > one.rate_constant > one.lower


def test_barrier_temperature_correlation_enters_log_variance() -> None:
    uncorrelated = kinetics.propagate_tst_uncertainty(
        barrier=40,
        barrier_unit="kJ/mol",
        temperature_K=350,
        sigma_barrier=2,
        sigma_barrier_unit="kJ/mol",
        sigma_temperature_K=5,
        correlation_barrier_temperature=0,
    )
    correlated = kinetics.propagate_tst_uncertainty(
        barrier=40,
        barrier_unit="kJ/mol",
        temperature_K=350,
        sigma_barrier=2,
        sigma_barrier_unit="kJ/mol",
        sigma_temperature_K=5,
        correlation_barrier_temperature=-0.5,
    )
    assert correlated.correlation_contribution > 0
    assert correlated.log_rate_sigma > uncorrelated.log_rate_sigma


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, -math.inf])
def test_tst_uncertainty_rejects_bool_and_nonfinite(bad: object) -> None:
    with pytest.raises(kinetics.KineticsUncertaintyError):
        kinetics.propagate_tst_uncertainty(barrier=bad, barrier_unit="kJ/mol", temperature_K=300)


def test_training_authorization_binds_current_dataset_and_qualified_labels(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("id,y\ns-train-1,-1\ns-test-1,-2\n", encoding="utf-8")
    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
    artifact = {
        "status": "PASS",
        "dataset_sha256": digest,
        "schema_version": "tsao.dft.dataset-validation.v5",
        "split_sha256": "3" * 64,
    }
    result = models.authorize_training(dataset_path=dataset, validation_artifact=artifact, labels=_labels())
    assert result["model_status_ceiling"] == "BASELINE_GENERATED"
    dataset.write_text("id,y\ns-train-1,-1\ns-test-1,-3\n", encoding="utf-8")
    with pytest.raises(models.ModelAcceptanceError, match="checksum"):
        models.authorize_training(dataset_path=dataset, validation_artifact=artifact, labels=_labels())


def test_label_validation_blocks_parent_leakage_mixed_method_and_constant_target() -> None:
    leakage = _labels()
    leakage[1]["parent_id"] = "p1"
    with pytest.raises(models.ModelAcceptanceError, match="leakage"):
        models.validate_labels(leakage)
    mixed = _labels()
    mixed[1]["method_fingerprint"] = "4" * 64
    with pytest.raises(models.ModelAcceptanceError, match="mixed method"):
        models.validate_labels(mixed)
    constant = _labels()
    constant[1]["value"] = -1.0
    with pytest.raises(models.ModelAcceptanceError, match="constant target"):
        models.validate_labels(constant)


def _accepted_card() -> dict[str, object]:
    return {
        "status": "ACCEPTED",
        "dataset_sha256": "1" * 64,
        "model_sha256": "2" * 64,
        "code_sha256": "3" * 64,
        "environment_sha256": "4" * 64,
        "trainer_identity": "trainer-a",
        "applicability_domain": {"method": "distance", "threshold": 1.0},
        "calibrated_uncertainty": {"method": "conformal", "coverage": 0.9},
        "holdout_validation": {"n": 20, "mae": 0.1},
        "independent_approval": {
            "issuer": "reviewer-b",
            "role": "qualified-scientist",
            "scope": "predictive-model-use",
            "model_sha256": "2" * 64,
            "signature": "external-signature",
            "issued_at": "2026-08-12T00:00:00Z",
            "expires_at": "2026-08-13T00:00:00Z",
        },
    }


def test_model_acceptance_requires_independent_hash_bound_current_approval() -> None:
    result = models.validate_predictive_model_card(_accepted_card(), now="2026-08-12T12:00:00Z")
    assert result["predictive_use_allowed"] is True
    assert result["truth_boundary"] == "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"
    self_approved = _accepted_card()
    self_approval = self_approved["independent_approval"]
    assert isinstance(self_approval, dict)
    self_approval["issuer"] = "trainer-a"
    with pytest.raises(models.ModelAcceptanceError, match="self-issued"):
        models.validate_predictive_model_card(self_approved, now="2026-08-12T12:00:00Z")
    wrong_hash = _accepted_card()
    wrong_hash_approval = wrong_hash["independent_approval"]
    assert isinstance(wrong_hash_approval, dict)
    wrong_hash_approval["model_sha256"] = "9" * 64
    with pytest.raises(models.ModelAcceptanceError, match="model hash"):
        models.validate_predictive_model_card(wrong_hash, now="2026-08-12T12:00:00Z")
    with pytest.raises(models.ModelAcceptanceError, match="not currently valid"):
        models.validate_predictive_model_card(_accepted_card(), now="2026-08-14T00:00:00Z")


def force(values: object, unit: str, mapping: tuple[str, ...]) -> QuantityLike:
    return cast(
        QuantityLike,
        quantities.TypedQuantity(
            quantity_kind="atomic_forces_full",
            values=values,
            unit=unit,
            shape=(2, 3),
            aggregation="full",
            atom_mapping=mapping,
            method_fingerprint="m1",
            periodicity="3D",
        ),
    )


def test_quantity_equivalence_converts_units_but_requires_mapping_and_method() -> None:
    left = force(((1, 2, 3), (4, 5, 6)), "eV/angstrom", ("H1", "H2"))
    factor = 27.211386245988 / 0.529177210903
    right = force(
        tuple(tuple(value / factor for value in row) for row in ((1, 2, 3), (4, 5, 6))), "hartree/bohr", ("H1", "H2")
    )
    assert quantities.equivalent(left, right)
    permuted = force(((4, 5, 6), (1, 2, 3)), "eV/angstrom", ("H2", "H1"))
    assert not quantities.equivalent(left, permuted)
    different_method = quantities.TypedQuantity(
        quantity_kind=left.quantity_kind,
        values=left.values,
        unit=left.unit,
        shape=left.shape,
        aggregation=left.aggregation,
        atom_mapping=left.atom_mapping,
        method_fingerprint="m2",
        periodicity=left.periodicity,
    )
    assert not quantities.equivalent(left, different_method)


def test_summary_scalar_cannot_masquerade_as_full_stress() -> None:
    with pytest.raises(quantities.QuantityEquivalenceError):
        quantities.TypedQuantity(
            quantity_kind="stress_tensor_full",
            values=1.0,
            unit="GPa",
            shape=(),
            aggregation="scalar",
            component_convention="pressure",
        )
