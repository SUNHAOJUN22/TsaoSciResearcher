#!/usr/bin/env python3
from __future__ import annotations

from html import escape
from itertools import pairwise
from pathlib import Path
from textwrap import wrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/readme"

W, H = 1200, 720

# TSAO README visual system: Scientific Midnight Bento
BG = "#07111F"
SURFACE = "#101E33"
SURFACE_2 = "#14243B"
BORDER = "#263A55"
TEXT = "#F8FAFC"
MUTED = "#A8B5C7"
DIM = "#6F8299"
BLUE = "#4F7CFF"
CYAN = "#22D3EE"
TEAL = "#2DD4BF"
GREEN = "#34D399"
AMBER = "#FBBF24"
ORANGE = "#FB923C"
RED = "#FB7185"
PURPLE = "#A78BFA"


def xesc(value: object) -> str:
    return escape(str(value), quote=True)


def svg_start(title: str, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{xesc(title)}</title>',
        f'<desc id="desc">{xesc(description)}</desc>',
        """
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#07111F"/>
    <stop offset="0.55" stop-color="#0B1729"/>
    <stop offset="1" stop-color="#07111F"/>
  </linearGradient>
  <radialGradient id="glowBlue" cx="0.1" cy="0.05" r="0.8">
    <stop offset="0" stop-color="#4F7CFF" stop-opacity="0.18"/>
    <stop offset="1" stop-color="#4F7CFF" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glowCyan" cx="0.9" cy="0.8" r="0.65">
    <stop offset="0" stop-color="#22D3EE" stop-opacity="0.12"/>
    <stop offset="1" stop-color="#22D3EE" stop-opacity="0"/>
  </radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#18304C" stroke-width="1" opacity="0.32"/>
  </pattern>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#020617" flood-opacity="0.45"/>
  </filter>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8.5" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,8 L9,4 z" fill="#6F8299"/>
  </marker>
  <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8.5" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,8 L9,4 z" fill="#4F7CFF"/>
  </marker>
  <style>
    .sans { font-family: Inter, "Segoe UI", Arial, sans-serif; }
    .mono { font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; }
  </style>
</defs>
""",
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#grid)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#glowBlue)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#glowCyan)"/>',
    ]


def finish(parts: list[str]) -> str:
    parts.append("</svg>\n")
    return "".join(parts)


def text(
    x: float,
    y: float,
    value: str,
    *,
    size: int = 16,
    fill: str = TEXT,
    weight: int = 500,
    anchor: str = "start",
    mono: bool = False,
    opacity: float = 1.0,
    letter: float = 0,
) -> str:
    cls = "mono" if mono else "sans"
    return (
        f'<text class="{cls}" x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" opacity="{opacity}" '
        f'letter-spacing="{letter}">{xesc(value)}</text>'
    )


def multiline(
    x: float,
    y: float,
    value: str,
    *,
    width_chars: int = 24,
    size: int = 15,
    fill: str = TEXT,
    weight: int = 500,
    anchor: str = "start",
    line_height: int | None = None,
    mono: bool = False,
) -> str:
    lines: list[str] = []
    for raw in value.split("\n"):
        lines.extend(
            wrap(raw, width=width_chars, break_long_words=False, break_on_hyphens=False) or [""]
        )
    height = line_height or int(size * 1.45)
    cls = "mono" if mono else "sans"
    spans = [
        f'<tspan x="{x}" dy="{0 if index == 0 else height}">{xesc(line_value)}</tspan>'
        for index, line_value in enumerate(lines)
    ]
    return (
        f'<text class="{cls}" x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">' + "".join(spans) + "</text>"
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str = SURFACE,
    stroke: str = BORDER,
    radius: int = 20,
    stroke_width: float = 1.2,
    opacity: float = 1.0,
    shadow: bool = False,
) -> str:
    filter_value = ' filter="url(#shadow)"' if shadow else ""
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
        f'opacity="{opacity}"{filter_value}/>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str = DIM,
    width: float = 2,
    dash: str | None = None,
    arrow: bool = False,
    blue_arrow: bool = False,
    opacity: float = 1.0,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    marker = ""
    if arrow:
        marker = ' marker-end="url(#arrowBlue)"' if blue_arrow else ' marker-end="url(#arrow)"'
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round" opacity="{opacity}"'
        f"{dash_attr}{marker}/>"
    ).replace('/>"', "/>")


def path(
    data: str,
    *,
    stroke: str = DIM,
    width: float = 2,
    fill: str = "none",
    arrow: bool = False,
    opacity: float = 1.0,
) -> str:
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    return (
        f'<path d="{data}" stroke="{stroke}" stroke-width="{width}" fill="{fill}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"{marker}/>'
    )


def circle(
    center_x: float,
    center_y: float,
    radius: float,
    *,
    fill: str = SURFACE_2,
    stroke: str = BORDER,
    width: float = 1.2,
) -> str:
    return (
        f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{width}"/>'
    )


def pill(
    x: float,
    y: float,
    label: str,
    color: str,
    *,
    width: float | None = None,
    height: float = 28,
    mono: bool = False,
) -> str:
    resolved_width = width or max(72, len(label) * (7.2 if mono else 7.8) + 28)
    return rect(
        x,
        y,
        resolved_width,
        height,
        fill=f"{color}18",
        stroke=f"{color}88",
        radius=int(height / 2),
        stroke_width=1,
    ) + text(
        x + resolved_width / 2,
        y + height / 2 + 5,
        label,
        size=12,
        fill=color,
        weight=700,
        anchor="middle",
        mono=mono,
        letter=0.2,
    )


def header(
    parts: list[str],
    title_value: str,
    subtitle: str,
    *,
    eyebrow: str = "TSAO PROCESS INTELLIGENCE OS",
    accent: str = BLUE,
) -> None:
    parts.extend(
        [
            pill(52, 38, eyebrow, accent, height=30, mono=True),
            text(52, 105, title_value, size=34, weight=800),
            text(52, 138, subtitle, size=15, fill=MUTED, weight=500),
            line(52, 164, 1148, 164, stroke=BORDER, width=1),
        ]
    )


def small_icon(parts: list[str], center_x: float, center_y: float, kind: str, color: str) -> None:
    parts.append(circle(center_x, center_y, 22, fill=f"{color}18", stroke=f"{color}AA", width=1.2))
    if kind == "flow":
        parts.extend(
            [
                circle(center_x - 8, center_y, 3.5, fill=color, stroke=color),
                circle(center_x + 8, center_y, 3.5, fill=color, stroke=color),
                line(
                    center_x - 4,
                    center_y,
                    center_x + 4,
                    center_y,
                    stroke=color,
                    width=2,
                    arrow=True,
                    blue_arrow=color == BLUE,
                ),
            ]
        )
    elif kind == "shield":
        parts.append(
            path(
                f"M {center_x} {center_y - 11} L {center_x + 10} {center_y - 7} "
                f"L {center_x + 8} {center_y + 5} Q {center_x} {center_y + 13} "
                f"{center_x - 8} {center_y + 5} L {center_x - 10} {center_y - 7} Z",
                stroke=color,
                width=2,
            )
        )
    elif kind == "cpu":
        parts.append(
            rect(
                center_x - 8,
                center_y - 8,
                16,
                16,
                fill="none",
                stroke=color,
                radius=3,
                stroke_width=2,
            )
        )
        for offset in (-10, 10):
            parts.append(
                line(
                    center_x + offset,
                    center_y - 5,
                    center_x + offset,
                    center_y + 5,
                    stroke=color,
                    width=1.6,
                )
            )
            parts.append(
                line(
                    center_x - 5,
                    center_y + offset,
                    center_x + 5,
                    center_y + offset,
                    stroke=color,
                    width=1.6,
                )
            )
    elif kind == "chart":
        parts.extend(
            [
                rect(center_x - 10, center_y + 2, 5, 8, fill=color, stroke=color, radius=1),
                rect(center_x - 2, center_y - 4, 5, 14, fill=color, stroke=color, radius=1),
                rect(center_x + 6, center_y - 10, 5, 20, fill=color, stroke=color, radius=1),
            ]
        )
    elif kind == "database":
        parts.extend(
            [
                f'<ellipse cx="{center_x}" cy="{center_y - 7}" rx="10" ry="4" fill="none" stroke="{color}" stroke-width="2"/>',
                path(
                    f"M {center_x - 10} {center_y - 7} V {center_y + 7} C {center_x - 10} {center_y + 12} "
                    f"{center_x + 10} {center_y + 12} {center_x + 10} {center_y + 7} V {center_y - 7}",
                    stroke=color,
                    width=2,
                ),
                path(
                    f"M {center_x - 10} {center_y} C {center_x - 10} {center_y + 5} "
                    f"{center_x + 10} {center_y + 5} {center_x + 10} {center_y}",
                    stroke=color,
                    width=1.5,
                ),
            ]
        )
    elif kind == "molecule":
        parts.extend(
            [
                circle(center_x - 9, center_y + 4, 3.5, fill=color, stroke=color),
                circle(center_x + 1, center_y - 7, 3.5, fill=color, stroke=color),
                circle(center_x + 10, center_y + 6, 3.5, fill=color, stroke=color),
                line(center_x - 6, center_y + 1, center_x - 2, center_y - 4, stroke=color, width=2),
                line(center_x + 4, center_y - 4, center_x + 7, center_y + 3, stroke=color, width=2),
            ]
        )
    else:
        parts.append(circle(center_x, center_y, 6, fill=color, stroke=color))


def node_card(
    parts: list[str],
    x: float,
    y: float,
    width: float,
    height: float,
    title_value: str,
    detail: str,
    color: str,
    *,
    icon: str = "flow",
    tag: str | None = None,
    title_size: int = 17,
) -> None:
    parts.append(
        rect(x, y, width, height, fill=SURFACE, stroke=f"{color}66", radius=20, shadow=True)
    )
    parts.append(rect(x, y, 5, height, fill=color, stroke=color, radius=3))
    small_icon(parts, x + 36, y + 38, icon, color)
    parts.append(text(x + 70, y + 43, title_value, size=title_size, weight=750))
    parts.append(
        multiline(
            x + 22,
            y + 82,
            detail,
            width_chars=max(16, int(width / 9.2)),
            size=13,
            fill=MUTED,
            line_height=20,
        )
    )
    if tag:
        parts.append(pill(x + 20, y + height - 40, tag, color, height=24, mono=True))


def footer_gate(parts: list[str], label: str = "SOFTWARE EVIDENCE ≠ ENGINEERING APPROVAL") -> None:
    parts.append(rect(52, 656, 1096, 38, fill="#0A1627", stroke=BORDER, radius=12))
    parts.append(text(76, 681, label, size=12, fill=MUTED, mono=True, weight=650, letter=0.6))
    parts.append(pill(1010, 661, "FAIL-CLOSED", AMBER, height=28, mono=True))


def render_platform() -> str:
    parts = svg_start(
        "TSAO Process Intelligence OS",
        "Four delivered Skills coordinated by a fail-closed process intelligence core.",
    )
    header(
        parts,
        "One operating system, four specialist Skills",
        "A single evidence, modeling, qualification and delivery contract for chemical-process work",
    )
    center_x, center_y = 600, 390
    parts.append(circle(center_x, center_y, 92, fill="#0D2038", stroke=BLUE, width=2))
    small_icon(parts, center_x, center_y - 22, "cpu", BLUE)
    parts.append(text(center_x, center_y + 20, "TSAO CORE", size=20, weight=800, anchor="middle"))
    parts.append(
        text(
            center_x,
            center_y + 44,
            "route · evidence · gates",
            size=12,
            fill=MUTED,
            anchor="middle",
            mono=True,
        )
    )
    cards = [
        (72, 215, "process-general", "14 modules\n6 workflows\nuniversal package", BLUE, "flow"),
        (72, 425, "polymer-general", "DoE · balance\nscale-up · evidence", TEAL, "chart"),
        (
            880,
            215,
            "EPDM flagship",
            "active sites · kinetics\nreactor · finishing",
            CYAN,
            "molecule",
        ),
        (880, 425, "POE specialist", "P0/P1 kernels\n139-asset lineage", PURPLE, "database"),
    ]
    for x, y, title_value, detail, color, icon in cards:
        node_card(
            parts,
            x,
            y,
            248,
            170,
            title_value,
            detail,
            color,
            icon=icon,
            tag="DELIVERED",
        )
        start_x = x + 248 if x < center_x else x
        end_x = center_x - 94 if x < center_x else center_x + 94
        start_y = y + 85
        parts.append(
            line(
                start_x,
                start_y,
                end_x,
                center_y + (start_y - center_y) * 0.25,
                stroke=DIM,
                width=2,
                arrow=x < center_x,
            )
        )
    parts.append(pill(500, 190, "TRACEABLE", GREEN, width=95))
    parts.append(pill(605, 190, "AUDITABLE", CYAN, width=95))
    parts.append(pill(710, 190, "OPERATIONAL", BLUE, width=108))
    footer_gate(parts)
    return finish(parts)


def render_linear(
    title_value: str,
    subtitle: str,
    stages: list[tuple[str, str, str, str]],
    *,
    footer: str,
    eyebrow: str = "DECISION FLOW",
) -> str:
    parts = svg_start(title_value, subtitle)
    header(parts, title_value, subtitle, eyebrow=eyebrow, accent=CYAN)
    count = len(stages)
    margin = 56
    gap = 18
    card_width = (W - 2 * margin - gap * (count - 1)) / count
    y, height = 228, 308
    for index, (stage_title, detail, color, icon) in enumerate(stages):
        x = margin + index * (card_width + gap)
        node_card(
            parts,
            x,
            y,
            card_width,
            height,
            stage_title,
            detail,
            color,
            icon=icon,
            tag=f"{index + 1:02d}",
        )
        if index < count - 1:
            parts.append(
                line(
                    x + card_width,
                    y + height / 2,
                    x + card_width + gap - 2,
                    y + height / 2,
                    stroke=DIM,
                    width=2,
                    arrow=True,
                )
            )
    footer_gate(parts, footer)
    return finish(parts)


def render_layers() -> str:
    parts = svg_start(
        "Layered process-package architecture",
        "A layered scientific and engineering architecture with explicit evidence and approval boundaries.",
    )
    header(
        parts,
        "Layered process-package architecture",
        "Every decision layer is supported by governed models, data and approvals",
        eyebrow="SYSTEM ARCHITECTURE",
    )
    layers = [
        (
            "Decision & acceptance",
            "targets · CQAs · trade-offs · Gate state · named approval",
            BLUE,
        ),
        (
            "Process & equipment",
            "streams · balances · reactors · separation · utilities · controls",
            CYAN,
        ),
        (
            "Models & computation",
            "kinetics · thermo · transport · estimation · uncertainty · simulation",
            PURPLE,
        ),
        (
            "Evidence & identity",
            "sources · assumptions · conflicts · manifests · provenance · audit trail",
            GREEN,
        ),
    ]
    y = 210
    widths = [1040, 980, 920, 860]
    for index, (layer_title, detail, color) in enumerate(layers):
        width = widths[index]
        x = (W - width) / 2
        height = 90
        parts.append(
            rect(x, y, width, height, fill=SURFACE, stroke=f"{color}77", radius=18, shadow=True)
        )
        parts.append(rect(x, y, 7, height, fill=color, stroke=color, radius=3))
        parts.append(text(x + 30, y + 38, layer_title, size=20, weight=780))
        parts.append(text(x + 30, y + 65, detail, size=13, fill=MUTED, mono=True))
        if index < len(layers) - 1:
            parts.append(
                line(600, y + height, 600, y + height + 25, stroke=DIM, width=2, arrow=True)
            )
        y += 110
    footer_gate(parts)
    return finish(parts)


def render_data_model() -> str:
    parts = svg_start(
        "Universal process-package data model",
        "Connected data entities for decisions, models, equipment, evidence and approvals.",
    )
    header(
        parts,
        "Connected process-package data model",
        "IDs and references turn narrative reports into an auditable engineering graph",
        eyebrow="CONNECTED DATA MODEL",
    )
    center_x, center_y = 600, 392
    parts.append(circle(center_x, center_y, 86, fill="#0E223B", stroke=BLUE, width=2))
    small_icon(parts, center_x, center_y - 26, "database", BLUE)
    parts.append(
        text(center_x, center_y + 18, "DESIGN BASIS", size=19, weight=800, anchor="middle")
    )
    parts.append(
        text(
            center_x,
            center_y + 42,
            "scope · units · limits",
            size=11,
            fill=MUTED,
            mono=True,
            anchor="middle",
        )
    )
    nodes = [
        (160, 232, "Streams", "components · flow · state", CYAN, "flow"),
        (160, 468, "Equipment", "duty · capacity · envelope", BLUE, "cpu"),
        (860, 232, "Models", "equations · parameters · domain", PURPLE, "chart"),
        (860, 468, "Controls & HSE", "alarms · trips · safeguards", RED, "shield"),
        (430, 205, "Evidence", "source · condition · uncertainty", GREEN, "database"),
        (650, 525, "Acceptance", "criterion · approver · status", AMBER, "shield"),
    ]
    for x, y, node_title, detail, color, icon in nodes:
        node_card(parts, x, y, 220, 118, node_title, detail, color, icon=icon)
        parts.append(
            line(
                center_x,
                center_y,
                x + 110,
                y + 59,
                stroke=f"{color}88",
                width=1.6,
                arrow=True,
            )
        )
    footer_gate(parts)
    return finish(parts)


def render_integration() -> str:
    parts = svg_start(
        "Simulator-neutral integration contract",
        "Governed inputs and qualified outputs around multiple simulation and automation tools.",
    )
    header(
        parts,
        "Simulator-neutral integration contract",
        "A simulator is a computation engine—not a substitute for design basis, evidence or approval",
        eyebrow="INTEROPERABILITY",
    )
    node_card(
        parts,
        52,
        230,
        250,
        310,
        "Governed inputs",
        "design basis\nstream & equipment IDs\nproperty-method basis\nparameter provenance\nmodel passport",
        BLUE,
        icon="database",
        tag="SOURCE OF TRUTH",
    )
    node_card(
        parts,
        898,
        230,
        250,
        310,
        "Qualified outputs",
        "balances & residuals\napplicability domain\nuncertainty & conflicts\nGate status\nnamed approval",
        GREEN,
        icon="shield",
        tag="DECISION READY",
    )
    tools = [
        (370, 215, "Aspen Plus", BLUE),
        (630, 215, "Aspen HYSYS", CYAN),
        (370, 350, "DWSIM", TEAL),
        (630, 350, "Python / custom", PURPLE),
        (500, 485, "DCS / PLC exchange", AMBER),
    ]
    for x, y, label, color in tools:
        parts.append(rect(x, y, 200, 86, fill=SURFACE, stroke=f"{color}66", radius=18, shadow=True))
        small_icon(parts, x + 38, y + 43, "cpu", color)
        parts.append(text(x + 70, y + 49, label, size=16, weight=750))
        parts.append(line(302, 385, x, y + 43, stroke=DIM, width=1.5, arrow=True))
        parts.append(line(x + 200, y + 43, 898, 385, stroke=DIM, width=1.5, arrow=True))
    footer_gate(parts, "SIMULATOR CONVERGENCE ≠ QUALIFICATION")
    return finish(parts)


def render_network() -> str:
    parts = svg_start(
        "EPDM catalyst-to-architecture network",
        "Reaction network linking active sites, monomers, transfer, deactivation and molecular architecture.",
    )
    header(
        parts,
        "EPDM catalyst → kinetics → architecture",
        "A compact network view of insertion, loss pathways and structure-forming consequences",
        eyebrow="EPDM FLAGSHIP",
    )
    center_x, center_y = 560, 365
    parts.append(circle(center_x, center_y, 74, fill="#0E223B", stroke=CYAN, width=2))
    small_icon(parts, center_x, center_y - 20, "molecule", CYAN)
    parts.append(text(center_x, center_y + 20, "ACTIVE SITE", size=18, weight=800, anchor="middle"))
    monomers = [
        (180, 240, "Ethylene", "E insertion", BLUE),
        (180, 365, "Propylene", "P insertion", TEAL),
        (180, 490, "Diene", "third-monomer topology", PURPLE),
    ]
    for x, y, label, detail, color in monomers:
        node_card(parts, x, y, 230, 92, label, detail, color, icon="molecule")
        parts.append(
            line(
                x + 230,
                y + 46,
                center_x - 75,
                center_y + (y + 46 - center_y) * 0.25,
                stroke=f"{color}AA",
                width=2,
                arrow=True,
                blue_arrow=color == BLUE,
            )
        )
    losses = [
        (790, 235, "Chain transfer", "MWD · chain birth", AMBER),
        (790, 365, "Deactivation", "site lifetime", RED),
        (790, 495, "Poison memory", "recycle impurity risk", ORANGE),
    ]
    for x, y, label, detail, color in losses:
        node_card(parts, x, y, 250, 92, label, detail, color, icon="shield")
        parts.append(
            line(
                center_x + 75,
                center_y + (y + 46 - center_y) * 0.25,
                x,
                y + 46,
                stroke=f"{color}99",
                width=2,
                arrow=True,
            )
        )
    parts.append(rect(430, 565, 340, 58, fill=f"{GREEN}14", stroke=f"{GREEN}77", radius=16))
    parts.append(
        text(
            600,
            592,
            "sequence · MWD/CCD · branching · gel risk",
            size=15,
            fill=GREEN,
            weight=750,
            anchor="middle",
        )
    )
    parts.append(line(center_x, center_y + 74, 600, 565, stroke=GREEN, width=2, arrow=True))
    footer_gate(parts)
    return finish(parts)


def render_reactor_map() -> str:
    parts = svg_start(
        "EPDM reactor-mode decision map",
        "Decision map for semibatch, continuous and multi-reactor EPDM process routes.",
    )
    header(
        parts,
        "EPDM reactor-mode decision map",
        "Choose the operating mode from control objective, heat removal, composition and grade-transition needs",
        eyebrow="REACTOR SYNTHESIS",
    )
    parts.append(rect(430, 195, 340, 78, fill=SURFACE_2, stroke=BLUE, radius=20, shadow=True))
    parts.append(
        text(600, 230, "What must the reactor preserve?", size=20, weight=800, anchor="middle")
    )
    parts.append(
        text(
            600,
            253,
            "composition · temperature · site state · residence history",
            size=12,
            fill=MUTED,
            anchor="middle",
            mono=True,
        )
    )
    branches = [
        (
            75,
            355,
            "Semibatch",
            "flexible feed policy\nstrong grade agility\nexplicit inventory history",
            CYAN,
            "screening / lab / specialty",
        ),
        (
            450,
            355,
            "Continuous",
            "steady throughput\nresidence distribution\nrecycle closure",
            BLUE,
            "industrial steady state",
        ),
        (
            825,
            355,
            "Multi-reactor",
            "sequence shaping\nsplit heat load\nbroader architecture control",
            PURPLE,
            "advanced product envelope",
        ),
    ]
    for x, y, label, detail, color, tag in branches:
        node_card(parts, x, y, 300, 220, label, detail, color, icon="flow", tag=tag.upper())
        parts.append(line(600, 273, x + 150, y, stroke=f"{color}88", width=2, arrow=True))
    footer_gate(parts, "MODE SELECTION REQUIRES HEAT, MIXING, PHASE AND OPERABILITY EVIDENCE")
    return finish(parts)


def render_flowsheet() -> str:
    stages = [
        ("Feed & catalyst", "E / P / diene\nsolvent · catalyst\npoison boundary", BLUE, "molecule"),
        ("Polymerization", "active sites\nheat removal\nmixing & residence", CYAN, "cpu"),
        ("Quench & deash", "kill chemistry\nmetal removal\nwash closure", TEAL, "shield"),
        ("Devolatilize", "solvent / monomer\nnon-equilibrium\nresidual target", PURPLE, "flow"),
        ("Recovery", "compression\ncondensation\npurification", GREEN, "database"),
        ("Product", "bale / pellet\nMooney · gel\ncustomer evidence", AMBER, "chart"),
    ]
    return render_linear(
        "EPDM process-package reference flowsheet",
        "Mechanism-aware polymerization connected to finishing, recovery and product evidence",
        stages,
        footer="RECYCLE, PURGE AND EMISSIONS MUST CLOSE",
        eyebrow="PROCESS FLOWSHEET",
    )


def render_recycle() -> str:
    parts = svg_start(
        "EPDM recovery, recycle and impurity-risk loop",
        "Closed recycle loop showing recovery, guard beds, poison memory and purge.",
    )
    header(
        parts,
        "Recovery, recycle and impurity-risk loop",
        "Recycle economics are valid only when impurities and catalyst poisons reach a finite steady state",
        eyebrow="RECYCLE CLOSURE",
    )
    center_x, center_y = 600, 390
    ring = [
        (600, 205, "Devolatilization", PURPLE, "flow"),
        (880, 310, "Recovery", GREEN, "database"),
        (800, 530, "Guard & purge", AMBER, "shield"),
        (400, 560, "Recycle header", CYAN, "flow"),
        (300, 310, "Reactor", BLUE, "molecule"),
    ]
    for x, y, label, color, icon in ring:
        parts.append(circle(x, y, 68, fill=SURFACE, stroke=f"{color}88", width=2))
        small_icon(parts, x, y - 13, icon, color)
        parts.append(text(x, y + 30, label, size=14, weight=750, anchor="middle"))
    rotated = ring[1:] + ring[:1]
    for source, destination in zip(ring, rotated, strict=True):
        x1, y1 = source[0], source[1]
        x2, y2 = destination[0], destination[1]
        parts.append(
            path(
                f"M {x1} {y1} Q {(x1 + x2) / 2} {(y1 + y2) / 2 - 20} {x2} {y2}",
                stroke=DIM,
                width=2,
                arrow=True,
            )
        )
    parts.append(circle(center_x, center_y, 92, fill="#0D2038", stroke=RED, width=2))
    small_icon(parts, center_x, center_y - 22, "shield", RED)
    parts.append(
        text(center_x, center_y + 15, "POISON MEMORY", size=18, weight=800, anchor="middle")
    )
    parts.append(
        text(
            center_x,
            center_y + 42,
            "accumulation · finite steady state",
            size=11,
            fill=MUTED,
            mono=True,
            anchor="middle",
        )
    )
    footer_gate(parts, "NO FINITE IMPURITY STEADY STATE → HOLD")
    return finish(parts)


def render_evidence() -> str:
    parts = svg_start(
        "Evidence and qualification gates",
        "Evidence-state ladder separating calculation, inference, proposal and approval.",
    )
    header(
        parts,
        "Evidence and qualification gates",
        "Claims advance only when their source, condition, uncertainty and accountable approval are explicit",
        eyebrow="EVIDENCE OPERATING MODEL",
    )
    states = [
        ("OBSERVED", "measured in project", GREEN),
        ("REPORTED", "external source", CYAN),
        ("CALCULATED", "transparent model", BLUE),
        ("INFERRED", "bounded interpretation", PURPLE),
        ("ASSUMED", "explicit placeholder", AMBER),
        ("PROPOSED", "future action", ORANGE),
        ("APPROVED", "named authority", GREEN),
    ]
    x0, y0 = 70, 235
    width, height, gap = 138, 230, 18
    for index, (state, detail, color) in enumerate(states):
        x = x0 + index * (width + gap)
        parts.append(
            rect(x, y0, width, height, fill=SURFACE, stroke=f"{color}77", radius=18, shadow=True)
        )
        parts.append(
            text(x + 18, y0 + 40, f"{index + 1:02d}", size=12, fill=color, mono=True, weight=700)
        )
        parts.append(text(x + 18, y0 + 80, state, size=16, fill=TEXT, mono=True, weight=800))
        parts.append(
            multiline(x + 18, y0 + 116, detail, width_chars=15, size=13, fill=MUTED, line_height=19)
        )
        if index < len(states) - 1:
            parts.append(
                line(
                    x + width,
                    y0 + height / 2,
                    x + width + gap - 2,
                    y0 + height / 2,
                    stroke=DIM,
                    width=1.7,
                    arrow=True,
                )
            )
    parts.append(rect(155, 515, 890, 78, fill="#0A1627", stroke=BORDER, radius=18))
    parts.append(
        text(
            600,
            546,
            "Required metadata",
            size=14,
            fill=BLUE,
            weight=800,
            anchor="middle",
            mono=True,
        )
    )
    parts.append(
        text(
            600,
            575,
            "source ID · locator · date · units · method boundary · uncertainty · conflict · reviewer",
            size=14,
            fill=MUTED,
            anchor="middle",
        )
    )
    footer_gate(parts, "MISSING EVIDENCE → HOLD / NOT_EVALUATED")
    return finish(parts)


def render_verification() -> str:
    stages = [
        ("Source identity", "manifest\nversion anchors\nrepository doctor", GREEN, "database"),
        ("Static checks", "compile · Ruff\nschemas · links\n18 SVG rebuild", BLUE, "shield"),
        (
            "Scientific tests",
            "pytest · coverage\nknown solutions\nadversarial cases",
            CYAN,
            "chart",
        ),
        ("Wheel content", "four-Skill tree\nreports · scripts\nMETADATA", PURPLE, "database"),
        ("Real install", "pip --target\nclean venv\norigin checks", TEAL, "cpu"),
        ("Release Gate", "performance\nsnapshot\nimmutable status", AMBER, "shield"),
    ]
    return render_linear(
        "Verification and release pipeline",
        "Every release is rebuilt, installed and checked from its own declared source identity",
        stages,
        footer="NO TEST OR INSTALL EVIDENCE → NO RELEASE",
        eyebrow="RELEASE QUALIFICATION",
    )


def render_batch_scan() -> str:
    parts = svg_start(
        "EPDM batch parameter-scan data flow",
        "Broadcast arrays pass through validated EPDM screening kernels to decision-ready outputs.",
    )
    header(
        parts,
        "EPDM batch parameter-scan data flow",
        "One boundary validation, NumPy broadcasting and explicit scenario dimensions for large screening studies",
        eyebrow="BATCH COMPUTING",
        accent=TEAL,
    )
    columns = [
        (
            52,
            "Scenario arrays",
            "temperature\nresidence time\nactive-site basis\nactivity multiplier",
            BLUE,
            "database",
        ),
        (
            300,
            "Shape contract",
            "broadcast-compatible\nfinite values\npositive domains",
            CYAN,
            "shield",
        ),
        (
            548,
            "Vectorized kernel",
            "Arrhenius arrays\nufunc conversions\nno numpy.vectorize",
            TEAL,
            "cpu",
        ),
        (
            796,
            "Decision outputs",
            "E/P/diene conversion\nshape metadata\nscenario count",
            GREEN,
            "chart",
        ),
    ]
    tags = ["INPUT", "VALIDATE", "COMPUTE", "OUTPUT"]
    for index, (x, label, detail, color, icon) in enumerate(columns):
        node_card(parts, x, 225, 215, 300, label, detail, color, icon=icon, tag=tags[index])
        if index < 3:
            parts.append(line(x + 215, 375, x + 245, 375, stroke=DIM, width=2, arrow=True))
    parts.append(rect(1030, 225, 118, 300, fill="#0D2038", stroke=AMBER, radius=20, shadow=True))
    parts.append(
        text(1089, 265, "GATE", size=13, fill=AMBER, mono=True, weight=800, anchor="middle")
    )
    parts.append(text(1089, 335, "≥3× gate", size=22, fill=TEXT, weight=850, anchor="middle"))
    parts.append(text(1089, 364, "1,000 cases", size=11, fill=MUTED, mono=True, anchor="middle"))
    parts.append(pill(1045, 405, "PARITY", GREEN, width=88))
    parts.append(pill(1045, 447, "NO DRIFT", BLUE, width=88))
    footer_gate(parts, "BROADCASTING IS USED ONLY FOR HOMOGENEOUS ARRAY KERNELS")
    return finish(parts)


def render_perf_gate() -> str:
    parts = svg_start(
        "Performance regression qualification gate",
        "Baseline and candidate workloads are compared on timing, memory, scale and numerical identity.",
    )
    header(
        parts,
        "Performance regression qualification gate",
        "Optimization claims survive only when results, memory and scale behavior remain within declared limits",
        eyebrow="PERFORMANCE EVIDENCE",
        accent=AMBER,
    )
    node_card(
        parts,
        52,
        225,
        210,
        300,
        "Frozen baseline",
        "same runner\nsame inputs\nsame repeats\nversioned JSON",
        BLUE,
        icon="database",
        tag="ALPHA.10",
    )
    node_card(
        parts,
        300,
        225,
        210,
        300,
        "Candidate run",
        "warm-ups\nmedian timing\npeak memory\ncProfile",
        CYAN,
        icon="chart",
        tag="ALPHA.11",
    )
    node_card(
        parts,
        548,
        225,
        260,
        300,
        "Parity policy",
        "exact digest\nanalytical tolerance\nsemantic contract\nscale normalization",
        PURPLE,
        icon="shield",
        tag="FAIL-CLOSED",
    )
    parts.append(line(262, 375, 300, 375, stroke=DIM, width=2, arrow=True))
    parts.append(line(510, 375, 548, 375, stroke=DIM, width=2, arrow=True))
    outcomes = [
        (845, 238, "PASS", "speed + parity", GREEN),
        (845, 338, "HOLD", "evidence missing", AMBER),
        (845, 438, "FAIL", "drift / regression", RED),
    ]
    for x, y, label, detail, color in outcomes:
        parts.append(
            rect(x, y, 303, 75, fill=f"{color}12", stroke=f"{color}88", radius=18, shadow=True)
        )
        small_icon(parts, x + 38, y + 38, "shield", color)
        parts.append(text(x + 72, y + 34, label, size=16, fill=color, weight=850, mono=True))
        parts.append(text(x + 72, y + 56, detail, size=12, fill=MUTED))
        parts.append(line(808, 375, x, y + 38, stroke=f"{color}88", width=1.5, arrow=True))
    footer_gate(parts, "PERFORMANCE PASS ≠ SCIENTIFIC OR INDUSTRIAL APPROVAL")
    return finish(parts)


def render_three_levels() -> str:
    parts = svg_start(
        "Three EPDM model levels",
        "Screening, engineering and detailed-reference model levels with increasing evidence requirements.",
    )
    header(
        parts,
        "Three EPDM model levels",
        "Fidelity increases only when the decision and available evidence justify the added complexity",
        eyebrow="MULTIFIDELITY MODELING",
    )
    cards = [
        (
            70,
            225,
            "Level 1 · Screening",
            "active-site normalization\nE/P/diene insertion\nrapid conversions\ninput boundary checks",
            BLUE,
            "fast ranking",
        ),
        (
            450,
            225,
            "Level 2 · Engineering",
            "Arrhenius correction\nsemibatch balances\nheat & mixing\nrecycle / devolatilization",
            CYAN,
            "flowsheet studies",
        ),
        (
            830,
            225,
            "Level 3 · Detailed",
            "site families\nchain moments\nbranching / gel\nphase & entropy references",
            PURPLE,
            "high-fidelity decision",
        ),
    ]
    icons = ["chart", "cpu", "molecule"]
    for index, (x, y, label, detail, color, tag) in enumerate(cards):
        node_card(
            parts,
            x,
            y,
            300,
            330,
            label,
            detail,
            color,
            icon=icons[index],
            tag=tag.upper(),
            title_size=19,
        )
        if index < 2:
            parts.append(line(x + 300, y + 165, x + 380, y + 165, stroke=DIM, width=2, arrow=True))
    footer_gate(parts, "ALL LEVELS RETURN CALCULATED_REFERENCE_ONLY")
    return finish(parts)


def render_multiscale() -> str:
    stages = [
        ("Catalyst & sites", "chemistry\nsite families\npoison boundary", BLUE, "molecule"),
        ("Chain events", "insertion\ntransfer\ndeactivation", CYAN, "flow"),
        ("Architecture", "sequence\nMWD / CCD\nbranching / gel", PURPLE, "chart"),
        ("Phase & transport", "solubility\nviscosity\nmixing / heat", TEAL, "cpu"),
        ("Reactor & process", "mode\nresidence\nrecycle / finishing", GREEN, "flow"),
        ("Product evidence", "Mooney\ncompound / cure\ncustomer line", AMBER, "shield"),
    ]
    return render_linear(
        "EPDM multiscale mechanism-to-package chain",
        "A continuous evidence path from catalyst chemistry to process-package acceptance",
        stages,
        footer="BROKEN SCALE LINK → HOLD",
        eyebrow="MULTISCALE CHAIN",
    )


def render_identifiability() -> str:
    stages = [
        ("Data boundary", "conditions · units\nsite basis · covariance", BLUE, "database"),
        ("Sensitivity", "local / global\nobservable response", CYAN, "chart"),
        ("Identifiability", "rank · correlation\nprofile likelihood", PURPLE, "cpu"),
        ("Uncertainty", "parameter / prediction\nscenario propagation", AMBER, "chart"),
        ("Decision Gate", "experiment · model\nscale-up / HOLD", GREEN, "shield"),
    ]
    return render_linear(
        "EPDM parameter identifiability and uncertainty",
        "Model fidelity advances only when experiments distinguish the parameters that drive the decision",
        stages,
        footer="NON-IDENTIFIABLE PARAMETERS REMAIN EXPLICIT",
        eyebrow="MODEL CONFIDENCE",
    )


def render_product_bridge() -> str:
    stages = [
        ("Raw polymer", "composition · MWD\nMooney · gel", BLUE, "molecule"),
        ("Compound", "fixed recipe\nmixing history", CYAN, "flow"),
        ("Cure", "rheometer\ncrosslink state", PURPLE, "chart"),
        ("Part", "geometry\naging · durability", TEAL, "cpu"),
        ("Customer line", "processing window\nquality evidence", GREEN, "database"),
        ("Approval", "named owner\nacceptance record", AMBER, "shield"),
    ]
    return render_linear(
        "EPDM raw-polymer-to-customer evidence bridge",
        "A reactor result becomes a product claim only through controlled formulation and qualification",
        stages,
        footer="REACTOR RESULT ≠ CUSTOMER CLAIM",
        eyebrow="PRODUCT QUALIFICATION",
    )


def render_dependency_lock() -> str:
    stages = [
        ("Dependency intent", "pyproject ranges\nruntime + dev extras", BLUE, "database"),
        ("Deterministic resolver", "Python 3.11\nbacktracking resolver", CYAN, "cpu"),
        ("Exact hashed lock", "name == version\nSHA-256 per artifact", PURPLE, "shield"),
        ("Clean installation", "--require-hashes\nno implicit upgrades", TEAL, "flow"),
        ("Vulnerability audit", "pip-audit\nmachine JSON evidence", AMBER, "chart"),
        ("Release Gate", "lock identity\nsource provenance", GREEN, "shield"),
    ]
    return render_linear(
        "Hashed dependency supply-chain gate",
        "Declared ranges become an exact, auditable and fail-closed installation contract",
        stages,
        footer="UNPINNED, UNHASHED OR VULNERABLE DEPENDENCY → HOLD",
        eyebrow="SOFTWARE SUPPLY CHAIN",
    )


def render_snapshot_self_validation() -> str:
    stages = [
        ("Source manifest", "canonical paths\nSHA-256 + bytes", BLUE, "database"),
        ("Snapshot staging", "manifest + overlay\nruntime support files", CYAN, "flow"),
        ("Identity metadata", "snapshot contract\nrelease SBOM", PURPLE, "database"),
        ("Re-extracted tree", "portable source\nno hidden checkout state", TEAL, "flow"),
        ("Self-validation", "provenance\nmetadata + Doctor", GREEN, "shield"),
        ("Archive digest", "deterministic ZIP\nexternal SHA-256", AMBER, "shield"),
    ]
    return render_linear(
        "Self-validating source snapshot",
        "The exported source must pass the same integrity rules after extraction",
        stages,
        footer="ARCHIVE CREATED ≠ ARCHIVE QUALIFIED",
        eyebrow="REPRODUCIBLE SOURCE DELIVERY",
    )


def render_main_only_delivery() -> str:
    stages = [
        ("main commit", "single authority\nno feature branch", BLUE, "database"),
        ("Qualification matrix", "Windows + Linux\nPython 3.11–3.14", CYAN, "cpu"),
        ("Evidence artifacts", "tests · coverage\nwheel · snapshot", PURPLE, "chart"),
        ("Atomic finalization", "lock + reports\nself-delete workflow", TEAL, "flow"),
        ("Branch cleanup", "delete stale refs\nretain commit history", AMBER, "shield"),
        ("main only", "auditable head\nreproducible release", GREEN, "shield"),
    ]
    return render_linear(
        "Main-only delivery lifecycle",
        "A one-shot release path qualifies the exact tree before removing obsolete branches",
        stages,
        footer="DELETE BRANCHES ONLY AFTER QUALIFICATION PASS",
        eyebrow="REPOSITORY GOVERNANCE",
    )


def render_ai_scientific_reasoning_loop() -> str:
    parts = svg_start(
        "Scientific AI reasoning loop",
        "A governed loop connecting observations, hypotheses, simulation, falsification and decisions.",
    )
    header(
        parts,
        "Scientific AI reasoning loop",
        "AI proposes; evidence, invariants and falsification decide",
        eyebrow="AI FOR PROCESS SCIENCE",
        accent=CYAN,
    )
    nodes = [
        (70, 245, "OBSERVE", "plant, laboratory and literature evidence", BLUE, "database"),
        (
            292,
            205,
            "HYPOTHESIZE",
            "mechanisms, hidden states and closure terms",
            PURPLE,
            "molecule",
        ),
        (706, 205, "SIMULATE", "reference kernels and scale bridges", CYAN, "cpu"),
        (928, 245, "FALSIFY", "balances, residuals and conflicting evidence", RED, "shield"),
        (706, 475, "QUALIFY", "uncertainty, applicability and named Gates", AMBER, "chart"),
        (292, 475, "DECIDE", "next experiment, model or package action", GREEN, "flow"),
    ]
    centers: list[tuple[float, float]] = []
    for x, y, title_value, detail, color, icon in nodes:
        node_card(
            parts,
            x,
            y,
            202,
            122,
            title_value,
            detail,
            color,
            icon=icon,
            tag="TRACEABLE",
            title_size=15,
        )
        centers.append((x + 101, y + 61))
    sequence = centers + [centers[0]]
    for (x1, y1), (x2, y2) in pairwise(sequence):
        parts.append(line(x1, y1, x2, y2, stroke=DIM, width=2.2, arrow=True, opacity=0.92))
    parts.extend(
        [
            circle(600, 388, 90, fill="#0C1A2C", stroke=CYAN, width=2),
            text(600, 372, "TSAO", size=27, weight=850, anchor="middle"),
            text(600, 402, "reasoning core", size=15, fill=CYAN, weight=750, anchor="middle"),
            multiline(
                600,
                431,
                "No silent promotion\nHOLD is a valid result",
                width_chars=22,
                size=13,
                fill=MUTED,
                weight=650,
                anchor="middle",
                line_height=19,
            ),
        ]
    )
    footer_gate(parts, "EVIDENCE -> MODEL -> TEST -> DECISION; EVERY TRANSITION IS RECORDED")
    return finish(parts)


def render_multiscale_digital_thread() -> str:
    parts = svg_start(
        "Multiscale digital thread",
        "A governed model and data thread from molecular evidence through reactors to process-package decisions.",
    )
    header(
        parts,
        "Multiscale digital thread",
        "Every scale carries units, provenance, assumptions and uncertainty",
        eyebrow="MECHANISM TO PROCESS PACKAGE",
        accent=PURPLE,
    )
    stages = [
        (54, "MOLECULE", "electronic structure\nand active sites", PURPLE, "molecule"),
        (278, "CHAIN", "kinetics, sequence\nand distributions", BLUE, "flow"),
        (502, "MESOSCALE", "phase, rheology\nand transport", CYAN, "chart"),
        (726, "REACTOR", "balances, mixing\nand heat removal", ORANGE, "cpu"),
        (950, "PACKAGE", "controls, HSE\nand acceptance", GREEN, "shield"),
    ]
    for index, (x, title_value, detail, color, icon) in enumerate(stages):
        node_card(
            parts,
            x,
            250,
            196,
            172,
            title_value,
            detail,
            color,
            icon=icon,
            tag=f"L{index}",
            title_size=16,
        )
        if index < len(stages) - 1:
            parts.append(
                line(
                    x + 196,
                    336,
                    stages[index + 1][0] - 12,
                    336,
                    stroke=color,
                    width=2.5,
                    arrow=True,
                )
            )
    parts.append(rect(84, 482, 1032, 126, fill="#0B182A", stroke=TEAL, radius=24))
    parts.append(
        text(112, 522, "DIGITAL THREAD CONTRACT", size=15, fill=TEAL, weight=800, letter=0.8)
    )
    rows = [
        (112, "STATE", "named variables"),
        (275, "UNITS", "dimensional closure"),
        (438, "SOURCE", "evidence lineage"),
        (601, "MODEL", "equations + domain"),
        (764, "UNCERTAINTY", "intervals + sensitivity"),
        (956, "GATE", "PASS / HOLD / FAIL"),
    ]
    for x, label, value in rows:
        parts.append(text(x, 560, label, size=12, fill=DIM, weight=750, mono=True))
        parts.append(text(x, 586, value, size=13, weight=650))
    footer_gate(parts, "NO SCALE JUMP WITHOUT A MACHINE-READABLE CONTRACT")
    return finish(parts)


def render_agentic_qualification_orchestrator() -> str:
    parts = svg_start(
        "Agentic qualification orchestrator",
        "An AI agent coordinates evidence, scientific kernels and verification without overriding independent Gates.",
    )
    header(
        parts,
        "Agentic qualification orchestrator",
        "Automation executes the protocol; independent Gates retain authority",
        eyebrow="AGENT CONTROL PLANE",
        accent=BLUE,
    )
    sources = [
        (58, 222, "EVIDENCE", "sources, conflicts, conditions and units", TEAL, "database"),
        (58, 374, "MODELS", "contracts, kernels, solvers and simulators", PURPLE, "cpu"),
        (58, 526, "REQUEST", "scope, CQA, risk and acceptance criteria", BLUE, "flow"),
    ]
    for x, y, title_value, detail, color, icon in sources:
        node_card(parts, x, y, 238, 112, title_value, detail, color, icon=icon, title_size=16)
        parts.append(line(296, y + 56, 458, 390, stroke=color, width=2.2, arrow=True))
    parts.extend(
        [
            circle(605, 390, 126, fill="#0C1B30", stroke=BLUE, width=2.2),
            circle(605, 390, 96, fill="#10243D", stroke=CYAN, width=1.4),
            text(605, 360, "AI", size=42, weight=900, anchor="middle"),
            text(
                605,
                394,
                "ORCHESTRATOR",
                size=15,
                fill=CYAN,
                weight=800,
                anchor="middle",
                letter=1.0,
            ),
            multiline(
                605,
                426,
                "route - execute - compare\nrecord - explain",
                width_chars=26,
                size=13,
                fill=MUTED,
                weight=650,
                anchor="middle",
                line_height=20,
            ),
        ]
    )
    gates = [
        (912, 216, "BALANCE", "mass / energy", GREEN),
        (912, 330, "NUMERICS", "stability / parity", CYAN),
        (912, 444, "EVIDENCE", "lineage / conflict", AMBER),
        (912, 558, "APPROVAL", "named authority", RED),
    ]
    for x, y, title_value, detail, color in gates:
        node_card(parts, x, y, 232, 80, title_value, detail, color, icon="shield", title_size=15)
        parts.append(line(731, 390, x - 14, y + 40, stroke=color, width=2.1, arrow=True))
    footer_gate(parts, "AGENT OUTPUT IS NOT ENGINEERING, HSE OR CUSTOMER APPROVAL")
    return finish(parts)


def render_uncertainty_decision_landscape() -> str:
    parts = svg_start(
        "Uncertainty-to-decision landscape",
        "A qualification landscape where uncertainty and applicability determine PASS, HOLD, FAIL or NOT_EVALUATED.",
    )
    header(
        parts,
        "Uncertainty-to-decision landscape",
        "Precision is not confidence; confidence requires independent closure",
        eyebrow="DECISION SCIENCE",
        accent=AMBER,
    )
    panels = [
        (72, PURPLE, "1 - UNCERTAINTY"),
        (435, CYAN, "2 - APPLICABILITY"),
        (798, GREEN, "3 - DECISION GATE"),
    ]
    for x, color, title_value in panels:
        parts.append(rect(x, 226, 330, 360, fill="#101D31", stroke=color, radius=28, shadow=True))
        parts.append(text(x + 30, 272, title_value, size=18, fill=color, weight=800))
    left = [
        ("PARAMETER", "identified / prior / nuisance"),
        ("MODEL FORM", "candidate closures and bias"),
        ("NUMERICAL", "tolerance, stiffness and drift"),
        ("MEASUREMENT", "noise, censoring and calibration"),
    ]
    middle = [
        ("DOMAIN", "temperature / pressure / composition"),
        ("SCALE", "laboratory / pilot / plant"),
        ("REGIME", "phase / transport / kinetics"),
        ("EVIDENCE", "direct / inferred / missing"),
    ]
    for index, (label, value) in enumerate(left):
        y = 320 + index * 62
        parts.append(pill(102, y - 22, label, PURPLE, width=116, height=26, mono=True))
        parts.append(text(232, y, value, size=13, weight=650))
    for index, (label, value) in enumerate(middle):
        y = 320 + index * 62
        parts.append(pill(465, y - 22, label, CYAN, width=104, height=26, mono=True))
        parts.append(text(583, y, value, size=13, weight=650))
    gates = [
        ("PASS", "declared Gate closed", GREEN),
        ("HOLD", "evidence incomplete", AMBER),
        ("FAIL", "contract violated", RED),
        ("NOT EVALUATED", "no qualified claim", DIM),
    ]
    for index, (label, value, color) in enumerate(gates):
        y = 304 + index * 66
        parts.append(rect(832, y, 264, 50, fill=f"{color}18", stroke=color, radius=14))
        parts.append(text(850, y + 31, label, size=13, fill=color, weight=800, mono=True))
        parts.append(text(1080, y + 31, value, size=12, weight=650, anchor="end"))
    parts.append(line(402, 406, 435, 406, stroke=PURPLE, width=3, arrow=True))
    parts.append(line(765, 406, 798, 406, stroke=CYAN, width=3, arrow=True))
    footer_gate(parts, "TRACEABILITY TURNS UNCERTAINTY INTO AN ACTIONABLE DECISION")
    return finish(parts)


def render_law_to_grade_inverse_design() -> str:
    parts = svg_start(
        "Law-to-Grade inverse design",
        "An inverse scientific workflow from observed product behavior to hidden mechanisms and forward reconstruction.",
    )
    header(
        parts,
        "Law-to-Grade inverse design",
        "Infer missing physics, then reconstruct the grade and process forward",
        eyebrow="INVERSE PROBLEM",
        accent=PURPLE,
    )
    top = [
        (62, "OBSERVED", "quality, failure and operating signatures", BLUE, "chart"),
        (300, "INFER", "hidden states, parameters and closure terms", PURPLE, "cpu"),
        (538, "PROPOSE", "candidate interactions and elementary events", CYAN, "molecule"),
        (776, "REBUILD", "chain, particle, reactor and finishing", TEAL, "flow"),
        (1014, "TEST", "new perturbations and falsification", GREEN, "shield"),
    ]
    for i, (x, title_value, detail, color, icon) in enumerate(top):
        node_card(
            parts,
            x,
            238,
            190,
            160,
            title_value,
            detail,
            color,
            icon=icon,
            tag=f"S{i + 1}",
            title_size=15,
        )
        if i < len(top) - 1:
            parts.append(
                line(x + 190, 318, top[i + 1][0] - 10, 318, stroke=color, width=2.4, arrow=True)
            )
    parts.append(rect(132, 474, 936, 118, fill="#0B182A", stroke=AMBER, radius=24))
    parts.append(text(160, 514, "IDENTIFIABILITY GATE", size=16, fill=AMBER, weight=800))
    checks = [
        "multiple experiments",
        "independent observables",
        "prior sensitivity",
        "out-of-sample perturbation",
        "mechanism competition",
    ]
    for index, label in enumerate(checks):
        x = 160 + index * 178
        parts.append(pill(x, 542, label.upper(), AMBER, width=158, height=28, mono=True))
    footer_gate(parts, "A GOOD FIT WITHOUT IDENTIFIABILITY REMAINS HOLD")
    return finish(parts)


def render_autonomous_experiment_loop() -> str:
    parts = svg_start(
        "Autonomous experiment loop",
        "A safe closed-loop workflow for selecting experiments, executing measurements and updating models.",
    )
    header(
        parts,
        "Autonomous experiment loop",
        "Maximize information gain while preserving safety and evidence quality",
        eyebrow="ACTIVE LEARNING",
        accent=TEAL,
    )
    center_x, center_y = 600, 392
    parts.extend(
        [
            circle(center_x, center_y, 90, fill="#0C1B30", stroke=TEAL, width=2),
            text(center_x, center_y - 5, "DoE", size=30, weight=850, anchor="middle"),
            text(
                center_x,
                center_y + 25,
                "information gain",
                size=14,
                fill=TEAL,
                weight=750,
                anchor="middle",
            ),
        ]
    )
    nodes = [
        (84, 238, "CANDIDATES", "feasible conditions and controllable factors", BLUE, "database"),
        (328, 190, "SELECT", "expected information, cost and risk", PURPLE, "chart"),
        (720, 190, "EXECUTE", "instrument recipe and operator boundary", ORANGE, "cpu"),
        (964, 238, "MEASURE", "calibrated signals and metadata", CYAN, "chart"),
        (720, 486, "UPDATE", "posterior, residuals and model ranking", GREEN, "database"),
        (328, 486, "REVIEW", "human approval and next-cycle decision", AMBER, "shield"),
    ]
    centers = []
    for x, y, title_value, detail, color, icon in nodes:
        node_card(parts, x, y, 190, 118, title_value, detail, color, icon=icon, title_size=15)
        centers.append((x + 95, y + 59))
    seq = centers + [centers[0]]
    for (x1, y1), (x2, y2) in pairwise(seq):
        parts.append(line(x1, y1, x2, y2, stroke=DIM, width=2.2, arrow=True))
    footer_gate(parts, "NO AUTONOMOUS ACTION MAY BYPASS EQUIPMENT OR HSE LIMITS")
    return finish(parts)


def render_process_knowledge_graph() -> str:
    parts = svg_start(
        "Process knowledge graph",
        "A traceable knowledge graph connecting evidence, variables, models, equipment, risks and decisions.",
    )
    header(
        parts,
        "Process knowledge graph",
        "Every claim is connected to its source, conditions and decision boundary",
        eyebrow="KNOWLEDGE ARCHITECTURE",
        accent=BLUE,
    )
    center = (600, 388)
    parts.extend(
        [
            circle(*center, 94, fill="#0D2038", stroke=BLUE, width=2),
            text(600, 374, "PROCESS", size=24, weight=850, anchor="middle"),
            text(
                600,
                405,
                "KNOWLEDGE GRAPH",
                size=14,
                fill=CYAN,
                weight=800,
                anchor="middle",
                letter=0.8,
            ),
        ]
    )
    nodes = [
        (94, 222, "EVIDENCE", "papers, tests, plant records", TEAL, "database"),
        (94, 488, "DECISIONS", "Gates, owners and rationale", GREEN, "shield"),
        (360, 180, "VARIABLES", "states, units and observability", BLUE, "chart"),
        (752, 180, "MODELS", "equations, domains and versions", PURPLE, "cpu"),
        (1018, 222, "EQUIPMENT", "streams, controls and limits", ORANGE, "flow"),
        (1018, 488, "RISKS", "hazards, uncertainty and conflicts", RED, "shield"),
    ]
    for x, y, title_value, detail, color, icon in nodes:
        node_card(parts, x, y, 184, 118, title_value, detail, color, icon=icon, title_size=15)
        start_x = x + 184 if x < center[0] else x
        end_x = center[0] - 96 if x < center[0] else center[0] + 96
        parts.append(line(start_x, y + 59, end_x, center[1], stroke=color, width=2.1, arrow=True))
    footer_gate(parts, "A CLAIM WITHOUT SOURCE, CONDITIONS OR OWNER IS NOT DECISION-READY")
    return finish(parts)


def render_model_risk_governance() -> str:
    parts = svg_start(
        "Model risk governance",
        "A layered governance architecture for scientific models from registration through retirement.",
    )
    header(
        parts,
        "Model risk governance",
        "Separate computational correctness from scientific validity and operational approval",
        eyebrow="MODEL GOVERNANCE",
        accent=RED,
    )
    layers = [
        (210, "REGISTER", "purpose, owner, version, equations and dependencies", BLUE, "database"),
        (296, "VERIFY", "tests, invariants, numerical stability and reproducibility", CYAN, "cpu"),
        (382, "VALIDATE", "independent evidence, uncertainty and applicability", PURPLE, "chart"),
        (
            468,
            "APPROVE",
            "named technical, engineering, HSE and customer authorities",
            AMBER,
            "shield",
        ),
        (554, "MONITOR", "drift, incidents, change control and retirement", GREEN, "flow"),
    ]
    widths = [980, 870, 760, 650, 540]
    for index, ((y, title_value, detail, color, icon), width) in enumerate(
        zip(layers, widths, strict=True)
    ):
        x = (1200 - width) / 2
        parts.append(
            rect(x, y, width, 64, fill=f"{color}14", stroke=color, radius=18, shadow=index == 0)
        )
        small_icon(parts, x + 38, y + 32, icon, color)
        parts.append(text(x + 74, y + 28, title_value, size=15, fill=color, weight=850, mono=True))
        parts.append(text(x + 74, y + 49, detail, size=13, weight=650))
    footer_gate(parts, "MODEL USE OUTSIDE ITS APPROVED DOMAIN RETURNS HOLD OR FAIL")
    return finish(parts)


ASSETS = {
    "ai-scientific-reasoning-loop.svg": render_ai_scientific_reasoning_loop,
    "multiscale-digital-thread.svg": render_multiscale_digital_thread,
    "agentic-qualification-orchestrator.svg": render_agentic_qualification_orchestrator,
    "uncertainty-decision-landscape.svg": render_uncertainty_decision_landscape,
    "law-to-grade-inverse-design.svg": render_law_to_grade_inverse_design,
    "autonomous-experiment-loop.svg": render_autonomous_experiment_loop,
    "process-knowledge-graph.svg": render_process_knowledge_graph,
    "model-risk-governance.svg": render_model_risk_governance,
    "tsao-process-intelligence-os.svg": render_platform,
    "universal-process-package.svg": lambda: render_linear(
        "Universal process-package lifecycle",
        "One decision-centered lifecycle from design basis to technology transfer",
        [
            (
                "Design basis",
                "scope · targets\ncomponents · units\nacceptance criteria",
                BLUE,
                "database",
            ),
            ("Evidence & models", "data boundary\nthermo · kinetics\nuncertainty", CYAN, "chart"),
            (
                "Process synthesis",
                "reactor · separation\nutilities · equipment\nbalances",
                TEAL,
                "flow",
            ),
            (
                "Control & HSE",
                "alarms · interlocks\nabnormal cases\nsafety interfaces",
                RED,
                "shield",
            ),
            ("Scale-up & TEA", "similarity breaks\npilot evidence\nCAPEX / OPEX", PURPLE, "chart"),
            (
                "Package & transfer",
                "documents · owners\nGate matrix\noperating handover",
                GREEN,
                "database",
            ),
        ],
        footer="MISSING EVIDENCE OR APPROVAL → HOLD",
        eyebrow="PROCESS-PACKAGE LIFECYCLE",
    ),
    "process-package-architecture.svg": render_layers,
    "process-package-data-model.svg": render_data_model,
    "control-safety-cause-effect.svg": lambda: render_linear(
        "Control, interlock and process-safety chain",
        "Normal control and independent protection remain connected but explicitly separated",
        [
            ("Measurement", "sensor · analyzer\nmeasurement boundary", BLUE, "chart"),
            ("Regulatory control", "PID · cascade\nconstraint control", CYAN, "cpu"),
            ("Alarm & operator", "priority · response\nabnormal procedure", AMBER, "shield"),
            ("Interlock / SIS", "trip · permissive\nindependent function", RED, "shield"),
            ("Relief & containment", "relief · flare\nsecondary containment", PURPLE, "shield"),
            ("Evidence Gate", "test · approval\nMOC · learning", GREEN, "database"),
        ],
        footer="QUALIFIED TEAMS OWN THE SAFETY DECISION",
        eyebrow="CONTROL & PROCESS SAFETY",
    ),
    "simulation-integration-contract.svg": render_integration,
    "epdm-multiscale-chain.svg": render_multiscale,
    "epdm-catalyst-kinetics-network.svg": render_network,
    "epdm-three-level-models.svg": render_three_levels,
    "epdm-reactor-mode-map.svg": render_reactor_map,
    "epdm-identifiability-uncertainty.svg": render_identifiability,
    "epdm-product-customer-bridge.svg": render_product_bridge,
    "epdm-process-flowsheet.svg": render_flowsheet,
    "recovery-recycle-risk-loop.svg": render_recycle,
    "evidence-gate-system.svg": render_evidence,
    "verification-pipeline.svg": render_verification,
    "batch-parameter-scan.svg": render_batch_scan,
    "performance-regression-gate.svg": render_perf_gate,
    "dependency-lock-supply-chain.svg": render_dependency_lock,
    "source-snapshot-self-validation.svg": render_snapshot_self_validation,
    "main-only-delivery-lifecycle.svg": render_main_only_delivery,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, renderer in ASSETS.items():
        (OUT / name).write_text(renderer(), encoding="utf-8")
    print(f"generated {len(ASSETS)} UI/UX Pro Max-aligned README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
