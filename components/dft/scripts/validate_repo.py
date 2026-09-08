#!/usr/bin/env python3
"""Static, deterministic and side-effect-free audit for the TsaoDFT repository."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".py",
    ".gjf",
    ".tcl",
    ".txt",
    ".cff",
    ".toml",
    ".sh",
    ".ps1",
    ".svg",
}
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
FORBIDDEN_PATH_PATTERNS = (
    r"\b[A-Za-z]:\\(?:Users|Documents|Projects|codex|work|data)\\",
    r"/home/[^/]+/",
    r"/Users/[^/]+/",
)
FORBIDDEN_ROOT_ENTRIES = {
    ".v05-workflow-probe",
    "_maintenance",
    "_patch_bootstrap",
    "_v05_bundle",
}
BACKUP_SUFFIXES = (".bak", ".old", ".orig", ".rej", ".swp", ".tmp", "~")
BASE64_PAYLOAD_RE = re.compile(r"[A-Za-z0-9+/=\r\n]+\Z")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:/")
REQUIRED_DEMOS = {
    "workflow-architecture.svg",
    "wavefunction-esp-gallery.svg",
    "free-energy-profile.svg",
    "dft-ml-dashboard.svg",
    "periodic-dft-materials.svg",
    "active-learning-loop.svg",
    "hpc-provenance.svg",
    "multiscale-kinetics.svg",
}
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_IMAGE_RE = re.compile(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


def yaml_load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def contained_path(root: Path, value: Any) -> Path | None:
    """Resolve one manifest path and reject absolute, traversal and symlink escapes."""

    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if WINDOWS_ABSOLUTE_RE.match(normalized) or relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def manifest_paths(value: Any, field: str, failures: list[str]) -> list[Any]:
    if not isinstance(value, list):
        failures.append(f"{field} must be a list")
        return []
    return value


def audit_repository_shape(failures: list[str]) -> None:
    for name in sorted(FORBIDDEN_ROOT_ENTRIES):
        if (ROOT / name).exists():
            failures.append(f"obsolete temporary root entry remains: {name}")

    for child in ROOT.iterdir():
        if child.name.startswith("_"):
            failures.append(f"private bootstrap/bundle entry is forbidden at repository root: {child.name}")
        if child.name.endswith(BACKUP_SUFFIXES):
            failures.append(f"backup or editor-temporary root entry is forbidden: {child.name}")

    workflows = ROOT / ".github" / "workflows"
    if not workflows.is_dir():
        failures.append("missing .github/workflows directory")
        return
    workflow_files = sorted(path.name for path in workflows.iterdir() if path.is_file())
    if workflow_files != ["ci.yml"]:
        failures.append(f"unexpected workflow files: {workflow_files}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    required_root = (
        "README.md",
        "README_EN.md",
        "LICENSE",
        "VERSION",
        "AGENTS.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "skills",
        "scripts",
        "tests",
        "docs",
        ".codex-plugin/plugin.json",
        ".github/workflows/ci.yml",
        "scripts/quality_gate.py",
        "scripts/generate_readme_demos.py",
        "scripts/validate_ai_assets.py",
        "scripts/validate_readme_visuals.py",
        "docs/ENGINE_SUPPORT_MATRIX.md",
        "docs/CAPABILITY_STATUS.yaml",
        "docs/AI_IMAGE_GOVERNANCE.md",
        "assets/ai/manifest.yaml",
    )
    for rel in required_root:
        if not (ROOT / rel).exists():
            failures.append(f"missing root path: {rel}")

    audit_repository_shape(failures)

    skills_root = ROOT / "skills"
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir()) if skills_root.is_dir() else []
    if not skill_dirs:
        failures.append("no skills found")
    release = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else None

    for skill in skill_dirs:
        for rel in ("SKILL.md", "manifest.yaml", "agents/openai.yaml"):
            if not (skill / rel).is_file():
                failures.append(f"{skill.name}: missing {rel}")
        manifest_path = skill / "manifest.yaml"
        if not manifest_path.is_file():
            continue
        try:
            manifest = yaml_load(manifest_path)
            if not isinstance(manifest, dict):
                failures.append(f"{skill.name}: manifest root must be mapping")
                continue
            if release and manifest.get("version") != release:
                failures.append(f"{skill.name}: manifest version {manifest.get('version')} != release {release}")
            always_load = manifest_paths(
                manifest.get("always_load", []) or [],
                f"{skill.name}: manifest always_load",
                failures,
            )
            for rel in always_load:
                target = contained_path(skill, rel)
                if target is None:
                    failures.append(f"{skill.name}: unsafe always_load path {rel!r}")
                elif not target.exists():
                    failures.append(f"{skill.name}: missing always_load path {rel}")
            routes = manifest.get("routes", {}) or {}
            if not isinstance(routes, dict):
                failures.append(f"{skill.name}: manifest routes must be a mapping")
                routes = {}
            for route_name, route in routes.items():
                if not isinstance(route, dict):
                    failures.append(f"{skill.name}: route {route_name} is not mapping")
                    continue
                route_paths = manifest_paths(
                    route.get("load", []) or [],
                    f"{skill.name}: route {route_name} load",
                    failures,
                )
                for rel in route_paths:
                    target = contained_path(skill, rel)
                    if target is None:
                        failures.append(f"{skill.name}: route {route_name} has unsafe path {rel!r}")
                    elif not target.exists():
                        failures.append(f"{skill.name}: route {route_name} missing {rel}")
            skill_text = (skill / "SKILL.md").read_text(encoding="utf-8") if (skill / "SKILL.md").is_file() else ""
            if release and release not in skill_text:
                failures.append(f"{skill.name}: SKILL metadata does not contain release version {release}")
        except Exception as exc:
            failures.append(f"{skill.name}: manifest/version validation failed: {exc}")

    capability_path = ROOT / "docs" / "CAPABILITY_STATUS.yaml"
    if capability_path.is_file():
        try:
            capability = yaml_load(capability_path)
            if not isinstance(capability, dict):
                failures.append("CAPABILITY_STATUS root must be mapping")
            else:
                if release and capability.get("release") != release:
                    failures.append("CAPABILITY_STATUS release mismatch")
                registered: set[str] = set()
                capabilities = capability.get("capabilities", [])
                if not isinstance(capabilities, list):
                    failures.append("CAPABILITY_STATUS capabilities must be a list")
                    capabilities = []
                for item in capabilities:
                    if isinstance(item, dict):
                        skill_name = item.get("skill")
                        if isinstance(skill_name, str):
                            registered.add(skill_name)
                missing = {skill.name for skill in skill_dirs} - registered
                if missing:
                    failures.append(f"skills missing from CAPABILITY_STATUS: {sorted(missing)}")
        except Exception as exc:
            failures.append(f"CAPABILITY_STATUS parse failed: {exc}")

    checked_files = 0
    text_failure_start = len(failures)
    for file_path in iter_files(ROOT):
        if file_path.name == "SHA256SUMS" or file_path.resolve() == Path(__file__).resolve():
            continue
        relative_path = file_path.relative_to(ROOT)
        if file_path.name.endswith(BACKUP_SUFFIXES):
            failures.append(f"backup or editor-temporary file is forbidden: {relative_path}")
        if file_path.stat().st_size == 0:
            failures.append(f"empty file is forbidden: {relative_path}")
            continue
        if file_path.suffix.lower() not in TEXT_SUFFIXES and file_path.name not in {"VERSION", "LICENSE"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            failures.append(f"non-UTF8 text file {relative_path}: {exc}")
            continue
        checked_files += 1
        if "�" in text:
            failures.append(f"UTF-8 replacement character in {relative_path}")
        if (
            file_path.suffix.lower() == ".txt"
            and file_path.stat().st_size > 65_536
            and BASE64_PAYLOAD_RE.fullmatch(text)
        ):
            failures.append(f"large encoded bootstrap payload is forbidden: {relative_path}")
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if re.search(pattern, text):
                warnings.append(f"possible local absolute path in {relative_path}")
        try:
            if file_path.suffix.lower() == ".json":
                json.loads(text)
            elif file_path.suffix.lower() in {".yaml", ".yml"}:
                yaml.safe_load(text)
            elif file_path.suffix.lower() == ".py":
                compile(text, str(relative_path), "exec")
            elif file_path.suffix.lower() == ".svg":
                ET.fromstring(text)
        except Exception as exc:
            failures.append(f"parse/compile failed {relative_path}: {exc}")

    for readme_name in ("README.md", "README_EN.md"):
        readme_path = ROOT / readme_name
        if not readme_path.is_file():
            continue
        image_failure_start = len(failures)
        text = readme_path.read_text(encoding="utf-8")
        refs: set[str] = set(MD_IMAGE_RE.findall(text)) | set(HTML_IMAGE_RE.findall(text))
        for ref in refs:
            if ref.startswith(("http://", "https://")):
                continue
            image_path = Path(ref)
            if image_path.is_absolute() or ".." in image_path.parts:
                failures.append(f"{readme_name} contains unsafe image path: {ref}")
            elif not (ROOT / image_path).is_file():
                failures.append(f"{readme_name} image missing: {ref}")
        checks.append(
            {
                "check": f"{readme_name}-images",
                "count": len(refs),
                "ok": len(failures) == image_failure_start,
            }
        )

    for name in sorted(REQUIRED_DEMOS):
        demo_path = ROOT / "assets" / "demo" / name
        if not demo_path.is_file() or demo_path.stat().st_size == 0:
            failures.append(f"missing demo asset: {demo_path.relative_to(ROOT)}")
        elif "SYNTHETIC DEMO · NOT SCIENTIFIC DATA" not in demo_path.read_text(encoding="utf-8"):
            failures.append(f"demo lacks synthetic-data notice: {demo_path.relative_to(ROOT)}")

    checks.extend(
        (
            {"check": "text-files", "count": checked_files, "ok": len(failures) == text_failure_start},
            {"check": "skills", "count": len(skill_dirs), "ok": bool(skill_dirs)},
        )
    )
    if args.strict:
        failures.extend(f"strict warning: {item}" for item in warnings)

    skill_names = [skill_path.name for skill_path in skill_dirs]
    result: dict[str, Any] = {
        "ok": not failures,
        "skills": skill_names,
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Repository: {ROOT}")
        print(f"Skills: {', '.join(skill_names)}")
        for item in warnings:
            print(f"WARN: {item}")
        for item in failures:
            print(f"FAIL: {item}")
        print(f"RESULT: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
