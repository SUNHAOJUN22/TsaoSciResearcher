#!/usr/bin/env python3
"""Deterministic fail-closed Unicode integrity gate for tracked text files."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA = "tsao.unicode-integrity/v1"
TEXT_EXTENSIONS = frozenset(
    {
        ".cfg",
        ".cjs",
        ".css",
        ".csv",
        ".html",
        ".ini",
        ".js",
        ".jsx",
        ".json",
        ".jsonl",
        ".md",
        ".mdx",
        ".mjs",
        ".ps1",
        ".py",
        ".pyi",
        ".scss",
        ".sh",
        ".sql",
        ".svg",
        ".toml",
        ".ts",
        ".tsx",
        ".tsv",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tsao-research",
        "__pycache__",
        "artifacts",
        "build",
        "dist",
        "site",
    }
)
CATEGORY_KEYS = (
    "unsafe_paths",
    "invalid_utf8",
    "replacement_characters",
    "bom_files",
    "line_ending_failures",
    "nfc_failures",
    "control_character_failures",
    "mojibake_failures",
)


def _token(*codepoints: int) -> str:
    return "".join(chr(value) for value in codepoints)


def mojibake_markers() -> tuple[tuple[str, str], ...]:
    return (
        ("latin1-replacement", _token(0x00EF, 0x00BF, 0x00BD)),
        ("smart-apostrophe", _token(0x00E2, 0x20AC, 0x2122)),
        ("smart-quote", _token(0x00E2, 0x20AC, 0x0153)),
        ("utf8-cjk-wen", _token(0x00E6, 0x2013, 0x2021)),
        ("utf8-cjk-zhong", _token(0x00E4, 0x00B8, 0x00AD)),
        ("utf8-cjk-tu", _token(0x00E5, 0x203A, 0x00BE)),
        ("gbk-replacement", _token(0x951F, 0x65A4, 0x62F7)),
        ("debug-fill-hot", _token(0x70EB, 0x70EB, 0x70EB)),
        ("debug-fill-tun", _token(0x5C6F, 0x5C6F, 0x5C6F)),
    )


def _selected_text_path(root: Path, path: Path, excluded_output: Path | None) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in relative.parts):
        return False
    if path.suffix.casefold() not in TEXT_EXTENSIONS:
        return False
    return excluded_output is None or path.resolve() != excluded_output


def _filesystem_text_files(root: Path, output: Path | None = None) -> list[Path]:
    """Enumerate a non-Git test tree deterministically without changing CLI semantics."""

    excluded_output = output.resolve() if output else None
    selected = [
        path
        for path in root.rglob("*")
        if _selected_text_path(root, path, excluded_output)
    ]
    return sorted(selected, key=lambda item: item.relative_to(root).as_posix())


def tracked_text_files(
    root: Path,
    output: Path | None = None,
    *,
    require_git: bool = False,
) -> list[Path]:
    """Return tracked text files, with a deterministic non-Git fallback for pure tests."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").casefold()
        is_non_git_tree = result.returncode == 128 and "not a git repository" in stderr
        if require_git or not is_non_git_tree:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )
        return _filesystem_text_files(root, output)

    excluded_output = output.resolve() if output else None
    selected: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8", errors="strict"))
        path = root / relative
        if not _selected_text_path(root, path, excluded_output):
            continue
        selected.append(path)
    return sorted(selected, key=lambda item: item.relative_to(root).as_posix())


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    os.chmod(temporary, stat.S_IMODE(mode))
    os.replace(temporary, path)


def normalize_file(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"unsafe tracked text path: {path}")
    original = path.read_bytes()
    text = original.decode("utf-8", errors="strict")
    if text.startswith(chr(0xFEFF)):
        text = text[1:]
    normalized = unicodedata.normalize(
        "NFC", text.replace("\r\n", "\n").replace("\r", "\n")
    )
    rendered = (normalized.rstrip("\n") + "\n").encode("utf-8")
    if rendered == original:
        return False
    _atomic_write(path, rendered, path.stat().st_mode)
    return True


def audit_repository(
    root: Path,
    output: Path | None = None,
    *,
    require_git: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    categories: dict[str, list[dict[str, str]]] = {key: [] for key in CATEGORY_KEYS}
    paths = tracked_text_files(root, output, require_git=require_git)

    def add(key: str, path: str, detail: str) -> None:
        categories[key].append({"path": path, "detail": detail})

    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.is_file():
            add("unsafe_paths", relative, "tracked path is not a regular file")
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            add("bom_files", relative, "UTF-8 BOM is forbidden")
        if b"\r" in data:
            add("line_ending_failures", relative, "CR or CRLF is forbidden")
        if not data.endswith(b"\n"):
            add("line_ending_failures", relative, "text file must end with LF")
        elif data.endswith(b"\n\n"):
            add("line_ending_failures", relative, "text file must end with exactly one LF")
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            add("invalid_utf8", relative, f"decode failed at byte {exc.start}")
            continue
        if chr(0xFFFD) in text:
            add("replacement_characters", relative, "U+FFFD is forbidden")
        if unicodedata.normalize("NFC", text) != text:
            add("nfc_failures", relative, "text is not NFC-normalized")
        controls = sorted(
            {
                f"U+{ord(character):04X}"
                for character in text
                if unicodedata.category(character) == "Cc"
                and character not in {"\n", "\t"}
            }
        )
        if controls:
            add("control_character_failures", relative, ", ".join(controls))
        found = [label for label, marker in mojibake_markers() if marker in text]
        if found:
            add("mojibake_failures", relative, ", ".join(found))

    for values in categories.values():
        values.sort(key=lambda item: (item["path"], item["detail"]))
    failures = [
        {"category": key, **item}
        for key in CATEGORY_KEYS
        for item in categories[key]
    ]
    return {
        "schema_version": SCHEMA,
        "verdict": "PASS" if not failures else "FAIL",
        "scanned_text_files": len(paths),
        **categories,
        "failures": failures,
    }


def render_report(report: dict[str, Any]) -> str:
    return (
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--normalize", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = (args.output or root / "reports" / "UNICODE_INTEGRITY_REPORT.json").resolve()
    if args.normalize and not args.write:
        parser.error("--normalize requires --write")
    normalized = 0
    if args.normalize:
        for path in tracked_text_files(root, output, require_git=True):
            normalized += int(normalize_file(path))
    report = audit_repository(root, output, require_git=True)
    rendered = render_report(report)
    if args.write:
        _atomic_write(output, rendered.encode("utf-8"), 0o644)
    else:
        if not output.is_file() or output.is_symlink():
            raise SystemExit(f"Unicode report is missing or unsafe: {output}")
        if output.read_text(encoding="utf-8", errors="strict") != rendered:
            raise SystemExit("Unicode report is stale; run with --write")
    print(rendered, end="")
    if args.normalize:
        print(f"normalized_text_files={normalized}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
