#!/usr/bin/env python3
"""Initialize an auditable TsaoDFT computational-chemistry project."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--name", help="Human-readable project name")
    parser.add_argument("--force", action="store_true", help="Overwrite generated metadata, never raw data")
    return parser.parse_args()


def render_template(name: str, mapping: dict[str, str]) -> str:
    text = (SKILL_DIR / "templates" / name).read_text(encoding="utf-8")
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


def write_if_allowed(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    dirs = [
        ".research/tasks",
        ".research/manifests",
        ".research/leases",
        "00_input",
        "01_structures",
        "02_calculations",
        "03_wavefunctions",
        "04_analysis",
        "05_figures",
        "06_tables",
        "07_reports",
        "08_logs",
        "09_provenance",
        "10_source_data",
    ]
    for rel in dirs:
        (project_dir / rel).mkdir(parents=True, exist_ok=True)

    project_id = project_dir.name.replace(" ", "-").lower()
    created_at = datetime.now(timezone.utc).isoformat()
    mapping = {
        "PROJECT_ID": project_id,
        "PROJECT_NAME": args.name or project_dir.name,
        "CREATED_AT": created_at,
    }

    generated = [
        ("project.yaml", project_dir / ".research/project.yaml"),
        ("calculation-passport.yaml", project_dir / "calculation-passport.yaml"),
        ("task.yaml", project_dir / ".research/tasks/T001-plan.yaml"),
        ("research-manifest.json", project_dir / ".research/manifests/research-manifest.json"),
        ("figure-manifest.json", project_dir / ".research/manifests/figure-manifest.json"),
    ]
    for template_name, destination in generated:
        write_if_allowed(destination, render_template(template_name, mapping), args.force)

    for jsonl in ["artifacts.jsonl", "claims.jsonl", "decisions.jsonl", "events.jsonl"]:
        path = project_dir / ".research" / jsonl
        if not path.exists():
            path.write_text("", encoding="utf-8")

    workflow = project_dir / "workflow.md"
    write_if_allowed(
        workflow,
        f"# {args.name or project_dir.name}\n\n"
        "Stage: T001 (planned)\n\n"
        "Research question: unknown\n\nObservable: unknown\n\n"
        "Validation rung: files not yet created\n\n"
        "Next: complete the scientific contract, calculation passport, and resource estimate.\n",
        args.force,
    )

    print(f"Initialized: {project_dir}")
    print("Next: edit .research/project.yaml and calculation-passport.yaml, then run preflight_project.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
