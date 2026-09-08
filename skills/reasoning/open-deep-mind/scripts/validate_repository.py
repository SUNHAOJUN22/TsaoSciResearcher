#!/usr/bin/env python3
"""Validate OpenDeepMind repository architecture without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"\b(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)
CFF_VERSION_RE = re.compile(r"^version:\s*[\"']?([^\"'\s]+)", re.MULTILINE)
README_VERSION_RE = re.compile(r"version-([0-9]+\.[0-9]+\.[0-9]+)")
SKILL_METADATA_VERSION_RE = re.compile(r"^\s{2,}version:\s*[\"']?([^\"'\s]+)", re.MULTILINE)
FORBIDDEN = ("NEEDS" + "_CHECK", "PLACEHOLDER" + "_CITATION", "INSERT" + "_SOURCE_HERE")

REQUIRED = (
    "VERSION",
    "README.md",
    "README.zh-CN.md",
    "BENCHMARK.md",
    "LICENSE.md",
    "NOTICE.md",
    "CITATION.cff",
    "CHANGELOG.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    ".github/workflows/validate.yml",
    "open-deep-mind/SKILL.md",
    "open-deep-mind/ARCHITECTURE.md",
    "open-deep-mind/MODULES.json",
    "open-deep-mind/FIRST_PHILOSOPHY.md",
    "open-deep-mind/FIRST_PRINCIPLES.md",
    "open-deep-mind/TRIZ_ENGINEERING.md",
    "open-deep-mind/first-philosophy/METHOD.md",
    "open-deep-mind/first-philosophy/README.md",
    "open-deep-mind/first-philosophy/module.json",
    "open-deep-mind/first-philosophy/foundation-charter.schema.json",
    "open-deep-mind/first-philosophy/example-foundation-charter.json",
    "open-deep-mind/first-philosophy/scripts/validate_module.py",
    "open-deep-mind/first-principles/METHOD.md",
    "open-deep-mind/first-principles/README.md",
    "open-deep-mind/first-principles/module.json",
    "open-deep-mind/first-principles/model-contract.schema.json",
    "open-deep-mind/first-principles/decision-record.schema.json",
    "open-deep-mind/first-principles/example-model-contract.json",
    "open-deep-mind/first-principles/example-decision-record.json",
    "open-deep-mind/first-principles/scripts/validate_module.py",
    "open-deep-mind/triz/ROUTER.md",
    "open-deep-mind/triz/README.md",
    "open-deep-mind/triz/module.json",
    "open-deep-mind/triz/VENDORED_LICENSE.md",
    "open-deep-mind/triz/resources/contradiction_matrix.json",
    "open-deep-mind/triz/resources/matrix_anomalies.json",
    "open-deep-mind/triz/resources/76_standard_solutions.md",
    "open-deep-mind/triz/resources/ariz_85c.md",
    "open-deep-mind/triz/resources/sources.md",
    "open-deep-mind/triz/scripts/lookup_matrix.py",
    "open-deep-mind/triz/scripts/lookup_standard_solution.py",
    "open-deep-mind/triz/scripts/validate_triz_module.py",
    "open-deep-mind/evals/README.md",
    "open-deep-mind/evals/evals.json",
    "open-deep-mind/evals/evals.schema.json",
    "open-deep-mind/evals/benchmark-config.json",
    "open-deep-mind/evals/run-record.schema.json",
    "open-deep-mind/evals/grading.schema.json",
    "open-deep-mind/evals/benchmark.schema.json",
    "open-deep-mind/evals/rubric.md",
    "open-deep-mind/evals/scripts/validate_evals.py",
    "open-deep-mind/evals/scripts/create_workspace.py",
    "open-deep-mind/evals/scripts/aggregate_benchmark.py",
    "open-deep-mind/references/method-atlas.md",
    "open-deep-mind/references/domain-routing.md",
    "open-deep-mind/references/quality-gates.md",
    "open-deep-mind/references/failure-modes.md",
    "open-deep-mind/references/intellectual-lineage.md",
    "open-deep-mind/references/glossary.md",
    "open-deep-mind/references/worked-examples.md",
    "open-deep-mind/assets/output-templates.md",
    "open-deep-mind/assets/claim-ledger-template.md",
    "open-deep-mind/assets/claim-ledger.schema.json",
    "open-deep-mind/assets/example-ledger.json",
    "open-deep-mind/scripts/validate_ledger.py",
    "open-deep-mind/tests/test_validators.py",
)

MODULE_MANIFESTS = {
    "first-philosophy": "open-deep-mind/first-philosophy/module.json",
    "first-principles": "open-deep-mind/first-principles/module.json",
    "triz": "open-deep-mind/triz/module.json",
}
OWNED_VALIDATORS = (
    "open-deep-mind/first-philosophy/scripts/validate_module.py",
    "open-deep-mind/first-principles/scripts/validate_module.py",
    "open-deep-mind/triz/scripts/validate_triz_module.py",
    "open-deep-mind/evals/scripts/validate_evals.py",
)
ALIASES = {
    "open-deep-mind/FIRST_PHILOSOPHY.md": "first-philosophy/METHOD.md",
    "open-deep-mind/FIRST_PRINCIPLES.md": "first-principles/METHOD.md",
    "open-deep-mind/TRIZ_ENGINEERING.md": "triz/ROUTER.md",
}


def frontmatter_block(text: str) -> str:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    return text[4:end]


def parse_top_level_frontmatter(text: str) -> dict[str, str]:
    raw = frontmatter_block(text)
    data: dict[str, str] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line[0].isspace() or ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if value in {">-", ">", "|-", "|"}:
            parts: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i] or lines[i][0].isspace()):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            data[key] = " ".join(parts)
            continue
        data[key] = value
        i += 1
    return data


def extract_skill_version(text: str) -> str | None:
    raw = frontmatter_block(text)
    match = SKILL_METADATA_VERSION_RE.search(raw)
    return match.group(1) if match else None


def local_targets(text: str) -> set[str]:
    return set(MD_LINK_RE.findall(text)) | set(HTML_LINK_RE.findall(text))


def validate_local_target(path: Path, root: Path, target: str, errors: list[str]) -> None:
    target = target.strip().split()[0].strip("<>")
    if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
        return
    target_path = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target_path:
        return
    resolved = (path.parent / target_path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"link escapes repository in {path.relative_to(root)}: {target}")
        return
    if not resolved.exists():
        errors.append(f"broken relative link in {path.relative_to(root)}: {target}")


def run_validator(root: Path, rel: str, errors: list[str], warnings: list[str]) -> None:
    proc = subprocess.run(
        [sys.executable, str(root / rel)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr + "\n" + proc.stdout).strip()
        errors.append(f"owned validator failed: {rel}\n{detail}")
    elif proc.stderr.strip():
        warnings.append(f"{rel}: {proc.stderr.strip()}")


def validate(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    version_path = root / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"VERSION must be semantic x.y.z; got {version!r}")

    skill_path = root / "open-deep-mind" / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        try:
            fm = parse_top_level_frontmatter(text)
            skill_version = extract_skill_version(text)
        except ValueError as exc:
            errors.append(str(exc))
            fm, skill_version = {}, None
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            errors.append("SKILL.md frontmatter missing name")
        elif not NAME_RE.fullmatch(name):
            errors.append(f"invalid skill name: {name!r}")
        elif name != skill_path.parent.name:
            errors.append("skill folder name must match frontmatter name")
        if not desc:
            errors.append("SKILL.md frontmatter missing description")
        elif len(desc) > 1024:
            errors.append(f"description exceeds 1024 characters: {len(desc)}")
        if skill_version != version:
            errors.append(f"SKILL metadata.version {skill_version!r} != VERSION {version!r}")
        line_count = len(text.splitlines())
        if line_count > 500:
            errors.append(f"SKILL.md is {line_count} lines; progressive-disclosure limit is 500")
        for marker in ("first-philosophy/METHOD.md", "first-principles/METHOD.md", "triz/ROUTER.md", "TRIZ is explicit-only"):
            if marker not in text:
                errors.append(f"SKILL.md missing canonical routing marker: {marker}")

    registry_path = root / "open-deep-mind" / "MODULES.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.is_file() else {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid MODULES.json: {exc}")
        registry = {}
    if registry.get("repository_version") != version:
        errors.append("MODULES.json repository_version != VERSION")
    registry_ids = [m.get("id") for m in registry.get("modules", []) if isinstance(m, dict)]
    if registry_ids != ["first-philosophy", "first-principles", "triz"]:
        errors.append(f"MODULES.json module order/IDs invalid: {registry_ids}")
    if "eval" in " ".join(str(x).lower() for x in registry_ids):
        errors.append("eval layer must not be registered as a reasoning module")

    for module_id, rel in MODULE_MANIFESTS.items():
        path = root / rel
        try:
            manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except json.JSONDecodeError as exc:
            errors.append(f"invalid {rel}: {exc}")
            manifest = {}
        if manifest.get("id") != module_id:
            errors.append(f"{rel} id mismatch")
        if manifest.get("version") != version:
            errors.append(f"{rel} version {manifest.get('version')!r} != VERSION {version!r}")

    for rel, target in ALIASES.items():
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if target not in text:
            errors.append(f"compatibility alias {rel} does not point to {target}")
        if len(text.splitlines()) > 45:
            errors.append(f"compatibility alias {rel} is too large; canonical method body is not isolated")

    citation_path = root / "CITATION.cff"
    if citation_path.is_file():
        match = CFF_VERSION_RE.search(citation_path.read_text(encoding="utf-8"))
        cff_version = match.group(1) if match else None
        if cff_version != version:
            errors.append(f"CITATION.cff version {cff_version!r} != VERSION {version!r}")

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        versions = README_VERSION_RE.findall(readme)
        if version not in versions:
            errors.append(f"README version badge(s) {versions} do not include VERSION {version}")
        for marker in ("first-philosophy/METHOD.md", "first-principles/METHOD.md", "triz/ROUTER.md", "MODULES.json"):
            if marker not in readme:
                errors.append(f"README.md missing canonical architecture link: {marker}")

    benchmark_path = root / "open-deep-mind/evals/benchmark-config.json"
    if benchmark_path.is_file():
        try:
            benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid benchmark-config.json: {exc}")
            benchmark = {}
        if benchmark.get("skill_version_target") != version:
            errors.append("benchmark-config skill_version_target != VERSION")
        if benchmark.get("publication", {}).get("publish_scores_before_real_runs") is not False:
            errors.append("benchmark publication policy must forbid scores before real runs")

    domain_path = root / "open-deep-mind/references/domain-routing.md"
    if domain_path.is_file():
        text = domain_path.read_text(encoding="utf-8")
        if "TRIZ isolation rule" not in text:
            errors.append("domain-routing.md missing TRIZ isolation rule")
        if "- TRIZ contradiction" in text or "Default methods\n\n- TRIZ" in text:
            errors.append("domain-routing.md still contains TRIZ in a default method list")
        if "Explicit TRIZ engineering route" not in text:
            errors.append("domain-routing.md missing explicit-only TRIZ route")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix not in {".md", ".py", ".json", ".yml", ".yaml", ".svg", ".cff"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non-UTF-8 text file: {rel}")
            continue
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"forbidden unresolved token {token!r} in {rel}")
        if suffix == ".md":
            for target in local_targets(text):
                validate_local_target(path, root, target, errors)
        elif suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {rel}: {exc}")
        elif suffix == ".svg":
            try:
                ElementTree.fromstring(text)
            except ElementTree.ParseError as exc:
                errors.append(f"invalid SVG XML in {rel}: {exc}")
        elif suffix == ".py":
            try:
                compile(text, rel, "exec")
            except SyntaxError as exc:
                errors.append(f"invalid Python in {rel}: {exc}")

    diagram_dir = root / "open-deep-mind/assets/diagrams"
    diagram_count = len(list(diagram_dir.rglob("*.svg"))) if diagram_dir.exists() else 0
    if diagram_count < 8:
        errors.append(f"expected at least 8 SVG diagrams recursively, found {diagram_count}")

    for validator in OWNED_VALIDATORS:
        if (root / validator).is_file():
            run_validator(root, validator, errors, warnings)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors, warnings = validate(root)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"ok": False, "errors": len(errors), "warnings": len(warnings)}))
        return 1

    print(json.dumps({
        "ok": True,
        "errors": 0,
        "warnings": len(warnings),
        "architecture_version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "modules": 3,
        "behavioral_benchmark": "validated-definition-layer",
        "svg_diagrams": len(list((root / "open-deep-mind/assets/diagrams").rglob("*.svg"))),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
