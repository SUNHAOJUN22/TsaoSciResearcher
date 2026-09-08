from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BALANCE_HEADER = (
    "component,quantity_basis,quantity_unit,time_unit,in,out,generation,"
    "consumption,accumulation,absolute_tolerance,relative_tolerance,reference_scale\n"
)


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(f"polymer_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scaleup_known_solutions_and_invalid():
    module = load("scaleup_numbers")
    result = module.calculate(
        rho=1000,
        mu=1,
        velocity=2,
        length=3,
        cp=4,
        k=2,
        diffusivity=0.5,
        reaction_time=10,
        mixing_time=2,
    )
    assert result["Re"] == pytest.approx(6000)
    assert result["Pr"] == pytest.approx(2)
    assert result["Sc"] == pytest.approx(0.002)
    assert result["Da_mixing"] == pytest.approx(0.2)
    with pytest.raises(ValueError):
        module.calculate(rho=float("nan"))
    with pytest.raises(ValueError):
        module.calculate(mu=0)


def test_balance_known_solution_and_duplicate_rejection(tmp_path: Path):
    module = load("check_balance")
    path = tmp_path / "balance.csv"
    path.write_text(
        BALANCE_HEADER + "A,mass,kg,h,10,8,0,2,0,1e-12,0,10\n",
        encoding="utf-8",
    )
    assert module.check(path)["pass"] is True
    path.write_text(
        BALANCE_HEADER
        + "A,mass,kg,h,10,8,0,2,0,1e-12,0,10\n"
        + "A,mass,kg,h,1,1,0,0,0,1e-12,0,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate component"):
        module.check(path)


def test_master_plan_is_full_g0_g18(tmp_path: Path):
    module = load("generate_master_plan")
    brief = tmp_path / "brief.yaml"
    brief.write_text("project_id: P-1\n", encoding="utf-8")
    out = tmp_path / "plan.csv"
    assert module.main(["--brief", str(brief), "--out", str(out)]) == 0
    with out.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 266
    assert {row["gate"] for row in rows} == {f"G{i}" for i in range(19)}


def test_doe_is_deterministic(tmp_path: Path):
    module = load("generate_doe")
    factors = tmp_path / "factors.yaml"
    factors.write_text(
        "factors:\n"
        "  - name: temperature\n"
        "    levels: [100, 120]\n"
        "  - name: pressure\n"
        "    levels: [1, 2]\n",
        encoding="utf-8",
    )
    first = tmp_path / "one.csv"
    second = tmp_path / "two.csv"
    assert module.main(["--factors", str(factors), "--out", str(first), "--seed", "7"]) == 0
    assert module.main(["--factors", str(factors), "--out", str(second), "--seed", "7"]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_balance_rejects_cross_component_cancellation(tmp_path: Path):
    module = load("check_balance")
    path = tmp_path / "cancel.csv"
    path.write_text(
        BALANCE_HEADER
        + "A,mass,kg,h,10,0,0,0,0,1e-12,0,10\n"
        + "B,mass,kg,h,0,10,0,0,0,1e-12,0,10\n",
        encoding="utf-8",
    )
    result = module.check(path)
    assert result["total_balance_pass"] is True
    assert result["component_balances_pass"] is False
    assert result["pass"] is False
    assert result["failed_components"] == ["A", "B"]
