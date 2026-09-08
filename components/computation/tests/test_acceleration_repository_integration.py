from __future__ import annotations

from pathlib import Path

from scripts.validate_accelerator_metadata import validate
from tsao_computation.registries import accelerators


def test_acceleration_metadata_validator_passes() -> None:
    assert validate() == []


def test_generated_acceleration_sections_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    for record in accelerators():
        text = (root / "adapters" / record["slug"] / "ADAPTER.md").read_text(encoding="utf-8")
        assert "## Acceleration and placement" in text
    for path in (root / "skills" / "workflows").glob("*/SKILL.md"):
        assert "## Acceleration and placement" in path.read_text(encoding="utf-8")
