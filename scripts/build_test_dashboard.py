#!/usr/bin/env python3
"""Generate deterministic HTML and SVG dashboards from scoped validation evidence."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "docs/VALIDATION_EVIDENCE.json"
HTML_PATH = ROOT / "docs/test-dashboard.html"
SVG_PATH = ROOT / "docs/test-dashboard.svg"

PLATFORM_LABELS = {
    "ubuntu_python_3_10": "Ubuntu / Python 3.10",
    "ubuntu_python_3_13": "Ubuntu / Python 3.13",
    "windows_python_3_12": "Windows / Python 3.12",
    "macos_python_3_12": "macOS / Python 3.12",
}
GATE_LABELS = {
    "baseline_repository_and_contract_audit": "Baseline repository and contract audit",
    "baseline_complete_regression": "Baseline complete regression",
    "baseline_reverse_order_regression": "Baseline reverse-order regression",
    "baseline_seeded_random_order_regression": "Baseline seeded-random regression",
    "baseline_ruff_format_and_lint": "Baseline Ruff format and lint",
    "baseline_mypy_strict": "Baseline strict Mypy",
    "baseline_bandit_high_severity": "Baseline Bandit high-severity scan",
    "baseline_critical_mutation_killed": "Baseline critical mutation gate",
    "baseline_bounded_performance": "Baseline bounded performance",
    "baseline_byte_identical_release_builds": "Baseline byte-identical release",
    "scientific_quality_guard_regression": "Current scientific-quality guards",
    "deterministic_visual_report_contract": "Current visual-report contract",
    "readme_version_and_mirror_alignment": "README version and mirror alignment",
    "focused_current_change_regression": "Focused current-change regression",
    "current_end_to_end_ci": "Current-tree end-to-end CI",
}


def _load_evidence(path: Path = EVIDENCE_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError("validation evidence root must be an object")
    return value


def _state(status: str) -> str:
    folded = status.strip().upper()
    if folded in {"PASS", "PASSED"} or folded.endswith(" PASS") or "/" in folded:
        return "PASS"
    if folded in {"NOT_RUN", "NOT RUN", "PENDING", "UNKNOWN", "N/A"}:
        return "NOT_RUN"
    return "FAIL"


def _payload(evidence: dict[str, Any]) -> dict[str, Any]:
    compatibility = evidence.get("compatibility", {})
    gates = evidence.get("gates", {})
    inventory = evidence.get("verified_inventory", {})
    if not isinstance(compatibility, dict) or not isinstance(gates, dict) or not isinstance(inventory, dict):
        raise ValueError("validation evidence has invalid compatibility, gates, or inventory data")
    platforms = [
        {
            "id": key,
            "label": PLATFORM_LABELS.get(key, key.replace("_", " ").title()),
            "status": str(compatibility[key]),
            "state": _state(str(compatibility[key])),
        }
        for key in sorted(compatibility)
    ]
    gate_keys = [key for key in GATE_LABELS if key in gates]
    gate_keys.extend(sorted(set(gates) - set(GATE_LABELS)))
    gate_rows = [
        {
            "id": key,
            "label": GATE_LABELS.get(key, key.replace("_", " ").title()),
            "status": str(gates[key]),
            "state": _state(str(gates[key])),
        }
        for key in gate_keys
    ]
    limitations = evidence.get("limitations", [])
    return {
        "release": str(evidence.get("release", "unknown")),
        "status": str(evidence.get("status", "UNKNOWN")),
        "validation_scope": str(evidence.get("validation_scope", "unknown")),
        "evidence_date": str(evidence.get("evidence_date", "unknown")),
        "run_id": evidence.get("workflow", {}).get("run_id")
        if isinstance(evidence.get("workflow"), dict)
        else None,
        "platforms": platforms,
        "gates": gate_rows,
        "limitations": [str(item) for item in limitations] if isinstance(limitations, list) else [],
        "inventory": {
            "capabilities": int(inventory.get("capability_records", 0)),
            "named_capabilities": int(inventory.get("workbook_named_capabilities", 0)),
            "workflows": int(inventory.get("workflows", 0)),
            "schemas": int(inventory.get("schemas", 0)),
            "test_modules": int(inventory.get("test_modules", 0)),
            "domain_packs": int(inventory.get("domain_packs", 0)),
            "generic_placeholders": int(inventory.get("generic_domain_placeholders", 0)),
        },
        "summary": {
            "platform_passes": sum(row["state"] == "PASS" for row in platforms),
            "platform_total": len(platforms),
            "gate_passes": sum(row["state"] == "PASS" for row in gate_rows),
            "gate_not_run": sum(row["state"] == "NOT_RUN" for row in gate_rows),
            "gate_total": len(gate_rows),
        },
    }


def _render_svg(payload: dict[str, Any]) -> str:
    esc = html.escape
    gates = payload["gates"]
    inventory = payload["inventory"]
    summary = payload["summary"]
    per_col = max(1, math.ceil(len(gates) / 2))
    height = max(820, 480 + per_col * 42)
    state_colors = {"PASS": "#247a48", "NOT_RUN": "#9a6700", "FAIL": "#b42318"}
    state_bg = {"PASS": "#eaf8ef", "NOT_RUN": "#fff7dd", "FAIL": "#fdecec"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">TsaoSciResearcher scoped test dashboard</title>',
        '<desc id="desc">Baseline, focused regression, and explicitly not-run validation states.</desc>',
        '<rect width="1200" height="100%" rx="24" fill="#f6f8fb"/>',
        "<style>text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#152033}.muted{fill:#5f6b7a}.small{font-size:14px}.label{font-size:17px;font-weight:600}.value{font-size:32px;font-weight:700}.title{font-size:30px;font-weight:700}.panel{fill:#fff;stroke:#d8e0ea;stroke-width:1.5}</style>",
        '<text x="70" y="62" class="title">Automated test dashboard</text>',
        f'<text x="70" y="91" class="muted small">Release {esc(payload["release"])} · {esc(payload["validation_scope"])} evidence · {esc(payload["evidence_date"])} · run {esc(str(payload["run_id"] or "n/a"))}</text>',
        '<rect x="950" y="40" width="180" height="54" rx="27" fill="#eff6ff" stroke="#8ab4e8"/>',
        f'<text x="1040" y="75" text-anchor="middle" class="label">{esc(payload["status"])}</text>',
    ]
    cards = [
        ("Platform baseline", f"{summary['platform_passes']}/{summary['platform_total']}", "recorded passes"),
        ("Quality gates", f"{summary['gate_passes']}/{summary['gate_total']}", "scoped passes"),
        ("Not run", str(summary["gate_not_run"]), "explicitly disclosed"),
        ("Test modules", str(inventory["test_modules"]), "repository modules"),
    ]
    for x, (label, value, note) in zip((70, 335, 600, 865), cards, strict=True):
        parts += [
            f'<rect x="{x}" y="125" width="235" height="128" rx="18" class="panel"/>',
            f'<text x="{x + 22}" y="160" class="muted small">{esc(label)}</text>',
            f'<text x="{x + 22}" y="207" class="value">{esc(value)}</text>',
            f'<text x="{x + 22}" y="232" class="muted small">{esc(note)}</text>',
        ]
    parts.append('<text x="70" y="302" class="label">Recorded platform baseline</text>')
    for x, row in zip((70, 335, 600, 865), payload["platforms"], strict=True):
        fg = state_colors[row["state"]]
        bg = state_bg[row["state"]]
        parts += [
            f'<rect x="{x}" y="322" width="235" height="46" rx="13" fill="{bg}" stroke="{fg}"/>',
            f'<circle cx="{x + 23}" cy="345" r="7" fill="{fg}"/>',
            f'<text x="{x + 40}" y="351" class="small">{esc(row["label"])}</text>',
        ]
    parts.append('<text x="70" y="407" class="label">Scoped validation gates</text>')
    for col, rows in enumerate((gates[:per_col], gates[per_col:])):
        x = 70 + col * 550
        for idx, row in enumerate(rows):
            y = 442 + idx * 42
            fg = state_colors[row["state"]]
            bg = state_bg[row["state"]]
            parts += [
                f'<text x="{x}" y="{y}" class="small">{esc(row["label"][:43])}</text>',
                f'<rect x="{x + 440}" y="{y - 25}" width="96" height="27" rx="13" fill="{bg}" stroke="{fg}"/>',
                f'<text x="{x + 488}" y="{y - 7}" text-anchor="middle" class="small" fill="{fg}">{esc(row["status"][:15])}</text>',
            ]
    footer_y = height - 42
    parts += [
        f'<rect x="70" y="{footer_y - 28}" width="1060" height="1" fill="#d8e0ea"/>',
        f'<text x="70" y="{footer_y}" class="muted small">Inventory: {inventory["capabilities"]} capability contracts · {inventory["named_capabilities"]} named contracts · {inventory["workflows"]} workflows · {inventory["schemas"]} schemas · {inventory["domain_packs"]} domain packs · {inventory["generic_placeholders"]} placeholders</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def _render_html(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TsaoSciResearcher test dashboard</title>
<style>:root{{--bg:#f5f7fb;--panel:#fff;--text:#172033;--muted:#647084;--border:#d8e0ea;--pass:#247a48;--pending:#9a6700;--fail:#b42318}}@media(prefers-color-scheme:dark){{:root{{--bg:#111827;--panel:#172033;--text:#f3f6fb;--muted:#a9b4c4;--border:#334155;--pass:#79d29b;--pending:#f2cc60;--fail:#ff8b82}}}}*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}}main{{max-width:1160px;margin:auto;padding:32px 20px 48px}}header{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}h1{{margin:0 0 8px}}p,footer{{color:var(--muted)}}.badge{{padding:10px 18px;border:1px solid var(--border);border-radius:999px;font-weight:700}}.metrics,.inventory{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:24px 0}}.metric,.inventory div,section{{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:18px}}.metric strong,.inventory strong{{display:block;font-size:1.8rem}}.metric span,.inventory span{{color:var(--muted)}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}}button{{font:inherit;padding:9px 13px;border-radius:10px;border:1px solid var(--border);background:var(--panel);color:var(--text);cursor:pointer}}button[aria-pressed="true"]{{font-weight:700;text-decoration:underline}}section{{margin-top:16px}}.list{{display:grid;gap:10px}}.row{{display:grid;grid-template-columns:minmax(230px,1fr) 130px;gap:14px;align-items:center;border-bottom:1px solid var(--border);padding:10px 0}}.status{{text-align:center;font-weight:700;border:1px solid currentColor;border-radius:999px;padding:5px 8px}}.PASS{{color:var(--pass)}}.NOT_RUN{{color:var(--pending)}}.FAIL{{color:var(--fail)}}.notice{{border-left:5px solid var(--pending)}}li{{margin:.5rem 0}}[hidden]{{display:none!important}}</style></head>
<body><main><header><div><h1>Automated test dashboard</h1><p id="subtitle"></p></div><div class="badge" id="overall"></div></header><div class="metrics" id="metrics"></div><div class="controls"><button data-view="all" aria-pressed="true">All</button><button data-view="platforms" aria-pressed="false">Platforms</button><button data-view="gates" aria-pressed="false">Quality gates</button></div><section class="notice"><h2>Evidence scope</h2><p>Full baseline gates and focused current-change regression are recorded separately; unexecuted gates are not shown as passing.</p></section><section id="platforms"><h2>Recorded platform baseline</h2><div class="list" id="platform-list"></div></section><section id="gates"><h2>Scoped validation gates</h2><div class="list" id="gate-list"></div></section><section><h2>Verified inventory</h2><div class="inventory" id="inventory-list"></div></section><section><h2>Limitations</h2><ul id="limitation-list"></ul></section><footer>Recorded software evidence; not scientific acceptance or an external execution receipt.</footer></main>
<script>const data={encoded};document.getElementById('subtitle').textContent=`Release ${{data.release}} · ${{data.validation_scope}} evidence · ${{data.evidence_date}} · run ${{data.run_id??'n/a'}}`;document.getElementById('overall').textContent=`${{data.status}} · ${{data.validation_scope}}`;const m=[['Platform baseline',`${{data.summary.platform_passes}}/${{data.summary.platform_total}}`],['Quality gates',`${{data.summary.gate_passes}}/${{data.summary.gate_total}}`],['Not run',String(data.summary.gate_not_run)],['Test modules',String(data.inventory.test_modules)]];document.getElementById('metrics').innerHTML=m.map(([k,v])=>`<div class="metric"><span>${{k}}</span><strong>${{v}}</strong></div>`).join('');function row(x){{const n=document.createElement('div');n.className='row';n.innerHTML=`<span>${{x.label}}</span><span class="status ${{x.state}}">${{x.status}}</span>`;return n}}document.getElementById('platform-list').replaceChildren(...data.platforms.map(row));document.getElementById('gate-list').replaceChildren(...data.gates.map(row));const inv=document.getElementById('inventory-list');Object.entries(data.inventory).forEach(([k,v])=>{{const b=document.createElement('div');b.innerHTML=`<strong>${{v}}</strong><span>${{k.replaceAll('_',' ')}}</span>`;inv.appendChild(b)}});document.getElementById('limitation-list').innerHTML=data.limitations.map(x=>`<li>${{x}}</li>`).join('');document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{{document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.getElementById('platforms').hidden=b.dataset.view==='gates';document.getElementById('gates').hidden=b.dataset.view==='platforms'}});</script></body></html>"""


def build() -> dict[Path, str]:
    payload = _payload(_load_evidence())
    return {HTML_PATH: _render_html(payload), SVG_PATH: _render_svg(payload)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.write:
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(ROOT)}")
        return
    stale = [
        path.relative_to(ROOT).as_posix()
        for path, content in expected.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
    if stale:
        raise SystemExit(f"test dashboard is stale: {stale}")
    print("test dashboard HTML and SVG PASS")


if __name__ == "__main__":
    main()
