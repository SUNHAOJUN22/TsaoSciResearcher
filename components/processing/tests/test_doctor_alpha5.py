from __future__ import annotations

import json
from pathlib import Path

from tsao.cli import main as cli_main
from tsao.doctor import diagnose
from tsao.provenance import build_manifest, verify_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_core_doctor_passes_for_public_source():
    result = diagnose(ROOT, profile="core")
    assert result["pass"], result["issues"]
    assert result["profile"] == "core"
    assert result["scientific_technical_approval"] == "NOT_EVALUATED"


def test_auto_doctor_does_not_claim_full_without_release_markers():
    result = diagnose(ROOT, profile="auto")
    assert result["profile"] == "core"


def test_manifest_detects_tampering(tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    target = root / "a.txt"
    target.write_text("alpha", encoding="utf-8")
    manifest = tmp_path / "manifest.tsv"
    assert build_manifest(root, manifest) == 1
    assert verify_manifest(root, manifest) == []
    target.write_text("tampered", encoding="utf-8")
    assert any("mismatch" in issue for issue in verify_manifest(root, manifest))


def test_manifest_text_identity_is_line_ending_independent(tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    target = root / "a.txt"
    target.write_bytes(b"alpha\nbeta\n")
    manifest = tmp_path / "manifest.tsv"
    assert build_manifest(root, manifest) == 1
    target.write_bytes(b"alpha\r\nbeta\r\n")
    assert verify_manifest(root, manifest) == []


def test_doctor_cli_is_structured(capsys):
    assert cli_main(["doctor", "--root", str(ROOT), "--profile", "core"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pass"] is True
    assert payload["profile"] == "core"
