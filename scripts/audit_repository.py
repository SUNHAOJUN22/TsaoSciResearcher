#!/usr/bin/env python3
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
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv", ".ps1", ".sh"}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
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
REQUIRED_SCHEMAS = {
    "research-project.schema.json",
    "evidence-record.schema.json",
    "claim.schema.json",
    "figure-contract.schema.json",
    "experiment-protocol.schema.json",
    "artifact-manifest.schema.json",
    "computation-handoff.schema.json",
    "capability.schema.json",
}
REQUIRED_SCRIPTS = {
    "archive_safety.py",
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
    "run_mutation_smoke.py",
    "performance_smoke.py",
}
REQUIRED_CAPABILITY_FIELDS = {
    "id",
    "slug",
    "name_zh",
    "name_en",
    "category_zh",
    "description_zh",
    "workflow",
    "triggers",
    "inputs",
    "outputs",
    "recommended_tools",
    "risk_level",
    "human_approval_required",
    "tsao_sci_computation_handoff",
    "references",
}
UNPINNED_ACTION = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@(?![0-9a-f]{40}(?:\s|#|$))[^\s#]+", re.MULTILINE)
FORBIDDEN_WORKFLOW = [
    re.compile(r"base64\.b(?:64|85)decode", re.IGNORECASE),
    re.compile(r"zlib\.decompress", re.IGNORECASE),
    re.compile(r"git\s+push", re.IGNORECASE),
    re.compile(r"permissions:\s*[\s\S]{0,200}contents:\s*write", re.IGNORECASE),
    re.compile(r"continue-on-error:\s*true", re.IGNORECASE),
    re.compile(r"\|\|\s*(?:true|exit\s+0)", re.IGNORECASE),
]
REQUIRED_TEST_SUPPORT = {
    "conftest.py",
    "helpers.py",
    "random_order_plugin.py",
    "reverse_order_plugin.py",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def _source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if path.is_file() or path.is_symlink():
            files.append(path)
    return files


def _markdown_local_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="strict")
    links: list[str] = []
    pattern = re.compile(r'(?:\[[^\]]*\]\(|href=["\']|src=["\'])([^)"\']+)')
    for href in pattern.findall(text):
        value = href.strip().split("#", 1)[0]
        if not value or value.startswith(("#", "mailto:", "data:")) or "://" in value:
            continue
        links.append(value)
    return links


def _load_capabilities() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index = json.loads(
        (ROOT / "capability-index/capabilities.json").read_text(encoding="utf-8", errors="strict")
    )
    rows: list[dict[str, Any]] = []
    for shard in index["shards"]:
        path = (ROOT / shard["path"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or path.is_symlink():
            raise ValueError(f"unsafe capability shard: {shard['path']}")
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
        rows.extend(payload["capabilities"])
    return index, rows


def audit() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}
    inventory: dict[str, int] = {}
    newlines = {"lf": 0, "crlf": 0, "mixed": 0}
    total_bytes = 0
    executable: list[str] = []
    file_records: list[dict[str, Any]] = []
    files = _source_files()
    for path in files:
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
            file_records.append(
                {
                    "path": relative,
                    "bytes": size,
                    "suffix": suffix,
                    "encoding": "binary",
                    "newlines": "n/a",
                    "executable": relative in executable,
                }
            )
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"invalid UTF-8 in {relative}: {exc}")
            continue
        has_crlf = b"\r\n" in raw
        has_lf = b"\n" in raw.replace(b"\r\n", b"")
        key = "mixed" if has_crlf and has_lf else "crlf" if has_crlf else "lf"
        newlines[key] += 1
        file_records.append(
            {
                "path": relative,
                "bytes": size,
                "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
                "suffix": suffix,
                "encoding": "utf-8",
                "newlines": key,
                "executable": relative in executable,
            }
        )
        if key == "mixed":
            warnings.append(f"mixed newlines: {relative}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {relative}")
        if suffix == ".py" and re.search(r"subprocess\.(?:run|Popen|call)\([^\n]*shell\s*=\s*True", text):
            errors.append(f"shell=True command execution in {relative}")
    checks["inventory"] = {
        "files_by_suffix": dict(sorted(inventory.items())),
        "total_bytes": total_bytes,
        "newlines": newlines,
        "executable_files": sorted(executable),
        "records": sorted(file_records, key=lambda row: str(row["path"])),
    }

    version = (ROOT / "VERSION").read_text(encoding="utf-8", errors="strict").strip()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8", errors="strict"))
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8", errors="strict")
    agent = yaml.safe_load((ROOT / "agents/openai.yaml").read_text(encoding="utf-8", errors="strict"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8", errors="strict")
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
    if missing_workflows:
        errors.append(f"missing workflows: {missing_workflows}")
    checks["workflows"] = {"count": len(workflow_dirs), "missing": missing_workflows}

    schema_paths = sorted((ROOT / "schemas").glob("*.json"))
    schema_names = {path.name for path in schema_paths}
    missing_schemas = sorted(REQUIRED_SCHEMAS - schema_names)
    if missing_schemas:
        errors.append(f"missing schemas: {missing_schemas}")
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8", errors="strict"))
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            errors.append(f"invalid schema {path.name}: {exc.message}")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or not schema.get("$id"):
            errors.append(f"schema identity missing: {path.name}")
    checks["schemas"] = {"count": len(schema_paths), "missing": missing_schemas}

    script_names = {path.name for path in (ROOT / "scripts").glob("*.py")}
    missing_scripts = sorted(REQUIRED_SCRIPTS - script_names)
    if missing_scripts:
        errors.append(f"missing scripts: {missing_scripts}")

    index, capabilities = _load_capabilities()
    capability_schema = json.loads(
        (ROOT / "schemas/capability.schema.json").read_text(encoding="utf-8", errors="strict")
    )
    capability_validator = jsonschema.Draft202012Validator(capability_schema)
    identifiers: list[str] = []
    slugs: list[str] = []
    for number, capability in enumerate(capabilities, 1):
        try:
            capability_validator.validate(capability)
        except jsonschema.ValidationError as exc:
            errors.append(f"capability {number} schema violation: {exc.message}")
        missing = REQUIRED_CAPABILITY_FIELDS - capability.keys()
        if missing:
            errors.append(f"capability {number} missing fields: {sorted(missing)}")
        identifiers.append(str(capability.get("id")))
        slugs.append(str(capability.get("slug")))
        if capability.get("workflow") not in workflow_dirs:
            errors.append(f"capability {capability.get('slug')} references missing workflow")
        for reference in capability.get("references", []):
            target = (ROOT / reference).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                errors.append(
                    f"capability {capability.get('slug')} references unsafe/missing file {reference}"
                )
    if len(capabilities) != 158 or index.get("total") != 158:
        errors.append(f"capability total {len(capabilities)} / {index.get('total')} != 158")
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate capability IDs")
    if len(slugs) != len(set(slugs)):
        errors.append("duplicate capability slugs")
    checks["capabilities"] = {
        "loaded": len(capabilities),
        "unique_ids": len(set(identifiers)),
        "unique_slugs": len(set(slugs)),
    }

    router = json.loads((ROOT / "router_rules.json").read_text(encoding="utf-8", errors="strict"))
    missing_router = sorted(REQUIRED_WORKFLOWS - router.keys())
    if missing_router:
        errors.append(f"router missing workflows: {missing_router}")

    checked_links = 0
    for markdown in [ROOT / "README.md", ROOT / "README.zh-CN.md", ROOT / "README_EN.md"]:
        for relative_link in _markdown_local_links(markdown):
            checked_links += 1
            target = (markdown.parent / relative_link).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.exists():
                errors.append(f"broken or unsafe local link in {markdown.name}: {relative_link}")
    checks["readme_links"] = checked_links

    workflow_files = list((ROOT / ".github/workflows").glob("*.yml")) + list(
        (ROOT / ".github/workflows").glob("*.yaml")
    )
    for workflow in workflow_files:
        text = workflow.read_text(encoding="utf-8", errors="strict")
        for match in UNPINNED_ACTION.finditer(text):
            errors.append(f"unpinned Action in {workflow.name}: {match.group(0).strip()}")
        for pattern in FORBIDDEN_WORKFLOW:
            if pattern.search(text):
                errors.append(f"opaque/self-modifying workflow pattern in {workflow.name}: {pattern.pattern}")
    checks["workflow_files"] = len(workflow_files)

    test_directory = ROOT / "tests"
    test_modules = sorted(test_directory.glob("test_*.py"))
    if len(test_modules) < 16:
        errors.append(f"expected at least 16 pytest modules, found {len(test_modules)}")
    missing_test_support = sorted(
        name for name in REQUIRED_TEST_SUPPORT if not (test_directory / name).is_file()
    )
    if missing_test_support:
        errors.append(f"missing test support files: {missing_test_support}")
    for test_path in test_modules:
        test_text = test_path.read_text(encoding="utf-8", errors="strict")
        if "sys.path.insert" in test_text:
            errors.append(f"test mutates sys.path at import time: {test_path.name}")
    checks["tests"] = {
        "modules": len(test_modules),
        "support_files": len(REQUIRED_TEST_SUPPORT) - len(missing_test_support),
    }

    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8", errors="strict")
    required_ci_markers = {
        "os: [ubuntu-latest, windows-latest, macos-latest]",
        'python-version: ["3.10", "3.11", "3.12", "3.13"]',
        "python -m ruff format --check scripts tests",
        "python -m ruff check scripts tests",
        "python -m mypy scripts",
        "tests.random_order_plugin",
        "tests.reverse_order_plugin",
        "run_mutation_smoke.py",
        "performance_smoke.py",
    }
    missing_ci_markers = sorted(marker for marker in required_ci_markers if marker not in ci_text)
    if missing_ci_markers:
        errors.append(f"CI coverage markers missing: {missing_ci_markers}")
    checks["ci_coverage_markers"] = {
        "required": len(required_ci_markers),
        "missing": missing_ci_markers,
    }

    checks["status"] = "PASS" if not errors else "FAIL"
    return {"status": checks["status"], "checks": checks, "errors": errors, "warnings": warnings}


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
