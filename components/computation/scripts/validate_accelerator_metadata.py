from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from tsao_computation.accelerators import acceleration_libraries

ROOT = Path(__file__).resolve().parents[1]
BACKENDS = {
    "cpu",
    "openmp",
    "mpi",
    "cuda",
    "hip",
    "sycl",
    "opencl",
    "kokkos",
    "task-parallel",
    "remote",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    source_path = root / "registry" / "accelerators.json"
    packaged_path = root / "tsao_computation" / "data" / "registry" / "accelerators.json"
    adapter_path = root / "registry" / "adapters.json"
    workflow_path = root / "registry" / "workflows.json"
    try:
        records = _load(source_path)
        adapters = _load(adapter_path)
        workflows = _load(workflow_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"invalid acceleration metadata: {exc}"]
    if not isinstance(records, list):
        return ["acceleration registry must be an array"]
    if not packaged_path.is_file() or source_path.read_bytes() != packaged_path.read_bytes():
        problems.append("packaged acceleration registry is not synchronized")

    adapter_slugs = {str(record["slug"]) for record in adapters}
    workflow_slugs = {str(record["slug"]) for record in workflows}
    library_slugs = {item.slug for item in acceleration_libraries()}
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            problems.append(f"acceleration entry {index} is not an object")
            continue
        slug = record.get("slug")
        if not isinstance(slug, str) or not slug:
            problems.append(f"acceleration entry {index} has an invalid slug")
            continue
        if slug in seen:
            problems.append(f"duplicate acceleration profile: {slug}")
        seen.add(slug)
        if slug not in adapter_slugs:
            problems.append(f"acceleration profile references unknown adapter: {slug}")
        workflow = record.get("workflow")
        if workflow not in workflow_slugs:
            problems.append(f"acceleration profile {slug} references unknown workflow: {workflow}")

        candidates = record.get("candidate_backends")
        preferred = record.get("preferred_backends")
        if not isinstance(candidates, list) or not candidates:
            problems.append(f"acceleration profile {slug} lacks candidate backends")
            candidates = []
        if not isinstance(preferred, list) or not preferred:
            problems.append(f"acceleration profile {slug} lacks preferred backends")
            preferred = []
        unknown = sorted((set(map(str, candidates)) | set(map(str, preferred))) - BACKENDS)
        if unknown:
            problems.append(f"acceleration profile {slug} has unknown backends: {unknown}")
        if "cpu" not in candidates:
            problems.append(f"acceleration profile {slug} lacks a CPU fallback")
        missing_preferred = sorted(set(map(str, preferred)) - set(map(str, candidates)))
        if missing_preferred:
            problems.append(
                f"acceleration profile {slug} prefers undeclared backends: {missing_preferred}"
            )
        libraries = record.get("library_candidates")
        if not isinstance(libraries, list) or len(libraries) != len(set(map(str, libraries))):
            problems.append(f"acceleration profile {slug} has invalid library_candidates")
        else:
            unknown_libraries = sorted(set(map(str, libraries)) - library_slugs)
            if unknown_libraries:
                problems.append(
                    f"acceleration profile {slug} references unknown libraries: {unknown_libraries}"
                )
        for key in (
            "interfaces",
            "implementation_languages",
            "parallel_strategies",
            "probe_hints",
            "limitations",
        ):
            values = record.get(key)
            if (
                not isinstance(values, list)
                or not values
                or len(values) != len(set(map(str, values)))
            ):
                problems.append(f"acceleration profile {slug} has invalid {key}")
        claim_boundary = record.get("claim_boundary")
        if not isinstance(claim_boundary, str) or len(claim_boundary) < 40:
            problems.append(f"acceleration profile {slug} has a weak claim boundary")

    missing = sorted(adapter_slugs - seen)
    extra = sorted(seen - adapter_slugs)
    if missing:
        problems.append(f"adapters missing acceleration profiles: {missing}")
    if extra:
        problems.append(f"unexpected acceleration profiles: {extra}")
    if len(records) != len(adapter_slugs):
        problems.append(
            f"acceleration profile count {len(records)} differs from adapter count {len(adapter_slugs)}"
        )
    return problems


def main() -> int:
    problems = validate()
    print(json.dumps({"passed": not problems, "problems": problems}, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
