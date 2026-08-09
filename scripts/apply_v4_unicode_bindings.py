#!/usr/bin/env python3
"""Bind the V4 Unicode gate into Researcher CI and final preflight."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    preflight_path = ROOT / "scripts" / "final_acceptance_preflight.py"
    preflight = preflight_path.read_text(encoding="utf-8")
    required_anchor = '    "scripts/validate_mathematical_contracts.py",\n'
    preflight = replace_once(
        preflight,
        required_anchor,
        required_anchor
        + '    "scripts/validate_unicode_integrity.py",\n'
        + '    "reports/UNICODE_INTEGRITY_REPORT.json",\n',
        "preflight required paths",
    )
    check_anchor = "    textual_paths = [\n"
    unicode_check = '''    unicode_verdict = "MISSING"
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
    preflight = replace_once(
        preflight,
        check_anchor,
        unicode_check + check_anchor,
        "preflight Unicode check",
    )
    return_anchor = '        "external_boundary_marker": EXTERNAL_BOUNDARY_MARKER,\n'
    preflight = replace_once(
        preflight,
        return_anchor,
        return_anchor + '        "unicode_integrity_verdict": unicode_verdict,\n',
        "preflight result field",
    )
    preflight_path.write_text(preflight, encoding="utf-8", newline="\n")

    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    ci = ci_path.read_text(encoding="utf-8")
    compile_anchor = "          python -m compileall -q scripts tsao_researcher tests\n"
    ci = replace_once(
        ci,
        compile_anchor,
        "          python scripts/validate_unicode_integrity.py --check\n"
        + compile_anchor,
        "compatibility Unicode gate",
    )
    full_anchor = "          python scripts/sync_version.py --check\n"
    ci = replace_once(
        ci,
        full_anchor,
        "          python scripts/validate_unicode_integrity.py --check\n"
        + full_anchor,
        "full-validation Unicode gate",
    )
    ci_path.write_text(ci, encoding="utf-8", newline="\n")

    controller = ROOT / ".github" / "workflows" / "v4-unicode-export-once.yml"
    controller.unlink()
    legacy = ROOT / ".github" / "workflows" / "v4-unicode-hardening-once.yml"
    legacy.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
