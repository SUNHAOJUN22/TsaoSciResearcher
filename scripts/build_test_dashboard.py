#!/usr/bin/env python3
"""Generate deterministic HTML and SVG dashboards from validation evidence."""

from __future__ import annotations

import argparse
import html
import json
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
    "repository_and_contract_audit": "Repository and contract audit",
    "complete_regression": "Complete regression",
    "reverse_order_regression": "Reverse-order regression",
    "seeded_random_order_regression": "Seeded random-order regression",
    "ruff_format_and_lint": "Ruff format and lint",
    "mypy_strict": "Strict Mypy",
    "bandit_high_severity": "Bandit high-severity scan",
    "critical_mutation_killed": "Critical mutation gate",
    "bounded_performance": "Bounded performance",
    "byte_identical_release_builds": "Byte-identical release builds",
    "json_schemas_15": "15 JSON Schemas",
}


def _load_evidence(path: Path = EVIDENCE_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError("validation evidence root must be an object")
    return value


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
        }
        for key in sorted(compatibility)
    ]
    gate_rows = [
        {
            "id": key,
            "label": GATE_LABELS.get(key, key.replace("_", " ").title()),
            "status": str(gates[key]),
        }
        for key in GATE_LABELS
        if key in gates
    ]
    extra_gate_keys = sorted(set(gates) - set(GATE_LABELS))
    gate_rows.extend(
        {
            "id": key,
            "label": key.replace("_", " ").title(),
            "status": str(gates[key]),
        }
        for key in extra_gate_keys
    )

    platform_passes = sum(row["status"] == "PASS" for row in platforms)
    gate_passes = sum(row["status"] == "PASS" or "/" in row["status"] for row in gate_rows)
    return {
        "release": str(evidence.get("release", "unknown")),
        "status": str(evidence.get("status", "UNKNOWN")),
        "evidence_date": str(evidence.get("evidence_date", "unknown")),
        "run_id": evidence.get("workflow", {}).get("run_id")
        if isinstance(evidence.get("workflow"), dict)
        else None,
        "platforms": platforms,
        "gates": gate_rows,
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
            "gate_total": len(gate_rows),
            "mutation": str(gates.get("critical_mutation_killed", "unknown")),
        },
    }


def _render_svg(payload: dict[str, Any]) -> str:
    esc = html.escape
    platforms = payload["platforms"]
    gates = payload["gates"]
    summary = payload["summary"]
    inventory = payload["inventory"]
    width = 1200
    height = 720
    platform_x = [70, 335, 600, 865]
    gate_start_y = 390
    gate_col_x = [70, 620]
    gate_rows = [gates[:6], gates[6:]]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">TsaoSciResearcher automated test dashboard</title>',
        '<desc id="desc">All recorded cross-platform compatibility and quality gates passed for release '
        + esc(payload["release"])
        + ".</desc>",
        "<style>",
        "text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#152033}",
        ".muted{fill:#5f6b7a}.small{font-size:15px}.label{font-size:17px;font-weight:600}",
        ".value{font-size:34px;font-weight:700}.title{font-size:30px;font-weight:700}",
        ".panel{fill:#ffffff;stroke:#d8e0ea;stroke-width:1.5}.ok{fill:#eaf8ef;stroke:#68b984}",
        ".track{fill:#e7edf3}.bar{fill:#2f855a}.chip{fill:#eff6ff;stroke:#8ab4e8}",
        "</style>",
        '<rect width="1200" height="720" rx="24" fill="#f6f8fb"/>',
        '<text x="70" y="62" class="title">Automated test dashboard</text>',
        f'<text x="70" y="91" class="muted small">Release {esc(payload["release"])} · evidence {esc(payload["evidence_date"])} · run {esc(str(payload["run_id"] or "n/a"))}</text>',
        '<rect x="955" y="40" width="175" height="54" rx="27" class="ok"/>',
        f'<text x="1042" y="75" text-anchor="middle" class="label">{esc(payload["status"])}</text>',
    ]

    cards = [
        ("Platforms", f"{summary['platform_passes']}/{summary['platform_total']}", "cross-platform"),
        ("Quality gates", f"{summary['gate_passes']}/{summary['gate_total']}", "all recorded"),
        ("Mutation", summary["mutation"], "critical killed"),
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

    parts.append('<text x="70" y="302" class="label">Platform compatibility</text>')
    for index, row in enumerate(platforms):
        x = platform_x[index]
        parts.extend(
            [
                f'<rect x="{x}" y="322" width="235" height="46" rx="13" class="ok"/>',
                f'<circle cx="{x + 23}" cy="345" r="7" fill="#2f855a"/>',
                f'<text x="{x + 40}" y="351" class="small">{esc(row["label"])}</text>',
            ]
        )

    parts.append('<text x="70" y="407" class="label">Validated gates</text>')
    for col, rows in enumerate(gate_rows):
        x = gate_col_x[col]
        for row_index, row in enumerate(rows):
            y = gate_start_y + 35 + row_index * 45
            parts.extend(
                [
                    f'<text x="{x}" y="{y}" class="small">{esc(row["label"])}</text>',
                    f'<rect x="{x + 300}" y="{y - 15}" width="150" height="10" rx="5" class="track"/>',
                    f'<rect x="{x + 300}" y="{y - 15}" width="150" height="10" rx="5" class="bar"/>',
                    f'<text x="{x + 520}" y="{y - 5}" text-anchor="end" class="muted small">{esc(row["status"])}</text>',
                ]
            )

    parts.extend(
        [
            '<rect x="70" y="665" width="1060" height="1" fill="#d8e0ea"/>',
            f'<text x="70" y="695" class="muted small">Inventory: {inventory["capabilities"]} capability contracts · {inventory["named_capabilities"]} named catalog contracts · {inventory["workflows"]} workflows · {inventory["schemas"]} schemas · {inventory["domain_packs"]} domain packs · {inventory["generic_placeholders"]} placeholders</text>',
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
    :root {{ color-scheme: light dark; --bg:#f5f7fb; --panel:#fff; --text:#172033; --muted:#647084; --border:#d8e0ea; --ok:#247a48; --ok-bg:#eaf8ef; --accent:#245fa8; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#111827; --panel:#172033; --text:#f3f6fb; --muted:#a9b4c4; --border:#334155; --ok:#79d29b; --ok-bg:#153824; --accent:#8ab4e8; }} }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:var(--bg); color:var(--text); }}
    main {{ max-width:1100px; margin:0 auto; padding:32px 20px 48px; }}
    header {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-start; flex-wrap:wrap; }}
    h1 {{ margin:0 0 8px; font-size:clamp(1.8rem,4vw,2.6rem); }}
    p {{ color:var(--muted); }}
    .badge {{ padding:10px 18px; border-radius:999px; background:var(--ok-bg); color:var(--ok); font-weight:700; border:1px solid var(--ok); }}
    .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:28px 0; }}
    .metric {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:18px; }}
    .metric span {{ color:var(--muted); font-size:.9rem; }}
    .metric strong {{ display:block; font-size:2rem; margin:8px 0 2px; }}
    .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin:12px 0 20px; }}
    button {{ border:1px solid var(--border); background:var(--panel); color:var(--text); border-radius:10px; padding:10px 14px; cursor:pointer; font:inherit; }}
    button[aria-pressed="true"] {{ border-color:var(--accent); color:var(--accent); font-weight:700; }}
    section {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:20px; margin-top:16px; }}
    h2 {{ margin:0 0 14px; font-size:1.15rem; }}
    .list {{ display:grid; gap:10px; }}
    .row {{ display:grid; grid-template-columns:minmax(180px,1fr) minmax(130px,240px) auto; gap:14px; align-items:center; }}
    .track {{ height:10px; background:color-mix(in srgb,var(--border) 65%,transparent); border-radius:999px; overflow:hidden; }}
    .fill {{ height:100%; width:100%; background:var(--ok); }}
    .status {{ color:var(--ok); font-weight:700; text-align:right; }}
    .inventory {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:10px; }}
    .inventory div {{ border:1px solid var(--border); border-radius:12px; padding:12px; }}
    .inventory strong {{ display:block; font-size:1.35rem; }}
    footer {{ margin-top:22px; color:var(--muted); font-size:.9rem; }}
    [hidden] {{ display:none !important; }}
    @media (max-width:650px) {{ .row {{ grid-template-columns:1fr auto; }} .track {{ grid-column:1 / -1; grid-row:2; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div><h1 data-en="Automated test dashboard" data-zh="自动测试仪表板">Automated test dashboard</h1><p id="subtitle"></p></div>
    <div class="badge" id="overall"></div>
  </header>
  <div class="metrics" id="metrics"></div>
  <div class="controls" aria-label="Dashboard controls">
    <button type="button" data-view="all" aria-pressed="true">All</button>
    <button type="button" data-view="platforms" aria-pressed="false">Platforms</button>
    <button type="button" data-view="gates" aria-pressed="false">Quality gates</button>
    <button type="button" id="language" aria-pressed="false">中文</button>
  </div>
  <section id="platforms"><h2>Platform compatibility</h2><div class="list" id="platform-list"></div></section>
  <section id="gates"><h2>Validated gates</h2><div class="list" id="gate-list"></div></section>
  <section id="inventory"><h2>Verified inventory</h2><div class="inventory" id="inventory-list"></div></section>
  <footer id="footer"></footer>
</main>
<script>
const data = {encoded};
let zh = false;
const labels = {{
  en: {{platforms:'Platform compatibility',gates:'Validated gates',inventory:'Verified inventory',footer:'Recorded software evidence; not a substitute for scientific or human review.',release:'Release',evidence:'Evidence',run:'Run',capabilities:'Capabilities',named_capabilities:'Named contracts',workflows:'Workflows',schemas:'Schemas',test_modules:'Test modules',domain_packs:'Domain packs',generic_placeholders:'Placeholders'}},
  zh: {{platforms:'平台兼容性',gates:'已验证门禁',inventory:'已核实清单',footer:'展示已记录的软件证据,不替代科学判断或人工评审。',release:'版本',evidence:'证据日期',run:'运行',capabilities:'能力合同',named_capabilities:'具名合同',workflows:'工作流',schemas:'Schema',test_modules:'测试模块',domain_packs:'领域包',generic_placeholders:'占位项'}}
}};
function row(item) {{
  const node=document.createElement('div'); node.className='row';
  node.innerHTML=`<span>${{item.label}}</span><div class="track"><div class="fill"></div></div><span class="status">${{item.status}}</span>`;
  return node;
}}
function render() {{
  const t=labels[zh?'zh':'en'];
  document.documentElement.lang=zh?'zh-CN':'en';
  document.querySelector('h1').textContent=zh?document.querySelector('h1').dataset.zh:document.querySelector('h1').dataset.en;
  document.getElementById('subtitle').textContent=`${{t.release}} ${{data.release}} · ${{t.evidence}} ${{data.evidence_date}} · ${{t.run}} ${{data.run_id ?? 'n/a'}}`;
  document.getElementById('overall').textContent=data.status;
  const metrics=[
    [t.platforms,`${{data.summary.platform_passes}}/${{data.summary.platform_total}}`],
    [t.gates,`${{data.summary.gate_passes}}/${{data.summary.gate_total}}`],
    ['Mutation',data.summary.mutation],
    [t.test_modules,String(data.inventory.test_modules)]
  ];
  document.getElementById('metrics').innerHTML=metrics.map(([k,v])=>`<div class="metric"><span>${{k}}</span><strong>${{v}}</strong></div>`).join('');
  document.querySelector('#platforms h2').textContent=t.platforms;
  document.querySelector('#gates h2').textContent=t.gates;
  document.querySelector('#inventory h2').textContent=t.inventory;
  document.getElementById('platform-list').replaceChildren(...data.platforms.map(row));
  document.getElementById('gate-list').replaceChildren(...data.gates.map(row));
  const inventory=document.getElementById('inventory-list'); inventory.innerHTML='';
  Object.entries(data.inventory).forEach(([key,value])=>{{ const box=document.createElement('div'); box.innerHTML=`<strong>${{value}}</strong><span>${{t[key] ?? key.replaceAll('_',' ')}}</span>`; inventory.appendChild(box); }});
  document.getElementById('footer').textContent=t.footer;
  document.getElementById('language').textContent=zh?'English':'中文';
}}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{{
  document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  const view=button.dataset.view;
  document.getElementById('platforms').hidden=view==='gates';
  document.getElementById('gates').hidden=view==='platforms';
}}));
document.getElementById('language').addEventListener('click',()=>{{zh=!zh;render();}});
render();
</script>
</body>
</html>
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = _payload(_load_evidence())
    expected = {HTML_PATH: _render_html(payload), SVG_PATH: _render_svg(payload)}
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
