#!/usr/bin/env python3
"""Apply the repository-staged v0.7.3 quantitative-integrity payload safely."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zlib

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".tsr-finalize"
PARTS = tuple(f"part-{index:03d}.b64" for index in range(5))
ALLOWED = {
    "CHANGELOG.md",
    "CITATION.cff",
    "README.md",
    "README.zh-CN.md",
    "README_CN.md",
    "README_EN.md",
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "docs/VALIDATION.md",
    "docs/VISUAL_ATLAS.md",
    "docs/VISUAL_ATLAS.zh-CN.md",
    "docs/assets/ai/applicability_extrapolation_guard.svg",
    "docs/assets/ai/evidence_conflict_resolution.svg",
    "docs/assets/ai/mechanism_identifiability_gate.svg",
    "docs/assets/ai/quantity_dimension_contract.svg",
    "manifest.json",
    "pyproject.toml",
    "schemas/v2/computation-strategy.schema.json",
    "scripts/build_readme_facts.py",
    "tests/test_strategy_passport.py",
    "tests/test_strategy_quantitative_integrity.py",
    "tsao_researcher/strategy.py",
}
MANDATORY = {
    "README.md",
    "README.zh-CN.md",
    "schemas/v2/computation-strategy.schema.json",
    "tests/test_strategy_quantitative_integrity.py",
    "tsao_researcher/strategy.py",
    "docs/assets/ai/applicability_extrapolation_guard.svg",
    "docs/assets/ai/evidence_conflict_resolution.svg",
    "docs/assets/ai/mechanism_identifiability_gate.svg",
    "docs/assets/ai/quantity_dimension_contract.svg",
}


def _decode_payload(raw: bytes) -> object:
    attempts: list[tuple[str, bytes]] = [("direct", raw)]
    for label, decoder in (("zlib", zlib.decompress), ("gzip", gzip.decompress)):
        try:
            attempts.append((label, decoder(raw)))
        except (OSError, zlib.error):
            continue
    errors: list[str] = []
    for label, candidate in attempts:
        try:
            value = json.loads(candidate.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: {exc}")
            continue
        print(f"payload envelope={label} bytes={len(candidate)}")
        return value
    raise SystemExit("payload is not supported UTF-8 JSON: " + " | ".join(errors))


def main() -> None:
    actual_names = sorted(path.name for path in STAGE.glob("part-*.b64") if path.is_file())
    if actual_names != list(PARTS):
        raise SystemExit(f"staged payload parts mismatch: {actual_names!r}")
    encoded = "".join((STAGE / name).read_text(encoding="ascii").strip() for name in PARTS)
    raw = base64.b64decode(encoded, validate=True)
    print(
        "staged payload",
        f"base64_chars={len(encoded)}",
        f"raw_bytes={len(raw)}",
        f"sha256={hashlib.sha256(raw).hexdigest()}",
    )
    payload = _decode_payload(raw)
    if isinstance(payload, dict) and isinstance(payload.get("files"), dict):
        files = payload["files"]
    else:
        files = payload
    if not isinstance(files, dict):
        raise SystemExit("payload root must be a path-to-text mapping or contain a files mapping")
    if not 10 <= len(files) <= len(ALLOWED):
        raise SystemExit(f"unexpected payload file count: {len(files)}")
    keys = set(files)
    if not MANDATORY.issubset(keys):
        raise SystemExit(f"mandatory payload paths missing: {sorted(MANDATORY - keys)}")
    if not keys.issubset(ALLOWED):
        raise SystemExit(f"payload contains disallowed paths: {sorted(keys - ALLOWED)}")

    for relative in sorted(keys):
        content = files[relative]
        if not isinstance(relative, str) or not isinstance(content, str):
            raise SystemExit("payload paths and contents must be strings")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
            raise SystemExit(f"unsafe payload path: {relative}")
        if "\x00" in content:
            raise SystemExit(f"NUL byte in payload text: {relative}")
        target = ROOT.joinpath(*pure.parts)
        if target.is_symlink():
            raise SystemExit(f"refusing to replace symlink: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    runner_temp = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    runner_temp.mkdir(parents=True, exist_ok=True)
    (runner_temp / "tsr_payload_paths.txt").write_text(
        "\n".join(sorted(keys)) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"quantitative-integrity payload applied: {len(keys)} files")


if __name__ == "__main__":
    main()
