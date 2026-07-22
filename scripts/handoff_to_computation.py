#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, load_data, write_json


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--input")
    p.add_argument("--question")
    p.add_argument("--property")
    p.add_argument(
        "--scale",
        choices=["electronic", "atomistic", "mesoscale", "continuum", "device", "process", "multiscale"],
    )
    p.add_argument("--method", action="append", default=[])
    p.add_argument("--expected-output", action="append", default=[])
    a = p.parse_args()
    try:
        if a.input:
            data = load_data(a.input)
        else:
            data = {
                "schema_version": "1.0",
                "handoff_id": "COMP-001",
                "scientific_question": a.question or "TO BE SPECIFIED",
                "target_property": a.property or "TO BE SPECIFIED",
                "scale": a.scale or "multiscale",
                "candidate_methods": a.method or ["method selection required"],
                "inputs": [],
                "boundary_conditions": [],
                "initial_conditions": [],
                "parameter_sources": [],
                "convergence_checks": ["method-appropriate convergence study required"],
                "uncertainty_analysis": ["identify parameter and model-form uncertainty"],
                "expected_outputs": a.expected_output or ["validated result artifact"],
                "acceptance_criteria": [
                    "numerical convergence",
                    "physical consistency",
                    "answers the scientific question",
                ],
                "evidence_level": "planned",
                "human_approval_points": ["approve method and assumptions before expensive execution"],
            }
        schema = load_data(ROOT / "schemas/computation-handoff.schema.json")
        jsonschema.Draft202012Validator(schema).validate(data)
        write_json(a.out, data)
        print(a.out)
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
