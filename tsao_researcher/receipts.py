"""Explicit execution receipts for externally run scientific computations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .errors import IntegrityError, ValidationError
from .io import (
    append_jsonl,
    atomic_write_text,
    exclusive_lock,
    new_id,
    project_regular_file,
    read_jsonl,
    sha256_file,
    utc_now,
)
from .state import load_project, project_root

RECEIPT_LOG = "execution-receipts.jsonl"
MAX_OUTPUT_FILES = 10_000


def _parse_timestamp(value: str, field: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValidationError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed


def _safe_project_file(state_root: Path, relative: str, *, field: str) -> Path:
    clean = relative.strip()
    if not clean:
        raise ValidationError(f"{field} path must not be blank")
    return project_regular_file(state_root, clean, field=field)


def _output_records(state_root: Path, outputs: list[str]) -> list[dict[str, Any]]:
    if len(outputs) > MAX_OUTPUT_FILES:
        raise ValidationError(f"receipt has more than {MAX_OUTPUT_FILES} outputs")
    resolved_root = state_root.resolve()
    records: list[dict[str, Any]] = []
    for relative in dict.fromkeys(value.strip() for value in outputs if value.strip()):
        candidate = _safe_project_file(state_root, relative, field="output")
        records.append(
            {
                "path": candidate.relative_to(resolved_root).as_posix(),
                "size_bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
            }
        )
    return records


def _environment(values: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or []:
        key, separator, value = item.partition("=")
        clean_key = key.strip()
        if not separator or not clean_key or clean_key in result:
            raise ValidationError("environment entries must be unique KEY=VALUE pairs")
        result[clean_key] = value.strip()
    return dict(sorted(result.items()))


def record_receipt(
    root: str | Path,
    handoff_path: str,
    engine: str,
    command: list[str],
    exit_code: int,
    outputs: list[str],
    started_at: str,
    finished_at: str,
    *,
    engine_version: str = "",
    environment: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Record user-supplied execution evidence without launching an external engine."""

    state_root = project_root(root)
    project = load_project(state_root)
    handoff_file = _safe_project_file(state_root, handoff_path, field="handoff")
    handoff = json.loads(handoff_file.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(handoff, dict) or handoff.get("project_id") != project.get("project_id"):
        raise ValidationError("handoff does not belong to this project")
    if not engine.strip() or not command or any(not value.strip() for value in command):
        raise ValidationError("engine and a non-empty command vector are required")
    start = _parse_timestamp(started_at, "started_at")
    finish = _parse_timestamp(finished_at, "finished_at")
    if finish < start:
        raise ValidationError("finished_at must not precede started_at")
    output_records = _output_records(state_root, outputs)
    status = "succeeded" if exit_code == 0 else "failed"
    if status == "succeeded" and not output_records:
        raise ValidationError("a successful execution receipt requires at least one checksum-verified output")
    receipt = {
        "schema_version": "2.0",
        "receipt_id": new_id("RUN"),
        "project_id": project["project_id"],
        "handoff_id": handoff.get("handoff_id"),
        "handoff_path": handoff_file.relative_to(state_root.resolve()).as_posix(),
        "engine": {"name": engine.strip(), "version": engine_version.strip() or None},
        "command": [value.strip() for value in command],
        "started_at": started_at.strip(),
        "finished_at": finished_at.strip(),
        "duration_seconds": round((finish - start).total_seconds(), 6),
        "exit_code": int(exit_code),
        "status": status,
        "evidence_level": "executed" if status == "succeeded" else "failed",
        "outputs": output_records,
        "environment": _environment(environment),
        "notes": notes.strip(),
        "recorded_at": utc_now(),
        "truth_boundary": "This receipt records supplied execution evidence; it does not grant scientific acceptance.",
    }
    relative_receipt = RECEIPT_LOG
    with exclusive_lock(state_root / "state" / ".mutation.lock"):
        project = load_project(state_root)
        registered = project.get("execution_receipts", [])
        if not isinstance(registered, list):
            raise ValidationError("project execution_receipts must be a list")
        append_jsonl(state_root / relative_receipt, receipt)
        registered.append(receipt["receipt_id"])
        project["execution_receipts"] = registered
        project["updated_at"] = receipt["recorded_at"]
        atomic_write_text(
            state_root / "project.yaml",
            yaml.safe_dump(project, sort_keys=False, allow_unicode=True),
        )
        append_jsonl(
            state_root / "artifacts.jsonl",
            {
                "artifact_id": new_id("ART"),
                "project_id": project["project_id"],
                "artifact_type": "execution-receipt",
                "path": relative_receipt,
                "status": status,
                "related_ids": [receipt["receipt_id"], str(receipt["handoff_id"])],
                "created_at": receipt["recorded_at"],
            },
        )
    return receipt


def verify_receipts(root: str | Path) -> dict[str, Any]:
    """Verify receipt registry, handoff identity, timestamps and output hashes."""

    state_root = project_root(root)
    project = load_project(state_root)
    receipts = list(read_jsonl(state_root / RECEIPT_LOG))
    registered = project.get("execution_receipts", [])
    if not isinstance(registered, list) or any(not isinstance(value, str) for value in registered):
        raise IntegrityError("project execution_receipts must be a list of receipt IDs")
    if len(registered) != len(set(registered)):
        raise IntegrityError("project execution_receipts contains duplicate IDs")
    output_count = 0
    successful = 0
    failed = 0
    actual_ids: list[str] = []
    for index, receipt in enumerate(receipts, 1):
        if not isinstance(receipt, dict):
            raise IntegrityError(f"execution receipt {index} is not an object")
        receipt_id = str(receipt.get("receipt_id", ""))
        if not receipt_id.startswith("RUN-"):
            raise IntegrityError(f"execution receipt {index} has an invalid ID")
        actual_ids.append(receipt_id)
        if receipt.get("project_id") != project.get("project_id"):
            raise IntegrityError(f"execution receipt project mismatch: {receipt_id}")
        handoff_path = str(receipt.get("handoff_path", ""))
        try:
            handoff_file = _safe_project_file(state_root, handoff_path, field="handoff")
        except ValidationError as exc:
            raise IntegrityError(str(exc)) from exc
        handoff = json.loads(handoff_file.read_text(encoding="utf-8", errors="strict"))
        if not isinstance(handoff, dict) or handoff.get("handoff_id") != receipt.get("handoff_id"):
            raise IntegrityError(f"execution receipt handoff mismatch: {receipt_id}")
        if handoff.get("project_id") != project.get("project_id"):
            raise IntegrityError(f"execution receipt handoff project mismatch: {receipt_id}")
        try:
            started = _parse_timestamp(str(receipt.get("started_at", "")), "started_at")
            finished = _parse_timestamp(str(receipt.get("finished_at", "")), "finished_at")
        except ValidationError as exc:
            raise IntegrityError(f"execution receipt timestamp invalid: {receipt_id}") from exc
        if finished < started:
            raise IntegrityError(f"execution receipt has negative duration: {receipt_id}")
        expected_duration = (finished - started).total_seconds()
        if abs(float(receipt.get("duration_seconds", -1)) - expected_duration) > 1e-6:
            raise IntegrityError(f"execution receipt duration mismatch: {receipt_id}")
        status = receipt.get("status")
        exit_code = receipt.get("exit_code")
        if status == "succeeded":
            if exit_code != 0 or receipt.get("evidence_level") != "executed":
                raise IntegrityError(f"successful execution receipt semantics invalid: {receipt_id}")
            successful += 1
        elif status == "failed":
            if receipt.get("evidence_level") != "failed":
                raise IntegrityError(f"failed execution receipt semantics invalid: {receipt_id}")
            failed += 1
        else:
            raise IntegrityError(f"execution receipt status invalid: {receipt_id}")
        outputs = receipt.get("outputs")
        if not isinstance(outputs, list) or (status == "succeeded" and not outputs):
            raise IntegrityError(f"execution receipt outputs invalid: {receipt_id}")
        seen_paths: set[str] = set()
        for output in outputs:
            if not isinstance(output, dict):
                raise IntegrityError(f"execution receipt output invalid: {receipt_id}")
            relative = str(output.get("path", ""))
            if relative in seen_paths:
                raise IntegrityError(f"duplicate execution output path: {relative}")
            seen_paths.add(relative)
            try:
                candidate = _safe_project_file(state_root, relative, field="output")
            except ValidationError as exc:
                raise IntegrityError(str(exc)) from exc
            if candidate.stat().st_size != output.get("size_bytes") or sha256_file(candidate) != output.get("sha256"):  # fmt: skip
                raise IntegrityError(f"execution output checksum mismatch: {relative}")
            output_count += 1
    if actual_ids != registered:
        raise IntegrityError("project execution_receipts registry does not match receipt log order")
    return {
        "valid": True,
        "receipts": len(receipts),
        "verified_outputs": output_count,
        "successful": successful,
        "failed": failed,
    }


__all__ = ["RECEIPT_LOG", "record_receipt", "verify_receipts"]
