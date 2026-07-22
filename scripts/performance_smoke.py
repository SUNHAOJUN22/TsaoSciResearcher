#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
import time
import tracemalloc
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.archive_safety import validate_zip
from scripts.capability_io import _load_all_capabilities, load_capabilities
from scripts.common import ROOT, read_jsonl
from scripts.install import install, uninstall
from scripts.package_release import build_release
from scripts.route_task import route
from scripts.validate_claims import validate_claim_graph
from tsao_researcher.capabilities import load_capabilities as load_v2_capabilities
from tsao_researcher.capabilities import search_capabilities
from tsao_researcher.router import route as route_v2

ROUTE_ITERATIONS = 10_000
CAPABILITY_LOAD_ITERATIONS = 100
JSONL_RECORDS = 1_000
GRAPH_RECORDS = 1_000
ZIP_MEMBERS = 1_000

THRESHOLDS_SECONDS = {
    "route_10000": 20.0,
    "v2_route_10000": 8.0,
    "v2_catalog_load_100": 4.0,
    "v2_search_1000": 4.0,
    "capability_load_100": 5.0,
    "jsonl_1000": 5.0,
    "claim_evidence_1000": 20.0,
    "schemas_all": 5.0,
    "zip_members_1000": 10.0,
    "install_uninstall": 20.0,
    "release_two_builds": 30.0,
}


def _measure(name: str, operation: Callable[[], Any], metrics: dict[str, float]) -> Any:
    started = time.perf_counter()
    value = operation()
    elapsed = time.perf_counter() - started
    metrics[name] = elapsed
    threshold = THRESHOLDS_SECONDS[name]
    if elapsed > threshold:
        raise SystemExit(f"performance regression {name}: {elapsed:.3f}s > {threshold:.3f}s")
    return value


def _write_graph(directory: Path) -> tuple[Path, Path]:
    evidence_path = directory / "evidence.jsonl"
    claims_path = directory / "claims.jsonl"
    evidence_rows: list[str] = []
    claim_rows: list[str] = []
    for index in range(GRAPH_RECORDS):
        evidence_id = f"EV-{index}"
        claim_id = f"CL-{index}"
        evidence_rows.append(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence_id": evidence_id,
                    "evidence_type": "sourced_fact",
                    "title": f"Source {index}",
                    "source": {"kind": "paper", "locator": f"10.1000/{index}"},
                    "supports_claims": [claim_id],
                    "limitations": [],
                },
                separators=(",", ":"),
            )
        )
        claim_rows.append(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "claim_id": claim_id,
                    "statement": f"Supported statement {index}",
                    "claim_type": "sourced_fact",
                    "evidence_ids": [evidence_id],
                    "assumptions": [],
                    "status": "checked",
                    "limitations": [],
                },
                separators=(",", ":"),
            )
        )
    evidence_path.write_text("\n".join(evidence_rows) + "\n", encoding="utf-8")
    claims_path.write_text("\n".join(claim_rows) + "\n", encoding="utf-8")
    return claims_path, evidence_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded performance smoke benchmarks.")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    metrics: dict[str, float] = {}

    def route_many() -> None:
        for index in range(ROUTE_ITERATIONS):
            route(f"用 GROMACS 做分子动力学并绘制 RMSD {index}")

    _measure("route_10000", route_many, metrics)

    def route_v2_many() -> None:
        for index in range(ROUTE_ITERATIONS):
            decision = route_v2(f"用 GROMACS 实际运行分子动力学 {index}")
            if decision["primary_workflow"] != "computation-handoff":
                raise SystemExit("v2 router returned an unexpected workflow")

    _measure("v2_route_10000", route_v2_many, metrics)

    first_v2_capabilities = load_v2_capabilities()

    def load_v2_capabilities_many() -> None:
        for _ in range(CAPABILITY_LOAD_ITERATIONS):
            if len(load_v2_capabilities()) != 340:
                raise SystemExit("v2 capability catalog was not loaded completely")

    _measure("v2_catalog_load_100", load_v2_capabilities_many, metrics)
    if len(first_v2_capabilities) != 340:
        raise SystemExit("v2 capability catalog must contain 340 records")

    def search_v2_many() -> None:
        for _ in range(1000):
            if not search_capabilities("polymer molecular dynamics", limit=10):
                raise SystemExit("v2 capability search returned no result")

    _measure("v2_search_1000", search_v2_many, metrics)

    _load_all_capabilities.cache_clear()
    first_capabilities = load_capabilities()

    def load_capabilities_many() -> None:
        for _ in range(CAPABILITY_LOAD_ITERATIONS):
            rows = load_capabilities()
            if len(rows) != 158:
                raise SystemExit("capability performance fixture was not loaded completely")

    _measure("capability_load_100", load_capabilities_many, metrics)
    if len(first_capabilities) != 158:
        raise SystemExit("capability catalog must contain 158 records")

    with tempfile.TemporaryDirectory(prefix="tsr-performance-") as directory_name:
        directory = Path(directory_name)
        jsonl_path = directory / "records.jsonl"
        jsonl_path.write_text(
            "\n".join(
                json.dumps(
                    {"schema_version": "1.0", "evidence_id": f"EV-{index}", "value": index},
                    separators=(",", ":"),
                )
                for index in range(JSONL_RECORDS)
            )
            + "\n",
            encoding="utf-8",
        )
        loaded = _measure("jsonl_1000", lambda: read_jsonl(jsonl_path), metrics)
        if len(loaded) != JSONL_RECORDS:
            raise SystemExit("JSONL performance fixture was not read completely")

        claims_path, evidence_path = _write_graph(directory)
        claims, evidence = _measure(
            "claim_evidence_1000",
            lambda: validate_claim_graph(claims_path, evidence_path),
            metrics,
        )
        if len(claims) != GRAPH_RECORDS or len(evidence) != GRAPH_RECORDS:
            raise SystemExit("claim/evidence graph was not validated completely")

        def validate_schemas() -> None:
            schemas = sorted((ROOT / "schemas").glob("*.json")) + sorted((ROOT / "schemas/v2").glob("*.json"))
            if len(schemas) != 15:
                raise SystemExit(f"expected 15 schemas, found {len(schemas)}")
            for schema_path in schemas:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator.check_schema(schema)

        _measure("schemas_all", validate_schemas, metrics)

        archive = directory / "members.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for index in range(ZIP_MEMBERS):
                handle.writestr(f"root/member-{index:04d}.txt", f"record-{index}\n")
        members = _measure("zip_members_1000", lambda: validate_zip(archive), metrics)
        if len(members) != ZIP_MEMBERS:
            raise SystemExit("ZIP performance fixture was not validated completely")

        install_target = directory / "installed-skill"

        def install_cycle() -> None:
            install(install_target, agent="codex", scope="user", force=False)
            uninstall(install_target)

        _measure("install_uninstall", install_cycle, metrics)
        if install_target.exists():
            raise SystemExit("install performance fixture left a target behind")

        def release_twice() -> None:
            first, _ = build_release(directory / "release-a")
            second, _ = build_release(directory / "release-b")
            if first.read_bytes() != second.read_bytes():
                raise SystemExit("performance release builds were not byte-identical")

        _measure("release_two_builds", release_twice, metrics)

    tracemalloc.start()
    for _ in range(10):
        load_capabilities()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {
        "status": "PASS",
        "platform": platform.platform(),
        "python": sys.version,
        "inputs": {
            "route_iterations": ROUTE_ITERATIONS,
            "capability_load_iterations": CAPABILITY_LOAD_ITERATIONS,
            "v2_capability_records": 340,
            "v2_search_iterations": 1000,
            "jsonl_records": JSONL_RECORDS,
            "claim_records": GRAPH_RECORDS,
            "evidence_records": GRAPH_RECORDS,
            "zip_members": ZIP_MEMBERS,
        },
        "seconds": {name: round(value, 6) for name, value in metrics.items()},
        "thresholds_seconds": THRESHOLDS_SECONDS,
        "peak_tracemalloc_bytes": peak_bytes,
    }
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
