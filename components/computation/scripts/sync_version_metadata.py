from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[a-zA-Z0-9.-]+)?$")


def read_version(root: Path = ROOT) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"invalid VERSION value: {version!r}")
    return version


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"expected one {label} field, found {count}")
    return updated


def citation_release_date(root: Path = ROOT) -> str:
    text = (root / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^date-released:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if match is None:
        raise ValueError("CITATION.cff has no date-released field")
    return match.group(1)


def rendered_metadata(root: Path, release_date: str) -> dict[Path, str]:
    version = read_version(root)
    date.fromisoformat(release_date)

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_once(
        readme,
        r"(?<=badge/version-)[0-9]+\.[0-9]+\.[0-9]+(?=-2563eb)",
        version,
        "README version badge",
    )
    readme = replace_once(
        readme,
        r"^\| Version \| [^|]+ \|$",
        f"| Version | {version} |",
        "README version table",
    )

    chinese_path = root / "README.zh-CN.md"
    chinese = chinese_path.read_text(encoding="utf-8")
    chinese = replace_once(
        chinese,
        r"(?<=badge/version-)[0-9]+\.[0-9]+\.[0-9]+(?=-2563eb)",
        version,
        "Chinese README version badge",
    )
    chinese = replace_once(
        chinese,
        r"^\| 版本 \| [^|]+ \|$",
        f"| 版本 | {version} |",
        "Chinese README version table",
    )

    skill_path = root / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    skill = replace_once(
        skill,
        r'^  version:\s*["\']?[^"\'\n]+["\']?\s*$',
        f'  version: "{version}"',
        "root Skill metadata version",
    )

    citation_path = root / "CITATION.cff"
    citation = citation_path.read_text(encoding="utf-8")
    citation = replace_once(
        citation,
        r"^version:\s*.+$",
        f"version: {version}",
        "CITATION version",
    )
    citation = replace_once(
        citation,
        r"^date-released:\s*.+$",
        f"date-released: {release_date}",
        "CITATION release date",
    )
    return {
        readme_path: readme,
        chinese_path: chinese,
        skill_path: skill,
        citation_path: citation,
    }


def consistency_problems(root: Path = ROOT, release_date: str | None = None) -> list[str]:
    version = read_version(root)
    resolved_date = release_date or citation_release_date(root)
    expected = rendered_metadata(root, resolved_date)
    problems = [
        f"{path.relative_to(root)} is not synchronized with VERSION"
        for path, content in expected.items()
        if path.read_text(encoding="utf-8") != content
    ]

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if 'dynamic = ["version"]' not in pyproject:
        problems.append("pyproject.toml must declare a dynamic version")
    if 'version = {file = ["VERSION"]}' not in pyproject:
        problems.append("pyproject.toml must source its version from VERSION")

    init_text = (root / "tsao_computation" / "__init__.py").read_text(encoding="utf-8")
    if 'version("tsao-scicomputation")' not in init_text:
        problems.append("package __version__ must come from installed metadata")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version} — {resolved_date}" not in changelog:
        problems.append("CHANGELOG.md lacks the current release heading")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize release metadata from VERSION.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--release-date")
    args = parser.parse_args(argv)

    release_date = args.release_date or citation_release_date(ROOT)
    if args.check:
        problems = consistency_problems(ROOT, release_date)
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "version": read_version(ROOT),
                    "release_date": release_date,
                    "passed": not problems,
                    "problems": problems,
                },
                sort_keys=True,
            )
        )
        return 1 if problems else 0

    for path, content in rendered_metadata(ROOT, release_date).items():
        path.write_text(content, encoding="utf-8", newline="\n")
    problems = consistency_problems(ROOT, release_date)
    if problems:
        raise SystemExit(f"version metadata remains inconsistent: {problems}")
    print(json.dumps({"version": read_version(ROOT), "release_date": release_date}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
