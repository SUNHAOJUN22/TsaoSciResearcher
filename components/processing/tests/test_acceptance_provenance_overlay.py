from __future__ import annotations

import hashlib
from pathlib import Path

from tsao.provenance import verify_manifest
from tsao.snapshot import _manifest_paths

HEADER = "path\tsha256\tbytes\tspecialist\tartifact_class\tlicense_scope\n"
TAIL = "\tmaster\tPUBLIC_SOURCE\tPROJECT_OWNED_OR_COMPATIBLE\n"


def _row(path: str, payload: bytes) -> str:
    return f"{path}\t{hashlib.sha256(payload).hexdigest()}\t{len(payload)}{TAIL}"


def test_acceptance_overlay_overrides_stale_core_identity(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    source = tmp_path / "example.txt"
    source.write_bytes(b"current\n")
    (reports / "SOURCE_CORE_MANIFEST.tsv").write_text(
        HEADER + _row("example.txt", b"base\n"), encoding="utf-8"
    )
    (reports / "SOURCE_CORE_OVERLAY.tsv").write_text(
        HEADER + _row("example.txt", b"stale\n"), encoding="utf-8"
    )
    (reports / "SOURCE_ACCEPTANCE_OVERLAY.tsv").write_text(
        HEADER + _row("example.txt", b"current\n"), encoding="utf-8"
    )

    assert verify_manifest(tmp_path, reports / "SOURCE_CORE_MANIFEST.tsv") == []


def test_snapshot_manifest_paths_include_acceptance_delta(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.tsv"
    core = tmp_path / "core.tsv"
    acceptance = tmp_path / "acceptance.tsv"
    manifest.write_text(HEADER + _row("base.txt", b"base"), encoding="utf-8")
    core.write_text(HEADER + _row("core.txt", b"core"), encoding="utf-8")
    acceptance.write_text(HEADER + _row("acceptance.txt", b"acceptance"), encoding="utf-8")

    assert _manifest_paths(manifest, (core, acceptance)) == [
        "base.txt",
        "core.txt",
        "acceptance.txt",
    ]
