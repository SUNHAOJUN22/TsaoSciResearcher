"""Focused DFT parser, standard-state, and model-evidence tests."""

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "scientific_contracts_v16.py"
)
SPEC = importlib.util.spec_from_file_location("tsao_dft_contracts_v16", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CONTRACTS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTRACTS
SPEC.loader.exec_module(CONTRACTS)


def test_late_fatal_overrides_earlier_success() -> None:
    assert CONTRACTS.parser_status("Normal termination\n--job--\nError termination") == "FAIL_FATAL"


def test_incomplete_output_is_held() -> None:
    assert CONTRACTS.parser_status("SCF iteration 4") == "HOLD_INCOMPLETE"


def test_bimolecular_tst_requires_standard_state() -> None:
    with pytest.raises(ValueError):
        CONTRACTS.tst_rate(
            delta_g_j_mol=50_000.0,
            temperature_k=298.15,
            molecularity=2,
        )


def test_tst_reports_order_consistent_units() -> None:
    rate, unit = CONTRACTS.tst_rate(
        delta_g_j_mol=50_000.0,
        temperature_k=298.15,
        molecularity=2,
        standard_state_mol_l=1.0,
    )
    assert rate > 0.0
    assert "L^1" in unit


def test_model_cannot_self_accept_without_independent_approval() -> None:
    digest = "0" * 64
    card = {
        "dataset_sha256": digest,
        "model_sha256": digest,
        "code_sha256": digest,
        "environment_sha256": digest,
        "applicability_domain": {},
        "calibrated_uncertainty": {},
        "holdout_validation": {},
        "independent_approval": False,
    }
    assert CONTRACTS.model_acceptance(card) == "HOLD_INDEPENDENT_APPROVAL"
