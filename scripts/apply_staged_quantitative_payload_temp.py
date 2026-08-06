#!/usr/bin/env python3
"""Verify and apply the consolidated repository-staged v0.7.3 candidate."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zlib

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".tsr-finalize-v2"
PART_SHA256 = {
    "part-000.b64": "3401a16bfb8b6758f58e361e7f130ee086e17677ba3c1e9d88e01a6b770c38ea",
    "part-001.b64": "35117a82be72d77cc67ce08b1435758c0a5117a7136fa2128f6e08aa79e5d784",
    "part-002.b64": "2440561223f421fb02c16d466f14e4456c10c1bc8f1c2a662b6da6033484de42",
    "part-003.b64": "fca6f4fa747c74124faae3b05566e2fbcd3820573d48a54c2aac625af8c9fa4b",
    "part-004.b64": "98340aa02ac9ab41f6502f9f109a930699f2f9cb3762079ec6ea5e5f07be3277",
    "part-005.b64": "942c48cf9c1d66de58fc6686085be6e45b8e900496e0f65adf7e3e4124fab7ea",
    "part-006.b64": "9711672571dab4710b2bf7277e61d4a3c9a755e30cab989054cae991071e679d",
    "part-007.b64": "a960fa711f416e68bd21a0896b4ae0c6107063f93e04b0bd2029fa915fc03c25",
    "part-008.b64": "26c3e50bd6289d9c73b78f47f4087f48f689cfb358601c01b03b8a6d6237a7b6",
    "part-009.b64": "cb476456eacbc0f4f6bfabdfb1a9fd1ae08f519615a3b119f9d140d24db9ae06",
    "part-010.b64": "e0e02c3d4d2d8d0ebe30ce794207159baafc1ff2bb47552dcbe5dadd9dc83aaf",
    "part-011.b64": "873b0f7f417ca01e897e3a31e6893f7d39bcd8f06840da542d26833fdc30b29d",
}
BASE64_CHARS = 81212
BASE64_SHA256 = "bc58d21b3386df7976279d7da801630206fe366113675e70b33b38135a1302d9"
COMPRESSED_BYTES = 60908
COMPRESSED_SHA256 = "4a7f4ea38fbf922746bf3b18a71d5c6ae02ddb94b53c11df50194068c23001b4"
FORMAT = "tsr-quantitative-integrity-v2"
PATHS = {
    "CHANGELOG.md",
    "README.md",
    "README.zh-CN.md",
    "docs/VALIDATION.md",
    "docs/VISUAL_ATLAS.md",
    "docs/VISUAL_ATLAS.zh-CN.md",
    "docs/assets/ai/applicability_extrapolation_guard.svg",
    "docs/assets/ai/evidence_conflict_resolution.svg",
    "docs/assets/ai/mechanism_identifiability_gate.svg",
    "docs/assets/ai/quantity_dimension_contract.svg",
    "schemas/v2/computation-strategy.schema.json",
    "scripts/build_readme_facts.py",
    "tests/test_strategy_passport.py",
    "tests/test_strategy_quantitative_integrity.py",
    "tsao_researcher/strategy.py",
}
STRATEGY_SIM114_BEFORE = """    if explicit and not transfer_markers:
        status = \"blocked\"
    elif explicit:
        status = \"review-required\"
    elif not conditions:
        status = \"review-required\"
    else:
        status = \"pass\"
"""
STRATEGY_SIM114_AFTER = """    if explicit and not transfer_markers:
        status = \"blocked\"
    elif explicit or not conditions:
        status = \"review-required\"
    else:
        status = \"pass\"
"""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    actual = sorted(path.name for path in STAGE.glob("part-*.b64") if path.is_file())
    expected = sorted(PART_SHA256)
    if actual != expected:
        raise SystemExit(f"staged part set mismatch: {actual!r}")

    fragments: list[str] = []
    mismatches: list[str] = []
    for name, expected_digest in PART_SHA256.items():
        fragment = (STAGE / name).read_text(encoding="ascii").strip()
        digest = _sha256(fragment.encode("ascii"))
        if digest != expected_digest:
            mismatches.append(
                f"{name}: expected={expected_digest} actual={digest} chars={len(fragment)}"
            )
        fragments.append(fragment)
    if mismatches:
        raise SystemExit("staged payload checksum mismatches:\n" + "\n".join(mismatches))

    encoded = "".join(fragments)
    encoded_digest = _sha256(encoded.encode("ascii"))
    if len(encoded) != BASE64_CHARS or encoded_digest != BASE64_SHA256:
        raise SystemExit(
            f"joined Base64 mismatch: chars={len(encoded)} sha256={encoded_digest}"
        )
    compressed = base64.b64decode(encoded, validate=True)
    compressed_digest = _sha256(compressed)
    if len(compressed) != COMPRESSED_BYTES or compressed_digest != COMPRESSED_SHA256:
        raise SystemExit(
            f"compressed payload mismatch: bytes={len(compressed)} sha256={compressed_digest}"
        )
    try:
        payload = json.loads(zlib.decompress(compressed).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, zlib.error) as exc:
        raise SystemExit(f"payload decode failed: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise SystemExit("payload format marker mismatch")
    files = payload.get("files")
    if not isinstance(files, dict) or set(files) != PATHS:
        raise SystemExit("payload path set mismatch")

    for relative in sorted(PATHS):
        content = files[relative]
        if not isinstance(content, str) or "\x00" in content:
            raise SystemExit(f"invalid text payload: {relative}")
        if relative == "tsao_researcher/strategy.py":
            occurrences = content.count(STRATEGY_SIM114_BEFORE)
            if occurrences != 1:
                raise SystemExit(
                    "strategy SIM114 repair precondition mismatch: "
                    f"expected=1 actual={occurrences}"
                )
            content = content.replace(
                STRATEGY_SIM114_BEFORE, STRATEGY_SIM114_AFTER, 1
            )
        pure = PurePosixPath(relative)
        if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
            raise SystemExit(f"unsafe payload path: {relative}")
        target = ROOT.joinpath(*pure.parts)
        if target.is_symlink():
            raise SystemExit(f"refusing to replace symlink: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    manifest_text = "\n".join(sorted(PATHS)) + "\n"
    runner_temp = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    manifest_dirs = [runner_temp]
    posix_tmp = Path("/tmp")
    if os.name != "nt" and runner_temp != posix_tmp:
        manifest_dirs.append(posix_tmp)
    for manifest_dir in manifest_dirs:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / "tsr_payload_paths.txt").write_text(
            manifest_text, encoding="utf-8", newline="\n"
        )
    print(
        "quantitative-integrity payload applied",
        f"files={len(PATHS)}",
        f"compressed_sha256={COMPRESSED_SHA256}",
    )


if __name__ == "__main__":
    main()
