from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator

from . import __version__
from .capabilities import capability_contract_issues
from .integrity import verify_release_metadata
from .provenance import verify_manifest

_REQUIRED = (
    "README.md",
    "README.zh-CN.md",
    "SKILL.md",
    "ARCHITECTURE.md",
    "manifest.yaml",
    "pyproject.toml",
    "CITATION.cff",
    "schemas/project.schema.json",
    "schemas/source_asset.schema.json",
    "skills/process-general/SKILL.md",
    "skills/epdm/SKILL.md",
    "skills/poe/SKILL.md",
    "skills/polymer-general/SKILL.md",
    "reports/SOURCE_CORE_MANIFEST.tsv",
)
_CACHE_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv"}
_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _version_issues(root: Path) -> list[str]:
    issues: list[str] = []
    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
        citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        return [f"cannot read version metadata: {exc}"]
    pep440 = __version__.replace("-alpha.", "a")
    if pyproject.get("project", {}).get("version") != pep440:
        issues.append("pyproject version does not match package version")
    if not isinstance(manifest, dict) or manifest.get("version") != __version__:
        issues.append("manifest version does not match package version")
    if not isinstance(citation, dict) or citation.get("version") != __version__:
        issues.append("CITATION version does not match package version")
    if f"version: {__version__}" not in skill:
        issues.append("SKILL frontmatter version does not match package version")
    return issues


def _schema_issues(schemas: tuple[Path, ...]) -> list[str]:
    issues: list[str] = []
    if not schemas:
        return ["repository contains no JSON Schemas"]
    for path in schemas:
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            issues.append(f"invalid schema {path.name}: {exc}")
    return issues


def _link_issues(root: Path, markdown_paths: tuple[Path, ...]) -> list[str]:
    issues: list[str] = []
    root_resolved = root.resolve()
    for path in markdown_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"cannot read Markdown file {path.relative_to(root)}: {exc}")
            continue
        for raw_target in _LINK_PATTERN.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target or any(character in target for character in "{}*|"):
                continue
            resolved = (path.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                issues.append(
                    f"Markdown link escapes root: {path.relative_to(root)} -> {raw_target}"
                )
                continue
            if not resolved.exists():
                issues.append(f"broken Markdown link: {path.relative_to(root)} -> {raw_target}")
    return issues


def _repository_issues(
    root: Path,
    *,
    strict_source_clean: bool,
    entries: tuple[Path, ...],
    markdown_paths: tuple[Path, ...],
) -> list[str]:
    issues = [f"missing required path: {item}" for item in _REQUIRED if not (root / item).exists()]
    for path in entries:
        relative_parts = path.relative_to(root).parts
        cache_hit = next((part for part in relative_parts if part in _CACHE_PARTS), None)
        if cache_hit:
            if strict_source_clean:
                issues.append(
                    f"source tree contains cache path: {path.relative_to(root).as_posix()}"
                )
            continue
        if path.is_symlink():
            issues.append(f"repository contains symlink: {path.relative_to(root).as_posix()}")
    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        for command in ("tsao.cli doctor", "tsao.cli init", "tsao.cli audit"):
            if command not in text:
                issues.append(f"README missing canonical command: {command}")
    issues.extend(_link_issues(root, markdown_paths))
    return sorted(set(issues))


def _has_full_distribution_markers(root: Path) -> bool:
    return all(
        (root / marker).is_file()
        for marker in (
            "reports/COMPLETE_DISTRIBUTION_MANIFEST.tsv",
            "FILE_MANIFEST.tsv",
            "checksums.sha256",
            "SBOM.json",
        )
    )


def _release_identity_issues(root: Path, profile: str) -> list[str]:
    path = root / "reports/RELEASE_IDENTITY.json"
    if not path.is_file():
        return [] if profile == "core" else ["missing reports/RELEASE_IDENTITY.json"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"invalid release identity: {exc}"]
    issues: list[str] = []
    if data.get("version") != __version__:
        issues.append("release identity version mismatch")
    if data.get("artifact_software_qualification") not in {"PASS", "NOT_EVALUATED"}:
        issues.append("release identity has invalid software qualification")
    for field in (
        "scientific_technical_approval",
        "engineering_design_approval",
        "industrial_performance_guarantee",
    ):
        if data.get(field) != "NOT_EVALUATED":
            issues.append(f"release identity must keep {field} NOT_EVALUATED")
    return issues


def diagnose(
    root: Path,
    *,
    profile: str = "auto",
    strict_source_clean: bool = False,
) -> dict[str, Any]:
    root = Path(root).resolve()
    if profile not in {"auto", "core", "full"}:
        raise ValueError("profile must be auto, core or full")
    active_profile = profile
    if active_profile == "auto":
        active_profile = "full" if _has_full_distribution_markers(root) else "core"

    entries = tuple(sorted(root.rglob("*")))
    markdown_paths = tuple(
        path
        for path in entries
        if path.is_file()
        and path.suffix.casefold() == ".md"
        and not any(part in _CACHE_PARTS or part == ".git" for part in path.relative_to(root).parts)
    )
    schemas = tuple(sorted((root / "schemas").glob("*.schema.json")))
    checks: dict[str, list[str]] = {
        "repository": _repository_issues(
            root,
            strict_source_clean=strict_source_clean,
            entries=entries,
            markdown_paths=markdown_paths,
        ),
        "version": _version_issues(root),
        "schemas": _schema_issues(schemas),
        "capabilities": capability_contract_issues(root),
    }
    manifest_name = (
        "reports/COMPLETE_DISTRIBUTION_MANIFEST.tsv"
        if active_profile == "full"
        else "reports/SOURCE_CORE_MANIFEST.tsv"
    )
    checks["provenance"] = verify_manifest(root, root / manifest_name)
    checks["release_identity"] = _release_identity_issues(root, active_profile)
    if active_profile == "full":
        checks["release_metadata"] = verify_release_metadata(root)
    issues = [f"{name}: {issue}" for name, values in checks.items() for issue in values]
    return {
        "version": __version__,
        "profile": active_profile,
        "pass": not issues,
        "strict_source_clean": strict_source_clean,
        "checks": {name: {"pass": not values, "issues": values} for name, values in checks.items()},
        "issues": issues,
        "warnings": [],
        "metrics": {
            "schemas": len(schemas),
            "specialists": 4,
        },
        "artifact_software_qualification": "PASS" if not issues else "FAIL",
        "technical_approval_status": "NOT_EVALUATED",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def doctor(root: Path, *, strict_source_clean: bool = False) -> dict[str, Any]:
    """Backward-compatible alias for older full-distribution callers."""
    return diagnose(root, profile="auto", strict_source_clean=strict_source_clean)
