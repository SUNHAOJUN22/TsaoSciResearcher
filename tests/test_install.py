from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from install import destination, uninstall, validate_destination  # noqa: E402


def test_custom_install_and_managed_uninstall(tmp_path: Path) -> None:
    dst = tmp_path / "skill"
    subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--target", str(dst), "--validate"], check=True, timeout=120)
    assert (dst / "SKILL.md").is_file()
    assert (dst / ".tsao-sci-researcher-install.json").is_file()
    uninstall(dst)
    assert not dst.exists()


@pytest.mark.parametrize("path", [Path.home(), Path.cwd(), ROOT, Path(Path.cwd().anchor)])
def test_rejects_dangerous_targets(path: Path) -> None:
    with pytest.raises(ValueError, match=r"dangerous|overlaps"):
        validate_destination(path)


def test_refuses_unmanaged_force_and_uninstall(tmp_path: Path) -> None:
    dst = tmp_path / "unmanaged"
    dst.mkdir()
    (dst / "important.txt").write_text("keep", encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--target", str(dst), "--force"], check=False, capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    assert (dst / "important.txt").read_text(encoding="utf-8") == "keep"
    with pytest.raises(ValueError, match="unmanaged"):
        uninstall(dst)


def test_destination_is_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert destination("codex", "project", "relative").is_absolute()
