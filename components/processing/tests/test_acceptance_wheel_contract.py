from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.verify_acceptance_runtime import _REQUIRED, _choose_wheel, verify


def test_acceptance_wheel_contract_names_are_complete() -> None:
    assert _REQUIRED == {
        "skills/epdm/acceptance.py",
        "skills/epdm/docs/SOFTWARE_ACCEPTANCE.md",
        "skills/epdm/tests/test_acceptance.py",
    }


def test_acceptance_wheel_verifier_rejects_missing_members(tmp_path: Path) -> None:
    wheel = tmp_path / "incomplete.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("skills/epdm/acceptance.py", "")
    result = verify(wheel)
    assert result["pass"] is False
    assert any("missing acceptance Wheel members" in item for item in result["errors"])


def test_acceptance_wheel_selection_is_fail_closed(tmp_path: Path) -> None:
    try:
        _choose_wheel(tmp_path)
    except ValueError as exc:
        assert "exactly one Wheel" in str(exc)
    else:
        raise AssertionError("missing Wheel should fail")
