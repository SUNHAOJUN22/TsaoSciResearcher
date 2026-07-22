#!/usr/bin/env python3
"""Deterministic cross-contract audit for the complete source repository."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv", ".ps1", ".sh", ".cff"}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    "artifacts",
    "__pycache__",
    "dist",
    "build",
}
REQUIRED_WORKFLOWS = {
    "research-question",
    "deep-research",
    "systematic-review",
    "research-design",
    "experiment-design",
    "data-analysis",
    "scientific-figure",
    "scientific-writing",
    "peer-review",
    "technical-report",
    "project-management",
    "patent-and-transfer",
    "research-integrity",
    "laboratory",
    "computation-handoff",
}
LEGACY_SCHEMAS = {
    "research-project.schema.json",
    "evidence-record.schema.json",
    "claim.schema.json",
    "figure-contract.schema.json",
    "experiment-protocol.schema.json",
    "artifact-manifest.schema.json",
    "computation-handoff.schema.json",
    "capability.schema.json",
}
V2_SCHEMAS = {
    "artifact.schema.json",
    "capability-invocation.schema.json",
    "handoff.schema.json",
    "project.schema.json",
    "routing.schema.json",
    "state-event.schema.json",
    "workflow.schema.json",
}
REQUIRED_SCRIPTS = {
    "archive_safety.py",
    "build_readme_facts.py",
    "audit_repository.py",
    "init_project.py",
    "install.py",
    "package_release.py",
    "route_task.py",
    "run_tests.py",
    "validate_claims.py",
    "validate_evidence.py",
    "validate_project.py",
    "validate_release.py",
    "validate_schemas.py",
    "run_mutation_smoke.py",
    "performance_smoke.py",
}
REQUIRED_PACKAGE_MODULES = {
    "__init__.py",
    "__main__.py",
    "capabilities.py",
    "errors.py",
    "handoff.py",
    "io.py",
    "router.py",
    "state.py",
    "vnext.py",
}
DOMAIN_PACK_FILES = {
    "README.md",
    "method-selection.md",
    "validation-checks.md",
    "result-interpretation.md",
    "figure-guides.md",
}
REQUIRED_TEST_SUPPORT = {"conftest.py", "helpers.py", "random_order_plugin.py", "reverse_order_plugin.py"}
UNPINNED_ACTION = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@(?![0-9a-f]{40}(?:\s|#|$))[^\s#]+", re.MULTILINE)
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
FORBIDDEN_SOURCE_PATHS = {".v050-payload", ".github/consolidation"}


def _is_ignored(relative: Path) -> bool:
    return any(part in IGNORED_DIRS or part.endswith(".egg-info") for part in relative.parts)


def _source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if _is_ignored(relative):
            continue
        if path.is_file() or path.is_symlink():
            files.append(path)
    return files


def _load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8", errors="strict"),
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {x}")),
    )


def _markdown_local_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="strict")
    pattern = re.compile(r'(?:\[[^\]]*\]\(|href=["\']|src=["\'])([^)"\']+)')
    links: list[str] = []
    for href in pattern.findall(text):
        value = href.strip().split("#", 1)[0]
        if value and not value.startswith(("#", "mailto:", "data:")) and "://" not in value:
            links.append(value)
    return links


def _legacy_capabilities() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index = _load_json(ROOT / "capability-index/capabilities.json")
    rows: list[dict[str, Any]] = []
    for shard in index["shards"]:
        path = (ROOT / shard["path"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or path.is_symlink():
            raise ValueError(f"unsafe capability shard: {shard['path']}")
        rows.extend(_load_json(path)["capabilities"])
    return index, rows


def _validate_schema(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        schema = _load_json(path)
        jsonschema.Draft202012Validator.check_schema(schema)
    except (ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        errors.append(f"invalid schema {path.relative_to(ROOT).as_posix()}: {exc}")
        return None
    if not isinstance(schema, dict):
        errors.append(f"schema root must be an object: {path.relative_to(ROOT).as_posix()}")
        return None
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or not schema.get("$id"):
        errors.append(f"schema identity missing: {path.relative_to(ROOT).as_posix()}")
    return schema


def audit() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    inventory: dict[str, int] = {}
    total_bytes = 0
    executable: list[str] = []
    newline_counts = {"lf": 0, "crlf": 0, "mixed": 0}
    for path in _source_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            errors.append(f"symbolic link forbidden in source tree: {relative}")
            continue
        size = path.stat().st_size
        total_bytes += size
        suffix = path.suffix.lower() or "<none>"
        inventory[suffix] = inventory.get(suffix, 0) + 1
        if path.stat().st_mode & stat.S_IXUSR:
            executable.append(relative)
        if suffix not in TEXT_SUFFIXES:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"invalid UTF-8 in {relative}: {exc}")
            continue
        has_crlf = b"\r\n" in raw
        has_lf = b"\n" in raw.replace(b"\r\n", b"")
        newline_key = "mixed" if has_crlf and has_lf else "crlf" if has_crlf else "lf"
        newline_counts[newline_key] += 1
        if newline_key == "mixed":
            warnings.append(f"mixed newlines: {relative}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {relative}")
        if suffix == ".py" and re.search(r"subprocess\.(?:run|Popen|call)\([^\n]*shell\s*=\s*True", text):
            errors.append(f"shell=True command execution in {relative}")
    checks["inventory"] = {
        "files_by_suffix": dict(sorted(inventory.items())),
        "total_bytes": total_bytes,
        "newlines": newline_counts,
        "executable_files": sorted(executable),
    }

    for forbidden in FORBIDDEN_SOURCE_PATHS:
        if (ROOT / forbidden).exists():
            errors.append(f"temporary transport/bootstrap path remains in source: {forbidden}")
    for transport_marker in ("materialize_v050", "consolidate_single_main", "v051-part-"):
        matches = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob(f"*{transport_marker}*")]
        if matches:
            errors.append(f"temporary self-materialization artifact remains: {matches}")

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = _load_json(ROOT / "manifest.json")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    agent = yaml.safe_load((ROOT / "agents/openai.yaml").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    versions = {
        "VERSION": version,
        "manifest": str(manifest.get("version")),
        "SKILL": (re.search(r"^version:\s*[\"']?([^\s\"']+)", skill, re.MULTILINE) or [None, None])[1],
        "agent": str(agent.get("version")),
        "pyproject": (re.search(r"^version\s*=\s*[\"']([^\"']+)", pyproject, re.MULTILINE) or [None, None])[
            1
        ],
    }
    if len(set(versions.values())) != 1:
        errors.append(f"version mismatch: {versions}")
    checks["versions"] = versions

    workflow_dirs = {path.parent.name for path in (ROOT / "workflows").glob("*/WORKFLOW.md")}
    missing_workflows = sorted(REQUIRED_WORKFLOWS - workflow_dirs)
    if missing_workflows or len(workflow_dirs) != 15:
        errors.append(f"workflow inventory mismatch: missing={missing_workflows}, count={len(workflow_dirs)}")
    workflow_schema = _validate_schema(ROOT / "schemas/v2/workflow.schema.json", errors)
    workflow_validator = jsonschema.Draft202012Validator(workflow_schema) if workflow_schema else None
    for name in sorted(workflow_dirs):
        directory = ROOT / "workflows" / name
        contract_path = directory / "workflow.yaml.json"
        gates_path = directory / "gates.yaml"
        if not contract_path.is_file() or not gates_path.is_file():
            errors.append(f"workflow {name} lacks v2 contract or gates")
            continue
        contract = _load_json(contract_path)
        if workflow_validator:
            for error in workflow_validator.iter_errors(contract):
                errors.append(f"workflow contract {name}: {error.message}")
        if contract.get("slug") != name:
            errors.append(f"workflow contract slug mismatch: {name}")
        gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
        if not isinstance(gates, dict) or not all(
            isinstance(gates.get(key), list) and gates[key] for key in ("entry", "blocking", "completion")
        ):
            errors.append(f"workflow gates invalid: {name}")
    checks["workflows"] = {
        "count": len(workflow_dirs),
        "missing": missing_workflows,
        "contracts": len(list((ROOT / "workflows").glob("*/workflow.yaml.json"))),
    }

    legacy_paths = sorted((ROOT / "schemas").glob("*.json"))
    v2_paths = sorted((ROOT / "schemas/v2").glob("*.json"))
    legacy_missing = sorted(LEGACY_SCHEMAS - {path.name for path in legacy_paths})
    v2_missing = sorted(V2_SCHEMAS - {path.name for path in v2_paths})
    if legacy_missing or v2_missing:
        errors.append(f"missing schemas: legacy={legacy_missing}, v2={v2_missing}")
    for path in [*legacy_paths, *v2_paths]:
        _validate_schema(path, errors)
    checks["schemas"] = {
        "count": len(legacy_paths),
        "v2_count": len(v2_paths),
        "total": len(legacy_paths) + len(v2_paths),
        "missing": legacy_missing + v2_missing,
    }

    script_names = {path.name for path in (ROOT / "scripts").glob("*.py")}
    package_modules = {path.name for path in (ROOT / "tsao_researcher").glob("*.py")}
    missing_scripts = sorted(REQUIRED_SCRIPTS - script_names)
    missing_modules = sorted(REQUIRED_PACKAGE_MODULES - package_modules)
    if missing_scripts or missing_modules:
        errors.append(f"runtime inventory incomplete: scripts={missing_scripts}, package={missing_modules}")
    checks["runtime"] = {
        "scripts": len(script_names),
        "package_modules": len(package_modules),
        "missing": missing_scripts + missing_modules,
    }

    required_readme_docs = {
        "README.md",
        "README_EN.md",
        "README.zh-CN.md",
        "docs/README_FACTS.json",
        "docs/README_AUDIT_REPORT.md",
        "docs/CAPABILITY_COVERAGE_MATRIX.md",
        "docs/README_ARCHITECTURE_MAPPING.md",
        "docs/VALIDATION_EVIDENCE.json",
    }
    missing_readme_docs = sorted(
        relative for relative in required_readme_docs if not (ROOT / relative).is_file()
    )
    if missing_readme_docs:
        errors.append(f"README evidence inventory incomplete: {missing_readme_docs}")
    checks["readme_evidence"] = {
        "required": len(required_readme_docs),
        "missing": missing_readme_docs,
    }

    index, legacy = _legacy_capabilities()
    legacy_schema = _load_json(ROOT / "schemas/capability.schema.json")
    legacy_validator = jsonschema.Draft202012Validator(legacy_schema)
    legacy_ids: set[str] = set()
    legacy_slugs: set[str] = set()
    for number, row in enumerate(legacy, 1):
        for error in legacy_validator.iter_errors(row):
            errors.append(f"legacy capability {number}: {error.message}")
        identifier = str(row.get("id"))
        slug = str(row.get("slug"))
        if identifier in legacy_ids or slug in legacy_slugs:
            errors.append(f"duplicate legacy capability at row {number}")
        legacy_ids.add(identifier)
        legacy_slugs.add(slug)
        if row.get("workflow") not in workflow_dirs:
            errors.append(f"legacy capability {slug} references missing workflow")
    if len(legacy) != 158 or index.get("total") != 158:
        errors.append(f"legacy capability total {len(legacy)} / {index.get('total')} != 158")

    v2 = _load_json(ROOT / "capabilities/v2/capabilities.json")
    v2_index = _load_json(ROOT / "capabilities/v2/index.json")
    if not isinstance(v2, list):
        errors.append("v2 capability catalog must be a list")
        v2 = []
    v2_ids: set[str] = set()
    v2_slugs: set[str] = set()
    workbook_catalog_ids: set[str] = set()
    generic_domain_slugs: list[str] = []
    v2_required = {
        "schema_version",
        "id",
        "slug",
        "name_zh",
        "name_en",
        "category",
        "domains",
        "description",
        "implementation_level",
        "maturity",
        "workflow",
        "input_schema",
        "output_schema",
        "validators",
        "failure_modes",
        "recovery",
        "human_approval",
        "computation_handoff",
        "references",
        "source_lineage",
    }
    for number, row in enumerate(v2, 1):
        if not isinstance(row, dict):
            errors.append(f"v2 capability {number} is not an object")
            continue
        missing = v2_required - row.keys()
        if missing:
            errors.append(f"v2 capability {number} missing fields: {sorted(missing)}")
        identifier = str(row.get("id"))
        slug = str(row.get("slug"))
        if identifier in v2_ids or slug in v2_slugs:
            errors.append(f"duplicate v2 capability at row {number}")
        v2_ids.add(identifier)
        v2_slugs.add(slug)
        if re.search(r"-capability-[0-9]+$", slug):
            generic_domain_slugs.append(slug)
        for lineage in row.get("source_lineage", []):
            if isinstance(lineage, dict) and lineage.get("source") == "ai-for-science-workbook-322":
                catalog_id = lineage.get("catalog_id")
                if isinstance(catalog_id, str):
                    workbook_catalog_ids.add(catalog_id)
        if row.get("workflow") not in workflow_dirs:
            errors.append(f"v2 capability {slug} references missing workflow")
        for field in ("input_schema", "output_schema"):
            target = (ROOT / str(row.get(field, ""))).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                errors.append(f"v2 capability {slug} has missing/unsafe {field}")
        for reference in row.get("references", []):
            target = (ROOT / str(reference)).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                errors.append(f"v2 capability {slug} references missing/unsafe file {reference}")
    if len(v2) != 340 or v2_index.get("total") != 340:
        errors.append(f"v2 capability total {len(v2)} / {v2_index.get('total')} != 340")
    if len(workbook_catalog_ids) != 322 or v2_index.get("workbook_named_total") != 322:
        errors.append(
            f"workbook-named capability coverage {len(workbook_catalog_ids)} / "
            f"{v2_index.get('workbook_named_total')} != 322"
        )
    if generic_domain_slugs or v2_index.get("generic_domain_slots") != 0:
        errors.append(
            f"generic domain capability slugs remain: {generic_domain_slugs[:5]} "
            f"(index={v2_index.get('generic_domain_slots')})"
        )
    checks["capabilities"] = {
        "loaded": len(legacy),
        "legacy_unique": len(legacy_ids),
        "v2_loaded": len(v2),
        "v2_unique": len(v2_ids),
        "workbook_named": len(workbook_catalog_ids),
        "domain_named": v2_index.get("domain_named"),
        "runtime_core": v2_index.get("core_added"),
        "generic_domain_slots": v2_index.get("generic_domain_slots"),
    }

    domain_dirs = sorted(path for path in (ROOT / "domain-packs").iterdir() if path.is_dir())
    if len(domain_dirs) != 7:
        errors.append(f"expected 7 domain packs, found {len(domain_dirs)}")
    for directory in domain_dirs:
        missing = DOMAIN_PACK_FILES - {path.name for path in directory.iterdir() if path.is_file()}
        if missing:
            errors.append(f"domain pack {directory.name} missing {sorted(missing)}")
        for filename in DOMAIN_PACK_FILES - missing:
            if len((directory / filename).read_text(encoding="utf-8").strip()) < 160:
                errors.append(f"domain pack file is too thin: {directory.name}/{filename}")
    checks["domain_packs"] = {
        "count": len(domain_dirs),
        "files": sum(1 for _ in (ROOT / "domain-packs").glob("*/*")),
    }

    for router_path in (ROOT / "router_rules.json", ROOT / "routing/router-rules-v2.json"):
        router = _load_json(router_path)
        router_missing = sorted(REQUIRED_WORKFLOWS - set(router))
        if router_missing:
            errors.append(f"router {router_path.name} missing workflows: {router_missing}")
    checks["routers"] = 2

    checked_links = 0
    for markdown in (ROOT / "README.md", ROOT / "README.zh-CN.md", ROOT / "README_EN.md"):
        for relative_link in _markdown_local_links(markdown):
            checked_links += 1
            target = (markdown.parent / relative_link).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.exists():
                errors.append(f"broken or unsafe local link in {markdown.name}: {relative_link}")
    checks["readme_links"] = checked_links

    workflow_files = sorted(
        [*(ROOT / ".github/workflows").glob("*.yml"), *(ROOT / ".github/workflows").glob("*.yaml")]
    )
    for workflow in workflow_files:
        text = workflow.read_text(encoding="utf-8")
        for match in UNPINNED_ACTION.finditer(text):
            errors.append(f"unpinned Action in {workflow.name}: {match.group(0).strip()}")
        if re.search(r"base64\.b(?:64|85)decode|zlib\.decompress", text, re.IGNORECASE):
            errors.append(f"opaque payload decoding in workflow: {workflow.name}")
        if re.search(r"continue-on-error:\s*true|\|\|\s*(?:true|exit\s+0)", text, re.IGNORECASE):
            errors.append(f"failure masking in workflow: {workflow.name}")
        has_write = re.search(r"contents:\s*write", text) is not None
        allowed_write = workflow.name == "cleanup-branches.yml"
        if workflow.name == "ci.yml" and has_write:
            guarded_markers = [
                "permissions:\n  contents: read",
                "record-main-validation:",
                "always() && github.event_name == 'push' && github.ref == 'refs/heads/main'",
                "permissions:\n      contents: write",
                ".github/finalize-v052",
            ]
            missing_guarded_markers = [marker for marker in guarded_markers if marker not in text]
            if missing_guarded_markers:
                errors.append(f"guarded CI write permission is incomplete: {missing_guarded_markers}")
            else:
                allowed_write = True
        if has_write and not allowed_write:
            errors.append(f"unexpected contents:write permission in {workflow.name}")
        if workflow.name == "cleanup-branches.yml":
            required_markers = [
                "branches: [main]",
                "contents: write",
                "pull-requests: write",
                "refs/heads/main",
                "/git/refs/heads/{encoded}",
            ]
            for marker in required_markers:
                if marker not in text:
                    errors.append(f"branch cleanup guard missing {marker!r}")
    checks["workflow_files"] = len(workflow_files)

    test_directory = ROOT / "tests"
    test_modules = sorted(test_directory.glob("test_*.py"))
    missing_support = sorted(name for name in REQUIRED_TEST_SUPPORT if not (test_directory / name).is_file())
    if len(test_modules) < 18 or missing_support:
        errors.append(f"test inventory incomplete: modules={len(test_modules)}, support={missing_support}")
    for test_path in test_modules:
        if "sys.path.insert" in test_path.read_text(encoding="utf-8"):
            errors.append(f"test mutates sys.path at import time: {test_path.name}")
    checks["tests"] = {
        "modules": len(test_modules),
        "support_files": len(REQUIRED_TEST_SUPPORT) - len(missing_support),
    }

    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    required_ci_markers = {
        'python-version: "3.10"',
        'python-version: "3.13"',
        "windows-latest",
        "macos-latest",
        "python -m ruff format --check scripts tsao_researcher tests",
        "python -m ruff check scripts tsao_researcher tests",
        "python -m mypy scripts tsao_researcher",
        "tests.random_order_plugin",
        "tests.reverse_order_plugin",
        "run_mutation_smoke.py",
        "performance_smoke.py",
        "package_release.py",
    }
    missing_markers = sorted(marker for marker in required_ci_markers if marker not in ci_text)
    if missing_markers:
        errors.append(f"CI coverage markers missing: {missing_markers}")
    checks["ci_coverage_markers"] = {"required": len(required_ci_markers), "missing": missing_markers}

    manifest_expectations = {
        "capability_count": 340,
        "legacy_capability_count": 158,
        "workbook_named_capability_count": 322,
        "domain_named_capability_count": 164,
        "workflow_count": 15,
        "schema_count": 15,
        "domain_pack_count": 7,
    }
    for key, expected in manifest_expectations.items():
        if manifest.get(key) != expected:
            errors.append(f"manifest {key}={manifest.get(key)!r}, expected {expected!r}")
    checks["manifest"] = {key: manifest.get(key) for key in manifest_expectations}

    status = "PASS" if not errors else "FAIL"
    checks["status"] = status
    return {"status": status, "checks": checks, "errors": errors, "warnings": warnings}


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit the complete TsaoSciResearcher repository")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = audit()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"repository audit {result['status']}")
        for key, value in result["checks"].items():
            print(f"- {key}: {value}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
