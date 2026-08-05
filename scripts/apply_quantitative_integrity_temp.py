#!/usr/bin/env python3
"""Apply the checksum-bound v0.7.3 quantitative-integrity payload once."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]
ISSUE_NUMBER = 202
TOTAL_SHA256 = "ad412cba1e03ef8d1fa89ef020a4dd2dedaa9f1743902f413eda47f4e4a27f9b"
PARTS = (
    ("QUANT_V1_PART_001:", "ea3250385c2a3daf6b13cdd5af28f1ec63a213ce5c4992ee5fbba876565ef833"),
    ("QUANT_V1_PART_002:", "92adbbe9db4742dd94454d5e8a5c8cb2129d09534262d924aa86f5c5c7323a5e"),
    ("QUANT_V1_PART_003:", "34705d9307d062f865cbe3e095c9e63ca8e65bd5fc789d2e1a304b5fdc7d8d27"),
    ("QUANT_V1_PART_004:", "42cd84d8632536fc8571ef7c95bdeec4d5bbdbfc679725ce35906c63406e289b"),
    ("QUANT_V1_PART_005:", "6d75f5b66dccae2c24ac4093dfebc2d5670d9323a38da7869e4473482ea69ca3"),
    ("QUANT_V1_PART_006_1:", "f8dd41ecf0a04cc08e3d163cf67f99973a8254bfc04b6ab999987e50f2014fb0"),
    ("QUANT_V1_PART_006_2:", "3bb0889a1225507928f2143c7adbf2696d5137740d09c30db95e4b824c80eae3"),
    ("QUANT_V1_PART_006_3:", "a198134fee30081fdd5dc6e90408934170276ba7de4f6a20cefadd49a36944f4"),
    ("QUANT_V1_PART_006_4:", "3b706a209a20ef3828587d31ca476c3d14a52a3d07ad800fca665a864b9dadb1"),
    ("QUANT_V1_PART_007:", "447e7b95b83c0fb228318f4daba01945c6ea392dca86ea6cad14cb4313f19f9f"),
)
BASELINE = {
    "CHANGELOG.md": "c69d8780c9f0075da7175e7b3bdf5c25387f7d4be6a30b2dad6dfbe31bcd8584",
    "CITATION.cff": "0f5195e75b647119e5e990b0e05d50c3ea4b3f1a1037573809e474872ec94211",
    "README.md": "94c571557b4b14f6ee62a572ebf62376ce9d2a86be7d6df29d074b17fc55b9d8",
    "README.zh-CN.md": "16d7f9aeae92ed3ade922a00fd5563bb87ccc60b1563bb436fb16a9455bd5c0c",
    "README_CN.md": "16d7f9aeae92ed3ade922a00fd5563bb87ccc60b1563bb436fb16a9455bd5c0c",
    "README_EN.md": "94c571557b4b14f6ee62a572ebf62376ce9d2a86be7d6df29d074b17fc55b9d8",
    "SKILL.md": "a2cb2b9e8afed24d975ad553a9b4b5f5032aef3319d8b0d6fa7d1a7f5793b994",
    "VERSION": "d0176718bd214ce8474c06ed61c395ca113fdfc2acdd86d9aa9933b40d9b561e",
    "agents/openai.yaml": "d6f4f703015f23ebeb1c350b6414ad677f8c6c38ce00ed445a6660491914c688",
    "docs/VALIDATION.md": "4284884a61a22ca2644986251c3de77dd18541560ecb60c7146afa92d2538af3",
    "docs/VISUAL_ATLAS.md": "1da9c2f5702a905a0f6a8816ab64e43e4f41c5c287a3ed13819ddda98b3a23db",
    "docs/VISUAL_ATLAS.zh-CN.md": "a9b2d721591ce4b4125041865abede9a5dde565d4cf6e5a0f496c17ec1553dc1",
    "docs/assets/ai/applicability_extrapolation_guard.svg": "ABSENT",
    "docs/assets/ai/evidence_conflict_resolution.svg": "ABSENT",
    "docs/assets/ai/mechanism_identifiability_gate.svg": "ABSENT",
    "docs/assets/ai/quantity_dimension_contract.svg": "ABSENT",
    "manifest.json": "f74bc8db1a5c6ee2e40c75defd7d1f6960e0f88a7a4ef9e8ed8babcd4c0adcc3",
    "pyproject.toml": "e78164062ca5f33c5f17150605a3c8db5ef8ccda1bac0d941e2a5c2374a10358",
    "schemas/v2/computation-strategy.schema.json": "c7dce8f762bf419203b55058cc7480a370a29367f2fb5ef4b0f28f158598015a",
    "scripts/build_readme_facts.py": "db5bb6e9add7d084dfc79f3819049fe45ed276f3b21e0c37cc4184c1f08a32d1",
    "tests/test_strategy_passport.py": "ddd237db0405e5322c93c6fa5d21154e9e78c70b2ee74287912e417951d10393",
    "tests/test_strategy_quantitative_integrity.py": "ABSENT",
    "tsao_researcher/strategy.py": "f432ab1f8cf1b6efde38e41c47a033f37d79128c3dba0a1fd8beda5016c2d37a",
}


def _comments() -> list[dict[str, object]]:
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/issues/{ISSUE_NUMBER}/comments?per_page=100",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TsaoSciResearcher-finalizer",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    if not isinstance(value, list):
        raise SystemExit("GitHub comments response is not a list")
    return value


def main() -> None:
    comments = _comments()
    fragments: list[str] = []
    for prefix, expected in PARTS:
        matches = [
            str(row.get("body", ""))[len(prefix) :]
            for row in comments
            if str(row.get("body", "")).startswith(prefix)
        ]
        if len(matches) != 1:
            raise SystemExit(f"{prefix} expected exactly once, found {len(matches)}")
        fragment = matches[0]
        actual = hashlib.sha256(fragment.encode("ascii")).hexdigest()
        if actual != expected:
            raise SystemExit(f"{prefix} checksum mismatch: {actual}")
        fragments.append(fragment)

    raw = base64.b64decode("".join(fragments), validate=True)
    if hashlib.sha256(raw).hexdigest() != TOTAL_SHA256:
        raise SystemExit("compressed payload checksum mismatch")
    payload = json.loads(zlib.decompress(raw).decode("utf-8"))
    if not isinstance(payload, dict) or set(payload) != set(BASELINE):
        raise SystemExit("payload path set mismatch")

    for relative, content in payload.items():
        if not isinstance(relative, str) or not isinstance(content, str):
            raise SystemExit("payload must map UTF-8 paths to text")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
            raise SystemExit(f"unsafe payload path: {relative}")
        target = ROOT.joinpath(*pure.parts)
        expected = BASELINE[relative]
        if expected == "ABSENT":
            if target.exists() or target.is_symlink():
                raise SystemExit(f"new payload target already exists: {relative}")
        else:
            if target.is_symlink() or not target.is_file():
                raise SystemExit(f"baseline target missing or unsafe: {relative}")
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit(f"concurrent change detected for {relative}: {actual}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    print(f"quantitative-integrity payload applied: {len(payload)} files")


if __name__ == "__main__":
    main()
