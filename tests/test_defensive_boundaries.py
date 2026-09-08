from __future__ import annotations

import io as stdlib_io
import json
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from tsao_researcher import capsule as capsule_module
from tsao_researcher import io as io_module
from tsao_researcher import receipts as receipts_module
from tsao_researcher import router as router_module
from tsao_researcher import state as state_module
from tsao_researcher.__main__ import _emit, _load_quality_request, main
from tsao_researcher.capabilities import load_capabilities, search_capabilities
from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.errors import IntegrityError, StateTransitionError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import (
    append_jsonl,
    atomic_write_text,
    clear_json_cache,
    exclusive_lock,
    iter_jsonl,
    load_json,
    new_id,
    read_jsonl,
    read_text,
    sha256_file,
)
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.router import load_rules, normalize
from tsao_researcher.scientific_quality import (
    check_evidence_traceability,
    check_measurement_boundary,
    evaluate_quality,
    guard_causal_claim,
)
from tsao_researcher.state import initialize, load_project, transition, verify


def _symlink_or_skip(target: Path, link: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


def _receipt_project(tmp_path: Path) -> Path:
    project = initialize("defensive", "what execution evidence was produced?", tmp_path)
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
        "engine",
        ["run"],
        0,
        ["computation/result.out"],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:00:01Z",
    )
    return project


def _load_receipt(project: Path) -> dict[str, Any]:
    return json.loads((project / receipts_module.RECEIPT_LOG).read_text(encoding="utf-8"))


def _write_receipt(project: Path, receipt: Any) -> None:
    (project / receipts_module.RECEIPT_LOG).write_text(json.dumps(receipt) + "\n", encoding="utf-8")


def test_io_identifier_regular_file_and_cache_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="prefix"):
        new_id("***")
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        read_text(missing)
    large = tmp_path / "large.txt"
    large.write_text("ab", encoding="utf-8")
    with pytest.raises(ValidationError, match="exceeds"):
        read_text(large, max_bytes=1)
    payload = tmp_path / "payload.json"
    payload.write_text('{"value": 1}', encoding="utf-8")
    assert load_json(payload)["value"] == 1
    clear_json_cache()
    assert load_json(payload)["value"] == 1


def test_io_symlink_and_write_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target.txt"
    target.write_text("original", encoding="utf-8")
    link = tmp_path / "link.txt"
    _symlink_or_skip(target, link)
    with pytest.raises(ValidationError, match="symbolic-link"):
        read_text(link)
    with pytest.raises(ValidationError, match="symbolic link"):
        atomic_write_text(link, "replacement")
    with pytest.raises(ValidationError, match="symbolic link"):
        append_jsonl(link, {"x": 1})
    with pytest.raises(ValidationError, match="regular file"):
        sha256_file(link)

    monkeypatch.setattr(io_module, "MAX_JSONL_RECORD_BYTES", 4)
    with pytest.raises(ValidationError, match="exceeds"):
        append_jsonl(tmp_path / "oversized.jsonl", {"value": "long"})


def test_jsonl_reader_rejects_malformed_and_bounded_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert read_jsonl(tmp_path / "absent.jsonl") == []
    blank = tmp_path / "blank.jsonl"
    blank.write_text("\n{}\n", encoding="utf-8")
    assert read_jsonl(blank) == [{}]

    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("{\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid JSON"):
        list(iter_jsonl(invalid))

    non_object = tmp_path / "non-object.jsonl"
    non_object.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="must be an object"):
        list(iter_jsonl(non_object))

    non_finite = tmp_path / "non-finite.jsonl"
    non_finite.write_text('{"x": NaN}\n', encoding="utf-8")
    with pytest.raises(ValidationError, match="non-finite"):
        list(iter_jsonl(non_finite))

    many = tmp_path / "many.jsonl"
    many.write_text("{}\n{}\n", encoding="utf-8")
    monkeypatch.setattr(io_module, "MAX_JSONL_RECORDS", 1)
    with pytest.raises(ValidationError, match="too many"):
        list(iter_jsonl(many))


def test_jsonl_short_write_and_lock_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_write = io_module.os.write

    def short_write(fd: int, payload: bytes) -> int:
        original_write(fd, payload[:1])
        return 1

    monkeypatch.setattr(io_module.os, "write", short_write)
    with pytest.raises(OSError, match="short JSONL write"):
        append_jsonl(tmp_path / "short.jsonl", {"value": 1})
    with (
        pytest.raises(ValidationError, match="lock timing"),
        exclusive_lock(tmp_path / "bad.lock", timeout=-1),
    ):
        pass


def test_state_load_initialize_and_rollback_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(FileNotFoundError):
        load_project(tmp_path)
    root = tmp_path / "mapping" / state_module.STATE_DIR
    root.mkdir(parents=True)
    (root / "project.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="mapping"):
        load_project(root)

    with pytest.raises(ValidationError, match="substantive"):
        initialize("", "x", tmp_path / "bad-name")
    with pytest.raises(ValidationError, match="unsupported"):
        initialize("study", "a real question", tmp_path / "bad-type", research_type="invalid")

    managed = initialize("study", "a real question", tmp_path / "managed")
    with pytest.raises(FileExistsError):
        initialize("study", "a real question", tmp_path / "managed")
    replaced = initialize("study-2", "another question", tmp_path / "managed", force=True)
    assert replaced == managed and load_project(replaced)["name"] == "study-2"

    original = state_module._write_project
    calls = 0

    def fail_once(path: Path, project: dict[str, Any]) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated staging failure")
        original(path, project)

    monkeypatch.setattr(state_module, "_write_project", fail_once)
    parent = tmp_path / "rollback"
    with pytest.raises(OSError, match="staging failure"):
        initialize("study", "a real question", parent)
    assert not list(parent.glob(".tsao-research.stage-*"))


def test_project_file_symlinks_are_rejected_across_handoff_receipt_and_state(
    tmp_path: Path,
) -> None:
    project = initialize("symlink", "what path boundary is enforced?", tmp_path)
    real_input = project / "data/real.dat"
    real_input.write_bytes(b"input")
    input_link = project / "data/link.dat"
    _symlink_or_skip(real_input, input_link)
    with pytest.raises(ValidationError, match="regular project file"):
        create_handoff(
            project,
            "computation/link-input.json",
            "what path boundary is enforced?",
            "energy",
            "quantum",
            ["DFT"],
            ["data/link.dat"],
        )

    create_handoff(
        project,
        "computation/job.json",
        "what path boundary is enforced?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/real.dat"],
    )
    output_target = project / "computation/real.out"
    output_target.write_text("result", encoding="utf-8")
    output_link = project / "computation/link.out"
    _symlink_or_skip(output_target, output_link)
    with pytest.raises(ValidationError, match="regular project file"):
        record_receipt(
            project,
            "computation/job.json",
            "engine",
            ["run"],
            0,
            ["computation/link.out"],
            "2026-07-24T00:00:00Z",
            "2026-07-24T00:00:01Z",
        )

    handoff_target = project / "computation/job.json"
    handoff_link = project / "computation/job-link.json"
    _symlink_or_skip(handoff_target, handoff_link)
    project_file = project / "project.yaml"
    record = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    record["computation_handoffs"] = ["computation/job-link.json"]
    project_file.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="regular project file"):
        verify(project)

    handoff_output_target = project / "computation/target.json"
    handoff_output_target.write_text("keep", encoding="utf-8")
    handoff_output_link = project / "computation/output-link.json"
    _symlink_or_skip(handoff_output_target, handoff_output_link)
    with pytest.raises(ValidationError, match="symbolic link"):
        create_handoff(
            project,
            "computation/output-link.json",
            "what path boundary is enforced?",
            "energy",
            "quantum",
            ["DFT"],
            ["data/real.dat"],
        )


def test_state_transition_validation_boundaries(tmp_path: Path) -> None:
    project = initialize("study", "what mechanism is tested?", tmp_path)
    with pytest.raises(ValidationError, match="reason"):
        transition(project, "planned", " ")
    with pytest.raises(StateTransitionError, match="illegal"):
        transition(project, "accepted", "skip states", approvals=["APR-1"])

    project_file = project / "project.yaml"
    record = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    record["approvals"] = "invalid"
    project_file.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="approvals"):
        transition(project, "planned", "plan")


def test_state_verify_registry_handoff_receipt_and_chain_boundaries(tmp_path: Path) -> None:
    project = initialize("study", "what mechanism is tested?", tmp_path / "missing-registry")
    (project / "questions.json").unlink()
    with pytest.raises(IntegrityError, match="registry missing"):
        verify(project)

    project = initialize("study", "what mechanism is tested?", tmp_path / "invalid-registry")
    (project / "questions.json").write_text('{"questions": "bad"}', encoding="utf-8")
    with pytest.raises(IntegrityError, match="invalid project registry"):
        verify(project)

    project = initialize("study", "what mechanism is tested?", tmp_path / "handoff-list")
    path = project / "project.yaml"
    record = yaml.safe_load(path.read_text(encoding="utf-8"))
    record["computation_handoffs"] = "bad"
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="handoffs"):
        verify(project)

    project = initialize("study", "what mechanism is tested?", tmp_path / "receipt-list")
    path = project / "project.yaml"
    record = yaml.safe_load(path.read_text(encoding="utf-8"))
    record["execution_receipts"] = "bad"
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="execution_receipts"):
        verify(project)

    project = initialize("study", "what mechanism is tested?", tmp_path / "empty-chain")
    (project / "state/events.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(IntegrityError, match="empty"):
        verify(project)

    project = initialize("study", "what mechanism is tested?", tmp_path / "wrong-head")
    path = project / "project.yaml"
    record = yaml.safe_load(path.read_text(encoding="utf-8"))
    record["latest_event_hash"] = "0" * 64
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="latest_event_hash"):
        verify(project)


def test_receipt_record_rejects_wrong_handoff_and_registry(tmp_path: Path) -> None:
    project = _receipt_project(tmp_path / "valid")
    handoff_path = project / "computation/job.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["project_id"] = "TSR-other"
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    with pytest.raises(ValidationError, match="does not belong"):
        record_receipt(
            project,
            "computation/job.json",
            "engine",
            ["run"],
            1,
            [],
            "2026-07-24T00:00:00Z",
            "2026-07-24T00:00:01Z",
        )

    project = _receipt_project(tmp_path / "registry")
    project_file = project / "project.yaml"
    record = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    record["execution_receipts"] = "invalid"
    project_file.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="must be a list"):
        record_receipt(
            project,
            "computation/job.json",
            "engine",
            ["run"],
            1,
            [],
            "2026-07-24T00:00:00Z",
            "2026-07-24T00:00:01Z",
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda row: row.update(receipt_id="bad"), "invalid ID"),
        (lambda row: row.update(project_id="TSR-other"), "project mismatch"),
        (lambda row: row.update(handoff_path="../escape"), "escapes project state"),
        (lambda row: row.update(started_at="not-a-time"), "timestamp invalid"),
        (
            lambda row: row.update(started_at="2026-07-24T00:00:02Z", finished_at="2026-07-24T00:00:01Z"),
            "negative duration",
        ),
        (lambda row: row.update(exit_code=7), "successful execution receipt semantics"),
        (
            lambda row: row.update(status="failed", evidence_level="executed"),
            "failed execution receipt semantics",
        ),
        (lambda row: row.update(outputs="bad"), "outputs invalid"),
        (lambda row: row.update(outputs=[1]), "output invalid"),
        (lambda row: row.update(outputs=row["outputs"] * 2), "duplicate execution output"),
        (
            lambda row: row["outputs"][0].update(path="../escape"),
            "escapes project state",
        ),
    ],
)
def test_receipt_verifier_defensive_semantics(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], None], message: str
) -> None:
    project = _receipt_project(tmp_path)
    receipt = _load_receipt(project)
    mutate(receipt)
    _write_receipt(project, receipt)
    with pytest.raises(IntegrityError, match=message):
        verify_receipts(project)


def test_receipt_verifier_non_object_and_registry_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _receipt_project(tmp_path / "non-object")
    monkeypatch.setattr(receipts_module, "read_jsonl", lambda path: ["bad"])
    with pytest.raises(IntegrityError, match="not an object"):
        verify_receipts(project)

    monkeypatch.undo()
    project = _receipt_project(tmp_path / "registry-order")
    project_file = project / "project.yaml"
    record = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    record["execution_receipts"] = ["RUN-other"]
    project_file.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    with pytest.raises(IntegrityError, match="registry does not match"):
        verify_receipts(project)


def test_capsule_export_and_archive_defensive_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = initialize("capsule", "what is reproducible?", tmp_path / "project")
    with pytest.raises(ValidationError, match="metadata or full"):
        export_capsule(project, tmp_path / "bad.zip", mode="invalid")

    destination = tmp_path / "destination.zip"
    target = tmp_path / "target.zip"
    target.write_bytes(b"x")
    _symlink_or_skip(target, destination)
    with pytest.raises(ValidationError, match="symbolic link"):
        export_capsule(project, destination, mode="full")

    with pytest.raises(IntegrityError, match="capsule/ prefix"):
        capsule_module._safe_member("other/member")

    archive = tmp_path / "symlink-member.zip"
    info = zipfile.ZipInfo("capsule/project/link")
    info.create_system = 3
    info.external_attr = (0o120777 & 0xFFFF) << 16
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(info, b"target")
        handle.writestr("capsule/manifest.json", "{}")
    with pytest.raises(IntegrityError, match="symbolic link member"):
        verify_capsule(archive)

    oversized = tmp_path / "oversized.zip"
    with zipfile.ZipFile(oversized, "w") as handle:
        handle.writestr("capsule/project/file", b"xx")
        handle.writestr("capsule/manifest.json", "{}")
    monkeypatch.setattr(capsule_module, "MAX_FILE_BYTES", 1)
    with pytest.raises(IntegrityError, match="size limit"):
        verify_capsule(oversized)


def test_capsule_manifest_inventory_boundaries(tmp_path: Path) -> None:
    invalid_schema = tmp_path / "invalid-schema.zip"
    with zipfile.ZipFile(invalid_schema, "w") as handle:
        handle.writestr("capsule/manifest.json", json.dumps({"schema_version": "bad"}))
    with pytest.raises(IntegrityError, match="schema"):
        verify_capsule(invalid_schema)

    invalid_inventory = tmp_path / "invalid-inventory.zip"
    with zipfile.ZipFile(invalid_inventory, "w") as handle:
        handle.writestr(
            "capsule/manifest.json",
            json.dumps({"schema_version": "1.0", "files": "bad", "file_count": 1}),
        )
    with pytest.raises(IntegrityError, match="inventory"):
        verify_capsule(invalid_inventory)

    invalid_record = tmp_path / "invalid-record.zip"
    with zipfile.ZipFile(invalid_record, "w") as handle:
        handle.writestr(
            "capsule/manifest.json",
            json.dumps({"schema_version": "1.0", "files": ["bad"], "file_count": 1}),
        )
    with pytest.raises(IntegrityError, match="record"):
        verify_capsule(invalid_record)

    missing_member = tmp_path / "missing-member.zip"
    record = {"path": "missing.txt", "size_bytes": 1, "sha256": "0" * 64, "role": "artifact"}
    with zipfile.ZipFile(missing_member, "w") as handle:
        handle.writestr(
            "capsule/manifest.json",
            json.dumps({"schema_version": "1.0", "files": [record], "file_count": 1}),
        )
    with pytest.raises(IntegrityError, match="member missing"):
        verify_capsule(missing_member)


def test_capability_catalog_and_search_defensive_boundaries(tmp_path: Path) -> None:
    bad_values = [
        ({"bad": True}, "catalog must be a list"),
        (["bad"], "must be an object"),
        ([{"id": "A"}], "lacks id or slug"),
        ([{"id": "A", "slug": "a"}, {"id": "A", "slug": "b"}], "duplicate"),
    ]
    for index, (value, message) in enumerate(bad_values):
        path = tmp_path / f"catalog-{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_capabilities(path)

    assert search_capabilities("   ") == []
    assert search_capabilities("molecular dynamics", workflow="does-not-exist") == []
    exact = search_capabilities("publication-quality-plot", limit=1)
    assert exact and exact[0]["slug"] == "publication-quality-plot"


def test_router_rule_validation_boundaries(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="string"):
        normalize(1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="blank"):
        router_module._trigger("   ")

    bad_rules = [
        ([], "non-empty object"),
        ({"rule": []}, "invalid router rule entry"),
        ({"rule": {"weight": 0, "positive": ["x"]}}, "weight or priority"),
        ({"rule": {"positive": "x"}}, "string list"),
        ({"rule": {"positive": []}}, "no positive trigger"),
    ]
    for index, (value, message) in enumerate(bad_rules):
        path = tmp_path / f"rules-{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_rules(path)


def test_quality_guard_defensive_and_warning_branches() -> None:
    with pytest.raises(ValidationError, match="spec"):
        evaluate_quality({"kind": "measurement-boundary", "spec": []})
    with pytest.raises(ValidationError, match="conditions"):
        check_measurement_boundary(
            {"measurand": "mass", "method": "balance", "sample": "x", "conditions": "23 C", "unit": "g"}
        )

    measurement = check_measurement_boundary(
        {"measurand": "mass", "method": "balance", "sample": "x", "conditions": ["23 C"], "unit": "g"}
    )
    assert measurement["status"] == "BLOCK"
    assert any(row["code"] == "MB-CALIBRATION" for row in measurement["findings"])

    association = guard_causal_claim({"claim": "A is associated with B.", "design": "observational"})
    assert association["details"]["verdict"] == "association-only"
    negated = guard_causal_claim({"claim": "A does not cause B.", "design": "observational"})
    assert negated["details"]["causal_wording_detected"] is False
    mechanism = guard_causal_claim(
        {
            "claim": "A mechanism is consistent with B.",
            "design": "observational",
            "temporal_order": True,
            "confounders_addressed": True,
            "mechanism_tested": True,
        }
    )
    assert mechanism["details"]["verdict"] == "mechanism-consistent"
    supported = guard_causal_claim(
        {
            "claim": "A causes B.",
            "design": "randomized controlled experiment",
            "temporal_order": True,
            "confounders_addressed": True,
            "comparison_or_control": True,
            "replication": False,
            "mechanism_tested": False,
            "uncertainty_reported": False,
        }
    )
    codes = {row["code"] for row in supported["findings"]}
    assert {"CG-REPLICATION", "CG-UNCERTAINTY"}.issubset(codes)

    trace = check_evidence_traceability(
        {
            "claim_id": "CLM-1",
            "claim": "bounded",
            "evidence_ids": ["E1", "E1"],
            "source_locators": ["source"],
            "evidence_roles": ["direct"],
            "execution_claim": False,
        }
    )
    trace_codes = {row["code"] for row in trace["findings"]}
    assert {"ET-DUPLICATE", "ET-LOCATORS", "ET-ROLES", "ET-UNCERTAINTY"}.issubset(trace_codes)


def test_cli_unicode_fallback_quality_root_and_block_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FallbackStream:
        def __init__(self) -> None:
            self.calls = 0
            self.value = ""

        def write(self, value: str) -> int:
            self.calls += 1
            if self.calls == 1:
                raise UnicodeEncodeError("ascii", value, 0, 1, "test")
            self.value += value
            return len(value)

    stream = FallbackStream()
    monkeypatch.setattr(sys, "stdout", stream)
    _emit({"中文": "值"})
    assert "\\u4e2d" in stream.value

    non_object = tmp_path / "quality-list.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        _load_quality_request(str(non_object))

    request = tmp_path / "quality-block.json"
    request.write_text(
        json.dumps(
            {
                "kind": "measurement-boundary",
                "spec": {
                    "measurand": "mass",
                    "method": "balance",
                    "sample": "specimen",
                    "conditions": ["23 C"],
                    "unit": "g",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "stdout", stdlib_io.StringIO())
    monkeypatch.setattr(sys, "argv", ["tsao-researcher", "quality", str(request)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
