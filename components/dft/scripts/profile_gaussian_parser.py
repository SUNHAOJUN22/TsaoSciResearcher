#!/usr/bin/env python3
"""Profile the Gaussian parser on deterministic synthetic logs without making speedup claims."""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import importlib.util
import json
import math
import pstats
import re
import statistics
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "skills/tsao-dft-researcher/scripts/parse_gaussian.py"
EVIDENCE_LABELS = ["SIMULATION_ONLY", "NOT_REAL_HARDWARE", "NOT_PERFORMANCE_EVIDENCE"]


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed <= 0 or str(parsed) != value.strip():
        raise argparse.ArgumentTypeError("value must be a positive exact integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed < 0 or str(parsed) != value.strip():
        raise argparse.ArgumentTypeError("value must be a non-negative exact integer")
    return parsed


def load_parser() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_gaussian_profile_target", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def orientation_block(atoms: int, offset: float) -> list[str]:
    lines = [
        " Standard orientation:",
        " ---------------------------------------------------------------------",
        " Center     Atomic      Atomic             Coordinates (Angstroms)",
        " Number     Number       Type             X           Y           Z",
        " ---------------------------------------------------------------------",
    ]
    for index in range(1, atoms + 1):
        atomic_number = 6 if index % 3 else 8
        x = offset + index * 0.01
        y = index * -0.02
        z = index * 0.03
        lines.append(f" {index:6d} {atomic_number:10d} {0:11d} {x:12.6f} {y:11.6f} {z:11.6f}")
    lines.append(" ---------------------------------------------------------------------")
    return lines


def build_synthetic_log(blocks: int, atoms: int, filler_lines: int) -> str:
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks <= 0:
        raise ValueError("blocks must be a positive exact integer")
    if isinstance(atoms, bool) or not isinstance(atoms, int) or atoms <= 0:
        raise ValueError("atoms must be a positive exact integer")
    if isinstance(filler_lines, bool) or not isinstance(filler_lines, int) or filler_lines < 0:
        raise ValueError("filler_lines must be a non-negative exact integer")

    lines = [
        " Gaussian 16: EM64L-G16RevC.01 1-Jan-2019",
        " #p UB3LYP/6-31G(d) Opt=(TS,CalcFC) Freq Stable SCRF=(Solvent=Water)",
        "",
        " Synthetic Gaussian parser profile",
        "",
        " Charge = 0 Multiplicity = 2",
    ]
    for block in range(blocks):
        energy = -100.0 - block * 1.0e-5
        lines.extend(
            [
                f" SCF Done:  E(UB3LYP) =  {energy:.12f}     A.U. after   10 cycles",
                " Alpha  occ. eigenvalues -- -0.70000 -0.50000 -0.25000",
                " Alpha virt. eigenvalues --  0.05000  0.10000  0.20000",
                " S**2 before annihilation     0.7600, after     0.7510",
                " Maximum Force            0.000100     0.000450     YES",
                " RMS     Force            0.000080     0.000300     YES",
                " Maximum Displacement     0.000900     0.001800     YES",
                " RMS     Displacement     0.000700     0.001200     YES",
            ]
        )
        lines.extend(orientation_block(atoms, block * 0.001))
        if block == blocks - 1:
            lines.append(" Frequencies --   -500.0000   120.0000   240.0000")
        else:
            lines.append(" Frequencies --    100.0000   200.0000   300.0000")
        for filler in range(filler_lines):
            lines.append(f" Synthetic filler block={block:06d} line={filler:04d} value={(block + filler) % 97:02d}")

    lines.extend(
        [
            " Optimization completed.",
            " Stationary point found.",
            " Zero-point correction=                           0.123456 (Hartree/Particle)",
            " Thermal correction to Energy=                    0.130000",
            " Thermal correction to Enthalpy=                  0.131000",
            " Thermal correction to Gibbs Free Energy=         0.100000",
            " Sum of electronic and zero-point Energies=     -100.500000",
            " Sum of electronic and thermal Energies=        -100.493456",
            " Sum of electronic and thermal Enthalpies=      -100.492456",
            " Sum of electronic and thermal Free Energies=   -100.523456",
            " Temperature   298.150 Kelvin.  Pressure   1.00000 Atm.",
            " Dipole moment (field-independent basis, Debye):",
            "    X=              0.1000    Y=             -0.2000    Z=              0.3000  Tot=              0.3742",
            "     1  C   Isotropic =   120.0000   Anisotropy =    30.0000",
            "     2  O   Isotropic =   220.0000   Anisotropy =    40.0000",
            " Excited State   1:      Singlet-A      3.0000 eV  413.28 nm  f=0.1000",
            "      3 -> 4        0.70000",
            "",
            " Point Number   1 in FORWARD path direction.",
            " Point Number   1 in REVERSE path direction.",
            " Calculation of FORWARD path complete.",
            " Calculation of REVERSE path complete.",
            " The wavefunction is stable under the perturbations considered.",
            " Normal termination of Gaussian 16",
        ]
    )
    return "\n".join(lines) + "\n"


def canonical_result_sha256(result: dict[str, Any]) -> str:
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def top_cumulative_functions(profile: cProfile.Profile, limit: int = 12) -> list[dict[str, Any]]:
    stats = pstats.Stats(profile)
    stats_data = vars(stats).get("stats", {})
    rows: list[tuple[float, int, str]] = []
    for (filename, line_number, function_name), (_, total_calls, _, cumulative_seconds, _) in stats_data.items():
        rows.append((cumulative_seconds, total_calls, f"{Path(filename).name}:{line_number}:{function_name}"))
    rows.sort(key=lambda item: (-item[0], item[2]))
    return [
        {
            "function": function_name,
            "calls": calls,
            "cumulative_seconds": cumulative_seconds,
        }
        for cumulative_seconds, calls, function_name in rows[:limit]
    ]


def legacy_error_taxonomy(parser: Any, text: str) -> list[dict[str, str]]:
    return [
        {"category": category, "evidence_pattern": pattern}
        for category, pattern in parser.ERROR_TAXONOMY_RULES
        if re.search(pattern, text, re.IGNORECASE)
    ]


def _measure_call(function: Callable[[], list[dict[str, str]]]) -> tuple[list[dict[str, str]], float]:
    started = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - started
    if not math.isfinite(elapsed) or elapsed < 0:
        raise RuntimeError("non-finite Gaussian taxonomy timing")
    return result, elapsed


def compare_taxonomy_algorithms(parser: Any, text: str, iterations: int) -> dict[str, Any]:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("taxonomy iterations must be a positive exact integer")

    def legacy_call() -> list[dict[str, str]]:
        return legacy_error_taxonomy(parser, text)

    def current_call() -> list[dict[str, str]]:
        return parser._error_taxonomy(text)

    legacy_seconds: list[float] = []
    current_seconds: list[float] = []
    for index in range(iterations):
        calls: list[tuple[Callable[[], list[dict[str, str]]], list[float]]] = [
            (legacy_call, legacy_seconds),
            (current_call, current_seconds),
        ]
        if index % 2:
            calls.reverse()
        results: list[list[dict[str, str]]] = []
        for function, timings in calls:
            result, elapsed = _measure_call(function)
            results.append(result)
            timings.append(elapsed)
        if results[0] != results[1]:
            raise RuntimeError("Gaussian taxonomy algorithms are not equivalent")

    legacy_median = statistics.median(legacy_seconds)
    current_median = statistics.median(current_seconds)
    if not math.isfinite(legacy_median) or legacy_median < 0:
        raise RuntimeError("non-finite legacy Gaussian taxonomy median")
    if not math.isfinite(current_median) or current_median < 0:
        raise RuntimeError("non-finite current Gaussian taxonomy median")
    ratio = legacy_median / current_median if current_median > 0 else None
    return {
        "iterations": iterations,
        "equivalent": True,
        "legacy_median_seconds": legacy_median,
        "current_median_seconds": current_median,
        "observed_legacy_over_current_ratio": ratio,
        "all_legacy_seconds": legacy_seconds,
        "all_current_seconds": current_seconds,
    }


def profile_parser(blocks: int, atoms: int, filler_lines: int, iterations: int) -> dict[str, Any]:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("iterations must be a positive exact integer")
    parser = load_parser()
    text = build_synthetic_log(blocks, atoms, filler_lines)
    expected = parser.parse_log(text)
    expected_hash = canonical_result_sha256(expected)

    elapsed: list[float] = []
    peaks: list[float] = []
    for _ in range(iterations):
        tracemalloc.start()
        started = time.perf_counter()
        result = parser.parse_log(text)
        elapsed_value = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if canonical_result_sha256(result) != expected_hash:
            raise RuntimeError("Gaussian parser output changed between identical profile iterations")
        elapsed.append(elapsed_value)
        peaks.append(peak / (1024 * 1024))

    profiler = cProfile.Profile()
    profiler.enable()
    profiled = parser.parse_log(text)
    profiler.disable()
    if canonical_result_sha256(profiled) != expected_hash:
        raise RuntimeError("cProfile execution changed Gaussian parser output")

    median_seconds = statistics.median(elapsed)
    median_peak_mib = statistics.median(peaks)
    if not math.isfinite(median_seconds) or median_seconds < 0:
        raise RuntimeError("non-finite Gaussian parser timing")
    if not math.isfinite(median_peak_mib) or median_peak_mib < 0:
        raise RuntimeError("non-finite Gaussian parser memory measurement")

    taxonomy_comparison = compare_taxonomy_algorithms(parser, text, max(5, iterations))
    return {
        "schema_version": "1.1",
        "scope": "gaussian_parser_synthetic_repository_microprofile",
        "labels": list(EVIDENCE_LABELS),
        "external_dft_engine_invoked": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "performance_qualification": "NOT_ELIGIBLE",
        "workload": {
            "blocks": blocks,
            "atoms_per_orientation": atoms,
            "filler_lines_per_block": filler_lines,
            "iterations": iterations,
            "input_bytes": len(text.encode("utf-8")),
            "input_lines": text.count("\n"),
            "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "parser_result": {
            "status": expected["status"],
            "normal_termination": expected["normal_termination"],
            "scf_energy_count": expected["scf_energy_count"],
            "frequency_count": expected["frequency_count"],
            "orientation_block_count": expected["orientation_block_count"],
            "result_sha256": expected_hash,
        },
        "measurement": {
            "median_seconds": median_seconds,
            "median_peak_mib": median_peak_mib,
            "all_seconds": elapsed,
            "all_peak_mib": peaks,
            "top_cumulative_functions": top_cumulative_functions(profiler),
        },
        "taxonomy_comparison": taxonomy_comparison,
        "limitations": [
            "The input is deterministic synthetic text rather than a Gaussian-produced log.",
            "Hosted CI timing is not target-workstation, HPC-cluster, GPU, or external-engine performance evidence.",
            "The result may identify parser hotspots but cannot establish end-to-end DFT acceleration.",
            "The observed taxonomy ratio is a same-process micro-observation and is not a product performance claim.",
        ],
    }


def write_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    try:
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blocks", type=positive_int, default=200)
    parser.add_argument("--atoms", type=positive_int, default=24)
    parser.add_argument("--filler-lines", type=nonnegative_int, default=24)
    parser.add_argument("--iterations", type=positive_int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = profile_parser(args.blocks, args.atoms, args.filler_lines, args.iterations)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        write_atomic(args.out, rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
