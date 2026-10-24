"""Adversarial tests of public receipt, evidence and approval integrity boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.common import source_candidates
from scripts.generate_checksums import build as source_checksum
from tsao_researcher import input_snapshots
from tsao_researcher.capsule import export_capsule
from tsao_researcher.contracts_v17 import canonical_event_hash, make_event, replay_state
from tsao_researcher.errors import IntegrityError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.input_snapshots import input_manifest
from tsao_researcher.io import append_jsonl, canonical_json, sha256_file
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.scientific_contracts_v16 import (
    ContractError,
    causal_clauses,
    compare_quantities,
    verify_event_chain,
)
from tsao_researcher.scientific_quality import check_evidence_traceability
from tsao_researcher.state import initialize, load_project, transition, verify


def project_fixture(tmp_path: Path) -> Path:
    root = initialize("integrity", "Which bytes support this calculation?", tmp_path)
    (root / "data/input.dat").write_bytes(b"declared input\n")
    (root / "computation/output.dat").write_bytes(b"recorded output\n")
    create_handoff(
        root,
        "computation/job.json",
        "Which bytes support this calculation?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )
    return root


def receipt_fixture(root: Path, **changes: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "root": root,
        "handoff_path": "computation/job.json",
        "engine": "external-engine",
        "engine_version": "1.0",
        "command": ["engine", "input.dat"],
        "exit_code": 0,
        "outputs": ["computation/output.dat"],
        "started_at": "2026-10-20T00:00:00Z",
        "finished_at": "2026-10-20T00:00:01Z",
    }
    args.update(changes)
    return record_receipt(**args)


def overwrite_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n")


def manifest_fixture() -> dict[str, Any]:
    return {"path": "data/input.dat", "size_bytes": 1, "sha256": "a" * 64}


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        [None],
        [manifest_fixture()] * 10001,
        [dict(manifest_fixture(), path=value) for value in ["data/input.dat", "data/input.dat"]],
        *[
            [dict(manifest_fixture(), path=value)]
            for value in [
                "",
                "..",
                "../escape",
                "/absolute",
                "C:/absolute",
                "./data/input.dat",
                1,
            ]
        ],
        *[[dict(manifest_fixture(), size_bytes=value)] for value in [True, -1, 1.5, "1"]],
        *[[dict(manifest_fixture(), sha256=value)] for value in ["x", "A" * 64, 1]],
    ],
)
def test_input_manifest_rejects_malformed_or_ambiguous_records(value: Any) -> None:
    with pytest.raises(ValidationError):
        input_manifest(value)


def test_snapshot_preserves_historical_input_and_full_capsule_bytes(tmp_path: Path) -> None:
    root = project_fixture(tmp_path)
    first = receipt_fixture(root)
    second = receipt_fixture(root)
    assert first["input_snapshots"] == second["input_snapshots"]
    (root / "data/input.dat").write_bytes(b"new mutable work in progress")
    assert verify(root)["valid"] is True
    snapshot = first["input_snapshots"][0]["snapshot_path"]
    assert (root / snapshot).read_bytes() == b"declared input\n"
    for mode in ("full", "metadata"):
        archive = tmp_path / f"{mode}.zip"
        export_capsule(root, archive, mode=mode)
        with zipfile.ZipFile(archive) as handle:
            assert (f"capsule/project/{snapshot}" in handle.namelist()) == (mode == "full")


def test_input_changed_before_recording_does_not_get_receipt(tmp_path: Path) -> None:
    root = project_fixture(tmp_path)
    (root / "data/input.dat").write_bytes(b"changed")
    with pytest.raises(ValidationError, match="input checksum"):
        receipt_fixture(root)
    assert verify_receipts(root)["receipts"] == 0


@pytest.mark.parametrize("kind", ["missing", "tampered", "wrong-binding", "boolean-size", "empty", "symlink"])
def test_snapshots_are_actually_verified_by_state_entrypoint(tmp_path: Path, kind: str) -> None:
    root = project_fixture(tmp_path)
    receipt = receipt_fixture(root)
    snapshot = root / receipt["input_snapshots"][0]["snapshot_path"]
    if kind == "missing":
        snapshot.unlink()
    elif kind == "tampered":
        snapshot.write_bytes(b"tampered")
        with pytest.raises(IntegrityError, match="existing input snapshot"):
            receipt_fixture(root)
    elif kind == "wrong-binding":
        receipt["input_snapshots"][0]["path"] = "data/other.dat"
    elif kind == "boolean-size":
        receipt["input_snapshots"][0]["size_bytes"] = True
    elif kind == "empty":
        receipt["input_snapshots"] = []
    else:
        snapshot.unlink()
        snapshot.symlink_to(root / "data/input.dat")
    overwrite_record(root / "execution-receipts.jsonl", receipt)
    with pytest.raises(IntegrityError):
        verify(root)


def test_snapshot_copy_detects_midstream_input_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project_fixture(tmp_path)
    original = input_snapshots._matches

    def change_after_hash(path: Path, item: dict[str, Any]) -> bool:
        result = original(path, item)
        path.write_bytes(b"input changed during snapshot")
        return result

    monkeypatch.setattr(input_snapshots, "_matches", change_after_hash)
    with pytest.raises(ValidationError, match="while taking snapshot"):
        receipt_fixture(root)
    assert not list((root / "artifacts/input-snapshots").glob(".snapshot-*"))


@pytest.mark.parametrize("corrupt", [False, True])
def test_snapshot_race_never_overwrites_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: bool
) -> None:
    root = project_fixture(tmp_path)

    def concurrent_create(source: Path, destination: Path) -> None:
        destination.write_bytes(b"bad" if corrupt else source.read_bytes())
        raise FileExistsError(destination)

    monkeypatch.setattr(os, "link", concurrent_create)
    if corrupt:
        with pytest.raises(IntegrityError, match="concurrent"):
            receipt_fixture(root)
    else:
        receipt_fixture(root)
        assert verify(root)["valid"]


def test_snapshot_directory_and_input_symlinks_are_rejected(tmp_path: Path) -> None:
    root = project_fixture(tmp_path)
    (root / "artifacts/input-snapshots").symlink_to(root / "data", target_is_directory=True)
    with pytest.raises(ValidationError, match="symbolic-link"):
        receipt_fixture(root)
    (root / "artifacts/input-snapshots").unlink()
    (root / "data/input.dat").unlink()
    (root / "data/input.dat").symlink_to(root / "computation/output.dat")
    with pytest.raises(ValidationError, match="regular"):
        receipt_fixture(root)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("outputs", "computation/output.dat"),
        ("outputs", [""]),
        ("outputs", ["computation/output.dat"] * 2),
        ("environment", "A=1"),
        ("environment", [1]),
        ("notes", None),
        ("engine_version", None),
        ("started_at", 1),
    ],
)
def test_record_receipt_rejects_ambiguous_public_arguments(tmp_path: Path, field: str, value: Any) -> None:
    root = project_fixture(tmp_path)
    with pytest.raises(ValidationError):
        receipt_fixture(root, **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("engine", None),
        ("engine", {"name": "", "version": "1"}),
        ("engine", {"name": "engine", "version": 1}),
        ("engine", {"name": "engine", "version": ""}),
        ("command", "engine input.dat"),
        ("command", []),
        ("command", [" "]),
        ("environment", {"A": 1}),
        ("environment", []),
        ("environment", {" ": "1"}),
        ("notes", 1),
    ],
)
def test_verify_receipt_rejects_untyped_persisted_execution_declarations(
    tmp_path: Path, field: str, value: Any
) -> None:
    root = project_fixture(tmp_path)
    receipt = receipt_fixture(root)
    receipt[field] = value
    overwrite_record(root / "execution-receipts.jsonl", receipt)
    with pytest.raises(IntegrityError):
        verify(root)


def test_state_verification_rehashes_output_not_only_receipt_ids(tmp_path: Path) -> None:
    root = project_fixture(tmp_path)
    receipt_fixture(root)
    (root / "computation/output.dat").write_bytes(b"wrong output")
    with pytest.raises(IntegrityError, match="checksum mismatch"):
        verify(root)
    with pytest.raises(IntegrityError):
        transition(root, "planned", "must not advance corrupted evidence")


def accepted_fixture(tmp_path: Path) -> Path:
    root = initialize("approval", "Who declared this transition?", tmp_path)
    for state in ("planned", "running", "completed", "checked", "validated"):
        transition(root, state, f"advance to {state}")
    transition(root, "accepted", "record local declaration", approvals=["review://local/42"])
    return root


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_id", "foreign"),
        ("scope", "other"),
        ("event_hash", "0" * 64),
        ("transition", "planned"),
        ("timestamp", "2020-01-01T00:00:00Z"),
        ("timestamp", "bad"),
        ("approval_id", ""),
        ("reference", ""),
        ("identity_verification", "VERIFIED"),
        *[("revoked", value) for value in [True, "false", "true", 0, 1, None]],
    ],
)
def test_accepted_transition_binds_actual_approval_ledger(tmp_path: Path, field: str, value: Any) -> None:
    root = accepted_fixture(tmp_path)
    path = root / "approvals.jsonl"
    approval = json.loads(path.read_text())
    assert approval["identity_verification"] == "DECLARED_NOT_IDENTITY_VERIFIED"
    approval[field] = value
    overwrite_record(path, approval)
    with pytest.raises(IntegrityError):
        verify(root)


def test_approval_false_revocation_unique_ids_and_registry_are_checked(tmp_path: Path) -> None:
    root = accepted_fixture(tmp_path)
    path = root / "approvals.jsonl"
    approval = json.loads(path.read_text())
    approval["revoked"] = False
    overwrite_record(path, approval)
    assert verify(root)["status"] == "accepted"
    append_jsonl(path, approval)
    with pytest.raises(IntegrityError, match="duplicate"):
        verify(root)
    overwrite_record(path, approval)
    project = load_project(root)
    project["approvals"] = []
    (root / "project.yaml").write_text(yaml.safe_dump(project))
    with pytest.raises(IntegrityError, match="ledger"):
        verify(root)


def test_accepted_requires_fresh_reference_and_existing_state_integrity(tmp_path: Path) -> None:
    root = initialize("approval", "Fresh authorization?", tmp_path)
    transition(root, "planned", "early declaration", approvals=["early-review"])
    for state in ("running", "completed", "checked", "validated"):
        transition(root, state, "advance")
    with pytest.raises(ValidationError, match="fresh"):
        transition(root, "accepted", "cannot reuse old scope", approvals=["early-review"])
    with pytest.raises(ValidationError, match="nonblank"):
        transition(root, "accepted", "invalid refs", approvals=[1])  # type: ignore[list-item]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("next_state", "accepted"),
        ("previous_state", "validated"),
        ("timestamp", "1900-01-01T00:00:00Z"),
        ("timestamp", "not-time"),
        ("timestamp", "2026-10-20T00:00:00"),
        ("timestamp", 1),
    ],
)
def test_rehashed_event_still_requires_legal_edges_and_time(tmp_path: Path, field: str, value: Any) -> None:
    root = initialize("edges", "Legal transition?", tmp_path)
    transition(root, "planned", "plan")
    path = root / "state/events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[-1][field] = value
    body = {key: val for key, val in events[-1].items() if key != "event_hash"}
    events[-1]["event_hash"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    path.write_text("".join(json.dumps(event) + "\n" for event in events))
    project = load_project(root)
    project["latest_event_hash"] = events[-1]["event_hash"]
    project["status"] = events[-1]["next_state"]
    (root / "project.yaml").write_text(yaml.safe_dump(project))
    with pytest.raises(IntegrityError):
        verify(root)


def evidence_fixture(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    root = project_fixture(tmp_path)
    receipt = receipt_fixture(root)
    statement = "The supplied calculation produced the registered output."
    append_jsonl(
        root / "claims.jsonl",
        {
            "schema_version": "1.0",
            "claim_id": "CL-1",
            "statement": statement,
            "claim_type": "calculation",
            "evidence_ids": ["EV-1"],
            "assumptions": [],
            "status": "checked",
            "limitations": ["declared external execution"],
        },
    )
    append_jsonl(
        root / "evidence.jsonl",
        {
            "schema_version": "1.0",
            "evidence_id": "EV-1",
            "evidence_type": "calculation",
            "title": "local output",
            "source": {
                "kind": "computation",
                "locator": "computation/output.dat",
                "checksum": sha256_file(root / "computation/output.dat"),
            },
            "supports_claims": ["CL-1"],
            "refutes_claims": [],
            "limitations": ["not independent scientific validation"],
        },
    )
    return root, {
        "project_root": str(root),
        "claim_id": "CL-1",
        "claim": statement,
        "evidence_ids": ["EV-1"],
        "source_locators": ["computation/output.dat"],
        "evidence_roles": ["execution-receipt"],
        "execution_claim": True,
        "execution_receipts": [receipt["receipt_id"]],
        "uncertainty": "Supplied execution and scientific truth are not authenticated.",
    }


def test_traceability_resolves_real_project_and_ignores_self_certifying_flags(tmp_path: Path) -> None:
    root, spec = evidence_fixture(tmp_path)
    result = check_evidence_traceability(spec)
    assert result["status"] == "PASS"
    assert result["details"]["verification_status"] == "LOCAL_ARTIFACT_LINKS_VERIFIED"
    assert result["details"]["bidirectional_traceability"] is True
    assert result["details"]["bound_receipts"] == spec["execution_receipts"]
    spec.pop("project_root")
    spec.update(sources_verified=True, receipts_verified=True, bidirectional_traceability=True)
    result = check_evidence_traceability(spec)
    assert result["status"] == "WARN" and result["details"]["bidirectional_traceability"] is False
    assert result["details"]["verification_status"] == "UNVERIFIED_DECLARATION"
    assert root.exists()


@pytest.mark.parametrize(
    "kind",
    [
        "claim-text",
        "missing-claim",
        "duplicate-claim",
        "missing-evidence",
        "duplicate-evidence",
        "missing-reverse",
        "refuted",
        "bad-checksum",
        "no-checksum",
        "wrong-kind",
        "wrong-locator",
        "wrong-output-binding",
        "background",
        "unbound-receipt",
        "unknown-receipt",
        "duplicate-receipt",
        "rejected-claim",
        "invalid-links",
        "extra-evidence",
        "missing-roles",
    ],
)
def test_traceability_rejects_actual_registry_or_artifact_mismatch(tmp_path: Path, kind: str) -> None:
    root, spec = evidence_fixture(tmp_path)
    claims = root / "claims.jsonl"
    evidence = root / "evidence.jsonl"
    claim = json.loads(claims.read_text())
    row = json.loads(evidence.read_text())
    if kind == "claim-text":
        spec["claim"] = "invented assertion"
    elif kind == "missing-claim":
        claims.write_text("")
    elif kind == "duplicate-claim":
        append_jsonl(claims, claim)
    elif kind == "missing-evidence":
        evidence.write_text("")
    elif kind == "duplicate-evidence":
        append_jsonl(evidence, row)
    elif kind == "missing-reverse":
        row["supports_claims"] = []
    elif kind == "refuted":
        row["refutes_claims"] = ["CL-1"]
    elif kind == "bad-checksum":
        row["source"]["checksum"] = "f" * 64
    elif kind == "no-checksum":
        row["source"].pop("checksum")
    elif kind == "wrong-kind":
        row["source"]["kind"] = "web"
    elif kind == "wrong-locator":
        spec["source_locators"] = ["computation/not-output.dat"]
    elif kind == "wrong-output-binding":
        row["source"]["locator"] = "data/input.dat"
        row["source"]["checksum"] = sha256_file(root / "data/input.dat")
        spec["source_locators"] = ["data/input.dat"]
        overwrite_record(evidence, row)
    elif kind == "background":
        spec["evidence_roles"] = ["background"]
    elif kind == "unbound-receipt":
        spec["evidence_roles"] = ["direct"]
    elif kind == "unknown-receipt":
        spec["execution_receipts"] = ["RUN-unknown"]
    elif kind == "duplicate-receipt":
        spec["execution_receipts"] *= 2
    elif kind == "rejected-claim":
        claim["status"] = "rejected"
        overwrite_record(claims, claim)
    elif kind == "invalid-links":
        row["supports_claims"] = "CL-1"
    elif kind == "extra-evidence":
        claim["evidence_ids"] = ["EV-1", "EV-2"]
        overwrite_record(claims, claim)
    else:
        spec["evidence_roles"] = []
    if kind in {"missing-reverse", "refuted", "bad-checksum", "no-checksum", "wrong-kind", "invalid-links"}:
        overwrite_record(evidence, row)
    result = check_evidence_traceability(spec)
    assert result["status"] == "BLOCK"
    assert result["details"]["bidirectional_traceability"] is False


def test_local_direct_evidence_without_execution_claim_can_verify(tmp_path: Path) -> None:
    _, spec = evidence_fixture(tmp_path)
    spec.update(evidence_roles=["direct"], execution_claim=False, execution_receipts=[])
    assert check_evidence_traceability(spec)["status"] == "PASS"
    spec["evidence_roles"] = ["TBD"]
    with pytest.raises(ValidationError, match="placeholder"):
        check_evidence_traceability(spec)


@pytest.mark.parametrize("value", [True, -1, 1.5, "0"])
def test_event_sequence_requires_an_exact_nonnegative_integer(value: Any) -> None:
    with pytest.raises(ValueError):
        canonical_event_hash(value, "GENESIS", "EVIDENCE_ADDED", {})


@pytest.mark.parametrize("value", ["true", "false", 0, 1, None])
def test_trust_flags_are_not_truthy_coercions(value: Any) -> None:
    for kind, key in (
        ("EVIDENCE_REVIEWED", "independent"),
        ("HUMAN_ACCEPTED", "qualified_approver"),
        ("EXTERNAL_EXECUTED", "signed_receipt"),
    ):
        with pytest.raises(ValueError, match="boolean"):
            replay_state([make_event(0, "GENESIS", kind, {key: value})])


def test_signed_receipt_is_a_declaration_not_verified_execution() -> None:
    assert (
        replay_state([make_event(0, "GENESIS", "EXTERNAL_EXECUTED", {"signed_receipt": True})])
        == "SIGNED_RECEIPT_DECLARED_UNVERIFIED"
    )
    with pytest.raises(ValueError, match="mapping"):
        canonical_event_hash(0, "GENESIS", "EVIDENCE_ADDED", [])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        canonical_event_hash(0, "GENESIS", "EVIDENCE_ADDED", {"x": float("nan")})


@pytest.mark.parametrize(
    ("left", "unit"), [(True, "Pa"), ("1", "Pa"), (10**400, "Pa"), (float("inf"), "Pa"), (1e308, "MPa")]
)
def test_quantity_conversion_rejects_non_numeric_nonfinite_and_overflow(left: Any, unit: str) -> None:
    with pytest.raises(ContractError):
        compare_quantities(left, unit, ">", 0, "Pa")


def test_v16_approval_declaration_type_is_explicit() -> None:
    for flag in ("true", 1, None):
        row = {"sequence": 0, "prev_hash": "0" * 64, "type": "approval", "verified": flag}
        row["record_hash"] = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        with pytest.raises(ContractError, match="boolean"):
            verify_event_chain([row])
    with pytest.raises(ContractError, match="boolean"):
        verify_event_chain([], accepted_requires_approval="true")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        "This cannot establish causality and C causes D",
        "A不能证明因果且C使得D增加",
        "结构導致性能变化",
        "结构驅動变化",
        "结构決定性能",
    ],
)
def test_local_negation_does_not_hide_separate_affirmed_causal_marker(text: str) -> None:
    assert any(clause["polarity"] == "AFFIRMED" for clause in causal_clauses(text))


def test_tracked_source_inventory_ignores_runtime_files_but_detects_source_drift(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = tmp_path / "source.py"
    tracked.write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "source.py"], check=True)
    before = source_checksum(tmp_path)
    (tmp_path / "untracked-venv-file.py").write_text("x = 100\n")
    assert source_candidates(tmp_path) == [tracked]
    assert source_checksum(tmp_path) == before
    tracked.write_text("x = 2\n")
    assert source_checksum(tmp_path) != before
    tracked.unlink()
    with pytest.raises(ValueError, match="tracked source file is missing"):
        source_candidates(tmp_path)
