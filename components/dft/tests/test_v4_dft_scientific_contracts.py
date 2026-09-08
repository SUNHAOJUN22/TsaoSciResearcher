from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "skills/tsao-dft-hpc-provenance/scripts/scientific_contracts_v4.py"
spec = importlib.util.spec_from_file_location("dft_contracts_v4", MODULE)
assert spec and spec.loader
contracts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contracts
spec.loader.exec_module(contracts)


@pytest.mark.parametrize(
    ("engine", "success", "fatal"),
    [
        ("gaussian", "Normal termination of Gaussian 16", "Error termination via Lnk1e"),
        (
            "vasp",
            "reached required accuracy\nGeneral timing and accounting informations for this job",
            "ZBRENT: fatal error",
        ),
        ("qe", "convergence has been achieved\nJOB DONE.", "Error in routine electrons"),
        ("cp2k", "SCF run converged\nPROGRAM ENDED AT 12:00", "*** ABORT ***"),
    ],
)
def test_later_fatal_outvotes_earlier_success(engine: str, success: str, fatal: str) -> None:
    result = contracts.evaluate_engine_output(engine, f"{success}\n{fatal}")
    assert result.parser_accepted is False
    assert "FATAL_OR_NONCONVERGENCE_MARKER" in result.reason_codes


@pytest.mark.parametrize(
    ("engine", "success"),
    [
        ("gaussian", "Normal termination of Gaussian 16"),
        ("vasp", "reached required accuracy\nGeneral timing and accounting informations for this job"),
        ("qe", "convergence has been achieved\nJOB DONE."),
        ("cp2k", "SCF run converged\nPROGRAM ENDED AT 12:00"),
    ],
)
def test_independent_later_complete_segment_can_be_accepted(engine: str, success: str) -> None:
    text = "--- JOB START ---\nError in routine or ABORT\n--- JOB START ---\n" + success
    result = contracts.evaluate_engine_output(engine, text)
    assert result.segment_count == 2
    assert result.final_segment == 1
    assert result.parser_accepted is True


def test_truncated_output_is_hold() -> None:
    result = contracts.evaluate_engine_output("qe", "Program PWSCF\niteration # 17")
    assert result.parser_accepted is False
    assert "NORMAL_TERMINATION_MISSING" in result.reason_codes


def test_unimolecular_tst_matches_eyring_formula() -> None:
    rate = contracts.tst_rate(barrier=50, barrier_unit="kJ/mol", temperature_K=298.15)
    expected = contracts.K_B * 298.15 / contracts.H * math.exp(-50000 / (contracts.R * 298.15))
    assert rate.value == pytest.approx(expected)
    assert rate.unit == "s^-1"


def test_bimolecular_tst_requires_and_uses_standard_state() -> None:
    with pytest.raises(contracts.DFTContractError):
        contracts.tst_rate(barrier=50, barrier_unit="kJ/mol", temperature_K=298.15, molecularity=2)
    one_molar = contracts.tst_rate(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=contracts.StandardState(1.0, "M", "dimensionless_activity_c_over_c0"),
    )
    half_molar = contracts.tst_rate(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=contracts.StandardState(0.5, "M", "dimensionless_activity_c_over_c0"),
    )
    assert one_molar.unit == "M^-1 s^-1"
    assert half_molar.value == pytest.approx(2 * one_molar.value)


def test_kcal_and_kj_barriers_are_equivalent() -> None:
    a = contracts.tst_rate(barrier=10, barrier_unit="kcal/mol", temperature_K=350)
    b = contracts.tst_rate(barrier=41.84, barrier_unit="kJ/mol", temperature_K=350)
    assert a.value == pytest.approx(b.value)


def test_quantity_shape_blocks_summary_scalar_as_full_stress() -> None:
    invalid = contracts.validate_quantity_shape(
        {"quantity_kind": "stress_tensor", "aggregation": "full", "values": 1.2, "component_convention": "pressure"}
    )
    assert invalid.accepted is False
    valid = contracts.validate_quantity_shape(
        {
            "quantity_kind": "stress_tensor",
            "aggregation": "full",
            "values": [1, 2, 3, 4, 5, 6],
            "component_convention": "voigt_xx_yy_zz_yz_xz_xy",
        }
    )
    assert valid.accepted is True


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, -math.inf])
def test_tst_rejects_bool_and_nonfinite(bad: object) -> None:
    with pytest.raises(contracts.DFTContractError):
        contracts.tst_rate(barrier=bad, barrier_unit="kJ/mol", temperature_K=298.15)
