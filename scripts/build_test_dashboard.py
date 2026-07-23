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
    platform_passes = sum(row["state"] == "PASS" for row in platforms)
    gate_passes = sum(row["state"] == "PASS" for row in gate_rows)
    gate_not_run = sum(row["state"] == "NOT_RUN" for row in gate_rows)
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
            "platform_passes": platform_passes,
            "platform_total": len(platforms),
            "gate_passes": gate_passes,
            "gate_not_run": gate_not_run,
            "gate_total": len(gate_rows),
            "mutation": str(
                gates.get("baseline_critical_mutation_killed", gates.get("critical_mutation_killed", "unknown"))
            ),
        },
    }


def _render_svg(payload: dict[str, Any]) -> str:
    esc = html.escape
    platforms = payload["platforms"]
    gates = payload["gates"]
    summary = payload["summary"]
    inventory = payload["inventory"]
    width = 1200
    gate_columns = 2
    rows_per_column = max(1, math.ceil(len(gates) / gate_columns))
    height = max(820, 475 + rows_per_column * 42)
    platform_x = [70, 335, 600, 865]
    state_style = {
        "PASS": ("#eaf8ef", "#247a48"),
        "NOT_RUN": ("#fff7dd", "#9a6700"),
        "FAIL": ("#fdecec", "#b42318"),
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">TsaoSciResearcher automated test dashboard</title>',
        '<desc id="desc">Scoped software evidence with baseline, focused-regression and not-run states.</desc>',
        "<style>",
        "text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#152033}",
        ".muted{fill:#5f6b7a}.small{font-size:14px}.label{font-size:17px;font-weight:600}",
        ".value{font-size:32px;font-weight:700}.title{font-size:30px;font-weight:700}",
        ".panel{fill:#fff;stroke:#d8e0ea;stroke-width:1.5}.track{fill:#e7edf3}",
        "</style>",
        f'<rect width="{width}" height="{height}" rx="24" fill="#f6f8fb"/>',
        '<text x="70" y="62" class="title">Automated test dashboard</text>',
        f'<text x="70" y="91" class="muted small">Release {esc(payload["release"])} · '
        f'{esc(payload["validation_scope"])} evidence · {esc(payload["evidence_date"])} · '
        f'run {esc(str(payload["run_id"] or "n/a"))}</text>',
        '<rect x="950" y="40" width="180" height="54" rx="27" fill="#eff6ff" stroke="#8ab4e8"/>',
        f'<text x="1040" y="75" text-anchor="middle" class="label">{esc(payload["status"])}</text>',
    ]
    cards = [
        ("Platform baseline", f"{summary['platform_passes']}/{summary['platform_total']}", "recorded passes"),
        ("Quality gates", f"{summary['gate_passes']}/{summary['gate_total']}", "scoped passes"),
        ("Not run", str(summary["gate_not_run"]), "explicitly disclosed"),
        ("Test modules", str(inventory["test_modules"]), "repository modules"),
    ]
    for x, (label, value, note) in zip(platform_x, cards, strict=True):
        parts.extend(
            [
                f'<rect x="{x}" y="125" width="235" height="128" rx="18" class="panel"/>',
                f'<text x="{x + 22}" y="160" class="muted small">{esc(label)}</text>',
                f'<text x="{x + 22}" y="207" class="value">{esc(value)}</text>',
                f'<text x="{x + 22}" y="232" class="muted small">{esc(note)}</text>',
            ]
        )
    parts.append('<text x="70" y="302" class="label">Recorded platform baseline</text>')
    for index, row in enumerate(platforms):
        x = platform_x[index]
        bg, fg = state_style[row["state"]]
        parts.extend(
            [
                f'<rect x="{x}" y="322" width="235" height="46" rx="13" fill="{bg}" stroke="{fg}"/>',
                f'<circle cx="{x + 23}" cy="345" r="7" fill="{fg}"/>',
                f'<text x="{x + 40}" y="351" class="small">{esc(row["label"])}</text>',
            ]
        )
    parts.append('<text x="70" y="407" class="label">Scoped validation gates</text>')
    split = rows_per_column
    for col, rows in enumerate((gates[:split], gates[split:])):
        x = 70 + col * 550
        for row_index, row in enumerate(rows):
            y = 442 + row_index * 42
            bg, fg = state_style[row["state"]]
            parts.extend(
                [
                    f'<text x="{x}" y="{y}" class="small">{esc(row["label"][:43])}</text>',
                    f'<rect x="{x + 310}" y="{y - 16}" width="140" height="10" rx="5" class="track"/>',
                    f'<rect x="{x + 310}" y="{y - 16}" width="140" height="10" rx="5" fill="{fg}"/>',
                    f'<rect x="{x + 458}" y="{y - 25}" width="78" height="27" rx="13" fill="{bg}" stroke="{fg}"/>',
                    f'<text x="{x + 497}" y="{y - 7}" text-anchor="middle" class="small" fill="{fg}">'
                    f'{esc(row["status"][:12])}</text>',
                ]
            )
    footer_y = height - 42
    parts.extend(
        [
            f'<rect x="70" y="{footer_y - 28}" width="1060" height="1" fill="#d8e0ea"/>',
            f'<text x="70" y="{footer_y}" class="muted small">Inventory: {inventory["capabilities"]} '
            f'capability contracts · {inventory["named_capabilities"]} named contracts · '
            f'{inventory["workflows"]} workflows · {inventory["schemas"]} schemas · '
            f'{inventory["domain_packs"]} domain packs · {inventory["generic_placeholders"]} placeholders</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def _render_html(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TsaoSciResearcher test dashboard</title>
  <style>
    :root {{ color-scheme:light dark; --bg:#f5f7fb; --panel:#fff; --text:#172033; --muted:#647084; --border:#d8e0ea; --pass:#247a48; --pending:#9a6700; --fail:#b42318; }}
    @media (prefers-color-scheme:dark) {{ :root {{ --bg:#111827; --panel:#172033; --text:#f3f6fb; --muted:#a9b4c4; --border:#334155; --pass:#79d29b; --pending:#f2cc60; --fail:#ff8b82; }} }}
    * {{ box-sizing:border-box; }} body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:var(--bg); color:var(--text); }}
    main {{ max-width:1160px; margin:auto; padding:32px 20px 48px; }} header {{ display:flex; justify-content:space-between; gap:20px; flex-wrap:wrap; }}
    h1 {{ margin:0 0 8px; }} p, footer {{ color:var(--muted); }} .badge {{ padding:10px 18px; border:1px solid var(--border); border-radius:999px; font-weight:700; }}
    .metrics,.inventory {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:24px 0; }}
    .metric,.inventory div,section {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:18px; }}
    .metric strong,.inventory strong {{ display:block; font-size:1.8rem; }} .metric span,.inventory span {{ color:var(--muted); }}
    .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin:16px 0; }} button {{ font:inherit; padding:9px 13px; border-radius:10px; border:1px solid var(--border); background:var(--panel); color:var(--text); cursor:pointer; }}
    button[aria-pressed="true"] {{ font-weight:700; text-decoration:underline; }} section {{ margin-top:16px; }} .list {{ display:grid; gap:10px; }}
    .row {{ display:grid; grid-template-columns:minmax(230px,1fr) 120px; gap:14px; align-items:center; border-bottom:1px solid var(--border); padding:10px 0; }}
    .status {{ text-align:center; font-weight:700; border:1px solid currentColor; border-radius:999px; padding:5px 8px; }} .PASS {{ color:var(--pass); }} .NOT_RUN {{ color:var(--pending); }} .FAIL {{ color:var(--fail); }}
    .notice {{ border-left:5px solid var(--pending); }} li {{ margin:.5rem 0; }} [hidden] {{ display:none!important; }}
  </style>
</head>
<body><main>
<header><div><h1 data-en="Automated test dashboard" data-zh="自动测试仪表板">Automated test dashboard</h1><p id="subtitle"></p></div><div class="badge" id="overall"></div></header>
<div class="metrics" id="metrics"></div>
<div class="controls"><button data-view="all" aria-pressed="true">All</button><button data-view="platforms" aria-pressed="false">Platforms</button><button data-view="gates" aria-pressed="false">Quality gates</button><button id="language">中文</button></div>
<section id="scope" class="notice"><h2>Evidence scope</h2><p id="scope-text"></p></section>
<section id="platforms"><h2>Recorded platform baseline</h2><div class="list" id="platform-list"></div></section>
<section id="gates"><h2>Scoped validation gates</h2><div class="list" id="gate-list"></div></section>
<section><h2>Verified inventory</h2><div class="inventory" id="inventory-list"></div></section>
<section id="limitations"><h2>Limitations</h2><ul id="limitation-list"></ul></section>
<footer>Recorded software evidence; not scientific acceptance or an external execution receipt.</footer>
</main><script>
const data={encoded}; let zh=false;
const t={{en:{{release:'Release',date:'Evidence',run:'Run',scope:'Scope',platforms:'Platform baseline',gates:'Quality gates',notrun:'Not run',tests:'Test modules'}},zh:{{release:'版本',date:'证据日期',run:'运行',scope:'范围',platforms:'平台基线',gates:'质量门禁',notrun:'未运行',tests:'测试模块'}}}};
function makeRow(item){{const node=document.createElement('div');node.className='row';node.innerHTML=`<span>${{item.label}}</span><span class="status ${{item.state}}">${{item.status}}</span>`;return node;}}
function render(){{const x=t[zh?'zh':'en'];document.documentElement.lang=zh?'zh-CN':'en';document.querySelector('h1').textContent=zh?document.querySelector('h1').dataset.zh:document.querySelector('h1').dataset.en;document.getElementById('subtitle').textContent=`${{x.release}} ${{data.release}} · ${{x.date}} ${{data.evidence_date}} · ${{x.run}} ${{data.run_id??'n/a'}}`;document.getElementById('overall').textContent=`${{data.status}} · ${{data.validation_scope}}`;document.getElementById('scope-text').textContent=zh?'基线完整门禁与当前改动聚焦回归分开记录；未运行项目不会显示为通过。':'Full baseline gates and focused current-change regression are recorded separately; unexecuted gates are not shown as passing.';const metrics=[[x.platforms,`${{data.summary.platform_passes}}/${{data.summary.platform_total}}`],[x.gates,`${{data.summary.gate_passes}}/${{data.summary.gate_total}}`],[x.notrun,String(data.summary.gate_not_run)],[x.tests,String(data.inventory.test_modules)]];document.getElementById('metrics').innerHTML=metrics.map(([k,v])=>`<div class="metric"><span>${{k}}</span><strong>${{v}}</strong></div>`).join('');document.getElementById('platform-list').replaceChildren(...data.platforms.map(makeRow));document.getElementById('gate-list').replaceChildren(...data.gates.map(makeRow));const inv=document.getElementById('inventory-list');inv.innerHTML='';Object.entries(data.inventory).forEach(([k,v])=>{{const box=document.createElement('div');box.innerHTML=`<strong>${{v}}</strong><span>${{k.replaceAll('_',' ')}}</span>`;inv.appendChild(box);}});document.getElementById('limitation-list').innerHTML=data.limitations.map(item=>`<li>${{item}}</li>`).join('');document.getElementById('language').textContent=zh?'English':'中文';}}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{{document.querySelectorAll('[data-view]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));const view=button.dataset.view;document.getElementById('platforms').hidden=view==='gates';document.getElementById('gates').hidden=view==='platforms';}});document.getElementById('language').onclick=()=>{{zh=!zh;render();}};render();
</script></body></html>"""


def build() -> dict[Path, str]:
    payload = _payload(_load_evidence())
    return {HTML_PATH: _render_html(payload), SVG_PATH: _render_svg(payload)}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.write:
        for path, content in expected.items():
            _write(path, content)
            print(f"wrote {path.relative_to(ROOT)}")
        return
    errors: list[str] = []
    for path, content in expected.items():
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing or unsafe dashboard asset: {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8", errors="strict") != content:
            errors.append(f"stale dashboard asset: {path.relative_to(ROOT)}")
    if errors:
        raise SystemExit("test dashboard check failed:\n- " + "\n- ".join(errors))
    print("test dashboard HTML and SVG PASS")


if __name__ == "__main__":
    main()
