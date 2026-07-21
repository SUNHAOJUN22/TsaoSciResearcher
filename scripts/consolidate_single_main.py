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
PATCH_GZIP_SHA256 = "8847d89426220797177827ed157c7e6adddf1330b643cab45d7c39dfbd6bd370"
PATCH_SHA256 = "080ad6c154671059ba182a17859a6261fe139d9b9e2fe90d29b6da88906e882b"
CHUNK_FILES = [
    (".github/consolidation/final-v051-part-00.txt", "fecfe1c163006dfa179b9df79a437763fc42f21f7e4cf3d22c248b5638f36599"),
    (".github/consolidation/final-v051-part-01.txt", "33d60cbcfa356dda23c21792e58ccb8873e76a9d9fab4f47a8a8ae719f32663e"),
    (".github/consolidation/final-v051-part-02.txt", "6c2e0dbb06046ecb16cee07e439f7e78801df8a1c025e3c978f43a3b26401002"),
    (".github/consolidation/final-v051-part-03.txt", "f54cf6df333c769ca80958f84db66667a358a9cc91dc8009583ac2a6354b2801"),
    (".github/consolidation/final-v051-tail-00.txt", "2841b1abe6459600438baeba3d6f641773dd7a6bcf560334daba1e08ddff43bb"),
    (".github/consolidation/final-v051-tail-01.txt", "efb1856040b917eaaf04371b28a8a6764cdcd43f341fdd7ba017d87c9e6afd58"),
    (".github/consolidation/final-v051-tail-02.txt", "bc4e92dddb604ddd921eb7b2056da76fbf82d581ec52a78dc422bd21b5ea0e48"),
    (".github/consolidation/final-v051-tail-03.txt", "6dd975590660b7353398ca2f810cb9ec961037e563e58d67d10b3324ea5a11f7"),
    (".github/consolidation/final-v051-tail-04.txt", "ba3d134d1d10bde2600faad871b8a7edc51ce6bddaf87743b22d4ec0353d12eb"),
    (".github/consolidation/final-v051-tail-05.txt", "e2f801aa603ab389533fd2b5d3ae0c5e6611dd74b7e0ed2fdc1c8ddcb5ffa74e"),
]
PRESERVED_HISTORY_HEADS = [
    "ee5147cb8d775f5f7933f57b681af6d4a501bcd1",
    "cf8c21356e3380055ba6504d1bb24339799128fc",
    "ac9e3dd50908010ecad5d4ed3ad510ca60c9b3f5",
    "7a4b9d1ee6c6182f820ee65d063f03df9bb911d8",
]

class ConsolidationError(RuntimeError):
    pass

def run(*args: str, cwd: Path, capture: bool = False) -> str:
    proc = subprocess.run(list(args), cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None, shell=False)
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

def clear_worktree(root: Path) -> None:
    for entry in root.iterdir():
        if entry.name != ".git":
            remove_path(entry)

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

def read_patch(root: Path, patch_ref: str, temp: Path) -> Path:
    encoded = bytearray()
    diagnostics: list[dict[str, object]] = []
    for index, (path, expected) in enumerate(CHUNK_FILES):
        data = run("git", "show", f"{patch_ref}:{path}", cwd=root, capture=True).encode("ascii")
        actual = sha256_bytes(data)
        diagnostics.append({"part": index, "path": path, "bytes": len(data), "sha256": actual})
        if actual != expected:
            raise ConsolidationError(f"chunk {index} digest mismatch: {actual} != {expected}")
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
    (temp / "patch-diagnostics.json").write_text(json.dumps({"chunks": diagnostics, "gzip_sha256": PATCH_GZIP_SHA256, "patch_sha256": PATCH_SHA256}, indent=2) + "\n", encoding="utf-8")
    return patch_path

def materialize_v050(root: Path, bootstrap_ref: str, temp: Path) -> Path:
    bootstrap = temp / "bootstrap"
    run("git", "worktree", "add", "--detach", str(bootstrap), bootstrap_ref, cwd=root)
    materializer = bootstrap / "scripts/materialize_v050_from_release.py"
    payload = bootstrap / ".v050-payload"
    if not materializer.is_file() or not payload.is_dir():
        raise ConsolidationError("v0.5.0 bootstrap branch lacks materializer or embedded payload")
    run(sys.executable, str(materializer), "--payload-dir", str(payload), "--sha256", V050_ARCHIVE_SHA256, "--checkout", str(bootstrap), cwd=bootstrap)
    version = (bootstrap / "VERSION").read_text(encoding="utf-8").strip()
    if version != "0.5.0":
        raise ConsolidationError(f"materialized source version is {version}, expected 0.5.0")
    return bootstrap

def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the verified v0.5.1 single-main candidate.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--bootstrap-ref", default="origin/agent/autonomous-v0.5.0")
    parser.add_argument("--patch-ref", default="HEAD")
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
        patch = read_patch(root, args.patch_ref, temp)
        bootstrap = materialize_v050(root, args.bootstrap_ref, temp)
        run("git", "switch", "-C", args.target_branch, args.patch_ref, cwd=root)
        clear_worktree(root)
        overlay(bootstrap, root)
        run("git", "apply", "--binary", str(patch), cwd=root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if version != "0.5.1":
        raise ConsolidationError(f"patched source version is {version}, expected 0.5.1")
    report = json.loads((root / "docs/SINGLE_MAIN_CONSOLIDATION.json").read_text(encoding="utf-8"))
    for head in PRESERVED_HISTORY_HEADS:
        if head not in report.get("preserved_history_heads", {}).values():
            raise ConsolidationError(f"consolidation report omits preserved history head: {head}")
    if report.get("target_branch") != "main" or report.get("version") != "0.5.1":
        raise ConsolidationError("consolidation report does not describe final main v0.5.1")
    print(json.dumps({"materialized": True, "version": version, "target_branch": args.target_branch}, sort_keys=True))

if __name__ == "__main__":
    main()
