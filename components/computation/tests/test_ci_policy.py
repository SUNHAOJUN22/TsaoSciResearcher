from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_is_blocking_but_separate_from_quality() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    quality = text.split("\n  quality:\n", 1)[1].split("\n  package:\n", 1)[0]
    benchmark = text.split("\n  benchmark:\n", 1)[1].split("\n  performance:\n", 1)[0]
    assert "--profile benchmark" not in quality
    assert "--profile benchmark" in benchmark
    assert "continue-on-error:" not in benchmark


def test_uploaded_artifact_names_are_unique_per_attempt() -> None:
    for filename in ("ci.yml", "release.yml"):
        text = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
        assert "github.run_id" in text
        assert "github.run_attempt" in text


def test_production_actions_remain_pinned_to_commits() -> None:
    pattern = re.compile(r"uses:\s+[^@\s]+@([0-9a-f]{40})$")
    for filename in ("ci.yml", "codeql.yml", "release.yml"):
        text = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
        uses_lines = [line.strip() for line in text.splitlines() if "uses:" in line]
        assert uses_lines
        assert all(pattern.search(line) for line in uses_lines), (filename, uses_lines)
