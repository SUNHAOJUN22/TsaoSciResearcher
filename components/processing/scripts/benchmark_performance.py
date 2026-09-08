from __future__ import annotations

import argparse
import cProfile
import gc
import hashlib
import json
import os
import platform
import pstats
import statistics
import subprocess
import sys
import tempfile
import timeit
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_wheel_contents import verify as verify_wheel  # noqa: E402
from skills.epdm.core import (  # noqa: E402
    EpdmActivationEnergies,
    EpdmKineticParameters,
    EpdmKineticState,
    SemibatchFeed,
    SemibatchInventory,
    pseudo_first_order_conversions,
    semibatch_material_energy_step,
    temperature_adjusted_parameters,
    three_level_kinetic_suite,
)
from skills.poe.dynamics import fopdt_response, response_metrics  # noqa: E402
from skills.poe.estimation import (  # noqa: E402
    assess_identifiability,
    finite_difference_jacobian,
    fit_first_order_rate,
)
from skills.poe.kinetics import (  # noqa: E402
    KineticParameters,
    KineticState,
    simulate_kinetics,
)
from tsao import __version__  # noqa: E402
from tsao.doctor import diagnose  # noqa: E402
from tsao.process_package import validate_process_package  # noqa: E402
from tsao.provenance import build_manifest, verify_manifest  # noqa: E402
from tsao.skillpacks import skillpack_inventory  # noqa: E402


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    function: Callable[[], object]
    number: int
    profile_loops: int
    warmups: int = 2
    repeat_override: int | None = None
    digest_projection: Callable[[object], object] | None = None


def _json_default(value: object) -> object:
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def _json_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _process_package_digest_projection(result: object) -> object:
    """Return stable fail-closed semantics without zero-detail allocation noise."""
    if not isinstance(result, dict):
        return result
    return {
        "status": result.get("status"),
        "declared_status": result.get("declared_status"),
        "pass": result.get("pass"),
        "errors": result.get("errors"),
        "holds": result.get("holds"),
        "reason_codes": result.get("reason_codes"),
        "failed_component_balances": result.get("failed_component_balances"),
        "metrics": result.get("metrics"),
    }


def _source_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GITHUB_SHA")


def _cpu_description() -> str:
    processor = platform.processor().strip()
    if processor:
        return processor
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.casefold().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def _profile(function: Callable[[], object], loops: int) -> list[dict[str, object]]:
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(loops):
        function()
    profiler.disable()
    stats = pstats.Stats(profiler)
    rows: list[dict[str, object]] = []
    for (filename, line, function_name), values in sorted(
        stats.stats.items(), key=lambda item: item[1][3], reverse=True
    )[:15]:
        primitive_calls, total_calls, total_time, cumulative_time, _ = values
        rows.append(
            {
                "function": f"{Path(filename).name}:{line}:{function_name}",
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_time_s": total_time,
                "cumulative_time_s": cumulative_time,
            }
        )
    return rows


def _peak_memory(function: Callable[[], object]) -> int:
    gc.collect()
    tracemalloc.start()
    try:
        function()
        _, peak = tracemalloc.get_traced_memory()
        return peak
    finally:
        tracemalloc.stop()


def _measure(case: BenchmarkCase, *, repeats: int) -> dict[str, object]:
    active_repeats = case.repeat_override or repeats
    for _ in range(case.warmups):
        case.function()
    result = case.function()
    timer = timeit.Timer(case.function)
    samples = [
        elapsed / case.number for elapsed in timer.repeat(number=case.number, repeat=active_repeats)
    ]
    return {
        "name": case.name,
        "number_per_repeat": case.number,
        "repeats": active_repeats,
        "warmups": case.warmups,
        "median_s_per_call": statistics.median(samples),
        "minimum_s_per_call": min(samples),
        "maximum_s_per_call": max(samples),
        "stdev_s_per_call": statistics.pstdev(samples),
        "peak_memory_bytes": _peak_memory(case.function),
        "result_sha256": _json_digest(
            case.digest_projection(result) if case.digest_projection is not None else result
        ),
        "profile_loops": case.profile_loops,
        "profile_top_cumulative": _profile(case.function, case.profile_loops),
    }


def _reference_epdm_state(active_site: float = 0.001) -> EpdmKineticState:
    return EpdmKineticState(1.2, 1.0, 0.04, active_site, 1e-6)


def _reference_epdm_parameters() -> EpdmKineticParameters:
    return EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)


def _reference_epdm_energies() -> EpdmActivationEnergies:
    return EpdmActivationEnergies(35_000, 37_000, 42_000, 28_000, 45_000, 20_000)


def _epdm_suite_case(families: int) -> object:
    fractions = tuple(1.0 / families for _ in range(families))
    multipliers = tuple(0.55 + 0.9 * index / (families - 1) for index in range(families))
    return three_level_kinetic_suite(
        _reference_epdm_state(),
        _reference_epdm_parameters(),
        _reference_epdm_energies(),
        temperature_K=323.15,
        residence_time_s=300.0,
        site_family_fractions=fractions,
        site_activity_multipliers=multipliers,
    )


def _epdm_semibatch_step_case() -> object:
    return semibatch_material_energy_step(
        SemibatchInventory(100.0, 120.0, 100.0, 4.0, 0.0, 323.15, 900.0),
        SemibatchFeed(0.08, 0.06, 0.002, 0.01),
        _reference_epdm_parameters(),
        active_site_mol_L=0.001,
        poison_mol_L=1e-6,
        step_s=30.0,
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=7.0,
    )


def _epdm_semibatch_trajectory_scalar(steps: int = 10_000) -> object:
    inventory = SemibatchInventory(100.0, 12.0, 10.0, 0.4, 0.0, 323.15, 900.0)
    feed = SemibatchFeed(0.0008, 0.0006, 0.00002, 0.0001)
    parameters = EpdmKineticParameters(0.2, 0.16, 0.05, 0.008, 0.002, 1.0)
    history: list[dict[str, float]] = []
    total_polymer = 0.0
    maximum_closure = 0.0
    for index in range(steps):
        result = semibatch_material_energy_step(
            inventory,
            feed,
            parameters,
            active_site_mol_L=0.0001,
            poison_mol_L=1e-7,
            step_s=0.1,
            reaction_enthalpy_kJ_mol=85.0,
            heat_removal_kW=0.01,
        )
        inventory_data = result["inventory"]
        assert isinstance(inventory_data, dict)
        inventory = SemibatchInventory(**inventory_data)
        total_polymer += float(result["polymer_increment_mol"])
        maximum_closure = max(maximum_closure, abs(float(result["molar_closure_residual"])))
        history.append({"step": index + 1, **inventory_data})
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "steps": steps,
        "final_inventory": history[-1],
        "history": history,
        "total_polymer_increment_mol": total_polymer,
        "maximum_abs_molar_closure_residual": maximum_closure,
    }


def _epdm_parameter_scan_scalar(scenarios: int = 1_000) -> object:
    temperatures = np.linspace(303.15, 353.15, scenarios)
    residence_times = np.linspace(30.0, 600.0, scenarios)
    active_sites = np.linspace(0.0004, 0.0016, scenarios)
    multipliers = np.linspace(0.75, 1.25, scenarios)
    parameters = _reference_epdm_parameters()
    energies = _reference_epdm_energies()
    rows: list[dict[str, object]] = []
    for temperature, residence, active_site, multiplier in zip(
        temperatures, residence_times, active_sites, multipliers, strict=True
    ):
        adjusted = temperature_adjusted_parameters(parameters, energies, float(temperature))
        scenario_parameters = EpdmKineticParameters(
            adjusted.kp_e_L_mol_s * float(multiplier),
            adjusted.kp_p_L_mol_s * float(multiplier),
            adjusted.kp_d_L_mol_s * float(multiplier),
            adjusted.k_transfer_s,
            adjusted.k_deactivation_s,
            adjusted.k_poison_L_mol_s,
        )
        conversions = pseudo_first_order_conversions(
            _reference_epdm_state(float(active_site)),
            scenario_parameters,
            float(residence),
        )
        rows.append(
            {
                "temperature_K": float(temperature),
                "residence_time_s": float(residence),
                "active_site_mol_L": float(active_site),
                "propagation_multiplier": float(multiplier),
                "conversions": conversions,
            }
        )
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "scenario_count": scenarios,
        "shape": [scenarios],
        "scenarios": rows,
    }


def _reference_poe_initial() -> KineticState:
    return KineticState(monomer_a=1.2, monomer_b=0.8, dormant_sites=0.01)


def _reference_poe_parameters() -> KineticParameters:
    return KineticParameters(
        k_init=0.002,
        k_prop_a=0.08,
        k_prop_b=0.05,
        k_transfer=0.003,
        k_deactivation=0.0005,
    )


def _poe_rk4_case(steps: int) -> object:
    duration = 20.0 if steps == 400 else 100.0
    return simulate_kinetics(
        _reference_poe_initial(),
        _reference_poe_parameters(),
        duration_s=duration,
        step_s=duration / steps,
    )


def _poe_jacobian_case() -> object:
    observations = np.linspace(0.0, 20.0, 200)

    def model(parameters: np.ndarray) -> np.ndarray:
        k1, k2, k3, k4, k5, k6, k7, k8 = parameters
        return (
            k1 * np.exp(-k2 * observations)
            + k3 * observations
            + k4 * observations**2
            + k5 * np.sin(k6 * observations)
            + k7 * np.cos(k8 * observations)
        )

    jacobian = finite_difference_jacobian(
        model,
        [1.0, 0.2, 0.1, 0.01, 0.5, 0.3, 0.4, 0.2],
    )
    return {
        "jacobian": jacobian,
        "identifiability": assess_identifiability(jacobian),
    }


def _poe_one_parameter_fit_case() -> object:
    times = np.linspace(0.0, 20.0, 401)
    observed = 1.0 - np.exp(-0.2 * times)
    return fit_first_order_rate(times, observed, lower_s=0.01, upper_s=1.0)


def _poe_dynamic_10k_case() -> object:
    times = np.linspace(0.0, 200.0, 10_000)
    response = fopdt_response(
        times,
        gain=2.0,
        time_constant_s=12.0,
        dead_time_s=3.0,
    )
    return {
        "response": response,
        "metrics": response_metrics(times, response, target=2.0),
    }


def _synthetic_process_package(equipment_count: int) -> dict[str, object]:
    streams: list[dict[str, object]] = []
    equipment: list[dict[str, object]] = []
    for index in range(equipment_count):
        equipment_id = f"E-{index:05d}"
        inlet = f"S-{index:05d}-IN"
        outlet = f"S-{index:05d}-OUT"
        streams.extend(
            [
                {
                    "stream_id": inlet,
                    "source": "BOUNDARY_IN",
                    "destination": equipment_id,
                    "total_mass_kg_h": 100.0,
                    "enthalpy_kW": 25.0,
                    "composition": {"A": 0.7, "B": 0.3},
                    "evidence_ids": ["EV-1"],
                },
                {
                    "stream_id": outlet,
                    "source": equipment_id,
                    "destination": "BOUNDARY_OUT",
                    "total_mass_kg_h": 100.0,
                    "enthalpy_kW": 25.0,
                    "composition": {"A": 0.7, "B": 0.3},
                    "evidence_ids": ["EV-1"],
                },
            ]
        )
        equipment.append(
            {
                "equipment_id": equipment_id,
                "inlet_stream_ids": [inlet],
                "outlet_stream_ids": [outlet],
                "duty_kW": 0.0,
                "design_status": "PASS",
            }
        )
    return {
        "package_id": "PERFORMANCE-SYNTHETIC",
        "process_family": "generic continuous process",
        "status": "NOT_EVALUATED",
        "tolerances": {"composition_abs": 1e-9, "mass_relative": 1e-9, "energy_relative": 1e-9},
        "design_basis": {
            "basis_version": "PERFORMANCE-FIXTURE",
            "capacity_kg_h": 100.0 * equipment_count,
            "operating_hours_h_y": 8_000.0,
            "components": ["A", "B"],
        },
        "streams": streams,
        "equipment": equipment,
        "utilities": [{"utility_id": "U-1", "consumption": 0.0, "unit": "kW"}],
        "controls": [
            {
                "loop_id": "LIC-1",
                "controlled_variable": "level",
                "manipulated_variable": "outlet flow",
                "measurement_tag": "LT-1",
                "final_element_tag": "LV-1",
                "status": "PASS",
            }
        ],
        "hse": [{"hazard_id": "HZ-1", "safeguards": ["independent trip"], "status": "PASS"}],
        "evidence_ledger": [
            {
                "evidence_id": "EV-1",
                "status": "QUALIFIED",
                "locator": "synthetic performance fixture",
                "applicability": "software benchmark only",
            }
        ],
        "acceptance": [
            {
                "criterion_id": "AC-1",
                "status": "PASS",
                "evidence_ids": ["EV-1"],
                "approver": "Performance Fixture",
            }
        ],
        "approvals": {
            "package_approver": "Performance Fixture",
            "process": "Performance Fixture",
            "controls": "Performance Fixture",
            "hse": "Performance Fixture",
        },
    }


def _prepare_provenance_fixture(root: Path, file_count: int) -> Callable[[], object]:
    for index in range(file_count):
        path = root / "sources" / f"group-{index % 20:02d}" / f"file-{index:05d}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((f"record={index}\n" + "0123456789abcdef" * 128), encoding="utf-8")
    target = root / "reports/SOURCE_CORE_MANIFEST.tsv"

    def exercise() -> object:
        count = build_manifest(root, target)
        issues = verify_manifest(root, target)
        return {"rows": count, "issues": issues}

    return exercise


def run_benchmarks(*, repeats: int, wheel_dir: Path | None = None) -> dict[str, object]:
    package_500 = _synthetic_process_package(500)
    package_5000 = _synthetic_process_package(5_000)
    with tempfile.TemporaryDirectory(prefix="tsao-performance-") as temporary:
        temporary_root = Path(temporary)
        provenance_300 = _prepare_provenance_fixture(temporary_root / "p300", 300)
        provenance_3000 = _prepare_provenance_fixture(temporary_root / "p3000", 3_000)
        cases: list[BenchmarkCase] = [
            BenchmarkCase(
                "epdm_three_level_64_site_families", lambda: _epdm_suite_case(64), 100, 20
            ),
            BenchmarkCase(
                "epdm_three_level_512_site_families", lambda: _epdm_suite_case(512), 10, 2
            ),
            BenchmarkCase(
                "epdm_semibatch_material_energy_step", _epdm_semibatch_step_case, 500, 50
            ),
            BenchmarkCase(
                "epdm_semibatch_10000_steps",
                _epdm_semibatch_trajectory_scalar,
                1,
                1,
                warmups=1,
                repeat_override=3,
            ),
            BenchmarkCase(
                "epdm_parameter_scan_1000_scalar",
                _epdm_parameter_scan_scalar,
                1,
                1,
                warmups=1,
                repeat_override=3,
            ),
            BenchmarkCase("poe_rk4_400_steps", lambda: _poe_rk4_case(400), 3, 1),
            BenchmarkCase(
                "poe_rk4_10000_steps",
                lambda: _poe_rk4_case(10_000),
                1,
                1,
                warmups=1,
                repeat_override=3,
            ),
            BenchmarkCase("poe_finite_difference_jacobian_8x200", _poe_jacobian_case, 20, 2),
            BenchmarkCase("poe_one_parameter_fit_401_points", _poe_one_parameter_fit_case, 20, 2),
            BenchmarkCase("poe_dynamic_response_10000_points", _poe_dynamic_10k_case, 20, 2),
            BenchmarkCase(
                "process_package_500_equipment",
                lambda: validate_process_package(package_500),
                4,
                1,
                digest_projection=_process_package_digest_projection,
            ),
            BenchmarkCase(
                "process_package_5000_equipment",
                lambda: validate_process_package(package_5000),
                1,
                1,
                warmups=1,
                repeat_override=3,
                digest_projection=_process_package_digest_projection,
            ),
            BenchmarkCase("provenance_300_files_build_and_verify", provenance_300, 2, 1),
            BenchmarkCase(
                "provenance_3000_files_build_and_verify",
                provenance_3000,
                1,
                1,
                warmups=1,
                repeat_override=3,
            ),
            BenchmarkCase(
                "doctor_core_repository",
                lambda: diagnose(ROOT, profile="core"),
                1,
                1,
                warmups=1,
                repeat_override=3,
            ),
            BenchmarkCase("skillpack_inventory", lambda: skillpack_inventory(ROOT), 10, 2),
        ]
        wheels = sorted(wheel_dir.glob("*.whl")) if wheel_dir and wheel_dir.is_dir() else []
        if len(wheels) == 1:
            cases.append(
                BenchmarkCase("wheel_content_verification", lambda: verify_wheel(wheels[0]), 3, 1)
            )
        results = [_measure(case, repeats=repeats) for case in cases]
    return {
        "schema": "TSAO-PERFORMANCE-2",
        "version": __version__,
        "source_commit": _source_commit(),
        "python": sys.version,
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "cpu": _cpu_description(),
        "repeats_default": repeats,
        "benchmark_count": len(results),
        "benchmarks": results,
        "qualification_scope": "SOFTWARE_PERFORMANCE_ONLY",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark TSAO computational and verification hot paths"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--wheel-dir", type=Path)
    args = parser.parse_args(argv)
    if args.repeats < 3:
        raise ValueError("repeats must be at least 3")
    report = run_benchmarks(repeats=args.repeats, wheel_dir=args.wheel_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
