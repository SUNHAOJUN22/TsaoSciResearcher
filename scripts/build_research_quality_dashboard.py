#!/usr/bin/env python3
"""Generate deterministic scientific-quality HTML and SVG demonstrations."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tsao_researcher.scientific_quality import evaluate_quality

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "docs/research-quality-dashboard.html"
SVG_PATH = ROOT / "docs/research-quality-dashboard.svg"
DATA_PATH = ROOT / "docs/SCIENTIFIC_QUALITY_EXAMPLES.json"


def _examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "title": "Measurement boundary",
            "summary": "Operational definition, calibration, uncertainty and applicability are explicit.",
            "payload": {
                "kind": "measurement-boundary",
                "spec": {
                    "measurand": "crystallinity",
                    "method": "DSC first-heating enthalpy",
                    "sample": "conditioned polymer specimen",
                    "conditions": ["10 K/min", "nitrogen"],
                    "unit": "%",
                    "calibration_or_reference": "indium calibration and declared reference enthalpy",
                    "uncertainty": "repeatability and reference-enthalpy contribution",
                    "applicability": "same thermal history and baseline protocol",
                    "exclusions": "not a direct phase-fraction measurement",
                },
            },
        },
        {
            "title": "Structure-property planner",
            "summary": "The reasoning chain cannot skip the measurable mediator.",
            "payload": {
                "kind": "structure-property-plan",
                "spec": {
                    "structure": "reduced long period",
                    "mediator": "higher interfacial density",
                    "property": "charge transport response",
                    "evidence": ["SAXS", "PEA"],
                    "alternative_explanations": ["crystallinity", "thermal history"],
                    "testable_prediction": "interfacial metrics should covary with charge response",
                },
            },
        },
        {
            "title": "Causality guard",
            "summary": "Association-only evidence blocks causal wording.",
            "payload": {
                "kind": "causality-guard",
                "spec": {
                    "claim": "The morphology causes the breakdown improvement.",
                    "design": "cross-sectional observational comparison",
                    "temporal_order": True,
                    "confounders_addressed": False,
                    "intervention_or_natural_experiment": False,
                    "mechanism_tested": False,
                    "uncertainty_reported": True,
                },
            },
        },
    ]
    for row in rows:
        row["result"] = evaluate_quality(row["payload"])
    return rows


def _data(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _svg(rows: list[dict[str, Any]]) -> str:
    esc = html.escape
    status_colors = {
        "PASS": ("#eaf8ef", "#247a48"),
        "WARN": ("#fff7dd", "#9a6700"),
        "BLOCK": ("#fdecec", "#b42318"),
    }
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" role="img">',
        '<rect width="1200" height="720" rx="24" fill="#f5f7fb"/>',
        '<style>text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#172033}.title{font-size:30px;font-weight:700}.h{font-size:21px;font-weight:700}.small{font-size:15px}.muted{fill:#647084}.panel{fill:#fff;stroke:#d8e0ea;stroke-width:1.5}</style>',
        '<text x="60" y="60" class="title">Scientific quality guard dashboard</text>',
        '<text x="60" y="90" class="small muted">Deterministic examples: measurement boundary · structure-property chain · causality guard</text>',
    ]
    x_values = [60, 405, 750]
    for x, row in zip(x_values, rows, strict=True):
        status = row["result"]["status"]
        bg, fg = status_colors[status]
        parts.extend(
            [
                f'<rect x="{x}" y="130" width="305" height="500" rx="20" class="panel"/>',
                f'<rect x="{x + 20}" y="155" width="100" height="38" rx="19" fill="{bg}" stroke="{fg}"/>',
                f'<text x="{x + 70}" y="180" text-anchor="middle" class="small" fill="{fg}">{status}</text>',
                f'<text x="{x + 20}" y="230" class="h">{esc(row["title"])}</text>',
                f'<text x="{x + 20}" y="266" class="small muted">{esc(row["summary"][:42])}</text>',
            ]
        )
        y = 320
        for finding in row["result"]["findings"]:
            parts.extend(
                [
                    f'<circle cx="{x + 28}" cy="{y - 5}" r="6" fill="{status_colors[finding["status"]][1]}"/>',
                    f'<text x="{x + 44}" y="{y}" class="small">{esc(finding["code"])}</text>',
                    f'<text x="{x + 44}" y="{y + 24}" class="small muted">{esc(finding["message"][:34])}</text>',
                ]
            )
            y += 72
        if row["payload"]["kind"] == "structure-property-plan":
            chain = row["result"]["details"]["chain"]
            y = 535
            for index, item in enumerate(chain):
                parts.append(
                    f'<text x="{x + 20}" y="{y + index * 28}" class="small">{index + 1}. {esc(item)}</text>'
                )
    parts.extend(
        [
            '<text x="60" y="680" class="small muted">Software guard results are bounded checks, not scientific acceptance.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def _html(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TsaoSciResearcher scientific quality dashboard</title>
<style>
:root{{--bg:#f5f7fb;--panel:#fff;--text:#172033;--muted:#647084;--border:#d8e0ea;--pass:#247a48;--warn:#9a6700;--block:#b42318}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111827;--panel:#172033;--text:#f3f6fb;--muted:#a9b4c4;--border:#334155}}}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}}main{{max-width:1180px;margin:auto;padding:32px 20px}}h1{{margin:0}}p{{color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:24px}}article{{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:20px}}.badge{{display:inline-block;border:1px solid currentColor;border-radius:999px;padding:7px 12px;font-weight:700}}.PASS{{color:var(--pass)}}.WARN{{color:var(--warn)}}.BLOCK{{color:var(--block)}}button{{font:inherit;padding:9px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel);color:var(--text);cursor:pointer}}pre{{white-space:pre-wrap;overflow:auto;background:color-mix(in srgb,var(--bg) 70%,transparent);padding:12px;border-radius:12px}}li{{margin:.65rem 0}}footer{{margin-top:24px;color:var(--muted)}}
</style></head><body><main><h1>Scientific quality guard dashboard</h1><p>Three deterministic controls turn research-method rules into executable checks.</p><div class="grid" id="grid"></div><footer>These guards prevent unsupported wording and incomplete boundaries; they do not replace qualified scientific review.</footer></main>
<script>const rows={encoded};const grid=document.getElementById('grid');for(const row of rows){{const a=document.createElement('article');const r=row.result;a.innerHTML=`<span class="badge ${{r.status}}">${{r.status}}</span><h2>${{row.title}}</h2><p>${{row.summary}}</p><ul>${{r.findings.map(f=>`<li><strong>${{f.code}}</strong>: ${{f.message}}</li>`).join('')}}</ul><button>Show machine result</button><pre hidden>${{JSON.stringify(r,null,2)}}</pre>`;const b=a.querySelector('button'),p=a.querySelector('pre');b.onclick=()=>{{p.hidden=!p.hidden;b.textContent=p.hidden?'Show machine result':'Hide machine result'}};grid.appendChild(a)}};</script></body></html>'''


def build() -> dict[Path, str]:
    rows = _examples()
    return {DATA_PATH: _data(rows), HTML_PATH: _html(rows), SVG_PATH: _svg(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.write:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(ROOT)}")
        return
    stale = [
        path.relative_to(ROOT).as_posix()
        for path, content in outputs.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
    if stale:
        raise SystemExit(f"scientific quality dashboard is stale: {stale}")
    print("scientific quality dashboard PASS")


if __name__ == "__main__":
    main()
