#!/usr/bin/env python3
"""Parse CP2K output evidence with memory-mapped scans."""

from __future__ import annotations

import argparse
import json
import mmap
import re
from pathlib import Path

FLOAT = rb"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?"
HARTREE_TO_EV = 27.211386245988
VERSION_RE = re.compile(rb"CP2K\| version string:\s*(.+)")
ENERGY_RE = re.compile(rb"ENERGY\| Total FORCE_EVAL.*?energy \(a\.u\.\):\s*(" + FLOAT + rb")")
MAX_GRADIENT_RE = re.compile(rb"Max\. gradient\s*=\s*(" + FLOAT + rb")")


def scan_last(data: mmap.mmap, pattern: re.Pattern[bytes]) -> tuple[bytes | None, int]:
    value = None
    count = 0
    for match in pattern.finditer(data):
        value = match.group(1)
        count += 1
    return value, count


def _parse_legacy(path: Path) -> dict:
    ended = False
    version = None
    last_energy = None
    energy_count = 0
    scf_converged = False
    geo_converged = False
    last_max_gradient = None
    scf_failed = False
    abort_detected = False

    if path.stat().st_size:
        with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            ended = data.find(b"PROGRAM ENDED AT") >= 0
            scf_converged = data.find(b"SCF run converged") >= 0
            geo_converged = (
                data.find(b"GEOMETRY OPTIMIZATION COMPLETED") >= 0
                or data.find(b"Reevaluating energy at the minimum") >= 0
            )
            scf_failed = data.find(b"SCF run NOT converged") >= 0
            abort_detected = data.find(b"ABORT") >= 0

            if match := VERSION_RE.search(data):
                version = match.group(1).decode("utf-8", errors="replace").strip()
            value, energy_count = scan_last(data, ENERGY_RE)
            last_energy = float(value) if value is not None else None
            value, _ = scan_last(data, MAX_GRADIENT_RE)
            last_max_gradient = float(value) if value is not None else None

    warnings = []
    if scf_failed:
        warnings.append("SCF not converged")
    if abort_detected:
        warnings.append("CP2K abort detected")

    status = (
        "RUN_FAILED"
        if not ended
        else (
            "RELAX_VALIDATED_CANDIDATE"
            if scf_converged and geo_converged
            else "STATIC_VALIDATED_CANDIDATE"
            if scf_converged
            else "COMPLETED_UNVALIDATED"
        )
    )
    return {
        "status": status,
        "program_ended": ended,
        "version": version,
        "last_total_energy_hartree": last_energy,
        "last_total_energy_eV": last_energy * HARTREE_TO_EV if last_energy is not None else None,
        "energy_count": energy_count,
        "scf_converged": scf_converged,
        "geometry_converged": geo_converged,
        "last_max_gradient": last_max_gradient,
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
    return module.parse_engine_output("cp2k", text)


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
        guarded["program_ended"] = False
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
