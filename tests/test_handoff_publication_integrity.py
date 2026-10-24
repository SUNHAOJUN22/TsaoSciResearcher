from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

import tsao_researcher.handoff as handoff_module
import tsao_researcher.io as io_module
from tsao_researcher.errors import ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import append_jsonl, load_json, write_json
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.state import initialize, load_project


def _project(tmp_path: Path) -> Path:
    root = initialize("handoff", "Can a revised handoff preserve prior evidence?", tmp_path)
    (root / "data/input.dat").write_bytes(b"original input")
    return root


def _create(root: Path, output: str = "computation/job.json") -> dict:
    return create_handoff(
        root,
        output,
        "Can a revised handoff preserve prior evidence?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )


def _metadata(root: Path) -> tuple[bytes, bytes]:
    return (root / "project.yaml").read_bytes(), (root / "artifacts.jsonl").read_bytes()


def test_revised_handoff_requires_new_identity_and_preserves_existing_receipt(tmp_path: Path) -> None:
    root = _project(tmp_path)
    first = _create(root)
    path = root / "computation/job.json"
    original = path.read_bytes()
    (root / "computation/result.out").write_bytes(b"fixture result")
    record_receipt(
        root,
        "computation/job.json",
        "fixture",
        ["fixture"],
        0,
        ["computation/result.out"],
        "2026-10-24T01:00:00Z",
        "2026-10-24T01:00:01Z",
    )
    before = _metadata(root)
    with pytest.raises(ValidationError, match="choose a new path"):
        _create(root)
    assert path.read_bytes() == original
    assert _metadata(root) == before
    second = _create(root, "computation/job-02.json")
    assert second["handoff_id"] != first["handoff_id"]
    assert load_json(path)["handoff_id"] == first["handoff_id"]
    assert verify_receipts(root)["valid"] is True
    assert load_project(root)["computation_handoffs"] == ["computation/job-02.json", "computation/job.json"]


@pytest.mark.parametrize(
    "output", ["data/input.dat", "project.yaml", "artifacts.jsonl", "state/events.jsonl"]
)
def test_handoff_never_replaces_input_or_project_metadata(tmp_path: Path, output: str) -> None:
    root = _project(tmp_path)
    target = root / output
    before = target.read_bytes()
    metadata = _metadata(root)
    with pytest.raises(ValidationError, match="choose a new path"):
        _create(root, output)
    assert target.read_bytes() == before
    assert _metadata(root) == metadata


def test_registered_but_missing_handoff_path_cannot_be_reused(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _create(root)
    target = root / "computation/job.json"
    target.unlink()
    before = _metadata(root)
    with pytest.raises(ValidationError, match="registered"):
        _create(root)
    assert not target.exists()
    assert _metadata(root) == before


def test_registered_draft_can_be_promoted_but_prepared_identity_is_immutable(tmp_path: Path) -> None:
    root = _project(tmp_path)
    draft = create_handoff(
        root, "computation/job.json", "Draft question?", "energy", "DFT", ["PBE"], [], ready=False
    )
    prepared = _create(root)
    assert prepared["handoff_id"] != draft["handoff_id"]
    assert prepared["status"] == "ready"
    assert load_project(root)["computation_handoffs"] == ["computation/job.json"]
    with pytest.raises(ValidationError, match="choose a new path"):
        _create(root)


def test_draft_claim_cannot_replace_a_receipt_bound_handoff(tmp_path: Path) -> None:
    root = _project(tmp_path)
    draft = create_handoff(
        root, "computation/job.json", "Draft question?", "energy", "DFT", ["PBE"], [], ready=False
    )
    append_jsonl(root / "execution-receipts.jsonl", {"handoff_id": draft["handoff_id"]})
    before = (root / "computation/job.json").read_bytes()
    with pytest.raises(ValidationError, match="choose a new path"):
        _create(root)
    assert (root / "computation/job.json").read_bytes() == before


def test_registered_foreign_or_nonobject_file_is_never_replaced(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _create(root)
    target = root / "computation/job.json"
    for value in (
        [],
        {"schema_version": "2.0", "project_id": "foreign", "status": "draft", "evidence_level": "planned"},
    ):
        write_json(target, value)
        before = target.read_bytes()
        with pytest.raises(ValidationError, match="choose a new path"):
            _create(root)
        assert target.read_bytes() == before


def test_concurrent_creation_is_preserved_even_after_precheck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    target = root / "computation/job.json"
    before = _metadata(root)
    real_link = os.link

    def concurrent_create(source: Path, destination: Path) -> None:
        destination.write_bytes(b"created by another writer")
        real_link(source, destination)

    monkeypatch.setattr(io_module.os, "link", concurrent_create)
    with pytest.raises(ValidationError, match="already exists"):
        _create(root)
    assert target.read_bytes() == b"created by another writer"
    assert _metadata(root) == before
    assert sorted(path.name for path in target.parent.iterdir()) == ["job.json"]


def test_registry_failure_rolls_back_only_the_new_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    before = _metadata(root)

    def fail_append(*_args: object) -> None:
        raise OSError("simulated ledger write failure")

    monkeypatch.setattr(handoff_module, "append_jsonl", fail_append)
    with pytest.raises(OSError, match="ledger write failure"):
        _create(root)
    assert not (root / "computation/job.json").exists()
    assert _metadata(root) == before
    assert not list((root / "computation").iterdir())


def test_rollback_keeps_a_replacement_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    target = root / "computation/job.json"
    before = _metadata(root)

    def replace_and_fail(*_args: object) -> None:
        replacement = root / "computation/replacement.json"
        replacement.write_bytes(b"replacement by another writer")
        os.replace(replacement, target)
        raise OSError("simulated ledger write failure")

    monkeypatch.setattr(handoff_module, "append_jsonl", replace_and_fail)
    with pytest.raises(OSError, match="ledger write failure"):
        _create(root)
    assert target.read_bytes() == b"replacement by another writer"
    assert _metadata(root) == before


def test_unsupported_filesystem_leaves_no_partial_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    before = _metadata(root)

    def unsupported(*_args: object) -> None:
        raise OSError(errno.EOPNOTSUPP, "hard links unavailable")

    monkeypatch.setattr(io_module.os, "link", unsupported)
    with pytest.raises(OSError, match="hard links unavailable"):
        _create(root)
    assert _metadata(root) == before
    assert not list((root / "computation").iterdir())
