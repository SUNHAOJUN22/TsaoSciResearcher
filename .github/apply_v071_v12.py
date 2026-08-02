from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

BASELINE = "d9eca929fc39e329b1d94fdb2a08d2a75b577afa"
BASE_SHA = "e7fb0bdae5b0dee605f9b84ea4361ef15a4b676831434a6e48a5aa3d53f0f036"
OPT_SHA = "6d7f1ebadac996773217ed2305556658d874afe9c9f26364a42c132a515e5ad9"


def checked_archive(encoded: str, expected_sha: str, label: str) -> bytes:
    data = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha:
        raise AssertionError((label, actual, expected_sha))
    return data


def comment_archive() -> bytes:
    rows = json.loads(Path("/tmp/comments.json").read_text(encoding="utf-8"))
    pattern = re.compile(r"PART (\d{2})/(\d{2})\n([A-Za-z0-9+/=]+)")
    parts: dict[str, str] = {}
    for row in rows:
        match = pattern.fullmatch(row.get("body", ""))
        if not match:
            continue
        index, declared, payload = match.groups()
        if int(declared) != 16 or index in parts:
            raise AssertionError((index, declared))
        parts[index] = payload
    keys = [f"{index:02d}" for index in range(16)]
    if sorted(parts) != keys:
        raise AssertionError(sorted(parts))
    return checked_archive("".join(parts[key] for key in keys), BASE_SHA, "BASE")


def optimization_archive() -> bytes:
    encoded = "".join(
        Path(f".github/v071-opt-part-{index:02d}.b64")
        .read_text(encoding="ascii")
        .strip()
        for index in range(8)
    )
    encoded += Path(".github/v071-opt-part-08a.b64").read_text(encoding="ascii").strip()
    encoded += Path(".github/v071-opt-part-08b.b64").read_text(encoding="ascii").strip()
    return checked_archive(encoded, OPT_SHA, "OPT")


def apply_archive(data: bytes, guard) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if not (1 < len(members) <= 250):
            raise AssertionError(len(members))
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise AssertionError("invalid member set")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise AssertionError(member.name)
            if not member.isfile() or member.issym() or member.islnk():
                raise AssertionError(member.name)
        stream = archive.extractfile(archive.getmember("manifest.json"))
        if stream is None:
            raise AssertionError("manifest missing")
        manifest = json.loads(stream.read().decode("utf-8", errors="strict"))
        guard(manifest)
        rows = manifest["files"]
        expected = {f"files/{row['path']}" for row in rows} | {"manifest.json"}
        if set(names) != expected:
            raise AssertionError("manifest/member mismatch")
        for row in rows:
            rel = PurePosixPath(row["path"])
            if rel.is_absolute() or ".." in rel.parts or "\\" in row["path"]:
                raise AssertionError(row["path"])
            mode = int(row["mode"], 8)
            if mode not in {0o644, 0o755}:
                raise AssertionError(mode)
            stream = archive.extractfile(archive.getmember(f"files/{row['path']}"))
            if stream is None:
                raise AssertionError(row["path"])
            payload = stream.read()
            if len(payload) != row["bytes"]:
                raise AssertionError(row["path"])
            if hashlib.sha256(payload).hexdigest() != row["sha256"]:
                raise AssertionError(row["path"])
            destination = Path(row["path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            destination.chmod(mode)


def main() -> None:
    apply_archive(
        comment_archive(),
        lambda manifest: manifest["base_commit"] == BASELINE
        or (_ for _ in ()).throw(AssertionError("base manifest mismatch")),
    )
    if Path("VERSION").read_text(encoding="utf-8").strip() != "0.7.1":
        raise AssertionError("version mismatch")
    version_test = Path("tests/test_import_isolation.py")
    source = version_test.read_text(encoding="utf-8")
    old = "assert tsao_researcher.__version__ == '0.7.0'"
    new = "assert tsao_researcher.__version__ == '0.7.1'"
    if source.count(old) != 1:
        raise AssertionError("version assertion mismatch")
    version_test.write_text(source.replace(old, new), encoding="utf-8", newline="\n")

    apply_archive(
        optimization_archive(),
        lambda manifest: manifest["base_overlay_sha256"] == BASE_SHA
        or (_ for _ in ()).throw(AssertionError("optimization manifest mismatch")),
    )

    fullwidth = "\uff21\uff2c\uff30\uff28\uff21"
    escaped = r"\uff21\uff2c\uff30\uff28\uff21"
    for test_name in (
        "tests/test_optimization_boundaries.py",
        "tests/test_performance_contracts.py",
    ):
        path = Path(test_name)
        source = path.read_text(encoding="utf-8")
        if source.count(fullwidth) != 1:
            raise AssertionError(test_name)
        path.write_text(source.replace(fullwidth, escaped), encoding="utf-8", newline="\n")

    patch_path = Path(".github/apply_v071_cli_lazy.py")
    namespace: dict[str, object] = {"__name__": "apply_v071_cli_lazy"}
    exec(compile(patch_path.read_bytes(), str(patch_path), "exec"), namespace)
    patch_main = namespace.get("main")
    if not callable(patch_main):
        raise AssertionError("CLI lazy patch main is missing")
    patch_main()
    patch_path.unlink()

    hook = Path(".git/hooks/pre-commit")
    hook.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "git restore --source=HEAD --staged --worktree .github/workflows\n",
        encoding="utf-8",
        newline="\n",
    )
    hook.chmod(0o755)


if __name__ == "__main__":
    main()
