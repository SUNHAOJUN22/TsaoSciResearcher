from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_completed_one_shot_migration_scripts_are_not_shipped() -> None:
    obsolete = (
        ROOT / "scripts" / "apply_skill_native_v15_fix2.py",
        ROOT / "scripts" / "apply_v4_ci_hardening.py",
    )
    assert all(not path.exists() for path in obsolete), obsolete


def test_chinese_readme_preserves_maintenance_and_acceptance_boundaries() -> None:
    text = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "维护与去重策略" in text
    assert "规范 parser contract" in text
    assert "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED" in text
    assert "不等于 Gaussian、VASP、Quantum ESPRESSO 或 CP2K" in text
