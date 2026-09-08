from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tsao_researcher import version as version_module
from tsao_researcher.errors import ValidationError
from tsao_researcher.handoff import MAX_INPUT_FILES, _verified_inputs, create_handoff
from tsao_researcher.state import initialize, load_project


def _draft_handoff(project: Path, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "root": project,
        "output": "computation/edge.json",
        "scientific_question": "Which stable observable should be computed?",
        "target_property": "free energy",
        "profile": "MD",
        "methods": ["umbrella sampling"],
        "inputs": [],
        "ready": False,
    }
    values.update(overrides)
    return create_handoff(**values)  # type: ignore[arg-type]


def test_version_uses_installed_metadata_when_source_version_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = Path(version_module.__file__).resolve().parents[1] / "VERSION"
    original_is_file = Path.is_file

    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: False if self == candidate else original_is_file(self),
    )
    monkeypatch.setattr(version_module, "version", lambda distribution: "9.9.9")

    assert version_module.get_version() == "9.9.9"


def test_version_returns_unknown_when_source_and_metadata_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = Path(version_module.__file__).resolve().parents[1] / "VERSION"
    original_is_file = Path.is_file

    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: False if self == candidate else original_is_file(self),
    )

    def missing(distribution: str) -> str:
        raise version_module.PackageNotFoundError(distribution)

    monkeypatch.setattr(version_module, "version", missing)
    assert version_module.get_version() == "0+unknown"


def test_handoff_input_inventory_is_bounded(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="more than"):
        _verified_inputs(tmp_path, ["input.dat"] * (MAX_INPUT_FILES + 1))


def test_handoff_rejects_missing_regular_input(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="not a regular project file"):
        _verified_inputs(tmp_path, ["missing.dat"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"scientific_question": "TBD"}, "placeholder"),
        ({"target_property": ""}, "target property"),
        ({"scale": "galactic"}, "unsupported computation scale"),
        ({"evidence_level": "imagined"}, "unsupported evidence level"),
        (
            {"evaluation_metrics": [""], "expected_outputs": [""]},
            "evaluation metric",
        ),
    ],
)
def test_handoff_rejects_invalid_scientific_contract_fields(
    tmp_path: Path,
    overrides: dict[str, object],
    message: str,
) -> None:
    project = initialize("handoff-edge", "What should be computed?", tmp_path)
    with pytest.raises(ValidationError, match=message):
        _draft_handoff(project, **overrides)


def test_ready_handoff_requires_checksum_verified_input(tmp_path: Path) -> None:
    project = initialize("handoff-ready", "What should be computed?", tmp_path)
    with pytest.raises(ValidationError, match="requires at least one"):
        _draft_handoff(project, ready=True)


def test_handoff_output_must_remain_inside_project(tmp_path: Path) -> None:
    project = initialize("handoff-output", "What should be computed?", tmp_path)
    outside = tmp_path / "outside.json"
    with pytest.raises(ValidationError, match="must stay inside"):
        _draft_handoff(project, output=outside)


def test_handoff_rejects_corrupt_project_handoff_inventory(tmp_path: Path) -> None:
    project = initialize("handoff-corrupt", "What should be computed?", tmp_path)
    project_file = project / "project.yaml"
    record = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    record["computation_handoffs"] = "not-a-list"
    project_file.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="must be a list"):
        _draft_handoff(project)


def test_rewriting_same_handoff_path_does_not_duplicate_registration(tmp_path: Path) -> None:
    project = initialize("handoff-repeat", "What should be computed?", tmp_path)
    first = _draft_handoff(project)
    second = _draft_handoff(project)

    assert first["handoff_id"] != second["handoff_id"]
    assert load_project(project)["computation_handoffs"] == ["computation/edge.json"]
