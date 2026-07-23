#!/usr/bin/env python3
"""Build a deterministic visual PDF engineering audit report without third-party PDF libraries."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/engineering-audit-report.pdf"
EVIDENCE = ROOT / "docs/VALIDATION_EVIDENCE.json"
QUALITY = ROOT / "docs/SCIENTIFIC_QUALITY_EXAMPLES.json"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text(x: float, y: float, value: str, size: int = 11, bold: bool = False) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({_escape(value)}) Tj ET\n"


def _wrapped(
    x: float,
    y: float,
    value: str,
    *,
    width: int,
    size: int = 8,
    leading: float = 13.0,
    bold: bool = False,
    max_lines: int | None = None,
) -> tuple[str, float]:
    lines = textwrap.wrap(value, width=width, break_long_words=False, break_on_hyphens=False) or [""]
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "..."
    content = ""
    for line in lines:
        content += _text(x, y, line, size, bold)
        y -= leading
    return content, y


def _rect(
    x: float,
    y: float,
    width: float,
    height: float,
    shade: float = 0.95,
    stroke: float = 0.75,
) -> str:
    return f"q {shade:.3f} g {stroke:.3f} G {x:.1f} {y:.1f} {width:.1f} {height:.1f} re B Q\n"


def _bar(x: float, y: float, width: float, ratio: float, shade: float = 0.30) -> str:
    ratio = max(0.0, min(1.0, ratio))
    return (
        f"q 0.92 g {x:.1f} {y:.1f} {width:.1f} 10 re f Q\n"
        f"q {shade:.2f} g {x:.1f} {y:.1f} {width * ratio:.1f} 10 re f Q\n"
    )


def _page_one(evidence: dict[str, Any]) -> str:
    inventory = evidence.get("verified_inventory", {})
    scope = evidence.get("validation_scope", "unknown")
    content = _text(46, 790, "TsaoSciResearcher Engineering Audit", 24, True)
    content += _text(
        46,
        765,
        f"Release {evidence.get('release', 'unknown')} | {scope} evidence | {evidence.get('evidence_date', 'unknown')}",
        11,
    )
    content += _rect(46, 650, 500, 88)
    content += _text(66, 708, "Evidence-first scientific research control layer", 16, True)
    content += _text(
        66,
        681,
        "Question -> evidence -> design -> execution handoff -> validation -> artifact",
        10,
    )
    content += _text(66, 660, "Truth boundary: a contract or handoff is not an execution receipt.", 10)
    cards = [
        ("Capability contracts", inventory.get("capability_records", 0)),
        ("Named catalog contracts", inventory.get("workbook_named_capabilities", 0)),
        ("Workflows", inventory.get("workflows", 0)),
        ("Schemas", inventory.get("schemas", 0)),
        ("Test modules", inventory.get("test_modules", 0)),
        ("Domain packs", inventory.get("domain_packs", 0)),
    ]
    y = 590
    for index, (label, value) in enumerate(cards):
        x = 46 + (index % 2) * 255
        if index % 2 == 0 and index:
            y -= 86
        content += _rect(x, y, 235, 64, 0.98)
        content += _text(x + 16, y + 39, str(value), 20, True)
        content += _text(x + 16, y + 17, label, 9)
    content += _text(46, 270, "Delivered integration", 15, True)
    for offset, item in enumerate(
        [
            "1. Measurement Boundary with calibration, uncertainty and applicability fields",
            "2. Structure-Property planning with confounders, alternatives and scale bridges",
            "3. Bilingual causality guard and evidence-to-source execution-receipt checks",
            "4. Deterministic test/quality HTML-SVG interfaces and this four-page PDF",
        ]
    ):
        content += _text(60, 240 - offset * 28, item, 9)
    content += _text(46, 105, "Repository operation", 13, True)
    content += _text(60, 80, "All changes were written directly to main; no branch and no pull request were created.", 9)
    return content


def _status_ratio(value: Any) -> tuple[float, str]:
    text = str(value)
    folded = text.upper()
    if folded in {"NOT_RUN", "NOT RUN", "PENDING", "UNKNOWN"}:
        return 0.55, "NOT RUN"
    if folded == "PASS" or folded.endswith(" PASS") or "/" in folded:
        return 1.0, text
    return 0.15, text


def _page_two(evidence: dict[str, Any]) -> str:
    content = _text(46, 790, "Scoped software validation matrix", 22, True)
    platforms = evidence.get("compatibility", {})
    gates = evidence.get("gates", {})
    content += _text(46, 760, "Recorded cross-platform baseline", 14, True)
    content += _text(46, 742, "These platform results are the last complete baseline, not a fresh current-tree run.", 8)
    y = 710
    for label, value in sorted(platforms.items()):
        content += _text(56, y, label.replace("_", " "), 9)
        ratio, shown = _status_ratio(value)
        content += _bar(330, y - 7, 150, ratio)
        content += _text(492, y, shown, 9, True)
        y -= 26
    content += _text(46, y - 5, "Baseline and focused current-change gates", 14, True)
    y -= 37
    for label, value in gates.items():
        if y < 95:
            break
        content += _text(56, y, label.replace("_", " ")[:39], 8)
        ratio, shown = _status_ratio(value)
        shade = 0.55 if shown == "NOT RUN" else 0.30
        content += _bar(330, y - 7, 150, ratio, shade)
        content += _text(492, y, shown[:16], 8, True)
        y -= 22
    content += _text(46, 68, "Composite PASS means the declared scopes passed; current end-to-end CI remains NOT RUN.", 9, True)
    return content


def _guard_card(x: float, y: float, row: dict[str, Any]) -> str:
    result = row["result"]
    score = int(result.get("details", {}).get("completeness_score", 0))
    content = _rect(x, y, 245, 275, 0.98)
    content += _text(x + 16, y + 242, row["title"][:34], 13, True)
    content += _text(x + 188, y + 242, result["status"], 11, True)
    content += _text(x + 16, y + 218, f"Declared completeness: {score}%", 9)
    content += _bar(x + 16, y + 198, 210, score / 100)
    summary_text, _ = _wrapped(
        x + 16, y + 173, row["summary"], width=43, size=8, leading=12, max_lines=2
    )
    content += summary_text
    finding_y = y + 133
    for finding in result["findings"][:3]:
        finding_text, finding_y = _wrapped(
            x + 20,
            finding_y,
            f"{finding['code']}: {finding['message']}",
            width=48,
            size=7,
            leading=11,
            max_lines=2,
        )
        content += finding_text
        finding_y -= 8
    content += _text(x + 16, y + 22, f"Kind: {result['kind']}", 7)
    return content


def _page_three(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    content = _text(46, 790, "Scientific quality controls", 22, True)
    statuses = summary.get("statuses", {})
    content += _text(
        46,
        762,
        "Four deterministic contracts: measurement, multiscale reasoning, causal claims and evidence provenance.",
        9,
    )
    content += _text(
        46,
        738,
        f"Examples: PASS {statuses.get('PASS', 0)} | WARN {statuses.get('WARN', 0)} | BLOCK {statuses.get('BLOCK', 0)} | average completeness {summary.get('average_completeness', 0)}%",
        9,
        True,
    )
    positions = [(46, 430), (304, 430), (46, 135), (304, 135)]
    for position, row in zip(positions, rows[:4], strict=True):
        content += _guard_card(position[0], position[1], row)
    content += _text(46, 82, "BLOCK is intentional when wording exceeds evidence or an execution claim lacks a receipt.", 8)
    content += _text(46, 62, "The guards remain configurable and do not hard-code material-specific trends.", 8)
    return content


def _page_four(evidence: dict[str, Any]) -> str:
    content = _text(46, 790, "Closed-loop evidence and limitations", 22, True)
    baseline = evidence.get("baseline_full_repository_run", {})
    focused = evidence.get("focused_current_change_regression", {})
    gates = evidence.get("gates", {})
    content += _rect(46, 650, 500, 92, 0.98)
    content += _text(64, 712, "Recorded full-repository baseline", 14, True)
    content += _text(64, 687, f"GitHub Actions run: {baseline.get('run_id', 'not recorded')}", 9)
    content += _text(64, 668, "All engineering/scientific gates passed before publication transport failed.", 8)
    content += _rect(46, 525, 500, 92, 0.98)
    content += _text(64, 587, "Focused current-change regression", 14, True)
    content += _text(
        64,
        562,
        f"Tests: {focused.get('passed', 0)} passed / {focused.get('failed', 0)} failed | {focused.get('environment', 'environment not recorded')[:53]}",
        8,
    )
    content += _text(64, 543, "Scope: scientific quality, report generators and visual data contract.", 8)
    content += _rect(46, 400, 500, 92, 0.98)
    content += _text(64, 462, "Current-tree end-to-end CI", 14, True)
    content += _text(64, 437, f"Status: {gates.get('current_end_to_end_ci', 'not recorded')}", 10, True)
    content += _text(64, 418, "No current source-tree digest or fresh cross-platform receipt is asserted.", 8)
    content += _text(46, 352, "Explicit limitations", 14, True)
    y = 325
    limitations = evidence.get("limitations", [])
    if isinstance(limitations, list):
        for index, item in enumerate(limitations[:4], 1):
            wrapped, y = _wrapped(
                60, y, f"{index}. {str(item)}", width=82, size=8, leading=12, max_lines=2
            )
            content += wrapped
            y -= 10
    content += _text(46, 155, "Reproduction entry points", 14, True)
    command_y = 128
    for command in [
        "python -m pytest -q tests/test_scientific_quality.py tests/test_visual_report_contract.py",
        "python scripts/build_test_dashboard.py --check",
        "python scripts/build_research_quality_dashboard.py --check",
        "python scripts/build_engineering_report.py --check",
    ]:
        wrapped, command_y = _wrapped(60, command_y, command, width=88, size=7, leading=10, max_lines=2)
        content += wrapped
        command_y -= 6
    content += _text(46, 42, "Software validation is not acceptance of experiments, external calculations, legal or safety claims.", 8, True)
    return content


def _pdf(pages: list[str]) -> bytes:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{5 + index * 2} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    for index, stream in enumerate(pages):
        page_object = 5 + index * 2
        content_object = page_object + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_object} 0 R >>".encode()
        )
        payload = stream.encode("ascii", errors="strict")
        objects.append(f"<< /Length {len(payload)} >>\nstream\n".encode() + payload + b"endstream")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def build() -> bytes:
    evidence = _load_object(EVIDENCE)
    quality = _load_object(QUALITY)
    rows = quality.get("guards")
    summary = quality.get("summary")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("scientific-quality examples must contain guard objects")
    if not isinstance(summary, dict):
        raise ValueError("scientific-quality examples must contain a summary object")
    guard_rows = [dict(row) for row in rows]
    return _pdf(
        [
            _page_one(evidence),
            _page_two(evidence),
            _page_three(guard_rows, summary),
            _page_four(evidence),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.write:
        OUTPUT.write_bytes(expected)
        print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(expected)} bytes)")
        return
    if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
        raise SystemExit("engineering audit PDF is stale")
    if expected.count(b"/Type /Page ") != 4:
        raise SystemExit("engineering audit PDF page count is invalid")
    print("engineering audit PDF PASS")


if __name__ == "__main__":
    main()
