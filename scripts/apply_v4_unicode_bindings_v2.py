#!/usr/bin/env python3
"""Apply V4 Unicode bindings with structural, idempotent edits."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def insert_after(text: str, anchor: str, addition: str, marker: str, label: str) -> str:
    count = text.count(marker)
    if count == 1:
        return text
    if count != 0 or text.count(anchor) != 1:
        raise RuntimeError(f"{label}: marker={count}, anchor={text.count(anchor)}")
    return text.replace(anchor, anchor + addition, 1)


def insert_before(text: str, anchor: str, block: str, marker: str, label: str) -> str:
    count = text.count(marker)
    if count == 1:
        return text
    if count != 0 or text.count(anchor) != 1:
        raise RuntimeError(f"{label}: marker={count}, anchor={text.count(anchor)}")
    return text.replace(anchor, block + anchor, 1)


def insert_command(text: str, anchor_command: str, command: str, label: str) -> str:
    lines = text.splitlines()
    anchors = [
        index for index, line in enumerate(lines) if line.strip() == anchor_command
    ]
    if len(anchors) != 1:
        raise RuntimeError(f"{label}: anchor count={len(anchors)}")
    index = anchors[0]
    if index > 0 and lines[index - 1].strip() == command:
        return text
    indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
    lines.insert(index, f"{indent}{command}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> int:
    preflight_path = ROOT / "scripts/final_acceptance_preflight.py"
    preflight = preflight_path.read_text(encoding="utf-8")
    required_anchor = '    "scripts/validate_mathematical_contracts.py",\n'
    preflight = insert_after(
        preflight,
        required_anchor,
        '    "scripts/validate_unicode_integrity.py",\n'
        '    "reports/UNICODE_INTEGRITY_REPORT.json",\n',
        '    "reports/UNICODE_INTEGRITY_REPORT.json",\n',
        "preflight required paths",
    )
    unicode_block = '''    unicode_verdict = "MISSING"
    unicode_report = root / "reports" / "UNICODE_INTEGRITY_REPORT.json"
    if unicode_report.is_file() and not unicode_report.is_symlink():
        try:
            unicode_payload = json.loads(
                unicode_report.read_text(encoding="utf-8", errors="strict")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            _issue(issues, "unicode_report_invalid", str(unicode_report), str(exc))
        else:
            if not isinstance(unicode_payload, dict):
                _issue(issues, "unicode_report_invalid", str(unicode_report), "root must be an object")
            else:
                unicode_verdict = str(unicode_payload.get("verdict", "MISSING"))
                if unicode_verdict != "PASS":
                    _issue(issues, "unicode_integrity_failed", str(unicode_report), unicode_verdict)
                if int(unicode_payload.get("scanned_text_files", 0)) <= 0:
                    _issue(issues, "unicode_scan_empty", str(unicode_report), "no tracked text files audited")
                if unicode_payload.get("failures"):
                    _issue(issues, "unicode_failures_present", str(unicode_report), "report contains failures")

'''
    preflight = insert_before(
        preflight,
        "    textual_paths = [\n",
        unicode_block,
        '    unicode_verdict = "MISSING"\n',
        "preflight Unicode check",
    )
    result_anchor = '        "external_boundary_marker": EXTERNAL_BOUNDARY_MARKER,\n'
    preflight = insert_after(
        preflight,
        result_anchor,
        '        "unicode_integrity_verdict": unicode_verdict,\n',
        '        "unicode_integrity_verdict": unicode_verdict,\n',
        "preflight result field",
    )
    preflight_path.write_text(preflight, encoding="utf-8", newline="\n")

    ci_path = ROOT / ".github/workflows/ci.yml"
    ci = ci_path.read_text(encoding="utf-8")
    ci = insert_command(
        ci,
        "python -m compileall -q scripts tsao_researcher tests",
        "python scripts/validate_unicode_integrity.py --check",
        "compatibility Unicode gate",
    )
    ci = insert_command(
        ci,
        "python scripts/sync_version.py --check",
        "python scripts/validate_unicode_integrity.py --check",
        "full-validation Unicode gate",
    )
    ci_path.write_text(ci, encoding="utf-8", newline="\n")

    (ROOT / ".github/workflows/v4-unicode-export-once.yml").unlink()
    (ROOT / ".github/workflows/v4-unicode-hardening-once.yml").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
