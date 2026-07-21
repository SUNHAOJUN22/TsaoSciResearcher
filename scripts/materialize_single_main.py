#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

MAX_MEMBERS = 10_000
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
EXPECTED_TOP_LEVEL = "TsaoSciResearcher"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member_path(name: str) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe archive member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"drive-qualified path is forbidden: {name!r}")
    if not path.parts or path.parts[0] != EXPECTED_TOP_LEVEL:
        raise ValueError(f"archive member is outside {EXPECTED_TOP_LEVEL}/: {name!r}")
    return path


def _load_manifest(payload_dir: Path) -> dict:
    manifest_path = payload_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "schema_version", "version", "encoding", "compression", "archive_format",
        "archive_sha256", "base64_sha256", "chunk_count", "chunk_names",
        "expected_main_sha", "history_heads",
    }
    if set(payload) != required:
        raise ValueError(f"manifest fields mismatch: missing={sorted(required-set(payload))}, extra={sorted(set(payload)-required)}")
    if payload["schema_version"] != "1.0" or payload["version"] != "0.5.1":
        raise ValueError("unsupported manifest schema/version")
    if payload["encoding"] != "base64" or payload["compression"] != "xz" or payload["archive_format"] != "tar":
        raise ValueError("unsupported payload encoding")
    names = payload["chunk_names"]
    if not isinstance(names, list) or len(names) != payload["chunk_count"] or len(names) != len(set(names)):
        raise ValueError("invalid chunk inventory")
    if names != [f"chunk-{index:03d}" for index in range(len(names))]:
        raise ValueError("chunk names must be contiguous and ordered")
    expected_files = {"manifest.json", *names}
    actual_files = {p.name for p in payload_dir.iterdir() if p.is_file()}
    if actual_files != expected_files:
        raise ValueError(f"payload inventory mismatch: expected={sorted(expected_files)}, actual={sorted(actual_files)}")
    return payload


def _decode_archive(payload_dir: Path, manifest: dict) -> bytes:
    chunks: list[str] = []
    for name in manifest["chunk_names"]:
        text = (payload_dir / name).read_text(encoding="ascii")
        if any(ch.isspace() for ch in text):
            raise ValueError(f"whitespace is forbidden inside chunk {name}")
        chunks.append(text)
    encoded_text = "".join(chunks)
    encoded = encoded_text.encode("ascii")
    if sha256_bytes(encoded) != manifest["base64_sha256"]:
        raise ValueError("base64 payload digest mismatch")
    try:
        archive = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid base64 payload") from exc
    if sha256_bytes(archive) != manifest["archive_sha256"]:
        raise ValueError("archive digest mismatch")
    return archive


def _extract_verified(archive: bytes, stage_parent: Path) -> Path:
    archive_path = stage_parent / "payload.tar.xz"
    archive_path.write_bytes(archive)
    extract_root = stage_parent / "extract"
    extract_root.mkdir()
    seen: set[str] = set()
    total = 0
    with tarfile.open(archive_path, mode="r:xz") as handle:
        members = handle.getmembers()
        if len(members) > MAX_MEMBERS:
            raise ValueError("archive has too many members")
        for member in members:
            path = _safe_member_path(member.name)
            collision_key = path.as_posix().casefold()
            if collision_key in seen:
                raise ValueError(f"duplicate or case-colliding member: {member.name}")
            seen.add(collision_key)
            if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
                raise ValueError(f"links and special files are forbidden: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"unsupported archive member: {member.name}")
            if member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"archive member too large: {member.name}")
            total += member.size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("archive expanded size exceeds configured limit")
        for member in members:
            path = _safe_member_path(member.name)
            output = extract_root.joinpath(*path.parts)
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            with source, output.open("xb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            mode = stat.S_IMODE(member.mode)
            os.chmod(output, 0o755 if mode & 0o111 else 0o644)
    candidate = extract_root / EXPECTED_TOP_LEVEL
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("archive did not produce the expected source directory")
    if (candidate / "VERSION").read_text(encoding="utf-8").strip() != "0.5.1":
        raise ValueError("materialized source version is not 0.5.1")
    if (candidate / ".git").exists() or (candidate / ".single-main-payload").exists():
        raise ValueError("candidate contains forbidden transport state")
    return candidate


def _replace_checkout(checkout: Path, candidate: Path) -> None:
    checkout = checkout.resolve()
    if checkout.is_symlink() or not (checkout / ".git").exists():
        raise ValueError("checkout must be a real Git working tree")
    sibling = checkout.parent
    backup = Path(tempfile.mkdtemp(prefix=f".{checkout.name}.backup-", dir=sibling))
    installed: list[Path] = []
    moved_old: list[tuple[Path, Path]] = []
    try:
        for child in list(checkout.iterdir()):
            if child.name == ".git":
                continue
            destination = backup / child.name
            os.replace(child, destination)
            moved_old.append((destination, checkout / child.name))
        for child in list(candidate.iterdir()):
            destination = checkout / child.name
            os.replace(child, destination)
            installed.append(destination)
        if (checkout / "VERSION").read_text(encoding="utf-8").strip() != "0.5.1":
            raise ValueError("post-install version verification failed")
        if (checkout / ".single-main-payload").exists() or (checkout / "scripts/materialize_single_main.py").exists():
            raise ValueError("temporary transport files survived materialization")
    except Exception:
        for path in reversed(installed):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        for source, destination in reversed(moved_old):
            if source.exists() or source.is_symlink():
                os.replace(source, destination)
        raise
    finally:
        shutil.rmtree(backup, ignore_errors=True)


def materialize(checkout: Path, payload_dir: Path) -> dict:
    manifest = _load_manifest(payload_dir)
    archive = _decode_archive(payload_dir, manifest)
    stage_parent = Path(tempfile.mkdtemp(prefix="tsr-single-main-", dir=checkout.resolve().parent))
    try:
        candidate = _extract_verified(archive, stage_parent)
        _replace_checkout(checkout, candidate)
    finally:
        shutil.rmtree(stage_parent, ignore_errors=True)
    return {
        "version": manifest["version"],
        "archive_sha256": manifest["archive_sha256"],
        "expected_main_sha": manifest["expected_main_sha"],
        "history_heads": manifest["history_heads"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely materialize the verified v0.5.1 single-main source tree.")
    parser.add_argument("--checkout", default=".")
    parser.add_argument("--payload", default=".single-main-payload")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    result = materialize(Path(args.checkout), Path(args.payload))
    text = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
