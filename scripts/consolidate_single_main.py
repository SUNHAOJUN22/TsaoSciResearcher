#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

V050_ARCHIVE_SHA256 = "75deca80fafaf8f5193bcbb106b52c9661cd072388968cde9fbf76332f2f61d7"
PATCH_GZIP_SHA256 = "bcccb99bf6d84a09a6227fa1709b389be5b2ce426f18196729bee93b6d9ea034"
PATCH_SHA256 = "47d980b77e26437cceaf0e9fa2795dba9c04625d4e9b27a8af29019c92935a10"
CHUNK_SHA256 = [
    "63cfef22cf2f3b7f654d10b1e11a584e18a7e16fd3bdb039d7451fe7dca82732",
    "89a7785f3cd449cc85b63c96951249ef022cc3516e0ba4656f8912d6d4113996",
    "83d51a4a9f3f32449584210523b0f1d25214d79f5ba449850d0c3836e72dfdca",
    "b059d5de99ba99e9d35218c74f7cb12d7ade7293476df81be0089425013a002c",
    "8b248f8cac8fd97fd850f29efa6091b98325445ad3b271b823324e9827f31301",
    "f1cac213cad7008f31ac08bdbef8e78a806dcff31a55963b2e36beae6371fc74",
    "367ec1bb15b34f4e2ce5e69cdb3b603b490585275b2a77a6ecdd516a57bf3189",
    "9b796ae187298eb350c328b9c2b89b8ec1744124b416f1009eb9a8e6680b60cf",
]

CONTROLLED_DIRS = [
    ".github/workflows",
    "adapters",
    "benchmarks",
    "capabilities",
    "domain-packs",
    "policies",
    "prompts",
    "routing",
    "scripts",
    "schemas/v2",
    "tsao_researcher",
    "workflows",
]
TEMPORARY_PATHS = [
    ".github/consolidation",
    ".github/workflows/consolidate-single-main.yml",
    ".github/workflows/materialize-autonomous-v050.yml",
    ".github/workflows/vnext-materialize.yml",
    ".v050-payload",
    ".tsao-research/ci-trigger.txt",
    "scripts/consolidate_single_main.py",
    "scripts/materialize_v050_from_release.py",
    "scripts/vnext_upgrade.py",
    "scripts/vnext_finalize.py",
]
BRANCH_HEADS = {
    "main_before_consolidation": "d4912dd80b85057d43b31d38b3e95a3a5d51fd38",
    "pr2_major_upgrade_history_only": "ee5147cb8d775f5f7933f57b681af6d4a501bcd1",
    "pr3_reaudit_history": "cf8c21356e3380055ba6504d1bb24339799128fc",
    "pr4_vnext_history": "ac9e3dd50908010ecad5d4ed3ad510ca60c9b3f5",
}


class ConsolidationError(RuntimeError):
    pass


def run(*args: str, cwd: Path, capture: bool = False) -> str:
    proc = subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return proc.stdout if capture else ""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def overlay(source: Path, target: Path) -> None:
    for entry in source.iterdir():
        if entry.name == ".git":
            continue
        destination = target / entry.name
        if entry.is_symlink():
            raise ConsolidationError(f"source tree contains symlink: {entry}")
        if entry.is_dir():
            shutil.copytree(entry, destination, dirs_exist_ok=True, copy_function=shutil.copy2)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, destination)


def read_chunks(root: Path, patch_ref: str, temp: Path) -> Path:
    encoded = bytearray()
    diagnostics = []
    for index, expected in enumerate(CHUNK_SHA256):
        path = f".github/consolidation/v051-part-{index:02d}.txt"
        data = run("git", "show", f"{patch_ref}:{path}", cwd=root, capture=True).encode("ascii")
        actual = sha256_bytes(data)
        diagnostics.append({"part": index, "bytes": len(data), "sha256": actual})
        if actual != expected:
            raise ConsolidationError(f"chunk {index} digest mismatch: {actual}")
        encoded.extend(data.strip())
    try:
        compressed = base64.b64decode(bytes(encoded), validate=True)
    except Exception as exc:
        raise ConsolidationError(f"invalid patch Base64: {exc}") from exc
    if sha256_bytes(compressed) != PATCH_GZIP_SHA256:
        raise ConsolidationError("compressed patch digest mismatch")
    try:
        patch = gzip.decompress(compressed)
    except Exception as exc:
        raise ConsolidationError(f"invalid patch gzip: {exc}") from exc
    if sha256_bytes(patch) != PATCH_SHA256:
        raise ConsolidationError("raw patch digest mismatch")
    patch_path = temp / "v051.patch"
    patch_path.write_bytes(patch)
    (temp / "patch-diagnostics.json").write_text(
        json.dumps({"chunks": diagnostics, "gzip_sha256": PATCH_GZIP_SHA256, "patch_sha256": PATCH_SHA256}, indent=2),
        encoding="utf-8",
    )
    return patch_path


def materialize_v050(root: Path, bootstrap_ref: str, temp: Path) -> Path:
    bootstrap = temp / "bootstrap"
    run("git", "worktree", "add", "--detach", str(bootstrap), bootstrap_ref, cwd=root)
    materializer = bootstrap / "scripts/materialize_v050_from_release.py"
    payload = bootstrap / ".v050-payload"
    if not materializer.is_file() or not payload.is_dir():
        raise ConsolidationError("v0.5.0 bootstrap branch lacks materializer or embedded payload")
    run(
        sys.executable,
        str(materializer),
        "--payload-dir",
        str(payload),
        "--sha256",
        V050_ARCHIVE_SHA256,
        "--checkout",
        str(bootstrap),
        cwd=bootstrap,
    )
    if (bootstrap / "VERSION").read_text(encoding="utf-8").strip() != "0.5.0":
        raise ConsolidationError("materialized source is not v0.5.0")
    return bootstrap


def write_report(root: Path, target_branch: str, bootstrap_ref: str, patch_ref: str) -> None:
    pr5_head = run("git", "rev-parse", bootstrap_ref, cwd=root, capture=True).strip()
    heads = dict(BRANCH_HEADS)
    heads["pr5_autonomous_payload_history"] = pr5_head
    report = {
        "schema_version": "1.0",
        "target_branch": target_branch,
        "version": "0.5.1",
        "source_strategy": "legacy-compatible main base + verified v0.5.0 overlay + verified v0.5.1 patch",
        "preserved_history_heads": heads,
        "bootstrap_ref": bootstrap_ref,
        "patch_ref": patch_ref,
        "temporary_payload_removed": True,
        "automatic_scientific_acceptance": False,
    }
    path = root / "docs/SINGLE_MAIN_CONSOLIDATION.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--bootstrap-ref", default="origin/agent/autonomous-v0.5.0")
    parser.add_argument("--patch-ref", default="origin/agent/single-main-consolidation")
    parser.add_argument("--target-branch", default="agent/single-main-consolidation")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        raise ConsolidationError(f"not a Git checkout: {root}")
    run("git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune", cwd=root)
    status = run("git", "status", "--porcelain", cwd=root, capture=True)
    if status.strip():
        raise ConsolidationError(f"checkout must be clean before consolidation:\n{status}")

    with tempfile.TemporaryDirectory(prefix="tsr-consolidate-", dir=root.parent) as temp_name:
        temp = Path(temp_name)
        patch = read_chunks(root, args.patch_ref, temp)
        bootstrap = materialize_v050(root, args.bootstrap_ref, temp)

        run("git", "switch", "-C", args.target_branch, args.patch_ref, cwd=root)
        for relative in CONTROLLED_DIRS:
            remove_path(root / relative)
        overlay(bootstrap, root)
        for relative in TEMPORARY_PATHS:
            remove_path(root / relative)

        run("git", "apply", "--binary", str(patch), cwd=root)
        if (root / "VERSION").read_text(encoding="utf-8").strip() != "0.5.1":
            raise ConsolidationError("patched source is not v0.5.1")
        write_report(root, args.target_branch, args.bootstrap_ref, args.patch_ref)
        run(sys.executable, "scripts/generate_checksums.py", "--write", cwd=root)

    print(json.dumps({"materialized": True, "version": "0.5.1", "branch": args.target_branch}, sort_keys=True))


if __name__ == "__main__":
    main()
