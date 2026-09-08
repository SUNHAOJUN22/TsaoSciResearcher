from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tsao.skillpacks import (
    _distribution_skillpack_candidates,
    resolve_skillpack_root,
    skillpack_inventory,
)

ROOT = Path(__file__).resolve().parents[1]


def test_source_checkout_skillpack_inventory_is_complete():
    inventory = skillpack_inventory(ROOT)
    assert inventory["pass"] is True
    assert inventory["delivery"] == "SOURCE_CHECKOUT"
    assert inventory["subskills"] == ["epdm", "poe", "polymer-general", "process-general"]
    assert inventory["process_general_modules_present"] == 14
    assert inventory["process_general_modules_expected"] == 14
    assert inventory["process_general_workflows_present"] == 6
    assert inventory["process_general_workflows_expected"] == 6
    assert inventory["polymer_general_scripts_present"] == 6
    assert inventory["polymer_general_scripts_expected"] == 6
    assert inventory["readme_svg_assets"] >= 32
    assert inventory["readme_svg_assets_expected_minimum"] == 32
    assert inventory["scientific_technical_approval"] == "NOT_EVALUATED"


def test_skillpack_root_rejects_incomplete_directory(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        resolve_skillpack_root(tmp_path)


def test_distribution_record_locates_standard_prefix_data(tmp_path: Path):
    installed_root = tmp_path / "venv/share/tsao-processing-skill"
    installed_root.mkdir(parents=True)
    marker = Path("../../../share/tsao-processing-skill/SKILL.md")

    class FakeDistribution:
        files = (marker,)

        @staticmethod
        def locate_file(member: object) -> Path:
            if Path(member).as_posix().endswith("share/tsao-processing-skill/SKILL.md"):
                return installed_root / "SKILL.md"
            return tmp_path / "venv/lib/site-packages" / Path(member)

    candidates = _distribution_skillpack_candidates(FakeDistribution())
    assert installed_root.resolve() in candidates


def test_inventory_rejects_duplicate_and_escaping_subskills(tmp_path: Path):
    (tmp_path / "SKILL.md").write_text("root\n", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """version: test
subskills:
- id: process-general
  path: skills/process-general
- id: process-general
  path: skills/process-general-copy
- id: epdm
  path: ../outside
""",
        encoding="utf-8",
    )
    result = skillpack_inventory(tmp_path)
    assert result["pass"] is False
    assert "duplicate subskill id: process-general" in result["errors"]
    assert "subskill path escapes Skillpack root: ../outside" in result["errors"]


def test_skillpacks_module_reports_source_delivery():
    completed = subprocess.run(
        [sys.executable, "-m", "tsao.skillpacks", "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["pass"] is True
    assert payload["delivery"] == "SOURCE_CHECKOUT"
    assert payload["readme_svg_assets_expected_minimum"] == 32
