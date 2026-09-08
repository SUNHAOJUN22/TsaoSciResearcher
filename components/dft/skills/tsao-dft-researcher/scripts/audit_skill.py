#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import load_yaml  # noqa: E402 -- script-local import follows an explicit sys.path setup

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:/")


def frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md has no YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    import yaml

    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    return data


def contained_path(root: Path, value: Any) -> Path | None:
    """Resolve a Skill-relative path without permitting traversal or symlink escape."""

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


def _path_list(value: Any, field: str, failures: list[str]) -> list[Any]:
    if not isinstance(value, list):
        failures.append(f"{field} must be a list")
        return []
    return value


def audit(skill_dir: Path) -> dict[str, Any]:
    skill_dir = skill_dir.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    required = {
        "SKILL.md": "file",
        "manifest.yaml": "file",
        "references": "directory",
        "templates": "directory",
        "scripts": "directory",
    }
    for rel, kind in required.items():
        path = skill_dir / rel
        ok = path.is_file() if kind == "file" else path.is_dir()
        checks.append({"check": f"required:{rel}", "ok": ok})
        if not ok:
            failures.append(f"missing required {kind}: {rel}")

    if failures:
        return {"ok": False, "skill_dir": str(skill_dir), "failures": failures, "warnings": warnings, "checks": checks}

    try:
        fm = frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        frontmatter_failures = len(failures)
        for key in ("name", "description", "license", "compatibility", "metadata"):
            if key not in fm:
                failures.append(f"SKILL.md frontmatter missing: {key}")
        checks.append(
            {
                "check": "skill-frontmatter",
                "ok": len(failures) == frontmatter_failures,
                "name": fm.get("name"),
            }
        )
    except Exception as exc:
        failures.append(str(exc))
        checks.append({"check": "skill-frontmatter", "ok": False})

    manifest_failure_start = len(failures)
    route_count = 0
    try:
        manifest = load_yaml(skill_dir / "manifest.yaml")
        always = _path_list(manifest.get("always_load", []) or [], "manifest always_load", failures)
        routes = manifest.get("routes", {}) or {}
        for rel in always:
            target = contained_path(skill_dir, rel)
            if target is None:
                failures.append(f"manifest always_load unsafe path: {rel!r}")
            elif not target.exists():
                failures.append(f"manifest always_load missing: {rel}")
        if not isinstance(routes, dict) or not routes:
            failures.append("manifest routes is empty or invalid")
        else:
            route_count = len(routes)
            for route, payload in routes.items():
                if not isinstance(payload, dict):
                    failures.append(f"route {route} must be a mapping")
                    continue
                route_paths = _path_list(payload.get("load", []) or [], f"route {route} load", failures)
                for rel in route_paths:
                    target = contained_path(skill_dir, rel)
                    if target is None:
                        failures.append(f"route {route} references unsafe path: {rel!r}")
                    elif not target.exists():
                        failures.append(f"route {route} references missing file: {rel}")
    except Exception as exc:
        failures.append(f"manifest parse failed: {exc}")
    checks.append(
        {
            "check": "manifest-references",
            "ok": len(failures) == manifest_failure_start,
            "routes": route_count,
        }
    )

    text_suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".gjf", ".tcl", ".txt"}
    control_issues = 0
    placeholder_issues = 0
    text_failure_start = len(failures)
    for path in skill_dir.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            path.resolve().relative_to(skill_dir)
        except ValueError:
            failures.append(f"file or symlink escapes Skill root: {path.relative_to(skill_dir)}")
            continue
        data = path.read_bytes()
        if path.suffix.lower() in text_suffixes:
            bad = [byte for byte in data if byte < 32 and byte not in (9, 10, 13)]
            if bad:
                control_issues += 1
                failures.append(f"control characters in text file: {path.relative_to(skill_dir)}")
            text = data.decode("utf-8", errors="replace")
            if path.name != "audit_skill.py":
                if chr(0xFFFD) in text:
                    failures.append(f"UTF-8 replacement character in: {path.relative_to(skill_dir)}")
                if re.search(r"\^M|\^L|M-bM-", text):
                    failures.append(f"possible escaped-text corruption in: {path.relative_to(skill_dir)}")
            if path.suffix.lower() in {".yaml", ".yml"}:
                try:
                    load_yaml(path)
                except Exception as exc:
                    failures.append(f"YAML parse failed {path.relative_to(skill_dir)}: {exc}")
            if path.suffix.lower() == ".json":
                try:
                    json.loads(text)
                except Exception as exc:
                    failures.append(f"JSON parse failed {path.relative_to(skill_dir)}: {exc}")
            if "{{" in text and path.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt"}:
                placeholder_issues += 1
                warnings.append(f"review unresolved template placeholder: {path.relative_to(skill_dir)}")

    for path in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"Python compile failed {path.name}: {exc}")
    checks.append(
        {
            "check": "text-and-syntax",
            "ok": len(failures) == text_failure_start,
            "control_issues": control_issues,
            "placeholder_warnings": placeholder_issues,
        }
    )

    examples = list((skill_dir / "examples").rglob("*.yaml")) if (skill_dir / "examples").exists() else []
    if not examples:
        warnings.append("no YAML examples found")
    checks.append({"check": "examples", "ok": bool(examples), "count": len(examples)})

    tests = list((skill_dir / "tests").glob("test_*.py")) if (skill_dir / "tests").exists() else []
    if not tests:
        warnings.append("no unit tests found")
    checks.append({"check": "tests-present", "ok": bool(tests), "count": len(tests)})

    return {
        "ok": not failures,
        "skill_dir": str(skill_dir),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the structure and static integrity of this Agent Skill.")
    parser.add_argument("skill_dir", nargs="?", type=Path, default=SCRIPT_DIR.parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(args.skill_dir)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Skill: {result['skill_dir']}")
        print(f"OK: {result['ok']}")
        for item in result["failures"]:
            print(f"FAIL: {item}")
        for item in result["warnings"]:
            print(f"WARN: {item}")
        for item in result["checks"]:
            print(f"CHECK: {item}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
