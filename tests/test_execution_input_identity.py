from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tsao_researcher.errors import IntegrityError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.receipts import record_receipt, verify_receipts
from tsao_researcher.state import initialize, load_project


def _project(tmp_path: Path) -> Path:
    root = initialize("identity", "Can execution metadata retain exact identity?", tmp_path)
    (root / "data/input.dat").write_bytes(b"input fixture")
    return root


def _handoff(root: Path, inputs: object, *, ready: object = True) -> dict:
    return create_handoff(
        root,
        "computation/job.json",
        "Can execution metadata retain exact identity?",
        "energy",
        "DFT",
        ["PBE"],
        inputs,
        ready=ready,
    )


@pytest.mark.parametrize("ready", [None, 0, 1, "false", "true", [], {}])
def test_handoff_rejects_non_boolean_readiness_without_publication(tmp_path: Path, ready: object) -> None:
    root = _project(tmp_path)
    before = (root / "project.yaml").read_bytes()
    with pytest.raises(ValidationError, match=r"ready.*boolean"):
        _handoff(root, ["data/input.dat"], ready=ready)
    assert not (root / "computation/job.json").exists()
    assert (root / "project.yaml").read_bytes() == before


@pytest.mark.parametrize("inputs", [None, "data/input.dat", ("data/input.dat",), [None], [True], [""]])
def test_handoff_rejects_invalid_input_vectors_without_publication(tmp_path: Path, inputs: object) -> None:
    root = _project(tmp_path)
    with pytest.raises(ValidationError, match=r"inputs.*list.*nonblank"):
        _handoff(root, inputs)
    assert not (root / "computation/job.json").exists()
    assert load_project(root)["computation_handoffs"] == []


@pytest.mark.parametrize("alias", ["data/input.dat", "./data/input.dat", "data/./input.dat"])
def test_handoff_rejects_duplicate_resolved_inputs(tmp_path: Path, alias: str) -> None:
    root = _project(tmp_path)
    with pytest.raises(ValidationError, match="input paths must be unique"):
        _handoff(root, ["data/input.dat", alias])
    assert not (root / "computation/job.json").exists()
    assert load_project(root)["computation_handoffs"] == []


def test_receipt_preserves_exact_argument_and_environment_values(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / "computation/result.out").write_bytes(b"synthetic fixture")
    command = ["engine", "--label", "  sample A  ", "\tinput.dat\t"]
    environment = {"LABEL": "  sample A  ", "EMPTY": "", "TABS": "\tA\t"}
    receipt = record_receipt(
        root,
        "computation/job.json",
        "fixture engine",
        command,
        0,
        ["computation/result.out"],
        "2026-11-15T01:00:00Z",
        "2026-11-15T01:00:01Z",
        environment=[f"{key}={value}" for key, value in environment.items()],
    )
    assert receipt["command"] == command
    assert receipt["environment"] == environment
    stored = json.loads((root / "execution-receipts.jsonl").read_text(encoding="utf-8"))
    assert stored["command"] == command
    assert stored["environment"] == environment
    assert verify_receipts(root)["valid"] is True


@pytest.mark.parametrize("alias", ["./computation/result.out", "computation/./result.out"])
def test_receipt_rejects_duplicate_resolved_outputs(tmp_path: Path, alias: str) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / "computation/result.out").write_bytes(b"synthetic fixture")
    before = (root / "execution-receipts.jsonl").read_bytes()
    with pytest.raises(ValidationError, match="output paths must be unique"):
        record_receipt(
            root,
            "computation/job.json",
            "fixture",
            ["fixture"],
            0,
            ["computation/result.out", alias],
            "2026-11-15T01:00:00Z",
            "2026-11-15T01:00:01Z",
        )
    assert (root / "execution-receipts.jsonl").read_bytes() == before


def test_receipt_preserves_empty_and_whitespace_only_arguments(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / "computation/result.out").write_bytes(b"synthetic fixture")
    command = ["engine", "--label", "", " \t "]
    receipt = record_receipt(
        root,
        "computation/job.json",
        "fixture",
        command,
        0,
        ["computation/result.out"],
        "2026-11-15T01:00:00Z",
        "2026-11-15T01:00:01Z",
    )
    assert receipt["command"] == command
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas/v2/execution-receipt.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(receipt)
    assert verify_receipts(root)["valid"] is True


@pytest.mark.parametrize("command", [[""], ["   "], ["engine", "bad\0argument"]])
def test_receipt_rejects_unexecutable_command_vectors(tmp_path: Path, command: list[str]) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / "computation/result.out").write_bytes(b"synthetic fixture")
    before = (root / "execution-receipts.jsonl").read_bytes()
    with pytest.raises(ValidationError, match="command vector"):
        record_receipt(
            root,
            "computation/job.json",
            "fixture",
            command,
            0,
            ["computation/result.out"],
            "2026-11-15T01:00:00Z",
            "2026-11-15T01:00:01Z",
        )
    assert (root / "execution-receipts.jsonl").read_bytes() == before


def test_receipt_verifier_rejects_duplicate_resolved_output_aliases(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / "computation/result.out").write_bytes(b"synthetic fixture")
    receipt = record_receipt(
        root,
        "computation/job.json",
        "fixture",
        ["engine"],
        0,
        ["computation/result.out"],
        "2026-11-15T01:00:00Z",
        "2026-11-15T01:00:01Z",
    )
    receipt["outputs"].append({**receipt["outputs"][0], "path": "./computation/result.out"})
    (root / "execution-receipts.jsonl").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="duplicate execution output path"):
        verify_receipts(root)


def test_receipt_does_not_trim_significant_output_path_whitespace(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    (root / " result.out").write_bytes(b"requested output")
    (root / "result.out").write_bytes(b"different output")
    receipt = record_receipt(
        root,
        "computation/job.json",
        "fixture",
        ["engine"],
        0,
        [" result.out"],
        "2026-11-15T01:00:00Z",
        "2026-11-15T01:00:01Z",
    )
    assert receipt["outputs"][0]["path"] == " result.out"
    assert receipt["outputs"][0]["size_bytes"] == len(b"requested output")
    assert verify_receipts(root)["valid"] is True


@pytest.mark.parametrize("metadata", ["project.yaml", "artifacts.jsonl", "execution-receipts.jsonl"])
@pytest.mark.parametrize("alias", ["direct", "dotdot", "hardlink"])
def test_receipt_rejects_its_own_mutable_metadata_without_publication(
    tmp_path: Path, metadata: str, alias: str
) -> None:
    root = _project(tmp_path)
    _handoff(root, ["data/input.dat"])
    output = metadata
    if alias == "dotdot":
        output = f"computation/../{metadata}"
    elif alias == "hardlink":
        output = "computation/metadata-alias.out"
        os.link(root / metadata, root / output)
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    with pytest.raises(ValidationError, match=r"receipt output.*metadata"):
        record_receipt(
            root,
            "computation/job.json",
            "fixture",
            ["engine"],
            0,
            [output],
            "2026-11-15T01:00:00Z",
            "2026-11-15T01:00:01Z",
        )

    assert {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()} == before
    assert verify_receipts(root)["receipts"] == 0
