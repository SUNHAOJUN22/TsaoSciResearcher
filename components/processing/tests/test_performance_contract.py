from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import skills.poe.estimation as poe_estimation
from skills.epdm.kinetics import (
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    three_level_kinetic_suite,
)
from skills.epdm.process import SemibatchFeed, SemibatchInventory, semibatch_material_energy_step
from skills.poe.dynamics import response_metrics
from skills.poe.kinetics import KineticParameters, KineticState, simulate_kinetics
from tsao.doctor import diagnose
from tsao.provenance import build_manifest, verify_manifest

ROOT = Path(__file__).resolve().parents[1]


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _epdm_suite() -> dict[str, object]:
    families = 64
    return three_level_kinetic_suite(
        EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1e-6),
        EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0),
        EpdmActivationEnergies(35_000, 37_000, 42_000, 28_000, 45_000, 20_000),
        temperature_K=323.15,
        residence_time_s=300.0,
        site_family_fractions=tuple(1.0 / families for _ in range(families)),
        site_activity_multipliers=tuple(
            0.55 + 0.9 * index / (families - 1) for index in range(families)
        ),
    )


def test_epdm_suite_preserves_baseline_result_and_validates_once(monkeypatch: pytest.MonkeyPatch):
    counts = {"state": 0, "parameters": 0, "activation": 0}
    original_state = EpdmKineticState.validated
    original_parameters = EpdmKineticParameters.validated
    original_activation = EpdmActivationEnergies.validated

    def state_validated(self):
        counts["state"] += 1
        return original_state(self)

    def parameters_validated(self):
        counts["parameters"] += 1
        return original_parameters(self)

    def activation_validated(self):
        counts["activation"] += 1
        return original_activation(self)

    monkeypatch.setattr(EpdmKineticState, "validated", state_validated)
    monkeypatch.setattr(EpdmKineticParameters, "validated", parameters_validated)
    monkeypatch.setattr(EpdmActivationEnergies, "validated", activation_validated)
    result = _epdm_suite()
    assert _digest(result) == "d937f48d88a566341f6df8d9cfb9b1ddfdf65d11980b098c7b963bc2b3536792"
    assert counts == {"state": 1, "parameters": 1, "activation": 1}


def test_epdm_semibatch_preserves_baseline_result_without_state_revalidation(
    monkeypatch: pytest.MonkeyPatch,
):
    def forbidden_state_validation(self):
        raise AssertionError("internally constructed semibatch state must use validated fast path")

    monkeypatch.setattr(EpdmKineticState, "validated", forbidden_state_validation)
    result = semibatch_material_energy_step(
        SemibatchInventory(100.0, 120.0, 100.0, 4.0, 0.0, 323.15, 900.0),
        SemibatchFeed(0.08, 0.06, 0.002, 0.01),
        EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0),
        active_site_mol_L=0.001,
        poison_mol_L=1e-6,
        step_s=30.0,
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=7.0,
    )
    assert _digest(result) == "aec440641c2b9c2de5572e7df51e9258d6f30344e22dde0c63ef5a020ca142f7"


def test_poe_rk4_preserves_baseline_result_and_validates_only_at_entry(
    monkeypatch: pytest.MonkeyPatch,
):
    counts = {"state": 0, "parameters": 0}
    original_state = KineticState.validate
    original_parameters = KineticParameters.validate

    def state_validate(self):
        counts["state"] += 1
        return original_state(self)

    def parameters_validate(self):
        counts["parameters"] += 1
        return original_parameters(self)

    monkeypatch.setattr(KineticState, "validate", state_validate)
    monkeypatch.setattr(KineticParameters, "validate", parameters_validate)
    result = simulate_kinetics(
        KineticState(monomer_a=1.2, monomer_b=0.8, dormant_sites=0.01),
        KineticParameters(0.002, 0.08, 0.05, 0.003, 0.0005),
        duration_s=20.0,
        step_s=0.05,
    )
    assert _digest(result) == "5a158478b8fd13c6c7ab77c6255a650f4025d8a5732a947ff2eaed47caf5acf5"
    assert counts == {"state": 1, "parameters": 1}


def test_first_order_fit_validates_input_arrays_once(monkeypatch: pytest.MonkeyPatch):
    calls = 0
    original = poe_estimation._finite_vector

    def counted(values, label):
        nonlocal calls
        calls += 1
        return original(values, label)

    monkeypatch.setattr(poe_estimation, "_finite_vector", counted)
    times = np.linspace(0.0, 20.0, 401)
    observed = 1.0 - np.exp(-0.2 * times)
    result = poe_estimation.fit_first_order_rate(times, observed, lower_s=0.01, upper_s=1.0)
    assert result["rate_constant_s"] == pytest.approx(0.2, abs=1e-6)
    assert calls == 2


def test_response_metrics_matches_legacy_settling_definition_without_quadratic_np_all(
    monkeypatch: pytest.MonkeyPatch,
):
    times = np.linspace(0.0, 40.0, 801)
    values = 2.0 * (1.0 - np.exp(-np.maximum(0.0, times - 2.0) / 5.0))
    change = 2.0 - float(values[0])
    band = 0.02 * abs(change)
    legacy = None
    for index in range(values.size):
        if np.all(np.abs(values[index:] - 2.0) <= band):
            legacy = float(times[index])
            break

    def forbidden_np_all(*args, **kwargs):
        raise AssertionError("settling-time calculation regressed to repeated tail scans")

    monkeypatch.setattr(np, "all", forbidden_np_all)
    result = response_metrics(times, values, target=2.0)
    assert result["settling_time_s"] == legacy


def test_manifest_build_and_verify_read_each_source_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    sources = []
    for index in range(8):
        path = tmp_path / "src" / f"file-{index}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"row={index}\r\n", encoding="utf-8")
        sources.append(path)
    target = tmp_path / "reports/SOURCE_CORE_MANIFEST.tsv"
    original = Path.read_bytes
    reads: dict[Path, int] = {}

    def counted(path: Path):
        resolved = path.resolve()
        if resolved in {item.resolve() for item in sources}:
            reads[resolved] = reads.get(resolved, 0) + 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)
    assert build_manifest(tmp_path, target) == len(sources)
    assert set(reads.values()) == {1}
    reads.clear()
    assert verify_manifest(tmp_path, target) == []
    assert set(reads.values()) == {1}


def test_doctor_reuses_one_repository_rglob(monkeypatch: pytest.MonkeyPatch):
    calls = 0
    original = Path.rglob
    root_resolved = ROOT.resolve()

    def counted(path: Path, pattern: str, *args, **kwargs):
        nonlocal calls
        if path.resolve() == root_resolved and pattern == "*":
            calls += 1
        return original(path, pattern, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", counted)
    result = diagnose(ROOT, profile="core")
    assert result["pass"], result["issues"]
    assert calls == 1
