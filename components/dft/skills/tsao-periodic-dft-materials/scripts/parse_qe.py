#!/usr/bin/env python3
"""Parse Quantum ESPRESSO pw.x output evidence with memory-mapped scans."""

from __future__ import annotations

import argparse
import json
import mmap
import re
from pathlib import Path

FLOAT = rb"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?"
RY_TO_EV = 13.605693122994
VERSION_RE = re.compile(rb"Program PWSCF v\.([\w.\-]+)")
ENERGY_RE = re.compile(rb"!\s+total energy\s+=\s*(" + FLOAT + rb")\s+Ry")
FERMI_RE = re.compile(rb"the Fermi energy is\s*(" + FLOAT + rb")\s*ev", re.IGNORECASE)
FORCE_RE = re.compile(rb"Total force =\s*(" + FLOAT + rb")")
PRESSURE_RE = re.compile(rb"P=\s*(" + FLOAT + rb")")


def scan_last(data: mmap.mmap, pattern: re.Pattern[bytes]) -> tuple[bytes | None, int]:
    value = None
    count = 0
    for match in pattern.finditer(data):
        value = match.group(1)
        count += 1
    return value, count


def _parse_legacy(path: Path) -> dict:
    done = False
    version = None
    last_energy = None
    energy_count = 0
    scf_converged = False
    ionic_converged = False
    last_fermi = None
    last_force = None
    last_pressure = None
    convergence_failed = False
    routine_error = False

    if path.stat().st_size:
        with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            done = data.find(b"JOB DONE.") >= 0
            scf_converged = data.find(b"convergence has been achieved") >= 0
            ionic_converged = (
                data.find(b"End of BFGS Geometry Optimization") >= 0
                or re.search(rb"bfgs converged in", data, re.IGNORECASE) is not None
            )
            convergence_failed = data.find(b"convergence NOT achieved") >= 0
            routine_error = data.find(b"Error in routine") >= 0

            if match := VERSION_RE.search(data):
                version = match.group(1).decode("ascii", errors="replace")
            value, energy_count = scan_last(data, ENERGY_RE)
            last_energy = float(value) if value is not None else None
            value, _ = scan_last(data, FERMI_RE)
            last_fermi = float(value) if value is not None else None
            value, _ = scan_last(data, FORCE_RE)
            last_force = float(value) if value is not None else None
            value, _ = scan_last(data, PRESSURE_RE)
            last_pressure = float(value) if value is not None else None

    warnings = []
    if convergence_failed:
        warnings.append("SCF convergence not achieved")
    if routine_error:
        warnings.append("QE Error in routine detected")

    status = (
        "RUN_FAILED"
        if not done
        else (
            "RELAX_VALIDATED_CANDIDATE"
            if scf_converged and ionic_converged
            else "STATIC_VALIDATED_CANDIDATE"
            if scf_converged
            else "COMPLETED_UNVALIDATED"
        )
    )
    return {
        "status": status,
        "job_done": done,
        "version": version,
        "last_total_energy_Ry": last_energy,
        "last_total_energy_eV": last_energy * RY_TO_EV if last_energy is not None else None,
        "energy_count": energy_count,
        "scf_converged": scf_converged,
        "ionic_converged": ionic_converged,
        "fermi_energy_eV": last_fermi,
        "last_total_force_Ry_per_bohr": last_force,
        "last_pressure_kbar": last_pressure,
        "warnings": warnings,
        "scientific_acceptance": "PENDING",
    }


def _canonical_parser_record(text: str):
    import importlib.util
    import sys

    contract = (
        Path(__file__).resolve().parents[2] / "tsao-dft-hpc-provenance" / "scripts" / "engine_parser_contract_v4.py"
    )
    spec = importlib.util.spec_from_file_location("tsao_engine_parser_contract_v4", contract)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {contract}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(contract.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.parse_engine_output("qe", text)


def parse(path: Path) -> dict:
    result = _parse_legacy(path)
    source = path
    if source.is_file() and source.stat().st_size:
        with source.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            text = mapped[:].decode("utf-8", errors="replace")
    else:
        text = ""
    decision = _canonical_parser_record(text)
    guarded = dict(result)
    guarded["parser_accepted"] = decision.parser_accepted
    guarded["parser_contract_status"] = decision.status
    guarded["parser_reason_codes"] = list(decision.reason_codes)
    guarded["parser_segment_count"] = len(decision.jobs)
    if not decision.parser_accepted:
        guarded["status"] = decision.status
        guarded["job_done"] = False
    return guarded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = parse(args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["parser_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
