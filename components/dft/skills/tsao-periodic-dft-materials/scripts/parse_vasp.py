#!/usr/bin/env python3
"""Parse VASP output evidence from OUTCAR/OSZICAR without scientific overclaiming."""

from __future__ import annotations

import argparse
import json
import math
import mmap
import re
from pathlib import Path

FLOAT = rb"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?"
VERSION_RE = re.compile(rb"vasp\.([\d.]+)", re.IGNORECASE)
ENERGY_RE = re.compile(rb"free\s+energy\s+TOTEN\s*=\s*(" + FLOAT + rb")\s+eV", re.IGNORECASE)
FERMI_RE = re.compile(rb"E-fermi\s*:\s*(" + FLOAT + rb")", re.IGNORECASE)
NIONS_RE = re.compile(rb"NIONS\s*=\s*(\d+)")
ELAPSED_RE = re.compile(rb"Elapsed time \(sec\):\s*(" + FLOAT + rb")")
WARNING_PATTERNS = (
    (re.compile(rb"BRMIX: very serious problems", re.IGNORECASE), "BRMIX mixing problem"),
    (re.compile(rb"ZBRENT: fatal error", re.IGNORECASE), "ZBRENT ionic optimization error"),
    (
        re.compile(rb"WARNING: Sub-Space-Matrix is not hermitian", re.IGNORECASE),
        "subspace matrix warning",
    ),
    (re.compile(rb"EDDDAV: Call to ZHEGV failed", re.IGNORECASE), "diagonalization failure"),
)


def scan_last(data: mmap.mmap, pattern: re.Pattern[bytes]) -> tuple[bytes | None, int]:
    value = None
    count = 0
    for match in pattern.finditer(data):
        value = match.group(1)
        count += 1
    return value, count


def last_match(data: mmap.mmap, marker: bytes, pattern: re.Pattern[bytes], window: int = 512):
    position = data.rfind(marker)
    if position < 0:
        return None
    match = pattern.search(data, position, min(len(data), position + window))
    return match.group(1) if match else None


def _parse_legacy(path: Path) -> dict:
    run = path if path.is_dir() else path.parent
    out = run / "OUTCAR" if path.is_dir() else path

    normal = False
    version = None
    last_energy = None
    energy_count = 0
    last_fermi = None
    nions = None
    electronic_converged = False
    ionic_converged = False
    max_force = None
    elapsed = None
    warnings: list[str] = []

    if out.exists() and out.stat().st_size:
        with out.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            normal = data.find(b"General timing and accounting informations for this job") >= 0
            electronic_converged = (
                data.find(b"aborting loop because EDIFF is reached") >= 0 or data.find(b"EDIFF is reached") >= 0
            )
            ionic_converged = data.find(b"reached required accuracy - stopping structural energy minimisation") >= 0

            if match := VERSION_RE.search(data):
                version = match.group(1).decode("ascii", errors="replace")
            value, energy_count = scan_last(data, ENERGY_RE)
            if value is not None:
                last_energy = float(value)
            if value := last_match(data, b"E-fermi", FERMI_RE):
                last_fermi = float(value)
            if value := last_match(data, b"NIONS", NIONS_RE):
                nions = int(value)
            if value := last_match(data, b"Elapsed time (sec):", ELAPSED_RE):
                elapsed = float(value)

            for pattern, message in WARNING_PATTERNS:
                if pattern.search(data):
                    warnings.append(message)

            force_start = data.rfind(b"TOTAL-FORCE (eV/Angst)")
            if force_start >= 0:
                force_end = data.find(b"total drift", force_start)
                if force_end < 0:
                    force_end = len(data)
                values = []
                for line in data[force_start:force_end].splitlines():
                    fields = line.split()
                    if len(fields) < 6:
                        continue
                    try:
                        fx, fy, fz = (float(value) for value in fields[-3:])
                    except ValueError:
                        continue
                    values.append(math.sqrt(fx * fx + fy * fy + fz * fz))
                max_force = max(values) if values else None

    status = "RUN_FAILED" if not out.exists() or not out.stat().st_size else "COMPLETED_UNVALIDATED"
    if normal and electronic_converged:
        status = "STATIC_VALIDATED_CANDIDATE"
    if normal and electronic_converged and ionic_converged:
        status = "RELAX_VALIDATED_CANDIDATE"
    if normal and not electronic_converged:
        warnings.append("VASP ended but electronic convergence marker was not found")

    return {
        "status": status,
        "normal_termination": normal,
        "version": version,
        "last_toten_eV": last_energy,
        "energy_count": energy_count,
        "fermi_energy_eV": last_fermi,
        "nions": nions,
        "electronic_converged": electronic_converged,
        "ionic_converged": ionic_converged,
        "max_force_eV_per_angstrom": max_force,
        "elapsed_seconds": elapsed,
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
    return module.parse_engine_output("vasp", text)


def parse(path: Path) -> dict:
    result = _parse_legacy(path)
    source = path / "OUTCAR" if path.is_dir() else path
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
        guarded["normal_termination"] = False
    return guarded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    result = parse(args.path)
    print(json.dumps(result, indent=2))
    return 0 if result["parser_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
