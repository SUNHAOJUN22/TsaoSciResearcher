from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
import yaml

import tsao_researcher.io as io_module
import tsao_researcher.state as state_module
from scripts.install import validate_destination
from scripts.package_release import build_release
from tsao_researcher.capabilities import CATALOG_PATH, EXTENSIONS_PATH, search_capabilities
from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.errors import IntegrityError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import append_jsonl, exclusive_lock, read_jsonl
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.router import DEFAULT_RULES_PATH, route
from tsao_researcher.state import initialize, transition
from tsao_researcher.strategy import advise_computation_strategy


def _project_with_handoff(tmp_path: Path) -> Path:
    project = initialize("hardening", "Which mechanism controls the result?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    create_handoff(
        project,
        "computation/job.json",
        "Which mechanism controls the result?",
        "energy",
        "DFT",
        ["periodic DFT"],
        ["data/input.dat"],
    )
    return project


def test_installed_runtime_data_is_package_local_and_complete() -> None:
    package = Path(__file__).resolve().parents[1] / "tsao_researcher"
    assert package / "data/capabilities/capabilities.json" == CATALOG_PATH
    assert package / "data/capabilities/extensions.json" == EXTENSIONS_PATH
    assert package / "data/routing/router-rules-v2.json" == DEFAULT_RULES_PATH
    assert CATALOG_PATH.is_file() and EXTENSIONS_PATH.is_file() and DEFAULT_RULES_PATH.is_file()
    assert search_capabilities("polymer molecular dynamics", limit=1)
    assert route("literature search")["primary_workflow"] != "unknown"


def test_lock_release_never_removes_replacement_owner(tmp_path: Path) -> None:
    lock = tmp_path / "owner.lock"
    with exclusive_lock(lock):
        lock.unlink()
        lock.write_text('{"token":"replacement"}\n', encoding="utf-8")
    assert lock.read_text(encoding="utf-8") == '{"token":"replacement"}\n'


def test_jsonl_short_write_rolls_back_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "records.jsonl"
    append_jsonl(target, {"existing": True})
    original = target.read_bytes()
    real_write = io_module.os.write

    def fail_record(fd: int, payload: bytes) -> int:
        if b'"new":true' in payload:
            real_write(fd, payload[:5])
            return 5
        return real_write(fd, payload)

    monkeypatch.setattr(io_module.os, "write", fail_record)
    with pytest.raises(OSError, match="short JSONL write"):
        append_jsonl(target, {"new": True})
    assert target.read_bytes() == original
    assert read_jsonl(target) == [{"existing": True}]


def test_transition_rolls_back_all_ledgers_on_project_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = initialize("rollback", "Does the mutation remain atomic?", tmp_path)
    paths = [
        project / "project.yaml",
        project / "approvals.jsonl",
        project / "decisions.jsonl",
        project / "state/events.jsonl",
    ]
    before = {path: path.read_bytes() for path in paths}

    def fail_write(path: Path, value: dict[str, object]) -> None:
        raise OSError("simulated project write failure")

    monkeypatch.setattr(state_module, "_write_project", fail_write)
    with pytest.raises(OSError, match="simulated"):
        transition(project, "planned", "test transaction rollback")
    assert {path: path.read_bytes() for path in paths} == before


def test_handoff_cannot_claim_execution_or_validation(tmp_path: Path) -> None:
    project = initialize("truth", "What must be computed?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    with pytest.raises(ValidationError, match="unsupported evidence level"):
        create_handoff(
            project,
            "computation/job.json",
            "What must be computed?",
            "energy",
            "DFT",
            ["DFT"],
            ["data/input.dat"],
            evidence_level="validated",
        )


def test_receipt_requires_registered_ready_handoff_and_binds_checksum(tmp_path: Path) -> None:
    project = _project_with_handoff(tmp_path)
    output = project / "computation/result.out"
    output.write_text("result\n", encoding="utf-8")
    receipt = record_receipt(
        project,
        "computation/job.json",
        "engine",
        ["run"],
        0,
        ["computation/result.out"],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:00:01Z",
    )
    assert len(receipt["handoff_sha256"]) == 64
    handoff = project / "computation/job.json"
    value = json.loads(handoff.read_text(encoding="utf-8"))
    value["target_property"] = "tampered"
    handoff.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(IntegrityError, match="handoff checksum mismatch"):
        verify_receipts(project)


def test_failed_receipt_with_zero_exit_code_is_rejected(tmp_path: Path) -> None:
    project = _project_with_handoff(tmp_path)
    record_receipt(
        project,
        "computation/job.json",
        "engine",
        ["run"],
        2,
        [],
        "2026-07-24T00:00:00Z",
        "2026-07-24T00:00:01Z",
    )
    log = project / "execution-receipts.jsonl"
    value = json.loads(log.read_text(encoding="utf-8"))
    value["exit_code"] = 0
    log.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="failed execution receipt semantics"):
        verify_receipts(project)


def test_capsule_rejects_members_not_declared_by_manifest(tmp_path: Path) -> None:
    project = _project_with_handoff(tmp_path)
    capsule = tmp_path / "project.zip"
    tampered = tmp_path / "extra.zip"
    export_capsule(project, capsule, mode="full")
    with zipfile.ZipFile(capsule) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        target.writestr("capsule/project/undeclared.txt", b"extra")
    with pytest.raises(IntegrityError, match="inventory is not exact"):
        verify_capsule(tampered)


def test_ascii_trigger_matching_uses_word_boundaries() -> None:
    result = advise_computation_strategy(
        "Select a model for ordinary descriptive analysis.",
        ["decision metric"],
        ["300 K"],
        available_evidence=["measurement"],
    )
    assert result["classification"]["primary_regime"] != "molecular-statistical"
    assert route("softonic package compatibility")["human_approval_required"] is False
    assert route("Perform an FTO analysis")["human_approval_required"] is True


def test_capability_search_rejects_invalid_public_inputs() -> None:
    with pytest.raises(TypeError, match="query"):
        search_capabilities(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="domains"):
        search_capabilities("polymer", domains={1})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="limit"):
        search_capabilities("polymer", limit=True)  # type: ignore[arg-type]


def test_install_rejects_symlinked_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable")
    with pytest.raises(ValueError, match="symbolic-link component"):
        validate_destination(linked / "skill")


def test_release_output_must_not_overlap_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "VERSION").write_text("0.7.1\n", encoding="utf-8")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    with pytest.raises(ValueError, match="overlaps source"):
        build_release(source / "unsafe" / "out", root=source)


def test_generated_handoff_schema_contains_truth_boundary(tmp_path: Path) -> None:
    project = _project_with_handoff(tmp_path)
    handoff = json.loads((project / "computation/job.json").read_text(encoding="utf-8"))
    assert handoff["execution_boundary"]["solver_executed"] is False
    assert handoff["execution_boundary"]["external_execution_required"] is True
    project_yaml = yaml.safe_load((project / "project.yaml").read_text(encoding="utf-8"))
    assert project_yaml["computation_handoffs"] == ["computation/job.json"]
