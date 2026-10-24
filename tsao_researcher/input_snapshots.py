"""Bind declared handoff inputs to retained, content-addressed receipt bytes."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import _reject_symlink_components, project_regular_file, sha256_file

MAX_INPUT_FILES = 10_000
SNAPSHOT_DIRECTORY = Path("artifacts/input-snapshots")


def input_manifest(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_INPUT_FILES:
        raise ValidationError("handoff inputs must be a non-empty bounded manifest")
    paths: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("handoff input record must be an object")
        relative = item.get("path")
        posix_path = PurePosixPath(relative) if isinstance(relative, str) else None
        windows_path = PureWindowsPath(relative) if isinstance(relative, str) else None
        if (
            not isinstance(relative, str)
            or not relative.strip()
            or posix_path is None
            or windows_path is None
            or posix_path.is_absolute()
            or windows_path.drive
            or windows_path.root
            or ".." in posix_path.parts
            or posix_path.as_posix() != relative
            or relative in paths
        ):
            raise ValidationError("handoff input paths must be unique canonical relative paths")
        paths.add(relative)
        if type(item.get("size_bytes")) is not int or item["size_bytes"] < 0:
            raise ValidationError("handoff input size must be a non-negative integer")
        if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValidationError("handoff input SHA256 must be 64 lowercase hex digits")
    return value


def _matches(path: Path, item: dict[str, Any]) -> bool:
    return bool(path.stat().st_size == item["size_bytes"] and sha256_file(path) == item["sha256"])


def snapshot_inputs(root: Path, declared: Any) -> list[dict[str, Any]]:
    records = input_manifest(declared)
    directory = root / SNAPSHOT_DIRECTORY
    _reject_symlink_components(directory)
    directory.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for item in records:
        source = project_regular_file(root, item["path"], field="handoff input")
        if not _matches(source, item):
            raise ValidationError(f"handoff input checksum mismatch before receipt: {item['path']}")
        relative_snapshot = (SNAPSHOT_DIRECTORY / item["sha256"]).as_posix()
        destination = root / relative_snapshot
        if destination.exists() or destination.is_symlink():
            existing = project_regular_file(root, relative_snapshot, field="input snapshot")
            if not _matches(existing, item):
                raise IntegrityError("existing input snapshot checksum mismatch")
        else:
            fd, name = tempfile.mkstemp(prefix=".snapshot-", dir=directory)
            temporary = Path(name)
            try:
                checksum = hashlib.sha256()
                size = 0
                with os.fdopen(fd, "wb") as output, source.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        checksum.update(block)
                        size += len(block)
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if size != item["size_bytes"] or checksum.hexdigest() != item["sha256"]:
                    raise ValidationError("handoff input changed while taking snapshot")
                # Never replace a previously retained content-addressed artifact.
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    existing = project_regular_file(root, relative_snapshot, field="input snapshot")
                    if not _matches(existing, item):
                        raise IntegrityError("concurrent input snapshot checksum mismatch") from None
            finally:
                temporary.unlink(missing_ok=True)
        snapshots.append(
            {
                "path": item["path"],
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
                "snapshot_path": relative_snapshot,
            }
        )
    return snapshots


def verify_input_snapshots(root: Path, declared: Any, snapshots: Any) -> None:
    try:
        records = input_manifest(declared)
        if not isinstance(snapshots, list) or len(snapshots) != len(records):
            raise ValidationError("receipt input snapshots must match the handoff manifest")
        for original, snapshot in zip(records, snapshots, strict=True):
            expected = {
                "path": original["path"],
                "size_bytes": original["size_bytes"],
                "sha256": original["sha256"],
                "snapshot_path": (SNAPSHOT_DIRECTORY / original["sha256"]).as_posix(),
            }
            if (
                not isinstance(snapshot, dict)
                or snapshot != expected
                or type(snapshot.get("size_bytes")) is not int
            ):
                raise ValidationError("receipt input snapshot binding mismatch")
            retained = project_regular_file(root, expected["snapshot_path"], field="input snapshot")
            if not _matches(retained, expected):
                raise ValidationError("retained input snapshot checksum mismatch")
    except ValidationError as exc:
        raise IntegrityError(str(exc)) from exc
