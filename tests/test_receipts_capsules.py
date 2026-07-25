from __future__ import annotations

import json
import zipfile
from pathlib import Path

import jsonschema
import pytest

from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.errors import IntegrityError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.state import initialize, verify

ROOT = Path(__file__).resolve().parents[1]


def _project(tmp_path: Path) -> Path:
    project = initialize("capsule", "what execution evidence was produced?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    create_handoff(
        project,
        "computation/job.json",
        "what execution evidence was produced?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )
    output = project / "computation/result.out"
    output.write_text("converged\n", encoding="utf-8")
    record_receipt(
        project,
        "computation/job.json",
        "Gaussian",
        ["g16", "job.com"],
        0,
        ["computation/result.out"],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:10:00Z",
        engine_version="16",
        environment=["OMP_NUM_THREADS=8", "QUEUE=cpu"],
    )
    return project


def test_receipt_record_and_verify(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = verify_receipts(project)
    assert result == {
        "valid": True,
        "receipts": 1,
        "verified_outputs": 1,
        "successful": 1,
        "failed": 0,
    }
    assert verify(project)["execution_receipts"] == 1
    receipt = json.loads((project / "execution-receipts.jsonl").read_text(encoding="utf-8").strip())
    schema = json.loads((ROOT / "schemas/v2/execution-receipt.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(receipt)


def test_receipt_detects_output_tampering(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "computation/result.out").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="checksum mismatch"):
        verify_receipts(project)


def test_capsule_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    project = _project(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    result = export_capsule(project, first, mode="full")
    export_capsule(project, second, mode="full")
    assert first.read_bytes() == second.read_bytes()
    assert result["files"] > 5
    verified = verify_capsule(first)
    assert verified["valid"] is True
    with zipfile.ZipFile(first) as handle:
        manifest = json.loads(handle.read("capsule/manifest.json"))
    schema = json.loads((ROOT / "schemas/v2/reproducibility-capsule.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)


def test_capsule_detects_manifest_preserving_tamper(tmp_path: Path) -> None:
    project = _project(tmp_path)
    original = tmp_path / "original.zip"
    tampered = tmp_path / "tampered.zip"
    export_capsule(project, original, mode="full")
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename.endswith("computation/result.out"):
                payload = b"tampered\n"
            target.writestr(info, payload)
    with pytest.raises(IntegrityError, match="checksum mismatch"):
        verify_capsule(tampered)


def test_metadata_capsule_excludes_raw_data(tmp_path: Path) -> None:
    project = _project(tmp_path)
    capsule = tmp_path / "metadata.zip"
    export_capsule(project, capsule, mode="metadata")
    with zipfile.ZipFile(capsule) as handle:
        names = set(handle.namelist())
    assert "capsule/project/data/input.dat" not in names
    assert "capsule/project/project.yaml" in names


def test_success_receipt_requires_output(tmp_path: Path) -> None:
    project = initialize("receipt", "what output was produced?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    create_handoff(
        project,
        "computation/job.json",
        "what output was produced?",
        "energy",
        "q",
        ["DFT"],
        ["data/input.dat"],
    )
    from tsao_researcher.errors import ValidationError

    with pytest.raises(ValidationError, match="requires at least one"):
        record_receipt(
            project,
            "computation/job.json",
            "engine",
            ["run"],
            0,
            [],
            "2026-07-24T00:00:00Z",
            "2026-07-24T00:00:01Z",
        )


def test_failed_receipt_is_explicit_and_may_have_no_output(tmp_path: Path) -> None:
    project = initialize("receipt", "why did execution fail?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    create_handoff(
        project, "computation/job.json", "why did execution fail?", "energy", "q", ["DFT"], ["data/input.dat"]
    )
    receipt = record_receipt(
        project,
        "computation/job.json",
        "engine",
        ["run"],
        2,
        [],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:00:01Z",
    )
    assert receipt["status"] == "failed" and receipt["evidence_level"] == "failed"
    assert verify_receipts(project)["failed"] == 1


def test_receipt_detects_handoff_and_duration_tampering(tmp_path: Path) -> None:
    project = _project(tmp_path)
    log = project / "execution-receipts.jsonl"
    receipt = json.loads(log.read_text(encoding="utf-8"))
    receipt["duration_seconds"] = 1
    log.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="duration mismatch"):
        verify_receipts(project)
    receipt["duration_seconds"] = 600
    receipt["handoff_id"] = "COMP-tampered"
    log.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="handoff mismatch"):
        verify_receipts(project)


def test_capsule_rejects_unsafe_or_incomplete_archives(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as handle:
        handle.writestr("../escape", b"x")
    with pytest.raises(IntegrityError, match="unsafe capsule member"):
        verify_capsule(unsafe)
    missing = tmp_path / "missing.zip"
    with zipfile.ZipFile(missing, "w") as handle:
        handle.writestr("capsule/readme.txt", b"x")
    with pytest.raises(IntegrityError, match="manifest is missing"):
        verify_capsule(missing)


def test_receipt_input_boundaries(tmp_path: Path) -> None:
    from tsao_researcher import receipts as receipt_module
    from tsao_researcher.errors import ValidationError

    project = initialize("receipt", "what boundaries are enforced?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    create_handoff(
        project,
        "computation/job.json",
        "what boundaries are enforced?",
        "energy",
        "q",
        ["DFT"],
        ["data/input.dat"],
    )
    output = project / "computation/result.out"
    output.write_bytes(b"result")
    base = {
        "root": project,
        "handoff_path": "computation/job.json",
        "engine": "engine",
        "command": ["run"],
        "exit_code": 0,
        "outputs": ["computation/result.out"],
        "started_at": "2026-07-24T00:00:00Z",
        "finished_at": "2026-07-24T00:00:01Z",
    }
    for field, value, message in [
        ("started_at", "", "required"),
        ("started_at", "not-a-time", "ISO-8601"),
        ("started_at", "2026-07-24T00:00:00", "timezone"),
        ("finished_at", "2026-07-23T23:59:59Z", "must not precede"),
        ("engine", " ", "engine"),
        ("command", [""], "command vector"),
        ("handoff_path", "../outside.json", "escapes"),
        ("handoff_path", "missing.json", "not a regular"),
    ]:
        args = dict(base)
        args[field] = value
        with pytest.raises(ValidationError, match=message):
            record_receipt(**args)
    with pytest.raises(ValidationError, match="KEY=VALUE"):
        record_receipt(**base, environment=["BAD"])
    with pytest.raises(ValidationError, match="KEY=VALUE"):
        record_receipt(**base, environment=["A=1", "A=2"])
    with pytest.raises(ValidationError, match="more than"):
        receipt_module._output_records(project, ["x"] * (receipt_module.MAX_OUTPUT_FILES + 1))


def test_receipt_registry_and_semantic_tamper_boundaries(tmp_path: Path) -> None:
    import yaml

    project = _project(tmp_path)
    project_path = project / "project.yaml"
    record = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    record["execution_receipts"].append(record["execution_receipts"][0])
    project_path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="duplicate IDs"):
        verify_receipts(project)

    project = _project(tmp_path / "second")
    log = project / "execution-receipts.jsonl"
    receipt = json.loads(log.read_text(encoding="utf-8"))
    receipt["status"] = "unknown"
    log.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="status invalid"):
        verify_receipts(project)


def test_capsule_manifest_identity_and_member_boundaries(tmp_path: Path) -> None:
    project = _project(tmp_path)
    original = tmp_path / "original-boundaries.zip"
    export_capsule(project, original, mode="full")
    invalid_id = tmp_path / "invalid-id.zip"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(invalid_id, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "capsule/manifest.json":
                manifest = json.loads(payload)
                manifest["capsule_id"] = "CAP-" + "0" * 24
                payload = (json.dumps(manifest, sort_keys=True) + "\n").encode()
            target.writestr(info, payload)
    with pytest.raises(IntegrityError, match="identifier"):
        verify_capsule(invalid_id)

    duplicate = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning, match="Duplicate name"), zipfile.ZipFile(duplicate, "w") as target:
        target.writestr("capsule/manifest.json", b"{}")
        target.writestr("capsule/manifest.json", b"{}")
    with pytest.raises(IntegrityError, match="duplicate capsule member"):
        verify_capsule(duplicate)

    with pytest.raises(FileNotFoundError):
        verify_capsule(tmp_path / "does-not-exist.zip")


def test_capsule_detects_tree_digest_tampering_with_consistent_identifier(
    tmp_path: Path,
) -> None:
    import hashlib

    from tsao_researcher.io import canonical_json

    project = _project(tmp_path)
    original = tmp_path / "tree-original.zip"
    tampered = tmp_path / "tree-tampered.zip"
    export_capsule(project, original, mode="full")
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "capsule/manifest.json":
                manifest = json.loads(payload)
                manifest["tree_sha256"] = "0" * 64
                identity = dict(manifest)
                identity.pop("capsule_id", None)
                manifest["capsule_id"] = (
                    "CAP-" + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:24]
                )
                payload = (canonical_json(manifest) + "\n").encode("utf-8")
            target.writestr(info, payload)
    with pytest.raises(IntegrityError, match="tree digest mismatch"):
        verify_capsule(tampered)
