#!/usr/bin/env python3
"""Validate periodic DFT project manifests with task-specific scientific gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ENGINES = {"vasp", "quantum-espresso", "cp2k"}
TASKS = {
    "relax",
    "cell-relax",
    "static",
    "band",
    "dos",
    "charge",
    "surface",
    "adsorption",
    "defect",
    "neb",
    "phonon",
    "elastic",
    "aimd",
}
STATUS = {
    "planned",
    "prepared",
    "preflight_passed",
    "running",
    "completed",
    "validated",
    "accepted",
    "rejected",
    "inconclusive",
}
LEVELS = {"L0_REFERENCE", "L1_HANDOFF", "L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def validate(d):
    e = []
    w = []
    for k in [
        "schema_version",
        "project_id",
        "engine",
        "engine_version",
        "support_level",
        "task_type",
        "structure_id",
        "structure_sha256",
        "method_fingerprint",
        "convergence",
        "validation_plan",
        "status",
    ]:
        if k not in d:
            e.append(f"missing {k}")
    if d.get("engine") not in ENGINES:
        e.append("unsupported engine")
    if d.get("task_type") not in TASKS:
        e.append("unsupported task_type")
    if d.get("status") not in STATUS:
        e.append("invalid status")
    if d.get("support_level") not in LEVELS:
        e.append("invalid support_level")
    if not SHA.match(str(d.get("structure_sha256", ""))):
        e.append("invalid structure_sha256")
    m = d.get("method_fingerprint") or {}
    required = [
        "xc",
        "dispersion",
        "basis_or_pseudopotential_family",
        "cutoff_or_grid_policy",
        "kpoint_or_supercell_policy",
        "smearing_or_occupations",
        "spin_and_u_policy",
        "electrostatics",
        "convergence_thresholds",
    ]
    for k in required:
        if m.get(k) in (None, "unknown"):
            w.append(f"method_fingerprint unresolved: {k}")
    conv = d.get("convergence") or {}
    if not conv.get("studies") and d.get("task_type") not in {"band", "dos", "charge"}:
        w.append("no convergence studies declared")
    val = d.get("validation_plan") or {}
    if not val.get("technical_checks"):
        e.append("validation_plan.technical_checks must not be empty")
    if not val.get("scientific_checks"):
        e.append("validation_plan.scientific_checks must not be empty")
    task = d.get("task_type")
    if task in {"band", "dos", "charge"} and not d.get("accepted_parent_artifact_ids"):
        e.append(f"{task} requires accepted parent SCF/static artifact")
    if task in {"surface", "adsorption", "defect", "neb"}:
        if not d.get("model_review_id"):
            e.append("surface/defect/path task requires model_review_id")
        pm = d.get("periodic_model") or {}
        for k in [
            "cell_or_supercell",
            "vacuum_policy",
            "termination_or_defect",
            "fixed_region_policy",
            "dipole_or_polarity_policy",
            "periodic_image_policy",
        ]:
            if not pm.get(k):
                e.append(f"periodic_model missing {k}")
    if task == "adsorption":
        expr = d.get("energy_expression") or {}
        if expr.get("formula") in (None, "unknown"):
            e.append("adsorption task requires explicit energy_expression.formula")
        refs = expr.get("reference_artifact_ids") or []
        if len(refs) < 2:
            e.append("adsorption energy requires clean-surface and adsorbate reference artifacts")
    if task == "defect":
        dm = d.get("defect_model") or {}
        for k in ["charge_states", "chemical_potential_policy", "finite_size_correction_policy"]:
            if dm.get(k) in (None, "unknown", []):
                e.append(f"defect_model missing {k}")
    if task == "neb":
        nm = d.get("neb_model") or {}
        for k in [
            "initial_artifact_id",
            "final_artifact_id",
            "image_count",
            "atom_order_mapping_id",
            "climbing_image_policy",
        ]:
            if nm.get(k) in (None, "unknown"):
                e.append(f"neb_model missing {k}")
        if nm.get("initial_artifact_id") == nm.get("final_artifact_id") and nm.get("initial_artifact_id"):
            e.append("NEB endpoints must be distinct")
    if task in {"phonon", "elastic"} and not d.get("accepted_parent_artifact_ids"):
        e.append(f"{task} requires accepted ground-state/relaxed parent")
    if d.get("status") in {"accepted", "validated"} and d.get("support_level") in {"L0_REFERENCE", "L1_HANDOFF"}:
        w.append("result status exceeds declared deterministic adapter support; record external validation evidence")
    if d.get("status") == "accepted" and (e or w):
        e.append("accepted project has unresolved errors/warnings")
    return e, w


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = yaml.safe_load(a.manifest.read_text()) or {}
    e, w = validate(d)
    r = {"ok": not e, "errors": e, "warnings": w}
    print(
        json.dumps(r, indent=2)
        if a.json
        else "\n".join(["PASS" if not e else "FAIL"] + [f"ERROR: {x}" for x in e] + [f"WARN: {x}" for x in w])
    )
    raise SystemExit(0 if not e else 1)


if __name__ == "__main__":
    main()
