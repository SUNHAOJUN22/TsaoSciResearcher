from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_performance import (  # noqa: E402
    BenchmarkCase,
    _json_default,
    _measure,
    _reference_epdm_energies,
    _reference_epdm_parameters,
    _reference_poe_initial,
    _reference_poe_parameters,
    run_benchmarks,
)
from skills.epdm.core import (  # noqa: E402
    EpdmKineticParameters,
    SemibatchFeed,
    SemibatchInventory,
    batch_pseudo_first_order_screening,
    semibatch_trajectory,
)
from skills.poe.kinetics import simulate_kinetics_terminal  # noqa: E402


def _epdm_parameter_scan_batch(scenarios: int = 1_000) -> object:
    temperatures = np.linspace(303.15, 353.15, scenarios)
    residence_times = np.linspace(30.0, 600.0, scenarios)
    active_sites = np.linspace(0.0004, 0.0016, scenarios)
    multipliers = np.linspace(0.75, 1.25, scenarios)
    batch = batch_pseudo_first_order_screening(
        _reference_epdm_parameters(),
        _reference_epdm_energies(),
        temperatures_K=temperatures,
        residence_times_s=residence_times,
        active_site_mol_L=active_sites,
        propagation_multipliers=multipliers,
    )
    conversions = batch["conversions"]
    assert isinstance(conversions, dict)
    rows = [
        {
            "temperature_K": float(temperatures[index]),
            "residence_time_s": float(residence_times[index]),
            "active_site_mol_L": float(active_sites[index]),
            "propagation_multiplier": float(multipliers[index]),
            "conversions": {
                "ethylene": float(conversions["ethylene"][index]),
                "propylene": float(conversions["propylene"][index]),
                "diene": float(conversions["diene"][index]),
            },
        }
        for index in range(scenarios)
    ]
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "scenario_count": scenarios,
        "shape": [scenarios],
        "scenarios": rows,
    }


def _epdm_semibatch_trajectory_compiled(steps: int = 10_000) -> object:
    result = semibatch_trajectory(
        SemibatchInventory(100.0, 12.0, 10.0, 0.4, 0.0, 323.15, 900.0),
        SemibatchFeed(0.0008, 0.0006, 0.00002, 0.0001),
        EpdmKineticParameters(0.2, 0.16, 0.05, 0.008, 0.002, 1.0),
        steps=steps,
        active_site_mol_L=0.0001,
        poison_mol_L=1e-7,
        step_s=0.1,
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=0.01,
    )
    return {
        "status": result["status"],
        "steps": result["steps"],
        "final_inventory": result["final_inventory"],
        "history": result["history"],
        "total_polymer_increment_mol": result["total_polymer_increment_mol"],
        "maximum_abs_molar_closure_residual": result["maximum_abs_molar_closure_residual"],
    }


def _poe_rk4_terminal_10000() -> object:
    return simulate_kinetics_terminal(
        _reference_poe_initial(),
        _reference_poe_parameters(),
        duration_s=100.0,
        step_s=0.01,
    )


def run_benchmarks_v2(*, repeats: int, wheel_dir: Path | None = None) -> dict[str, object]:
    report = run_benchmarks(repeats=repeats, wheel_dir=wheel_dir)
    extra_cases = (
        BenchmarkCase(
            "epdm_parameter_scan_1000_batch",
            _epdm_parameter_scan_batch,
            5,
            2,
            warmups=2,
        ),
        BenchmarkCase(
            "epdm_semibatch_10000_steps_compiled",
            _epdm_semibatch_trajectory_compiled,
            1,
            1,
            warmups=1,
            repeat_override=3,
        ),
        BenchmarkCase(
            "poe_rk4_10000_steps_terminal",
            _poe_rk4_terminal_10000,
            1,
            1,
            warmups=1,
            repeat_override=3,
        ),
    )
    extras = [_measure(case, repeats=repeats) for case in extra_cases]
    benchmarks = report.get("benchmarks")
    assert isinstance(benchmarks, list)
    benchmarks.extend(extras)
    report["schema"] = "TSAO-PERFORMANCE-2-OPTIMIZED"
    report["benchmark_count"] = len(benchmarks)
    report["optimized_extensions"] = [case.name for case in extra_cases]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark TSAO alpha11 optimized and extended workloads"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--wheel-dir", type=Path)
    args = parser.parse_args(argv)
    if args.repeats < 3:
        raise ValueError("repeats must be at least 3")
    report = run_benchmarks_v2(repeats=args.repeats, wheel_dir=args.wheel_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
