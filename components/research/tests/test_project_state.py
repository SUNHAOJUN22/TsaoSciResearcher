from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_project import transition_allowed, validate
from tsao_researcher.io import new_id
from tsao_researcher.state import initialize


def test_project_ids_are_collision_resistant() -> None:
    values = {new_id("TSR") for _ in range(1000)}
    assert len(values) == 1000


def test_transition_order_and_idempotency() -> None:
    assert transition_allowed("proposed", "proposed")
    assert transition_allowed("proposed", "planned")
    assert not transition_allowed("proposed", "accepted")
    assert not transition_allowed("accepted", "validated")


def test_timestamp_monotonicity(tmp_path: Path) -> None:
    state_root = initialize("name", "question", tmp_path)
    path = state_root / "project.yaml"
    project = yaml.safe_load(path.read_text(encoding="utf-8"))
    project["updated_at"] = "2000-01-01T00:00:00Z"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="earlier"):
        validate(path)


def test_accepted_requires_approval(tmp_path: Path) -> None:
    state_root = initialize("name", "question", tmp_path)
    path = state_root / "project.yaml"
    project = yaml.safe_load(path.read_text(encoding="utf-8"))
    project["status"] = "accepted"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="approval"):
        validate(path)
