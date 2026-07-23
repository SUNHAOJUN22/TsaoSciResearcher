#!/usr/bin/env python3
"""Generate deterministic scientific-quality HTML, SVG and JSON demonstrations."""

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
                    "replication": "three independently prepared specimens",
                    "data_reduction": "declared baseline and integration limits",
                    "detection_limit": "method-specific reporting threshold",
                    "traceability": "raw thermogram and analysis record",
                },
            },
        },
        {
            "title": "Structure-property planner",
            "summary": "The chain records intervention, structure, mediator, response and competing explanations.",
            "payload": {
                "kind": "structure-property-plan",
                "spec": {
                    "processing_or_intervention": "controlled cooling protocol",
                    "structure": "reduced long period",
                    "mediator": "higher interfacial density",
                    "property": "charge transport response",
                    "evidence": ["SAXS", "PEA"],
                    "alternative_explanations": ["crystallinity", "thermal history"],
                    "confounders": ["specimen thickness", "electrode contact"],
                    "testable_prediction": "interfacial metrics should covary with charge response",
                    "validation_strategy": "independent morphology and electrical measurements",
                    "uncertainty": "replicate dispersion and model sensitivity",
                    "applicability": "tested material family and cooling window",
                    "scale_bridge": "lamellar organization to mesoscopic interfaces",
                    "statistical_basis": "replicate distributions, not single-point values",
                    "conservation_constraints": ["mass balance", "dimensionally consistent units"],
                },
            },
        },
        {
            "title": "Causality guard",
            "summary": "Association-only evidence blocks causal wording in English and Chinese.",
            "payload": {
                "kind": "causality-guard",
                "spec": {
                    "claim": "The morphology causes the breakdown improvement.",
                    "design": "cross-sectional observational comparison",
                    "temporal_order": True,
                    "confounders_addressed": False,
                    "intervention_or_natural_experiment": False,
                    "comparison_or_control": True,
                    "replication": True,
                    "mechanism_tested": False,
                    "uncertainty_reported": True,
                },
            },
        },
        {
            "title": "Evidence traceability",
            "summary": "Claims link to evidence locators and execution claims require receipts.",
            "payload": {
                "kind": "evidence-traceability",
                "spec": {
                    "claim_id": "CLM-001",
                    "claim": "The recorded workflow completed successfully.",
                    "evidence_ids": ["EVD-001", "RUN-001"],
                    "source_locators": ["paper.pdf#page=4", "actions/run/123"],
                    "evidence_roles": ["direct", "execution-receipt"],
                    "execution_claim": True,
                    "execution_receipts": ["actions/run/123"],
                    "uncertainty": "Software completion does not imply scientific acceptance.",
                },
            },
        },
    ]
    for row in rows:
        row["result"] = evaluate_quality(row["payload"])
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = {
        name: sum(row["result"]["status"] == name for row in rows)
        for name in ("PASS", "WARN", "BLOCK")
    }
    scores = [int(row["result"]["details"].get("completeness_score", 0)) for row in rows]
    return {
        "guard_count": len(rows),
        "statuses": statuses,
        "average_completeness": round(sum(scores) / len(scores)) if scores else 0,
        "truth_boundary": "Software guards constrain claims; they do not grant scientific acceptance.",
    }


def _data(rows: list[dict[str, Any]]) -> str:
    payload = {"schema_version": "1.1", "summary": _summary(rows), "guards": rows}
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _svg(rows: list[dict[str, Any]]) -> str:
    esc = html.escape
    status_colors = {
        "PASS": ("#eaf8ef", "#247a48"),
        "WARN": ("#fff7dd", "#9a6700"),
        "BLOCK": ("#fdecec", "#b42318"),
    }
    summary = _summary(rows)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900" role="img" aria-labelledby="title desc">',
        '<title id="title">TsaoSciResearcher scientific quality dashboard</title>',
        '<desc id="desc">Measurement boundary, structure-property planning, causality and evidence traceability examples.</desc>',
        '<rect width="1200" height="900" rx="24" fill="#f5f7fb"/>',
        '<style>text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#172033}.title{font-size:30px;font-weight:700}.h{font-size:21px;font-weight:700}.metric{font-size:27px;font-weight:700}.small{font-size:15px}.tiny{font-size:13px}.muted{fill:#647084}.panel{fill:#fff;stroke:#d8e0ea;stroke-width:1.5}</style>',
        '<text x="60" y="58" class="title">Scientific quality guard dashboard</text>',
        '<text x="60" y="87" class="small muted">Executable boundaries for evidence, measurement, multiscale reasoning and causal claims</text>',
        '<rect x="60" y="112" width="250" height="72" rx="16" class="panel"/>',
        f'<text x="82" y="145" class="metric">{summary["guard_count"]}</text>',
        '<text x="82" y="170" class="tiny muted">guard contracts</text>',
        '<rect x="330" y="112" width="250" height="72" rx="16" class="panel"/>',
        f'<text x="352" y="145" class="metric">{summary["statuses"]["PASS"]}</text>',
        '<text x="352" y="170" class="tiny muted">passing demonstrations</text>',
        '<rect x="600" y="112" width="250" height="72" rx="16" class="panel"/>',
        f'<text x="622" y="145" class="metric">{summary["statuses"]["BLOCK"]}</text>',
        '<text x="622" y="170" class="tiny muted">intentional blocked overclaims</text>',
        '<rect x="870" y="112" width="270" height="72" rx="16" class="panel"/>',
        f'<text x="892" y="145" class="metric">{summary["average_completeness"]}%</text>',
        '<text x="892" y="170" class="tiny muted">average declared completeness</text>',
    ]
    card_positions = [(60, 215), (610, 215), (60, 525), (610, 525)]
    for (x, y), row in zip(card_positions, rows, strict=True):
        result = row["result"]
        status = result["status"]
        bg, fg = status_colors[status]
        score = int(result["details"].get("completeness_score", 0))
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="530" height="275" rx="20" class="panel"/>',
                f'<rect x="{x + 22}" y="{y + 22}" width="100" height="38" rx="19" fill="{bg}" stroke="{fg}"/>',
                f'<text x="{x + 72}" y="{y + 47}" text-anchor="middle" class="small" fill="{fg}">{status}</text>',
                f'<text x="{x + 505}" y="{y + 47}" text-anchor="end" class="small muted">{score}% complete</text>',
                f'<text x="{x + 22}" y="{y + 92}" class="h">{esc(row["title"])}</text>',
                f'<text x="{x + 22}" y="{y + 121}" class="small muted">{esc(row["summary"][:66])}</text>',
            ]
        )
        finding_y = y + 162
        for finding in result["findings"][:3]:
            finding_color = status_colors[finding["status"]][1]
            parts.extend(
                [
                    f'<circle cx="{x + 30}" cy="{finding_y - 5}" r="6" fill="{finding_color}"/>',
                    f'<text x="{x + 48}" y="{finding_y}" class="small">{esc(finding["code"])}</text>',
                    f'<text x="{x + 170}" y="{finding_y}" class="tiny muted">{esc(finding["message"][:50])}</text>',
                ]
            )
            finding_y += 31
    parts.extend(
        [
            '<text x="60" y="854" class="small muted">Truth boundary: software guard results are bounded checks, not scientific acceptance or an execution receipt.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def _html(rows: list[dict[str, Any]]) -> str:
    payload = {"summary": _summary(rows), "guards": rows}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TsaoSciResearcher scientific quality dashboard</title>
<style>
:root{{--bg:#f5f7fb;--panel:#fff;--text:#172033;--muted:#647084;--border:#d8e0ea;--pass:#247a48;--warn:#9a6700;--block:#b42318}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111827;--panel:#172033;--text:#f3f6fb;--muted:#a9b4c4;--border:#334155}}}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}}main{{max-width:1180px;margin:auto;padding:32px 20px 48px}}h1{{margin:0}}p{{color:var(--muted)}}.metrics,.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-top:24px}}.metric,article{{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:20px}}.metric strong{{display:block;font-size:2rem}}.badge{{display:inline-block;border:1px solid currentColor;border-radius:999px;padding:7px 12px;font-weight:700}}.PASS{{color:var(--pass)}}.WARN{{color:var(--warn)}}.BLOCK{{color:var(--block)}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0 6px}}button{{font:inherit;padding:9px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel);color:var(--text);cursor:pointer}}button[aria-pressed="true"]{{font-weight:700;text-decoration:underline}}pre{{white-space:pre-wrap;overflow:auto;background:color-mix(in srgb,var(--bg) 70%,transparent);padding:12px;border-radius:12px}}li{{margin:.65rem 0}}footer{{margin-top:24px;color:var(--muted)}}
</style></head><body><main><h1>Scientific quality guard dashboard</h1><p>Executable controls turn research-method rules into deterministic, inspectable checks.</p><div class="metrics" id="metrics"></div><div class="controls"><button data-filter="ALL" aria-pressed="true">All</button><button data-filter="PASS" aria-pressed="false">PASS</button><button data-filter="WARN" aria-pressed="false">WARN</button><button data-filter="BLOCK" aria-pressed="false">BLOCK</button></div><div class="grid" id="grid"></div><footer>These guards constrain unsupported wording and incomplete boundaries; they do not replace qualified scientific review.</footer></main>
<script>const data={encoded};const metrics=document.getElementById('metrics'),grid=document.getElementById('grid');for(const [label,value] of [['Guards',data.summary.guard_count],['PASS',data.summary.statuses.PASS],['BLOCK',data.summary.statuses.BLOCK],['Average completeness',data.summary.average_completeness+'%']]){{const d=document.createElement('div');d.className='metric';d.innerHTML=`<strong>${{value}}</strong><span>${{label}}</span>`;metrics.appendChild(d)}}function render(filter){{grid.textContent='';for(const row of data.guards){{const r=row.result;if(filter!=='ALL'&&r.status!==filter)continue;const a=document.createElement('article');a.dataset.status=r.status;a.innerHTML=`<span class="badge ${{r.status}}">${{r.status}}</span><h2>${{row.title}}</h2><p>${{row.summary}}</p><p><strong>${{r.details.completeness_score??0}}%</strong> declared completeness</p><ul>${{r.findings.map(f=>`<li><strong>${{f.code}}</strong>: ${{f.message}}</li>`).join('')}}</ul><button class="machine">Show machine result</button><pre hidden>${{JSON.stringify(r,null,2)}}</pre>`;const b=a.querySelector('.machine'),p=a.querySelector('pre');b.onclick=()=>{{p.hidden=!p.hidden;b.textContent=p.hidden?'Show machine result':'Hide machine result'}};grid.appendChild(a)}}}}for(const button of document.querySelectorAll('[data-filter]')){{button.onclick=()=>{{for(const item of document.querySelectorAll('[data-filter]'))item.setAttribute('aria-pressed','false');button.setAttribute('aria-pressed','true');render(button.dataset.filter)}}}}render('ALL');</script></body></html>'''


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
