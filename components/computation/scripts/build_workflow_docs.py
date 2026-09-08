from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADINGS = (
    "## Purpose",
    "## Entry questions",
    "## Core capabilities",
    "## Recommended adapters",
    "## Acceleration and placement",
    "## Preflight",
    "## State and gates",
    "## Failure handling",
    "## Multiscale handoff",
    "## Required outputs",
    "## Human approval",
)


def _load(path: Path) -> list[dict[str, Any]]:
    return list(json.loads(path.read_text(encoding="utf-8")))


def render_workflow(
    record: dict[str, Any],
    capability_map: dict[str, dict[str, Any]],
    accelerator_map: dict[str, dict[str, Any]],
) -> str:
    capability_lines = "\n".join(
        f"- `{identifier}` `{capability_map[identifier]['slug']}` — {capability_map[identifier]['name_en']}"
        for identifier in record["capability_ids"]
    )
    recommended = [str(item) for item in record.get("recommended_adapters", [])]
    adapters = (
        ", ".join(f"`{item}`" for item in recommended)
        or "No adapter is preselected; route by method fitness and lawful availability."
    )
    profiles = [accelerator_map[item] for item in recommended if item in accelerator_map]
    backends = sorted(
        {str(item) for profile in profiles for item in profile.get("candidate_backends", [])}
        or {"cpu", "task-parallel"}
    )
    libraries = sorted(
        {str(item) for profile in profiles for item in profile.get("library_candidates", [])}
    )
    edge_modes = sorted(
        {str(profile.get("edge_suitability", "unsuitable")) for profile in profiles}
    )
    gates = " → ".join(f"`{item}`" for item in record["required_gates"])
    keywords = ", ".join(f"`{item}`" for item in record.get("keywords", []))
    return f"""---
name: {record["slug"]}
description: {record["name_en"]} workflow with explicit contracts, preflight, convergence, physical validation, uncertainty, provenance, and fail-closed acceptance.
---

# {record["name_en"]}

## Purpose

Use this workflow for {record["name_en"].lower()} tasks after the root contract establishes the observable, scale, method, evidence, and resource boundary. Routing keywords include {keywords}.

## Entry questions

- What observable and decision must this workflow produce?
- Which system, scale, conditions, boundary/initial conditions, and reference state apply?
- What method and fidelity are justified, and what alternatives were rejected?
- What evidence, convergence study, validation target, uncertainty, and compute resources are available?
- Is the workload dominated by tensor algebra, dense/sparse linear algebra, FFT, particle/mesh work, independent cases, communication, I/O, training, inference, or control latency?
- Must execution occur at the edge, on a workstation, or through an HPC/cloud scheduler?

## Core capabilities

{capability_lines}

## Recommended adapters

{adapters}

Adapters are candidates, not availability claims. Probe before preparing native inputs.

## Acceleration and placement

- Candidate backends represented by recommended adapters: {", ".join(f"`{item}`" for item in backends)}.
- Candidate libraries: {", ".join(f"`{item}`" for item in libraries) if libraries else "None preselected; select only from a measured workload."}
- Edge-suitability classifications represented by recommended adapters: {", ".join(f"`{item}`" for item in edge_modes) if edge_modes else "No adapter-specific edge classification."}

Use the Python control plane for contracts, routing, validation, uncertainty, provenance, and acceptance. Prefer the professional solver's native OpenMP, MPI, CUDA, HIP, SYCL, OpenCL, or library backend before writing a new Tsao-owned kernel. Use task-parallel execution for independent cases, parameter sweeps, uncertainty ensembles, and process-model calibration. Add C++20, Kokkos, CUDA-X, cuTENSOR, cuEquivariance, nvmath-python, NCCL, TensorRT, RAPIDS, DLPack, or Arrow paths only for a measured hotspot and only as optional backends.

Run `python -m tsao_computation probe-accelerators` and create a plan with `python -m tsao_computation plan-acceleration <adapter>`. Detecting a GPU, compiler, runtime, or library is planning evidence only. Require a CPU or analytical reference, numerical-equivalence tolerances, precision and determinism policies, data-transfer and communication measurement, memory/VRAM limits, energy and thermal evidence, CPU fallback, and the unchanged scientific acceptance chain.

Edge placement should prioritize acquisition, preprocessing, validated surrogate inference, anomaly detection, bounded control, offline behavior, and escalation. Large DFT, MD, CFD, FEM, multiphysics, or training workloads normally move to a workstation or HPC target unless a measured contract proves otherwise.

## Preflight

Require a strict calculation contract; validate structures/files, syntax, units, conditions, parameter provenance, lawful software and data access, CPU/GPU resources, driver/runtime and solver build features, device/rank/thread binding, output locations, convergence plan, numerical-equivalence plan, validation plan, restart policy, energy/thermal boundaries, fallback, and human gates.

## State and gates

Expected gate order: {gates}. Preserve the distinction `completed ≠ parsed ≠ converged ≠ validated ≠ accepted`. Likewise, `GPU detected ≠ solver backend verified ≠ accelerated run completed ≠ speedup demonstrated ≠ scientifically accepted`.

## Failure handling

Classify environment, file, syntax, structure, unit, numerical, resource, MPI/GPU, device binding, precision, memory, transfer, communication, energy, thermal, queue, license, parser, conservation, and model-applicability failures. Retry only with a bounded, recorded scientific rationale and preserve the CPU fallback.

## Multiscale handoff

When data enters or leaves this workflow, record source, units, temperature/pressure/composition, reference state, transformation, array/tensor ownership, host/device location, precision, statistical error, model error, applicability, receiving model, and validation status.

## Required outputs

Calculation contract, environment and accelerator probe, acceleration plan, native inputs/outputs or explicit guidance-only status, method and hardware fingerprints, CPU/accelerated equivalence evidence, convergence evidence, physical checks, performance/memory/energy/thermal measurements, uncertainty/applicability statement, provenance manifest, failure/recovery log, fallback outcome, and acceptance decision.

## Human approval

Human review is mandatory for high-risk model selection, unavailable or commercial environments, precision reduction, safety/runaway/control conclusions, extrapolation beyond applicability, repeated recovery, disabled fallback, and final scientific acceptance where required by the capability record.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    workflows = _load(ROOT / "registry" / "workflows.json")
    capabilities = _load(ROOT / "registry" / "capabilities.json")
    accelerators = _load(ROOT / "registry" / "accelerators.json")
    capability_map = {str(item["id"]): item for item in capabilities}
    accelerator_map = {str(item["slug"]): item for item in accelerators}
    changed: list[str] = []
    for record in workflows:
        path = ROOT / "skills" / "workflows" / str(record["slug"]) / "SKILL.md"
        text = render_workflow(record, capability_map, accelerator_map)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                changed.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if changed:
        print(json.dumps({"out_of_date": changed}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
