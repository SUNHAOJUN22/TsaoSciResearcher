from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = ROOT / "scripts/build_validation_evidence.py"
text = path.read_text(encoding="utf-8")
text = once(
    text,
    'DEFAULT_COMPATIBILITY = {\n    "macos_python_3_12": "PASS",\n    "ubuntu_python_3_10": "PASS",\n    "ubuntu_python_3_13": "PASS",\n    "windows_python_3_12": "PASS",\n}\n',
    'DEFAULT_COMPATIBILITY = {\n    "ubuntu_python_3_10": "PASS",\n    "ubuntu_python_3_13": "PASS",\n    "windows_python_3_12": "PASS",\n}\n',
    "compatibility matrix",
)
text = once(
    text,
    '''def _compatibility(current: dict[str, Any]) -> dict[str, str]:
    value = current.get("compatibility")
    if not isinstance(value, dict):
        return dict(DEFAULT_COMPATIBILITY)
    rows = {str(key): str(status) for key, status in value.items()}
    return rows or dict(DEFAULT_COMPATIBILITY)
''',
    '''def _compatibility(current: dict[str, Any]) -> dict[str, str]:
    value = current.get("compatibility")
    if not isinstance(value, dict):
        return dict(DEFAULT_COMPATIBILITY)
    rows = {key: str(value[key]) for key in DEFAULT_COMPATIBILITY if key in value}
    return rows or dict(DEFAULT_COMPATIBILITY)
''',
    "compatibility filter",
)
text = once(text, '        "json_schemas_19": "PASS",\n', '        "json_schemas_20": "PASS",\n', "schema gate")
text = once(
    text,
    '    compatibility = {str(key): str(value) for key, value in baseline["compatibility"].items()}\n',
    '    compatibility = _compatibility({"compatibility": baseline["compatibility"]})\n',
    "composite compatibility",
)
text = once(
    text,
    '''        "limitations": [
            "Checked-in preflight evidence is not a substitute for the external CI attestation.",
            "External scientific execution requires a checksum-verifiable execution receipt.",
        ],
''',
    '''        "limitations": (
            [
                "The external CI attestation qualifies repository software only.",
                "External scientific execution requires a checksum-verifiable execution receipt.",
            ]
            if attested
            else [
                "Checked-in preflight evidence is not a substitute for the external CI attestation.",
                "External scientific execution requires a checksum-verifiable execution receipt.",
            ]
        ),
''',
    "scope limitations",
)
path.write_text(text, encoding="utf-8", newline="\n")

english = '''## 6. Acceptance strategy: checked-in evidence + current-tree attestation

The repository separates two machine-readable evidence roles so that a commit never pretends to contain its own final external attestation:

- `docs/VALIDATION_EVIDENCE.json` is the checked-in, non-self-referential record. It may remain `composite/PARTIAL` when it combines a pinned full-tree baseline with a SHA-256-bound focused delta.
- every successful `full-validation-and-release-evidence` CI job writes `artifacts/VALIDATION_EVIDENCE.json` in `current-tree/PASS` mode, bound to the tested commit, workflow run, attempt, dependency lock and validation-tree digest;
- the qualified matrix is Windows and Linux only: Ubuntu/Python 3.10, Ubuntu/Python 3.13 and Windows/Python 3.12. macOS is outside release qualification;
- neither evidence form certifies a DFT, MD, CFD, process-simulation, instrument or laboratory result.

The CI badge and uploaded `validation-evidence-<sha>` artifact are authoritative for the exact current-tree software verdict.

![Reproducibility quality gates](docs/assets/ai/reproducibility_quality_gates.svg)
![Compatibility matrix](docs/assets/ai/installation_compatibility_matrix.svg)
![Supply-chain attestation](docs/assets/ai/supply_chain_release_attestation.svg)

'''
chinese = '''## 6. 验收策略：仓库内证据 + 当前树外部证明

仓库把两类机器证据严格分开，避免一个 commit 伪装成“已经把自己的最终外部证明写进自身”：

- `docs/VALIDATION_EVIDENCE.json` 是仓库内、非自引用的记录；当它由固定全树基线与 SHA-256 绑定的聚焦增量组成时，可以保持 `composite/PARTIAL`；
- 每次成功的 `full-validation-and-release-evidence` CI 作业都会生成 `artifacts/VALIDATION_EVIDENCE.json`，状态为 `current-tree/PASS`，并绑定被测试 commit、工作流 run、attempt、依赖锁和验证树摘要；
- 正式兼容矩阵仅包括 Windows 与 Linux：Ubuntu/Python 3.10、Ubuntu/Python 3.13、Windows/Python 3.12；macOS 不属于发布资格；
- 两类证据都只验证仓库软件，不会自动认证 DFT、MD、CFD、流程模拟、仪器或实验结果。

CI 徽章和上传的 `validation-evidence-<sha>` 工件是精确当前树的软件判定依据。

![可复现质量门](docs/assets/ai/reproducibility_quality_gates.svg)
![兼容性矩阵](docs/assets/ai/installation_compatibility_matrix.svg)
![供应链证明](docs/assets/ai/supply_chain_release_attestation.svg)

'''
for filename in ("README.md", "README_EN.md"):
    readme = ROOT / filename
    value = readme.read_text(encoding="utf-8")
    value, count = re.subn(r"## 6\. Acceptance strategy:.*?(?=## 7\. Core CLI)", english, value, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{filename}: acceptance section count={count}")
    readme.write_text(value, encoding="utf-8", newline="\n")
zh = ROOT / "README.zh-CN.md"
value = zh.read_text(encoding="utf-8")
value, count = re.subn(r"## 6\. 验收策略：.*?(?=## 7\. 核心 CLI 使用方法)", chinese, value, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f"README.zh-CN.md: acceptance section count={count}")
zh.write_text(value, encoding="utf-8", newline="\n")

(ROOT / "tests/test_validation_evidence_contract.py").write_text(
    '''from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_validation_evidence.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("validation_evidence_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_matrix_matches_permanent_ci() -> None:
    module = _load()
    expected = {
        "ubuntu_python_3_10": "PASS",
        "ubuntu_python_3_13": "PASS",
        "windows_python_3_12": "PASS",
    }
    assert module.DEFAULT_COMPATIBILITY == expected
    assert module._compatibility({"compatibility": {"macos_python_3_12": "PASS", **expected}}) == expected


def test_attested_schema_gate_and_limitations() -> None:
    module = _load()
    gates = module._attested_gates()
    assert gates["json_schemas_20"] == "PASS"
    assert "json_schemas_19" not in gates
    value = module.build(source_commit="1" * 40, publication_parent="2" * 40, run_id=1, run_attempt=1, attested=True)
    assert value["status"] == "PASS"
    assert value["validation_scope"] == "current-tree"
    assert value["compatibility"] == module.DEFAULT_COMPATIBILITY
    assert all("preflight" not in row.casefold() for row in value["limitations"])


def test_composite_record_filters_legacy_macos() -> None:
    module = _load()
    value = module.build(composite=True)
    assert value["compatibility"] == module.DEFAULT_COMPATIBILITY
''',
    encoding="utf-8",
    newline="\n",
)
print("reconciliation staged")
