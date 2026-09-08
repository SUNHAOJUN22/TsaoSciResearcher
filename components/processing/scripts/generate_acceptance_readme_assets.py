#!/usr/bin/env python3
from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/readme"
W, H = 1200, 720
BG = "#07111F"
SURFACE = "#101E33"
TEXT = "#F8FAFC"
MUTED = "#A8B5C7"
BLUE = "#4F7CFF"
CYAN = "#22D3EE"
GREEN = "#34D399"
AMBER = "#FBBF24"
PURPLE = "#A78BFA"
RED = "#FB7185"


def _start(title: str, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc" focusable="false" preserveAspectRatio="xMidYMid meet" shape-rendering="geometricPrecision" text-rendering="optimizeLegibility" data-design-system="scientific-midnight-bento" data-design-version="2">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        '<style>text{font-family:Inter,"Segoe UI",Arial,sans-serif}.mono{font-family:"JetBrains Mono",Consolas,monospace}</style>',
    ]


def _text(
    x: int,
    y: int,
    value: str,
    *,
    size: int = 16,
    color: str = TEXT,
    weight: int = 600,
    anchor: str = "start",
    mono: bool = False,
) -> str:
    klass = ' class="mono"' if mono else ""
    return f'<text{klass} x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>'


def _card(
    x: int, y: int, w: int, h: int, title: str, lines: tuple[str, ...], color: str
) -> list[str]:
    body = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{SURFACE}" stroke="{color}" stroke-width="2"/>',
        _text(x + 22, y + 34, title, size=15, color=color, weight=800, mono=True),
    ]
    for index, line in enumerate(lines):
        body.append(_text(x + 22, y + 66 + 23 * index, line, size=13, color=MUTED, weight=500))
    return body


def _finish(parts: list[str], footer: str) -> str:
    parts.extend(
        [
            f'<rect x="52" y="650" width="1096" height="42" rx="12" fill="{SURFACE}" stroke="#263A55"/>',
            _text(76, 677, footer, size=12, color=AMBER, weight=700, mono=True),
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def render_canonical_publication_pipeline() -> str:
    p = _start(
        "EPDM canonical publication pipeline",
        "Transactional strict JSON to immutable registry publication.",
    )
    p += [
        _text(52, 72, "EPDM CANONICAL PUBLICATION", size=30, weight=850),
        _text(
            52,
            108,
            "No partial typed state is published before every contract closes",
            size=15,
            color=MUTED,
        ),
    ]
    stages = [
        (52, "STRICT JSON", ("duplicate keys rejected", "finite values only"), BLUE),
        (278, "VERSION", ("explicit migration", "2.0.0 -> 2.0.0"), PURPLE),
        (504, "SCHEMA", ("Draft 2020-12", "unknown fields closed"), CYAN),
        (730, "DATACLASSES", ("frozen objects", "typed IDs and units"), AMBER),
        (956, "REGISTRY", ("cross-reference closure", "stable SHA256"), GREEN),
    ]
    for x, title, lines, color in stages:
        p += _card(x, 200, 192, 150, title, lines, color)
    for x in (244, 470, 696, 922):
        p.append(f'<path d="M{x} 275 H{x + 28}" stroke="{MUTED}" stroke-width="3"/>')
    p += _card(
        255,
        430,
        690,
        130,
        "IMMUTABLE PUBLICATION",
        (
            "source_sha256 / registry_content_sha256 / publication_sha256",
            "failure at any stage exposes no partial registry",
        ),
        GREEN,
    )
    return _finish(p, "STRUCTURAL PASS DOES NOT OVERRIDE SCIENTIFIC OR HSE APPROVAL")


def render_governed_math_stack() -> str:
    p = _start(
        "Governed mathematical stack",
        "Balances, kinetics, thermodynamics, numerics and inference with explicit Gates.",
    )
    p += [
        _text(52, 72, "GOVERNED MATHEMATICAL STACK", size=30, weight=850),
        _text(52, 108, "Equation + units + domain + evidence + Gate", size=15, color=MUTED),
    ]
    rows = [
        (52, 175, "BALANCES", "dN/dt = Fin - Fout + nu^T r", BLUE),
        (52, 315, "KINETICS", "k(T) = A exp(-E/RT)", CYAN),
        (52, 455, "CHAIN MOMENTS", "dmu_k/dt = generation - loss", GREEN),
        (626, 175, "THERMODYNAMICS", "Gmix/RT = entropy + chi phi1 phi2", PURPLE),
        (626, 315, "NUMERICS", "err = norm((y5-y4)/scale)", AMBER),
        (626, 455, "INFERENCE", "J(theta) = sum w_i residual_i^2", GREEN),
    ]
    for x, y, title, equation, color in rows:
        p += _card(x, y, 522, 105, title, (equation, "fail-closed applicability contract"), color)
    return _finish(p, "NON-IDENTIFIABLE OR OUT-OF-DOMAIN RESULTS RETURN HOLD")


def render_acceptance_readiness_map() -> str:
    p = _start(
        "Software acceptance readiness map",
        "Separation of verified software evidence from external approvals.",
    )
    p += [
        _text(52, 72, "SOFTWARE ACCEPTANCE READINESS", size=30, weight=850),
        _text(
            52,
            108,
            "Software delivery can pass while external approval remains NOT_EVALUATED",
            size=15,
            color=MUTED,
        ),
    ]
    p += _card(
        52, 190, 300, 120, "SOURCE IDENTITY", ("manifest / overlay", "SHA256 / byte count"), BLUE
    )
    p += _card(
        52,
        350,
        300,
        120,
        "SOFTWARE GATES",
        ("tests / coverage / Ruff", "Doctor / Wheel / CI"),
        CYAN,
    )
    p += _card(
        848,
        190,
        300,
        120,
        "SCIENTIFIC",
        ("parameters / evidence", "applicability / uncertainty"),
        PURPLE,
    )
    p += _card(
        848,
        350,
        300,
        120,
        "ENGINEERING / HSE",
        ("equipment / relief", "HAZOP / LOPA / authority"),
        RED,
    )
    p += [
        f'<rect x="430" y="210" width="340" height="260" rx="28" fill="{SURFACE}" stroke="{GREEN}" stroke-width="3"/>',
        _text(
            600,
            275,
            "SOFTWARE DELIVERY",
            size=17,
            color=GREEN,
            weight=850,
            anchor="middle",
            mono=True,
        ),
        _text(600, 350, "PASS", size=56, color=GREEN, weight=900, anchor="middle"),
        _text(
            600,
            405,
            "EXTERNAL: NOT_EVALUATED",
            size=16,
            color=AMBER,
            weight=800,
            anchor="middle",
            mono=True,
        ),
    ]
    return _finish(p, "GREEN CI QUALIFIES SOFTWARE - NOT PLANT OR CUSTOMER PERFORMANCE")


ASSETS = {
    "epdm-canonical-publication-pipeline.svg": render_canonical_publication_pipeline,
    "governed-math-stack.svg": render_governed_math_stack,
    "acceptance-readiness-map.svg": render_acceptance_readiness_map,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, renderer in ASSETS.items():
        (OUT / name).write_text(renderer(), encoding="utf-8", newline="\n")
    print(f"generated {len(ASSETS)} acceptance README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
