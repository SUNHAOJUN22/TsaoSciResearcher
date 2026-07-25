"""Deterministic, verifiable reproducibility capsules for project state."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import IntegrityError, ValidationError
from .io import atomic_write_text, canonical_json, sha256_file
from .receipts import verify_receipts
from .state import load_project, project_root, verify
from .version import __version__

CAPSULE_SCHEMA_VERSION = "1.0"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MAX_FILES = 20_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
METADATA_EXCLUDED_TOP_LEVEL = {"data", "figures", "artifacts"}
IGNORED_NAMES = {".mutation.lock", ".DS_Store"}


def _safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrityError(f"unsafe capsule member: {name}")
    if path.parts[0] != "capsule":
        raise IntegrityError(f"capsule member must use capsule/ prefix: {name}")
    return path


def _role(relative: Path) -> str:
    top = relative.parts[0] if relative.parts else "root"
    return {
        "state": "event-chain",
        "data": "research-data",
        "computation": "computation",
        "protocols": "protocol",
        "reports": "report",
        "figures": "figure",
        "artifacts": "artifact",
        "literature": "literature",
        "registry": "registry",
    }.get(top, "project-metadata")


def _project_files(root: Path, output: Path, mode: str) -> list[Path]:
    rows: list[Path] = []
    total = 0
    resolved_output = output.resolve(strict=False)
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.resolve(strict=False) == resolved_output or path.name in IGNORED_NAMES:
            continue
        if path.is_symlink():
            raise ValidationError(f"symbolic links are forbidden in capsules: {relative.as_posix()}")
        if not path.is_file():
            continue
        if mode == "metadata" and relative.parts and relative.parts[0] in METADATA_EXCLUDED_TOP_LEVEL:
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValidationError(f"capsule file exceeds {MAX_FILE_BYTES} bytes: {relative.as_posix()}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValidationError("capsule exceeds total expanded-size limit")
        rows.append(path)
    if len(rows) > MAX_FILES:
        raise ValidationError(f"capsule has more than {MAX_FILES} files")
    return sorted(rows, key=lambda item: item.relative_to(root).as_posix())


def _tree_digest(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o644 << 16
    info.flag_bits |= 0x800
    return info


def export_capsule(
    root: str | Path,
    output: str | Path,
    *,
    mode: str = "metadata",
) -> dict[str, Any]:
    """Export project state to a deterministic ZIP with a complete checksum manifest."""

    if mode not in {"metadata", "full"}:
        raise ValidationError("capsule mode must be metadata or full")
    state_root = project_root(root)
    project = load_project(state_root)
    state_result = verify(state_root)
    receipt_result = verify_receipts(state_root)
    destination = Path(output).expanduser().resolve(strict=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValidationError("capsule output cannot be a symbolic link")
    files = _project_files(state_root, destination, mode)
    records = [
        {
            "path": path.relative_to(state_root).as_posix(),
            "role": _role(path.relative_to(state_root)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    base_manifest: dict[str, Any] = {
        "schema_version": CAPSULE_SCHEMA_VERSION,
        "project_id": project.get("project_id"),
        "project_status": project.get("status"),
        "mode": mode,
        "project_created_at": project.get("created_at"),
        "project_updated_at": project.get("updated_at"),
        "software": {
            "name": "TsaoSciResearcher",
            "version": __version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "state_verification": state_result,
        "receipt_verification": receipt_result,
        "file_count": len(records),
        "total_bytes": sum(path.stat().st_size for path in files),
        "tree_sha256": _tree_digest(records),
        "files": records,
        "truth_boundary": "A verified capsule proves internal integrity and provenance, not scientific acceptance.",
    }
    capsule_id = "CAP-" + hashlib.sha256(canonical_json(base_manifest).encode("utf-8")).hexdigest()[:24]
    manifest = {"capsule_id": capsule_id, **base_manifest}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
            handle.writestr(_zip_info("capsule/manifest.json"), manifest_bytes)
            for path in files:
                relative = path.relative_to(state_root).as_posix()
                handle.writestr(_zip_info(f"capsule/project/{relative}"), path.read_bytes())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    sidecar = destination.with_name(destination.name + ".sha256")
    atomic_write_text(sidecar, f"{sha256_file(destination)}  {destination.name}\n")
    return {
        "valid": True,
        "capsule": str(destination),
        "sidecar": str(sidecar),
        "capsule_id": capsule_id,
        "mode": mode,
        "files": len(records),
        "tree_sha256": manifest["tree_sha256"],
        "archive_sha256": sha256_file(destination),
    }


def verify_capsule(path: str | Path) -> dict[str, Any]:
    """Verify archive safety, manifest integrity and every project-file checksum."""

    capsule = Path(path).expanduser().resolve(strict=False)
    if capsule.is_symlink() or not capsule.is_file():
        raise FileNotFoundError(capsule)
    total = 0
    names: set[str] = set()
    with zipfile.ZipFile(capsule) as handle:
        for info in handle.infolist():
            _safe_member(info.filename)
            if info.filename in names:
                raise IntegrityError(f"duplicate capsule member: {info.filename}")
            names.add(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise IntegrityError(f"symbolic link member forbidden: {info.filename}")
            if info.file_size > MAX_FILE_BYTES:
                raise IntegrityError(f"capsule member exceeds size limit: {info.filename}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise IntegrityError("capsule exceeds expanded-size limit")
        if "capsule/manifest.json" not in names:
            raise IntegrityError("capsule manifest is missing")
        manifest = json.loads(handle.read("capsule/manifest.json").decode("utf-8", errors="strict"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != CAPSULE_SCHEMA_VERSION:
            raise IntegrityError("capsule manifest schema is invalid")
        records = manifest.get("files")
        if not isinstance(records, list) or len(records) != manifest.get("file_count"):
            raise IntegrityError("capsule file inventory is invalid")
        normalized: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                raise IntegrityError("capsule file record is invalid")
            relative = str(record.get("path", ""))
            member = f"capsule/project/{relative}"
            _safe_member(member)
            if member not in names:
                raise IntegrityError(f"capsule project member missing: {relative}")
            payload = handle.read(member)
            digest = hashlib.sha256(payload).hexdigest()
            if record.get("size_bytes") != len(payload) or record.get("sha256") != digest:
                raise IntegrityError(f"capsule checksum mismatch: {relative}")
            normalized.append(record)
        if manifest.get("tree_sha256") != _tree_digest(normalized):
            raise IntegrityError("capsule tree digest mismatch")
        base = dict(manifest)
        capsule_id = str(base.pop("capsule_id", ""))
        expected_id = "CAP-" + hashlib.sha256(canonical_json(base).encode("utf-8")).hexdigest()[:24]
        if capsule_id != expected_id:
            raise IntegrityError("capsule identifier does not match manifest")
    return {
        "valid": True,
        "capsule_id": manifest["capsule_id"],
        "project_id": manifest.get("project_id"),
        "mode": manifest.get("mode"),
        "files": manifest.get("file_count"),
        "tree_sha256": manifest.get("tree_sha256"),
        "archive_sha256": sha256_file(capsule),
    }


__all__ = ["CAPSULE_SCHEMA_VERSION", "export_capsule", "verify_capsule"]
