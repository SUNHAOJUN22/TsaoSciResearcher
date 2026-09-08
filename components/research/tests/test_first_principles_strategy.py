from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from tsao_researcher.errors import ValidationError
from tsao_researcher.strategy import advise_computation_strategy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v2/computation-strategy.schema.json").read_text(encoding="utf-8"))


def _families(result: dict[str, object]) -> str:
    return " ".join(
        str(row["family"])
        for row in result["method_ladder"]  # type: ignore[index,union-attr]
    ).casefold()


def test_electronic_defect_strategy_starts_from_quantum_states() -> None:
    result = advise_computation_strategy(
        "How do interface defects change trap depth and the electronic density of states?",
        ["trap depth", "PDOS"],
        ["300 K", "fixed composition"],
        available_evidence=["thermally stimulated current", "XPS"],
    )
    assert result["classification"]["primary_regime"] == "electronic-structure"
    assert "ground-state electronic structure" in _families(result)
    assert result["method_ladder"][0]["role"] == "minimum-sufficient"
    assert "total charge" in result["first_principles_frame"]["conserved_quantities"]

    excited = advise_computation_strategy(
        "Which excited state controls the optical absorption spectrum and electron-hole response?",
        ["absorption spectrum", "excitation energy"],
        ["room temperature"],
    )
    assert excited["classification"]["primary_regime"] == "electronic-structure"
    methods = " ".join(method for row in excited["method_ladder"] for method in row["representative_methods"])
    assert "TDDFT" in methods
    assert "GW/BSE" in methods


def test_reaction_strategy_includes_quantum_barriers_and_statistical_kinetics() -> None:
    result = advise_computation_strategy(
        "Which catalytic reaction pathway controls selectivity and the apparent activation energy?",
        ["selectivity", "rate constant"],
        ["operando temperature and pressure"],
    )
    assert result["classification"]["primary_regime"] == "reaction-kinetics"
    families = _families(result)
    assert "quantum reaction energetics" in families
    assert "statistical kinetics" in families


def test_polymer_morphology_strategy_uses_statistical_physics_and_mesoscale_models() -> None:
    result = advise_computation_strategy(
        "How do polymer chain architecture and cooling history control phase separation and lamellar morphology?",
        ["domain size", "lamellar thickness"],
        ["non-isothermal cooling"],
    )
    assert result["classification"]["primary_regime"] == "soft-matter-polymer"
    assert "entropy-energy competition" in result["first_principles_frame"]["governing_principles"]
    assert "mesoscopic structure evolution" in _families(result)


def test_free_energy_strategy_selects_ensemble_sampling_not_single_structure_only() -> None:
    result = advise_computation_strategy(
        "What is the solvation free energy and conformational equilibrium of this molecule?",
        ["solvation free energy", "conformer population"],
        ["298 K", "1 bar"],
    )
    assert result["classification"]["primary_regime"] == "molecular-thermodynamics"
    ensemble = " ".join(result["first_principles_frame"]["statistical_ensemble"])
    assert "NVT" in ensemble or "NPT" in ensemble
    assert "molecular sampling" in _families(result)


def test_non_newtonian_pressure_drop_starts_from_conservation_and_scale_analysis() -> None:
    result = advise_computation_strategy(
        "Predict the pressure drop and temperature field for non-Newtonian flow through a narrow channel.",
        ["pressure drop", "temperature field"],
        ["steady inlet flow"],
    )
    assert result["classification"]["primary_regime"] == "continuum-transport"
    principles = result["first_principles_frame"]["governing_principles"]
    assert "mass conservation" in principles
    assert "momentum balance" in principles
    assert "Reynolds number" in result["first_principles_frame"]["dimensionless_or_scale_tests"]
    assert "conservation-law scaling" in _families(result)


def test_fracture_strategy_uses_energy_and_constitutive_hierarchy() -> None:
    result = advise_computation_strategy(
        "Which mechanism controls crack initiation and fatigue failure in the composite?",
        ["critical load", "crack path"],
        ["cyclic loading"],
    )
    assert result["classification"]["primary_regime"] == "solid-mechanics"
    assert "fracture energetics" in result["first_principles_frame"]["governing_principles"]
    assert "finite-element field analysis" in _families(result)


def test_charge_transport_strategy_connects_quantum_states_to_mesoscopic_transport() -> None:
    result = advise_computation_strategy(
        "How do trap states and morphology control space charge, conductivity, and electrical breakdown?",
        ["space charge", "conductivity", "breakdown strength"],
        ["applied electric field", "elevated temperature"],
    )
    assert result["classification"]["primary_regime"] == "charge-transport-dielectric"
    families = _families(result)
    assert "electronic and electrostatic state analysis" in families
    assert "mesoscopic carrier transport" in families
    assert result["cross_scale_plan"]["required"] is True


def test_process_strategy_uses_balances_population_models_and_identifiability() -> None:
    result = advise_computation_strategy(
        "How do reactor residence time and polymerization kinetics determine the molecular weight distribution?",
        ["conversion", "molecular weight distribution"],
        ["continuous reactor"],
    )
    assert result["classification"]["primary_regime"] == "process-kinetics-population"
    assert "mass and energy balances" in result["first_principles_frame"]["governing_principles"]
    assert "population and reactor modelling" in _families(result)


def test_ambiguous_problem_requests_observable_and_conditions() -> None:
    result = advise_computation_strategy("Suggest a first-principles simulation strategy for this material.")
    classification = result["classification"]
    assert classification["primary_regime"] == "multiscale-general"
    assert classification["clarification_required"] is True
    assert classification["clarification_questions"]


def test_strategy_is_deterministic_and_explicitly_non_executing() -> None:
    args = (
        "How does temperature affect dielectric relaxation?",
        ["relaxation time"],
        ["250-400 K"],
    )
    first = advise_computation_strategy(*args)
    second = advise_computation_strategy(*args)
    assert first == second
    assert first["strategy_id"].startswith("FPS-")
    assert first["execution_boundary"]["solver_executed"] is False
    assert first["execution_boundary"]["external_execution_required"] is True


def test_strategy_schema_validation() -> None:
    result = advise_computation_strategy(
        "Estimate the band gap and defect level of a crystal.",
        ["band gap", "defect level"],
        ["0 K reference structure"],
    )
    jsonschema.Draft202012Validator(SCHEMA).validate(result)


def test_schema_rejects_false_execution_claim() -> None:
    result = advise_computation_strategy("Estimate the band gap.", ["band gap"])
    result["execution_boundary"]["solver_executed"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(result)


def test_rejects_invalid_or_unbounded_input() -> None:
    with pytest.raises(ValidationError):
        advise_computation_strategy("x")
    with pytest.raises(ValidationError):
        advise_computation_strategy("valid question", ["x"] * 65)


def test_cli_and_validation_script_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "strategy.json"
    generated = subprocess.run(
        [
            sys.executable,
            "-m",
            "tsao_researcher",
            "strategy",
            "How does a defect change the electronic band gap?",
            "--observable",
            "band gap",
            "--condition",
            "fixed charge state",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert generated.returncode == 0, generated.stderr
    assert json.loads(generated.stdout)["status"] == "advisory-only"
    validated = subprocess.run(
        [sys.executable, "scripts/validate_computation_strategy.py", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert validated.returncode == 0, validated.stderr
    assert "PASS" in validated.stdout
