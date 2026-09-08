from __future__ import annotations

import importlib.util
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


parser = load("skills/tsao-dft-hpc-provenance/scripts/engine_parser_contract_v4.py", "dft_parser_v4")
tst = load("skills/tsao-dft-kinetics-multiscale/scripts/tst_standard_state_v4.py", "tst_v4")


def test_fatal_dominates_earlier_success_for_all_engines() -> None:
    fixtures = {
        "gaussian": "Entering Gaussian System\nNormal termination of Gaussian\nError termination via Lnk1e\n",
        "vasp": "vasp.6\nreached required accuracy\nGeneral timing and accounting informations\nZBRENT: fatal error\n",
        "qe": "Program PWSCF\nconvergence has been achieved\nJOB DONE.\nError in routine cdiaghg\n",
        "cp2k": "CP2K| version 2026\nSCF run converged\nPROGRAM ENDED AT\n*** ABORT\n",
    }
    for engine, text in fixtures.items():
        result = parser.parse_engine_output(engine, text)
        assert not result.parser_accepted, engine
        assert result.status == "FATAL", engine
        assert "FATAL_MARKER_PRESENT" in result.reason_codes


def test_independent_later_success_can_be_selected() -> None:
    text = "Entering Gaussian System\nError termination\nEntering Gaussian System\nNormal termination of Gaussian\n"
    result = parser.parse_engine_output("gaussian", text)
    assert result.parser_accepted
    assert len(result.jobs) == 2
    assert result.jobs[0].fatal
    assert result.jobs[1].status == "CONVERGED"


def test_nonconvergence_and_truncation_are_not_candidates() -> None:
    assert (
        parser.parse_engine_output("qe", "Program PWSCF\nconvergence NOT achieved\nJOB DONE\n").status == "NONCONVERGED"
    )
    assert parser.parse_engine_output("vasp", "vasp.6\niteration 10\n").status == "INCOMPLETE"


def test_legacy_adapters_return_nonzero_on_fatal(tmp_path: Path) -> None:
    output = tmp_path / "g.log"
    output.write_text("Normal termination of Gaussian\nError termination\n", encoding="utf-8")
    script = ROOT / "skills/tsao-dft-researcher/scripts/parse_gaussian.py"
    result = subprocess.run([sys.executable, str(script), str(output)], text=True, capture_output=True)
    assert result.returncode != 0
    assert '"parser_accepted": false' in result.stdout


def test_quantity_shape_contract() -> None:
    q = parser.QuantityRecord(
        quantity_kind="atomic_forces_full",
        value=((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)),
        unit="eV/angstrom",
        shape=(2, 3),
        aggregation="full",
        atom_count=2,
        atom_mapping=("H:1", "H:2"),
    )
    assert q.shape == (2, 3)
    try:
        parser.QuantityRecord(
            quantity_kind="atomic_forces_full",
            value=(1.0,),
            unit="eV/angstrom",
            shape=(1,),
            aggregation="max",
            atom_count=1,
        )
    except parser.ParserContractError:
        pass
    else:
        raise AssertionError("summary scalar was accepted as full forces")


def test_first_order_eyring_analytical_value_and_unit() -> None:
    rate = tst.eyring_rate(barrier=50.0, barrier_unit="kJ/mol", temperature_K=298.15)
    expected = tst.BOLTZMANN * 298.15 / tst.PLANCK * math.exp(-50000.0 / (tst.GAS_CONSTANT * 298.15))
    assert rate.status == "OK"
    assert rate.unit == "s^-1"
    assert math.isclose(rate.rate_constant, expected, rel_tol=1e-13)


def test_bimolecular_requires_and_uses_standard_state() -> None:
    invalid = tst.eyring_rate(barrier=50, barrier_unit="kJ/mol", temperature_K=298.15, molecularity=2)
    assert invalid.status == "INVALID"
    assert invalid.rate_constant is None
    a = tst.eyring_rate(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=tst.StandardState(1.0, "mol/L", "a=c/c°"),
    )
    b = tst.eyring_rate(
        barrier=50,
        barrier_unit="kJ/mol",
        temperature_K=298.15,
        molecularity=2,
        standard_state=tst.StandardState(0.1, "mol/L", "a=c/c°"),
    )
    assert a.unit == "L^1 mol^-1 s^-1"
    assert math.isclose(b.rate_constant / a.rate_constant, 10.0, rel_tol=1e-12)


def test_barrier_unit_invariance_and_finite_rejection() -> None:
    a = tst.eyring_rate(barrier=12.0, barrier_unit="kcal/mol", temperature_K=300)
    b = tst.eyring_rate(barrier=50.208, barrier_unit="kJ/mol", temperature_K=300)
    assert math.isclose(a.rate_constant, b.rate_constant, rel_tol=1e-12)
    for value in [True, float("nan"), float("inf")]:
        try:
            tst.eyring_rate(barrier=value, barrier_unit="kJ/mol", temperature_K=300)
        except tst.TSTContractError:
            pass
        else:
            raise AssertionError(f"non-finite/Bool barrier accepted: {value!r}")
