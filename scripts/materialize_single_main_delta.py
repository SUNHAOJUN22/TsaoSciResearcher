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
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

MAX_MEMBERS = 10_000
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
DELTA_ROOT = "TsaoSciResearcher-delta"
EXCLUDED_TREE_PARTS = {".git", "__pycache__", ".pytest_cache", ".coverage", "dist", "dist-a", "dist-b", ".tsao-research"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(name: str, *, required_root: str | None = None) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe member path: {name!r}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"drive-qualified path is forbidden: {name!r}")
    if required_root is not None and (not path.parts or path.parts[0] != required_root):
        raise ValueError(f"member is outside {required_root}/: {name!r}")
    return path


def _tree_digest(root: Path) -> tuple[int, str]:
    rows: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_TREE_PARTS for part in relative.parts):
            continue
        rows.append((relative.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    digest = hashlib.sha256()
    for relative, file_digest in rows:
        digest.update(relative.encode("utf-8") + b"\0" + file_digest.encode("ascii") + b"\n")
    return len(rows), digest.hexdigest()


def _load_manifest(payload_dir: Path) -> dict:
    payload = json.loads((payload_dir / "manifest.json").read_text(encoding="utf-8"))
    required = {
        "schema_version", "version", "base_url", "base_sha256",
        "delta_archive_sha256", "delta_base64_sha256", "chunk_count", "chunk_names",
        "expected_main_sha", "history_heads", "final_file_count", "final_tree_sha256",
    }
    if set(payload) != required:
        raise ValueError(f"manifest fields mismatch: missing={sorted(required-set(payload))}, extra={sorted(set(payload)-required)}")
    if payload["schema_version"] != "1.0" or payload["version"] != "0.5.1":
        raise ValueError("unsupported manifest schema/version")
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


def _download(url: str, expected_sha256: str, destination: Path) -> None:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TsaoSciResearcher-single-main/0.5.1"})
            with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as sink:
                shutil.copyfileobj(response, sink, length=1024 * 1024)
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual != expected_sha256:
                raise ValueError(f"downloaded base archive digest mismatch: {actual}")
            return
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"unable to download verified base archive: {last_error}")


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir()
    seen: set[str] = set()
    total = 0
    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValueError("base archive has too many members")
        for info in infos:
            path = _safe_relative(info.filename)
            key = path.as_posix().casefold()
            if key in seen:
                raise ValueError(f"duplicate or case-colliding ZIP member: {info.filename}")
            seen.add(key)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError(f"symbolic links are forbidden in ZIP: {info.filename}")
            if info.flag_bits & 0x1:
                raise ValueError(f"encrypted ZIP members are forbidden: {info.filename}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"ZIP member too large: {info.filename}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("ZIP expanded size exceeds configured limit")
            if info.compress_size and info.file_size / info.compress_size > 200:
                raise ValueError(f"ZIP compression ratio too high: {info.filename}")
        for info in infos:
            path = _safe_relative(info.filename)
            output = destination.joinpath(*path.parts)
            if info.is_dir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(info, "r") as source, output.open("xb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            os.chmod(output, 0o644)


def _decode_delta(payload_dir: Path, manifest: dict, output: Path) -> None:
    texts: list[str] = []
    for name in manifest["chunk_names"]:
        text = (payload_dir / name).read_text(encoding="ascii")
        if any(ch.isspace() for ch in text):
            raise ValueError(f"whitespace is forbidden inside chunk {name}")
        texts.append(text)
    encoded = "".join(texts).encode("ascii")
    if sha256_bytes(encoded) != manifest["delta_base64_sha256"]:
        raise ValueError("delta base64 digest mismatch")
    try:
        data = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid delta base64") from exc
    if sha256_bytes(data) != manifest["delta_archive_sha256"]:
        raise ValueError("delta archive digest mismatch")
    output.write_bytes(data)


def _extract_delta(archive: Path, destination: Path) -> Path:
    destination.mkdir()
    seen: set[str] = set()
    total = 0
    with tarfile.open(archive, mode="r:xz") as handle:
        members = handle.getmembers()
        if len(members) > MAX_MEMBERS:
            raise ValueError("delta archive has too many members")
        for member in members:
            path = _safe_relative(member.name, required_root=DELTA_ROOT)
            key = path.as_posix().casefold()
            if key in seen:
                raise ValueError(f"duplicate or case-colliding delta member: {member.name}")
            seen.add(key)
            if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
                raise ValueError(f"links and special files are forbidden: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"unsupported delta member: {member.name}")
            if member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"delta member too large: {member.name}")
            total += member.size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("delta expanded size exceeds configured limit")
        for member in members:
            path = _safe_relative(member.name, required_root=DELTA_ROOT)
            output = destination.joinpath(*path.parts)
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read delta member: {member.name}")
            with source, output.open("xb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            mode = stat.S_IMODE(member.mode)
            os.chmod(output, 0o755 if mode & 0o111 else 0o644)
    return destination / DELTA_ROOT


def _apply_delta(base: Path, delta: Path) -> None:
    delta_manifest_path = delta / "DELTA-MANIFEST.json"
    delta_manifest = json.loads(delta_manifest_path.read_text(encoding="utf-8"))
    if set(delta_manifest) != {"added", "changed", "deleted"}:
        raise ValueError("invalid delta manifest fields")
    sets: dict[str, list[str]] = {}
    for key in ("added", "changed", "deleted"):
        values = delta_manifest[key]
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise ValueError(f"invalid {key} path list")
        normalized = [_safe_relative(value).as_posix() for value in values]
        sets[key] = normalized
    if (set(sets["added"]) & set(sets["changed"])) or (set(sets["added"]) & set(sets["deleted"])) or (set(sets["changed"]) & set(sets["deleted"])):
        raise ValueError("delta path categories overlap")
    expected_payload = {"DELTA-MANIFEST.json", *sets["added"], *sets["changed"]}
    actual_payload = {path.relative_to(delta).as_posix() for path in delta.rglob("*") if path.is_file()}
    if actual_payload != expected_payload:
        raise ValueError("delta payload inventory does not match manifest")
    for relative in sets["deleted"]:
        target = base / relative
        if not target.exists() or not target.is_file() or target.is_symlink():
            raise ValueError(f"declared deletion is not a regular existing file: {relative}")
        target.unlink()
    for category in ("added", "changed"):
        for relative in sets[category]:
            source = delta / relative
            target = base / relative
            if category == "added" and target.exists():
                raise ValueError(f"added path already exists in base: {relative}")
            if category == "changed" and (not target.is_file() or target.is_symlink()):
                raise ValueError(f"changed path is missing from base: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".delta-tmp")
            shutil.copy2(source, temporary)
            os.replace(temporary, target)


def _replace_checkout(checkout: Path, candidate: Path) -> None:
    checkout = checkout.resolve()
    if checkout.is_symlink() or not (checkout / ".git").exists():
        raise ValueError("checkout must be a real Git working tree")
    backup = Path(tempfile.mkdtemp(prefix=f".{checkout.name}.backup-", dir=checkout.parent))
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


def materialize(checkout: Path, payload_dir: Path, *, base_override: str | None = None) -> dict:
    manifest = _load_manifest(payload_dir)
    stage = Path(tempfile.mkdtemp(prefix="tsr-single-main-delta-", dir=checkout.resolve().parent))
    try:
        base_zip = stage / "base.zip"
        _download(base_override or manifest["base_url"], manifest["base_sha256"], base_zip)
        candidate = stage / "candidate"
        _safe_extract_zip(base_zip, candidate)
        delta_archive = stage / "delta.tar.xz"
        _decode_delta(payload_dir, manifest, delta_archive)
        delta = _extract_delta(delta_archive, stage / "delta")
        _apply_delta(candidate, delta)
        count, digest = _tree_digest(candidate)
        if count != manifest["final_file_count"] or digest != manifest["final_tree_sha256"]:
            raise ValueError(f"final tree mismatch: count={count}, digest={digest}")
        _replace_checkout(checkout, candidate)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return {
        "version": manifest["version"], "final_file_count": manifest["final_file_count"],
        "final_tree_sha256": manifest["final_tree_sha256"], "expected_main_sha": manifest["expected_main_sha"],
        "history_heads": manifest["history_heads"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize verified v0.5.1 from a pinned v0.5.0 archive and SHA256 delta.")
    parser.add_argument("--checkout", default=".")
    parser.add_argument("--payload", default=".single-main-delta")
    parser.add_argument("--base-override")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    result = materialize(Path(args.checkout), Path(args.payload), base_override=args.base_override)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
