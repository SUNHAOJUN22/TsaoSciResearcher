from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from init_project import build_project, project_id  # noqa: E402
from validate_project import transition_allowed, validate  # noqa: E402


def test_project_ids_are_collision_resistant() -> None:
    values = {project_id() for _ in range(1000)}
    assert len(values) == 1000


def test_transition_order_and_idempotency() -> None:
    assert transition_allowed("proposed", "proposed")
    assert transition_allowed("proposed", "planned")
    assert not transition_allowed("proposed", "accepted")
    assert not transition_allowed("accepted", "validated")


def test_timestamp_monotonicity(tmp_path: Path) -> None:
    project = build_project("name", "question", "mixed")
    project["updated_at"] = "2000-01-01T00:00:00Z"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="earlier"):
        validate(path)


def test_accepted_requires_approval(tmp_path: Path) -> None:
    project = build_project("name", "question", "mixed")
    project["status"] = "accepted"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="approval"):
        validate(path)
