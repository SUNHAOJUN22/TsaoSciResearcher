"""External evidence readers must enforce the same unambiguous JSON contract."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import sha256_file
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.state import initialize, verify

ROOT = Path(__file__).resolve().parents[1]


def _prepared_project(tmp_path: Path) -> Path:
    project = initialize("strict-json", "Which input evidence is valid?", tmp_path)
    (project / "data/input.dat").write_bytes(b"synthetic input")
    create_handoff(
        project,
        "computation/job.json",
        "Which input evidence is valid?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )
    (project / "computation/result.out").write_bytes(b"synthetic output")
    return project


def _record(project: Path) -> None:
    record_receipt(
        project,
        "computation/job.json",
        "test-fixture",
        ["fixture"],
        0,
        ["computation/result.out"],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:00:01Z",
    )


@pytest.mark.parametrize("consumer", ["record", "verify-receipts", "verify-project"])
@pytest.mark.parametrize("prefix", ['"status":"blocked",', '"measurement":1e-400,', '"measurement":1e999,'])
def test_handoff_consumers_reject_ambiguous_or_unrepresentable_json(
    tmp_path: Path, consumer: str, prefix: str
) -> None:
    project = _prepared_project(tmp_path)
    if consumer != "record":
        _record(project)
    handoff = project / "computation/job.json"
    handoff.write_text("{" + prefix + handoff.read_text(encoding="utf-8")[1:], encoding="utf-8")
    if consumer != "record":
        log = project / "execution-receipts.jsonl"
        receipt = json.loads(log.read_text(encoding="utf-8"))
        receipt["handoff_sha256"] = sha256_file(handoff)
        log.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    original_log = (project / "execution-receipts.jsonl").read_bytes()
    with pytest.raises(ValueError, match=r"duplicate|underflow|non-finite"):
        if consumer == "record":
            _record(project)
        elif consumer == "verify-receipts":
            verify_receipts(project)
        else:
            verify(project)
    assert (project / "execution-receipts.jsonl").read_bytes() == original_log


@pytest.mark.parametrize(
    "payload",
    [
        '{"questions":"invalid","questions":[]}',
        '{"questions":[],"measurement":1e-400}',
        '{"questions":[],"measurement":1e999}',
    ],
)
def test_project_verification_rejects_invalid_registry_json(tmp_path: Path, payload: str) -> None:
    project = initialize("registry", "Which registry is valid?", tmp_path)
    (project / "questions.json").write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=r"duplicate|underflow|non-finite"):
        verify(project)


def test_capsule_rejects_duplicate_manifest_key_even_with_valid_decoded_digest(tmp_path: Path) -> None:
    project = _prepared_project(tmp_path)
    original, ambiguous = tmp_path / "original.zip", tmp_path / "ambiguous.zip"
    export_capsule(project, original, mode="full")
    assert verify_capsule(original)["valid"] is True
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(ambiguous, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "capsule/manifest.json":
                payload = b'{"schema_version":"invalid",' + payload[1:]
            target.writestr(info, payload)
    with pytest.raises(ValueError, match="duplicate"):
        verify_capsule(ambiguous)


def test_actual_strategy_validator_rejects_duplicate_schema_version(tmp_path: Path) -> None:
    original = (ROOT / "examples/first-principles-strategy.json").read_text(encoding="utf-8")
    source = tmp_path / "strategy.json"
    source.write_text('{"schema_version":"invalid",' + original[1:], encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/validate_computation_strategy.py", str(source)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout
    assert "duplicate" in result.stderr
