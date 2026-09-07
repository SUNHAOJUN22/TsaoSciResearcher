#!/usr/bin/env python3
"""Unified fail-closed parser state machines for Gaussian, VASP, QE and CP2K."""

from __future__ import annotations

import importlib.util
import math
import mmap
import re
import sys
from pathlib import Path
from typing import Any

PARSER_VERSION = "1.1"
HARTREE_TO_EV = 27.211386245988
RY_TO_EV = 13.605693122994
RY_BOHR_TO_EV_ANGSTROM = 25.71104309541616
KBAR_TO_GPA = 0.1
FLOAT = rb"[-+]?\d*\.?\d+(?:[DEde][-+]?\d+)?"


def _load_scan_core() -> Any:
    path = Path(__file__).with_name("engine_scan_core.py")
    spec = importlib.util.spec_from_file_location("tsao_engine_scan_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_SCAN = _load_scan_core()

GAUSSIAN_VERSION_RE = re.compile(rb"Gaussian\s+(?:16[:,]?\s*)?.*?Revision\s+([A-Z0-9.]+)", re.IGNORECASE)
GAUSSIAN_SCF_RE = re.compile(rb"SCF Done:\s+E\([^)]*\)\s*=\s*(" + FLOAT + rb")")
GAUSSIAN_FREQUENCY_RE = re.compile(rb"Frequencies --\s+([^\r\n]+)")
VASP_VERSION_RE = re.compile(rb"vasp\.([\d.]+)", re.IGNORECASE)
VASP_ENERGY_RE = re.compile(rb"free\s+energy\s+TOTEN\s*=\s*(" + FLOAT + rb")\s+eV", re.IGNORECASE)
VASP_ELAPSED_RE = re.compile(rb"Elapsed time \(sec\):\s*(" + FLOAT + rb")")
QE_VERSION_RE = re.compile(rb"Program PWSCF v\.([\w.\-]+)")
QE_ENERGY_RE = re.compile(rb"!\s+total energy\s+=\s*(" + FLOAT + rb")\s+Ry")
QE_FORCE_RE = re.compile(rb"Total force =\s*(" + FLOAT + rb")")
QE_PRESSURE_RE = re.compile(rb"P=\s*(" + FLOAT + rb")")
CP2K_VERSION_RE = re.compile(rb"CP2K\| version string:\s*([^\r\n]+)")
CP2K_ENERGY_RE = re.compile(rb"ENERGY\| Total FORCE_EVAL.*?energy \(a\.u\.\):\s*(" + FLOAT + rb")")
CP2K_GRADIENT_RE = re.compile(rb"Max\. gradient\s*=\s*(" + FLOAT + rb")")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compatibility entry point for the shared bounded artifact hasher."""

    return _SCAN.sha256_file(path, chunk_size=chunk_size)


def base_result(engine: str, path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "engine": engine,
        "engine_version": None,
        "parser_version": PARSER_VERSION,
        "source_artifact": {"path": path.name, "sha256": None},
        "normal_termination": False,
        "fatal_marker": None,
        "electronic_converged": False,
        "geometry_converged": None,
        "parser_accepted": False,
        "parser_acceptance_reasons": [],
        "energy": {"value": None, "unit": "eV"},
        "forces": {"values": None, "unit": "eV/angstrom"},
        "stress": {"values": None, "unit": "GPa"},
        "scf_iterations": None,
        "elapsed_time_s": None,
        "warnings": [],
        "failed_stage": None,
        "scientific_acceptance": "PENDING",
        "job_index": None,
    }


def missing_result(engine: str, path: Path) -> dict[str, Any]:
    result = base_result(engine, path)
    result["fatal_marker"] = "SOURCE_MISSING"
    result["failed_stage"] = "input"
    result["parser_acceptance_reasons"] = ["source output is missing or empty"]
    return result


def _finalize(result: dict[str, Any], artifact: Any) -> dict[str, Any]:
    if isinstance(artifact, Path):
        digest = sha256_file(artifact) if artifact.is_file() else None
    else:
        digest = getattr(artifact, "sha256", None)
    result["source_artifact"]["sha256"] = digest
    result["parser_acceptance_reasons"] = sorted(set(result["parser_acceptance_reasons"]))
    result["warnings"] = sorted(set(result["warnings"]))
    return result


def _float(value: bytes) -> float:
    parsed = float(value.replace(b"D", b"E").replace(b"d", b"e"))
    if not math.isfinite(parsed):
        raise ValueError("engine output contains a non-finite numeric value")
    return parsed


def _numbers(text: bytes) -> list[float]:
    return [_float(value) for value in re.findall(FLOAT, text)]


def _parse_force_block(data: mmap.mmap, bounds: tuple[int, int] | None) -> list[float] | None:
    if bounds is None:
        return None
    vector: list[float] = []
    start, end = bounds
    for line in data[start:end].splitlines():
        fields = line.split()
        if len(fields) < 6:
            continue
        try:
            vector.extend(_float(value) for value in fields[-3:])
        except ValueError:
            continue
    return vector or None


def parse_gaussian(path: Path) -> dict[str, Any]:
    with _SCAN.mapped_artifact(path) as artifact:
        if artifact is None:
            return missing_result("gaussian", path)
        data = artifact.data
        final_start = data.rfind(b"Entering Link 1")
        final_start = 0 if final_start < 0 else final_start
        result = base_result("gaussian", path)
        result["job_index"] = _SCAN.count(data, b"Entering Link 1") + 1
        result["engine_version"] = _SCAN.decode(_SCAN.first_group(data, GAUSSIAN_VERSION_RE, start=final_start))
        normal = _SCAN.contains(data, b"Normal termination of Gaussian", start=final_start)
        error = _SCAN.contains(data, b"Error termination", start=final_start)
        result["normal_termination"] = normal and not error
        result["fatal_marker"] = "ERROR_TERMINATION" if error else None

        scf_values = _SCAN.all_groups(data, GAUSSIAN_SCF_RE, start=final_start)
        if scf_values:
            result["energy"]["value"] = _float(scf_values[-1]) * HARTREE_TO_EV
            result["electronic_converged"] = True
            result["scf_iterations"] = len(scf_values)

        final_lines = data[final_start:].splitlines()
        route = b" ".join(line.strip() for line in final_lines if line.lstrip().startswith(b"#"))
        frequencies: list[float] = []
        for value in _SCAN.all_groups(data, GAUSSIAN_FREQUENCY_RE, start=final_start):
            frequencies.extend(_numbers(value))
        imaginary = [value for value in frequencies if value < -1e-6]
        geometry = _SCAN.contains(data, b"Optimization completed", start=final_start) or _SCAN.contains(
            data,
            b"Stationary point found",
            start=final_start,
        )
        result["geometry_converged"] = geometry if b"opt" in route.lower() else None
        if error:
            result["failed_stage"] = "engine"
            result["parser_acceptance_reasons"].append("final Link1 job ended with error termination")
        elif not normal:
            result["failed_stage"] = "termination"
            result["parser_acceptance_reasons"].append("final Link1 job lacks normal termination")
        elif b"opt" in route.lower() and not geometry:
            result["failed_stage"] = "geometry"
            result["parser_acceptance_reasons"].append("optimization route lacks completion marker")
        elif b"freq" in route.lower() and len(imaginary) > 1:
            result["failed_stage"] = "scientific-gate"
            result["parser_acceptance_reasons"].append("frequency result is a higher-order saddle candidate")
        else:
            result["parser_accepted"] = True
            result["parser_acceptance_reasons"].append("final Link1 job passed termination and route-specific gates")
        if result["job_index"] > 1:
            result["warnings"].append("multiple Link1 jobs detected; only the final job determines acceptance")
        return _finalize(result, artifact)


def parse_vasp(path: Path) -> dict[str, Any]:
    with _SCAN.mapped_artifact(path) as artifact:
        if artifact is None:
            return missing_result("vasp", path)
        data = artifact.data
        result = base_result("vasp", path)
        result["engine_version"] = _SCAN.decode(_SCAN.first_group(data, VASP_VERSION_RE))
        fatal_rules = (
            ("BRMIX_FATAL", re.compile(rb"BRMIX: very serious problems", re.IGNORECASE)),
            ("ZBRENT_FATAL", re.compile(rb"ZBRENT: fatal error", re.IGNORECASE)),
            ("DIAGONALIZATION_FATAL", re.compile(rb"EDDDAV: Call to ZHEGV failed", re.IGNORECASE)),
            ("SUBSPACE_FATAL", re.compile(rb"Sub-Space-Matrix is not hermitian", re.IGNORECASE)),
        )
        for label, pattern in fatal_rules:
            if pattern.search(data):
                result["fatal_marker"] = label
                result["parser_acceptance_reasons"].append(f"fatal VASP marker detected: {label}")
                break
        normal = _SCAN.contains(data, b"General timing and accounting informations for this job")
        electronic = _SCAN.contains(data, b"EDIFF is reached") or _SCAN.contains(
            data,
            b"aborting loop because EDIFF is reached",
        )
        geometry = _SCAN.contains(
            data,
            b"reached required accuracy - stopping structural energy minimisation",
        )
        result["normal_termination"] = normal and result["fatal_marker"] is None
        result["electronic_converged"] = electronic
        result["geometry_converged"] = geometry
        energy, energy_count = _SCAN.last_group(data, VASP_ENERGY_RE)
        if energy is not None:
            result["energy"]["value"] = _float(energy)
            result["scf_iterations"] = energy_count
        elapsed, _ = _SCAN.last_group(data, VASP_ELAPSED_RE)
        result["elapsed_time_s"] = _float(elapsed) if elapsed is not None else None
        result["forces"]["values"] = _parse_force_block(
            data,
            _SCAN.last_block(data, b"TOTAL-FORCE (eV/Angst)", b"total drift"),
        )
        if result["fatal_marker"]:
            result["failed_stage"] = "engine"
        elif not normal:
            result["failed_stage"] = "termination"
            result["parser_acceptance_reasons"].append("VASP timing/accounting termination marker is missing")
        elif not electronic:
            result["failed_stage"] = "electronic"
            result["parser_acceptance_reasons"].append("electronic convergence marker is missing")
        else:
            result["parser_accepted"] = True
            result["parser_acceptance_reasons"].append("termination and electronic convergence gates passed")
        return _finalize(result, artifact)


def parse_qe(path: Path) -> dict[str, Any]:
    with _SCAN.mapped_artifact(path) as artifact:
        if artifact is None:
            return missing_result("quantum-espresso", path)
        data = artifact.data
        result = base_result("quantum-espresso", path)
        result["engine_version"] = _SCAN.decode(_SCAN.first_group(data, QE_VERSION_RE))
        routine_error = bool(re.search(rb"Error in routine", data, re.IGNORECASE))
        nonconverged = _SCAN.contains(data, b"convergence NOT achieved")
        done = _SCAN.contains(data, b"JOB DONE.")
        result["fatal_marker"] = "ERROR_IN_ROUTINE" if routine_error else "SCF_NOT_CONVERGED" if nonconverged else None
        result["normal_termination"] = done and result["fatal_marker"] is None
        result["electronic_converged"] = (
            _SCAN.contains(
                data,
                b"convergence has been achieved",
            )
            and not nonconverged
        )
        result["geometry_converged"] = _SCAN.contains(
            data,
            b"End of BFGS Geometry Optimization",
        ) or bool(re.search(rb"bfgs converged in", data, re.IGNORECASE))
        energy, energy_count = _SCAN.last_group(data, QE_ENERGY_RE)
        if energy is not None:
            result["energy"]["value"] = _float(energy) * RY_TO_EV
            result["scf_iterations"] = energy_count
        force, _ = _SCAN.last_group(data, QE_FORCE_RE)
        if force is not None:
            result["forces"]["values"] = [_float(force) * RY_BOHR_TO_EV_ANGSTROM]
        pressure, _ = _SCAN.last_group(data, QE_PRESSURE_RE)
        if pressure is not None:
            result["stress"]["values"] = [_float(pressure) * KBAR_TO_GPA]
        if result["fatal_marker"]:
            result["failed_stage"] = "engine" if routine_error else "electronic"
            result["parser_acceptance_reasons"].append(f"QE fatal marker detected: {result['fatal_marker']}")
        elif not done:
            result["failed_stage"] = "termination"
            result["parser_acceptance_reasons"].append("JOB DONE marker is missing")
        elif not result["electronic_converged"]:
            result["failed_stage"] = "electronic"
            result["parser_acceptance_reasons"].append("SCF convergence marker is missing")
        else:
            result["parser_accepted"] = True
            result["parser_acceptance_reasons"].append("termination and SCF gates passed")
        return _finalize(result, artifact)


def parse_cp2k(path: Path) -> dict[str, Any]:
    with _SCAN.mapped_artifact(path) as artifact:
        if artifact is None:
            return missing_result("cp2k", path)
        data = artifact.data
        result = base_result("cp2k", path)
        version = _SCAN.decode(_SCAN.first_group(data, CP2K_VERSION_RE))
        result["engine_version"] = version.strip() if version else None
        abort = bool(re.search(rb"\bABORT\b", data))
        nonconverged = _SCAN.contains(data, b"SCF run NOT converged")
        ended = _SCAN.contains(data, b"PROGRAM ENDED AT")
        result["fatal_marker"] = "ABORT" if abort else "SCF_NOT_CONVERGED" if nonconverged else None
        result["normal_termination"] = ended and result["fatal_marker"] is None
        result["electronic_converged"] = _SCAN.contains(data, b"SCF run converged") and not nonconverged
        result["geometry_converged"] = _SCAN.contains(
            data,
            b"GEOMETRY OPTIMIZATION COMPLETED",
        ) or _SCAN.contains(data, b"Reevaluating energy at the minimum")
        energy, energy_count = _SCAN.last_group(data, CP2K_ENERGY_RE)
        if energy is not None:
            result["energy"]["value"] = _float(energy) * HARTREE_TO_EV
            result["scf_iterations"] = energy_count
        gradient, _ = _SCAN.last_group(data, CP2K_GRADIENT_RE)
        if gradient is not None:
            result["forces"]["values"] = [_float(gradient) * HARTREE_TO_EV / 0.529177210903]
        if result["fatal_marker"]:
            result["failed_stage"] = "engine" if abort else "electronic"
            result["parser_acceptance_reasons"].append(f"CP2K fatal marker detected: {result['fatal_marker']}")
        elif not ended:
            result["failed_stage"] = "termination"
            result["parser_acceptance_reasons"].append("PROGRAM ENDED AT marker is missing")
        elif not result["electronic_converged"]:
            result["failed_stage"] = "electronic"
            result["parser_acceptance_reasons"].append("SCF convergence marker is missing")
        else:
            result["parser_accepted"] = True
            result["parser_acceptance_reasons"].append("termination and SCF gates passed")
        return _finalize(result, artifact)


def parse_engine_output(engine: str, path: Path) -> dict[str, Any]:
    routes = {
        "gaussian": parse_gaussian,
        "vasp": parse_vasp,
        "quantum-espresso": parse_qe,
        "cp2k": parse_cp2k,
    }
    if engine not in routes:
        raise ValueError(f"unsupported engine parser: {engine}")
    return routes[engine](path)
