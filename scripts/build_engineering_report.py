#!/usr/bin/env python3
"""Build a deterministic visual PDF engineering audit report without third-party PDF libraries."""

from __future__ import annotations

import argparse
import json
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


def _rect(
    x: float,
    y: float,
    width: float,
    height: float,
    shade: float = 0.95,
    stroke: float = 0.75,
) -> str:
    return f"q {shade:.3f} g {stroke:.3f} G {x:.1f} {y:.1f} {width:.1f} {height:.1f} re B Q\n"


def _bar(x: float, y: float, width: float, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    return (
        f"q 0.92 g {x:.1f} {y:.1f} {width:.1f} 10 re f Q\n"
        f"q 0.30 g {x:.1f} {y:.1f} {width * ratio:.1f} 10 re f Q\n"
    )


def _page_one(evidence: dict[str, Any]) -> str:
    inventory = evidence.get("verified_inventory", {})
    content = _text(46, 790, "TsaoSciResearcher Engineering Audit", 24, True)
    content += _text(
        46,
        765,
        f"Release {evidence.get('release', 'unknown')} | evidence {evidence.get('evidence_date', 'unknown')}",
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
    content += _text(46, 270, "Audit focus", 15, True)
    for offset, item in enumerate(
        [
            "1. Current-main traceability and non-self-referential validation evidence",
            "2. Cross-platform CI, regression, security, mutation and reproducible release",
            "3. Executable measurement-boundary, structure-property and causality guards",
            "4. Deterministic HTML/SVG dashboards and a reproducible PDF report",
        ]
    ):
        content += _text(60, 240 - offset * 28, item, 10)
    return content


def _page_two(evidence: dict[str, Any]) -> str:
    content = _text(46, 790, "Software validation matrix", 22, True)
    platforms = evidence.get("compatibility", {})
    gates = evidence.get("gates", {})
    content += _text(46, 760, "Recorded compatibility", 14, True)
    y = 728
    for label, value in sorted(platforms.items()):
        content += _text(56, y, label.replace("_", " "), 10)
        content += _bar(330, y - 7, 180, 1.0 if value == "PASS" else 0.2)
        content += _text(520, y, str(value), 10, True)
        y -= 28
    content += _text(46, y - 8, "Quality and reproducibility gates", 14, True)
    y -= 42
    for label, value in sorted(gates.items()):
        content += _text(56, y, label.replace("_", " ")[:38], 9)
        passed = value == "PASS" or (isinstance(value, str) and "/" in value)
        content += _bar(330, y - 7, 180, 1.0 if passed else 0.2)
        content += _text(520, y, str(value), 9, True)
        y -= 24
    content += _text(
        46,
        75,
        "Interpretation: software PASS does not grant scientific acceptance.",
        10,
        True,
    )
    return content


def _page_three(rows: list[dict[str, Any]]) -> str:
    content = _text(46, 790, "Scientific quality controls", 22, True)
    y = 710
    for row in rows:
        result = row["result"]
        content += _rect(46, y - 145, 500, 135, 0.98)
        content += _text(64, y - 38, row["title"], 15, True)
        content += _text(430, y - 38, result["status"], 13, True)
        content += _text(64, y - 62, row["summary"][:78], 9)
        finding_y = y - 88
        for finding in result["findings"][:3]:
            content += _text(
                74,
                finding_y,
                f"{finding['code']}: {finding['message'][:66]}",
                8,
            )
            finding_y -= 19
        y -= 170
    content += _text(46, 126, "Guard behavior", 14, True)
    content += _text(60, 100, "PASS: declared boundary or inference level is internally complete.", 9)
    content += _text(60, 80, "WARN: the output remains usable but an uncertainty or alternative is missing.", 9)
    content += _text(60, 60, "BLOCK: the claim exceeds the method, boundary or study design.", 9)
    return content


def _page_four(evidence: dict[str, Any]) -> str:
    content = _text(46, 790, "Closed-loop delivery summary", 22, True)
    items = [
        "No new branch: all publication is targeted to main.",
        "README commands are tied to checked scripts and CI markers.",
        "Dashboards are deterministic generated artifacts, not manually edited screenshots.",
        "The PDF is regenerated from machine-readable validation and guard examples.",
        "Validation evidence records a source-tree digest rather than claiming self-validation.",
        "External simulations and laboratory work remain delegated and require execution receipts.",
    ]
    y = 720
    for index, item in enumerate(items, 1):
        content += _rect(46, y - 50, 500, 46, 0.985)
        content += _text(62, y - 24, f"{index}. {item}", 10)
        y -= 66
    content += _text(46, 280, "Recorded baseline", 14, True)
    provenance = evidence.get("provenance", {})
    content += _text(
        60,
        250,
        f"Validated tree digest: {str(provenance.get('validated_tree_sha256', 'not recorded'))[:64]}",
        8,
    )
    content += _text(
        60,
        228,
        f"Publication parent: {provenance.get('publication_parent_commit', 'not recorded')}",
        8,
    )
    content += _text(
        60,
        206,
        f"Workflow run: {provenance.get('workflow_run_id', 'not recorded')}",
        8,
    )
    content += _text(46, 140, "Final boundary", 14, True)
    content += _text(
        60,
        112,
        "This report demonstrates repository engineering controls. It does not certify external",
        10,
    )
    content += _text(
        60,
        92,
        "scientific calculations, experiments, legal conclusions, medical claims or safety decisions.",
        10,
    )
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
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("scientific-quality examples must contain guard objects")
    guard_rows = [dict(row) for row in rows]
    return _pdf(
        [
            _page_one(evidence),
            _page_two(evidence),
            _page_three(guard_rows),
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
