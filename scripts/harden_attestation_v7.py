#!/usr/bin/env python3
"""Apply the final attestation-governance and README truth-boundary patch."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/main-attestation.yml"
README = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_ZH = ROOT / "README.zh-CN.md"
SELF = Path(__file__).resolve()


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8", errors="strict")
    marker = "\n  maintenance-hardening:\n"
    if marker not in text:
        raise SystemExit("maintenance-hardening bootstrap job is missing")
    text = text.split(marker, 1)[0].rstrip() + "\n"

    required = (
        "types: [opened]",
        "group: exact-main-attestation-${{ github.sha }}",
        "cancel-in-progress: true",
        "name: Validate attestation governance policy",
        "permissions:\n      contents: read\n      issues: write",
    )
    for token in required:
        if token not in text:
            raise SystemExit(f"final attestation workflow is missing: {token}")
    top_level = text.split("concurrency:", 1)[0]
    if "issues: write" in top_level:
        raise SystemExit("top-level attestation permissions still grant issues: write")
    if "assigned" in text:
        raise SystemExit("assigned issue trigger remains in final attestation workflow")
    WORKFLOW.write_text(text, encoding="utf-8", newline="\n")


def patch_english() -> None:
    text = README.read_text(encoding="utf-8", errors="strict")
    text = replace_once(
        text,
        "The published 0.7.0 tree was verified by GitHub Actions run `30525731965` on Ubuntu / Python 3.12 using the exact locked toolchain:",
        "The release 0.7.0 quality baseline was verified by GitHub Actions run `30525731965` on Ubuntu / Python 3.12 using the exact locked toolchain:",
        label="English validation heading",
    )
    text = replace_once(
        text,
        "| Exact-lock dependency audit | **PASS; no known vulnerabilities** |\nChecked-in `docs/VALIDATION_EVIDENCE.json` remains deliberately `preflight/PARTIAL`; commit-bound PASS evidence is produced externally by CI to avoid self-referential commit claims.",
        "| Exact-lock dependency audit | **PASS; no known vulnerabilities** |\n\nThe current `main` commit is independently verified by the [Exact main attestation workflow](.github/workflows/main-attestation.yml). Successful runs publish an artifact named `exact-main-attestation-<commit SHA>`, so the commit does not need to embed a self-referential run ID.\n\nChecked-in `docs/VALIDATION_EVIDENCE.json` remains deliberately `preflight/PARTIAL`; commit-bound PASS evidence is produced externally by CI to avoid self-referential commit claims.",
        label="English exact-attestation note",
    )
    README.write_text(text, encoding="utf-8", newline="\n")
    README_EN.write_text(text, encoding="utf-8", newline="\n")


def patch_chinese() -> None:
    text = README_ZH.read_text(encoding="utf-8", errors="strict")
    text = replace_once(
        text,
        "已发布的 0.7.0 主分支代码已由 GitHub Actions 运行 `30525731965` 在 Ubuntu / Python 3.12 与精确锁定工具链下完成验证：",
        "0.7.0 版本质量基线已由 GitHub Actions 运行 `30525731965` 在 Ubuntu / Python 3.12 与精确锁定工具链下完成验证：",
        label="Chinese validation heading",
    )
    text = replace_once(
        text,
        "| 精确锁依赖审计 | **PASS；未发现已知漏洞** |\n仓库内 `docs/VALIDATION_EVIDENCE.json` 有意保留为 `preflight/PARTIAL`；与提交绑定的 PASS 证明由 CI 外部生成，避免在提交内部制造自引用 SHA。",
        "| 精确锁依赖审计 | **PASS；未发现已知漏洞** |\n\n当前 `main` 提交由[精确主线证明工作流](.github/workflows/main-attestation.yml)独立验证。成功运行会发布名为 `exact-main-attestation-<提交 SHA>` 的产物，从而避免在被证明的提交内部写入自引用运行号。\n\n仓库内 `docs/VALIDATION_EVIDENCE.json` 有意保留为 `preflight/PARTIAL`；与提交绑定的 PASS 证明由 CI 外部生成，避免在提交内部制造自引用 SHA。",
        label="Chinese exact-attestation note",
    )
    README_ZH.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    patch_workflow()
    patch_english()
    patch_chinese()
    SELF.unlink()
    print("attestation governance and README truth boundary patched")


if __name__ == "__main__":
    main()
