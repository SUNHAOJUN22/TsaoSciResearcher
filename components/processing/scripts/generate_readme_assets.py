from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/readme"

INK = "#102033"
MUTED = "#52647a"
WHITE = "#ffffff"
BLUE = "#2563eb"
CYAN = "#0891b2"
TEAL = "#0f766e"
GREEN = "#15803d"
AMBER = "#d97706"
RED = "#dc2626"
PURPLE = "#7c3aed"
SLATE = "#334155"


def text(
    x: int,
    y: int,
    value: str,
    *,
    size: int = 20,
    weight: int = 500,
    fill: str = INK,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Inter,Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">'
        f"{escape(value)}</text>"
    )


def rect(
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    fill: str = WHITE,
    stroke: str = "#d7e0ea",
    radius: int = 18,
    width: int = 2,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
    )


def line(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    stroke: str = SLATE,
    width: int = 3,
    dash: str | None = None,
    marker: bool = False,
) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    end = ' marker-end="url(#arrow)"' if marker else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round"{extra}{end}/>'
    )


def circle(
    cx: int,
    cy: int,
    r: int,
    *,
    fill: str,
    stroke: str = WHITE,
    width: int = 4,
) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{width}"/>'
    )


def pill(x: int, y: int, w: int, label: str, color: str) -> str:
    return rect(
        x,
        y,
        w,
        38,
        fill=f"{color}18",
        stroke=f"{color}55",
        radius=19,
        width=1,
    ) + text(
        x + w // 2,
        y + 26,
        label,
        size=15,
        weight=650,
        fill=color,
        anchor="middle",
    )


def header(title_value: str, subtitle: str, width: int) -> list[str]:
    return [
        text(54, 68, title_value, size=34, weight=760),
        text(54, 102, subtitle, size=17, weight=450, fill=MUTED),
        line(54, 124, width - 54, 124, stroke="#dce4ee", width=2),
    ]


def wrap(
    title_value: str,
    description: str,
    body: list[str],
    *,
    width: int = 1200,
    height: int = 680,
) -> str:
    defs = """
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#f8fbff"/><stop offset="100%" stop-color="#eef4fb"/>
      </linearGradient>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="7" stdDeviation="9" flood-color="#17365d" flood-opacity="0.12"/>
      </filter>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#52647a"/>
      </marker>
    </defs>
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f"<title>{escape(title_value)}</title><desc>{escape(description)}</desc>{defs}"
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>' + "".join(body) + "</svg>\n"
    )


def hero() -> str:
    body = header(
        "TSAO Process Intelligence OS",
        "One auditable operating system for universal process packages — with EPDM as the flagship specialist",
        1200,
    )
    body += [
        rect(54, 162, 1092, 434, fill=WHITE, stroke="#cbd8e7", radius=28),
        circle(600, 378, 102, fill=BLUE),
        text(600, 362, "TSAO", size=34, weight=800, fill=WHITE, anchor="middle"),
        text(
            600,
            397,
            "evidence-driven",
            size=17,
            weight=600,
            fill="#dbeafe",
            anchor="middle",
        ),
        text(
            600,
            421,
            "fail-closed",
            size=17,
            weight=600,
            fill="#dbeafe",
            anchor="middle",
        ),
    ]
    nodes = [
        (210, 250, "Design basis", CYAN),
        (205, 505, "Safety & control", RED),
        (990, 250, "Balances & models", PURPLE),
        (995, 505, "Acceptance & transfer", GREEN),
        (600, 545, "EPDM flagship", AMBER),
    ]
    for x, y, label, color in nodes:
        body += [
            line(600, 378, x, y, stroke="#8394aa", width=3, marker=True),
            circle(x, y, 52, fill=color),
            text(
                x,
                y + 6,
                label,
                size=15,
                weight=700,
                fill=WHITE,
                anchor="middle",
            ),
        ]
    body += [
        pill(90, 620, 180, "Traceable evidence", BLUE),
        pill(288, 620, 180, "Mass & energy", TEAL),
        pill(486, 620, 180, "Thermodynamics", PURPLE),
        pill(684, 620, 180, "HSE & operability", RED),
        pill(882, 620, 220, "Qualified deliverables", GREEN),
    ]
    return wrap(
        "TSAO Process Intelligence OS",
        "Overview of the TSAO universal process-package system.",
        body,
        height=690,
    )


def lifecycle() -> str:
    body = header(
        "Universal process-package lifecycle",
        "From an evidence-framed brief to a controlled, auditable engineering package",
        1200,
    )
    stages = [
        (70, "01", "Brief & CQA", BLUE),
        (250, "02", "Evidence & data", CYAN),
        (430, "03", "Models & balances", PURPLE),
        (610, "04", "Equipment & control", AMBER),
        (790, "05", "HSE & operability", RED),
        (970, "06", "Acceptance & transfer", GREEN),
    ]
    for index, (x, number, label, color) in enumerate(stages):
        body += [
            rect(x, 190, 160, 250, fill=WHITE, stroke=f"{color}55", radius=22),
            circle(x + 80, 245, 34, fill=color),
            text(
                x + 80,
                253,
                number,
                size=18,
                weight=800,
                fill=WHITE,
                anchor="middle",
            ),
            text(x + 80, 310, label, size=18, weight=720, anchor="middle"),
        ]
        details = {
            "01": ("scope", "specification", "decision rights"),
            "02": ("sources", "measurements", "uncertainty"),
            "03": ("thermo", "reaction", "mass/energy"),
            "04": ("sizing", "PFD/P&ID", "control"),
            "05": ("HAZID", "relief", "abnormal cases"),
            "06": ("gates", "evidence", "approval"),
        }[number]
        for item_index, item in enumerate(details):
            body.append(
                text(
                    x + 80,
                    350 + 30 * item_index,
                    item,
                    size=15,
                    fill=MUTED,
                    anchor="middle",
                )
            )
        if index < len(stages) - 1:
            body.append(line(x + 160, 315, x + 180, 315, stroke="#8394aa", marker=True))
    body += [
        rect(180, 500, 840, 96, fill="#102033", stroke="#102033", radius=22),
        text(
            600,
            538,
            "Every stage emits machine-readable artifacts, evidence IDs and explicit HOLD conditions",
            size=21,
            weight=720,
            fill=WHITE,
            anchor="middle",
        ),
        text(
            600,
            571,
            "Software PASS never substitutes for scientific, engineering, HSE, customer or industrial approval",
            size=16,
            weight=500,
            fill="#d7e4f2",
            anchor="middle",
        ),
    ]
    return wrap(
        "Universal process-package lifecycle",
        "Lifecycle of the universal process package.",
        body,
    )


def architecture() -> str:
    body = header(
        "Layered architecture",
        "A small executable core surrounded by specialist contracts, evidence and delivery gates",
        1200,
    )
    layers = [
        (
            90,
            170,
            1020,
            88,
            "Interfaces",
            "CLI · JSON Schema · project workspace · deterministic archive",
            BLUE,
        ),
        (
            135,
            278,
            930,
            88,
            "Universal process package",
            "design basis · streams · equipment · balances · controls · HSE · acceptance",
            CYAN,
        ),
        (
            180,
            386,
            840,
            88,
            "Specialist routes",
            "EPDM flagship · POE evidence-rich specialist · polymer-general · process-general",
            PURPLE,
        ),
        (
            225,
            494,
            750,
            88,
            "Assurance kernel",
            "provenance · evidence ledger · gates · source identity · fail-closed audits",
            GREEN,
        ),
    ]
    for x, y, w, h, title_value, subtitle, color in layers:
        body += [
            rect(x, y, w, h, fill=WHITE, stroke=f"{color}66", radius=20),
            rect(x, y, 180, h, fill=color, stroke=color, radius=20),
            text(
                x + 90,
                y + 53,
                title_value,
                size=19,
                weight=750,
                fill=WHITE,
                anchor="middle",
            ),
            text(x + 205, y + 53, subtitle, size=17, weight=530, fill=INK),
        ]
    return wrap("Layered architecture", "Layered architecture of TSAO.", body)


def epdm_multiscale() -> str:
    body = header(
        "EPDM multiscale mechanism-to-package chain",
        "Chemical events are connected to architecture, reactor behavior, finishing and customer acceptance",
        1200,
    )
    levels = [
        (70, 180, "Active sites", "catalyst family\nsite fraction\npoison memory", BLUE),
        (
            285,
            180,
            "Elementary kinetics",
            "E/P/diene insertion\ntransfer\ndeactivation",
            CYAN,
        ),
        (
            500,
            180,
            "Chain architecture",
            "sequence · MWD/CCD\nunsaturation\nbranch/gel",
            PURPLE,
        ),
        (
            715,
            180,
            "Reactor physics",
            "phase stability\nmixing · heat removal\nresidence time",
            AMBER,
        ),
        (
            930,
            180,
            "Process package",
            "recovery · devol\ncontrol · HSE\nacceptance",
            GREEN,
        ),
    ]
    for index, (x, y, title_value, detail, color) in enumerate(levels):
        body += [
            rect(x, y, 190, 240, fill=WHITE, stroke=f"{color}66", radius=24),
            circle(x + 95, y + 54, 34, fill=color),
            text(
                x + 95,
                y + 116,
                title_value,
                size=18,
                weight=760,
                anchor="middle",
            ),
        ]
        for item_index, item in enumerate(detail.split("\n")):
            body.append(
                text(
                    x + 95,
                    y + 158 + 30 * item_index,
                    item,
                    size=15,
                    fill=MUTED,
                    anchor="middle",
                )
            )
        if index < len(levels) - 1:
            body.append(
                line(
                    x + 190,
                    y + 120,
                    x + 215,
                    y + 120,
                    marker=True,
                    stroke="#8394aa",
                )
            )
    body += [
        rect(150, 485, 900, 105, fill="#fff7ed", stroke="#fdba74", radius=22),
        text(
            600,
            528,
            "Causal guardrail",
            size=20,
            weight=800,
            fill=AMBER,
            anchor="middle",
        ),
        text(
            600,
            560,
            "A software calculation may propose a mechanism; only named evidence and qualified experiments may promote it",
            size=17,
            weight=560,
            fill=INK,
            anchor="middle",
        ),
    ]
    return wrap(
        "EPDM multiscale chain",
        "EPDM mechanism-to-process-package chain.",
        body,
    )


def epdm_models() -> str:
    body = header(
        "Three EPDM model levels",
        "Use the simplest model that can answer the decision — preserve a path to greater fidelity",
        1200,
    )
    cards = [
        (
            80,
            180,
            "Level 1",
            "Screening",
            BLUE,
            ("active-site normalized", "ternary insertion", "rapid conversion"),
        ),
        (
            430,
            180,
            "Level 2",
            "Engineering",
            AMBER,
            ("Arrhenius scaling", "semibatch balances", "heat/mixing/recycle"),
        ),
        (
            780,
            180,
            "Level 3",
            "Detailed reference",
            PURPLE,
            ("site heterogeneity", "chain moments", "phase/entropy/gel"),
        ),
    ]
    for x, y, level, name, color, items in cards:
        body += [
            rect(x, y, 320, 330, fill=WHITE, stroke=f"{color}66", radius=28),
            pill(x + 28, y + 28, 112, level, color),
            text(x + 28, y + 108, name, size=27, weight=780),
        ]
        for item_index, item in enumerate(items):
            body += [
                circle(
                    x + 42,
                    y + 162 + 55 * item_index,
                    8,
                    fill=color,
                    stroke=color,
                    width=0,
                ),
                text(
                    x + 65,
                    y + 169 + 55 * item_index,
                    item,
                    size=18,
                    weight=550,
                ),
            ]
        body.append(
            text(
                x + 28,
                y + 298,
                "CALCULATED_REFERENCE_ONLY",
                size=13,
                weight=730,
                fill=RED,
            )
        )
    body += [
        line(400, 345, 430, 345, marker=True, stroke="#8394aa"),
        line(750, 345, 780, 345, marker=True, stroke="#8394aa"),
        text(
            600,
            565,
            "Fidelity increases only when data, parameter identifiability and decision value justify it",
            size=18,
            weight=650,
            fill=SLATE,
            anchor="middle",
        ),
    ]
    return wrap(
        "Three EPDM model levels",
        "Three levels of EPDM kinetic and process models.",
        body,
    )


def epdm_flowsheet() -> str:
    body = header(
        "EPDM process-package reference flowsheet",
        "A process-centered map for reaction, finishing, recycle and quality integration",
        1200,
    )
    units = [
        (60, 270, 150, "Feed purification", BLUE),
        (260, 270, 150, "Catalyst & dosing", CYAN),
        (460, 240, 210, "Solution polymerization", PURPLE),
        (720, 270, 150, "Quench / deashing", AMBER),
        (920, 270, 150, "Devolatilization", RED),
    ]
    for index, (x, y, w, label, color) in enumerate(units):
        body += [
            rect(x, y, w, 100, fill=WHITE, stroke=f"{color}77", radius=18),
            rect(x, y, w, 12, fill=color, stroke=color, radius=6),
            text(
                x + w // 2,
                y + 61,
                label,
                size=17,
                weight=720,
                anchor="middle",
            ),
        ]
        if index < len(units) - 1:
            next_x = units[index + 1][0]
            body.append(
                line(
                    x + w,
                    y + 50,
                    next_x,
                    units[index + 1][1] + 50,
                    marker=True,
                    stroke="#65778d",
                )
            )
    body += [
        rect(940, 455, 170, 86, fill=WHITE, stroke=f"{GREEN}77", radius=18),
        text(1025, 490, "Finishing", size=18, weight=760, anchor="middle"),
        text(1025, 516, "bale / pellet", size=15, fill=MUTED, anchor="middle"),
        line(995, 370, 1025, 455, marker=True, stroke="#65778d"),
        rect(470, 455, 200, 86, fill="#ecfeff", stroke="#67e8f9", radius=18),
        text(
            570,
            490,
            "Solvent / monomer",
            size=17,
            weight=740,
            anchor="middle",
        ),
        text(
            570,
            516,
            "recovery + purge",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        line(995, 370, 670, 455, marker=True, stroke="#65778d"),
        line(470, 498, 335, 370, marker=True, stroke=CYAN, dash="8 7"),
        pill(90, 565, 190, "impurity guard", RED),
        pill(300, 565, 190, "phase stability", PURPLE),
        pill(510, 565, 190, "heat removal", AMBER),
        pill(720, 565, 190, "volatile closure", CYAN),
        pill(930, 565, 190, "quality bridge", GREEN),
    ]
    return wrap(
        "EPDM process-package reference flowsheet",
        "EPDM process reference flowsheet.",
        body,
    )


def evidence_gates() -> str:
    body = header(
        "Evidence and qualification gates",
        "Claims advance only when data lineage, model boundaries and qualified approvals are complete",
        1200,
    )
    body += [line(130, 340, 1070, 340, stroke="#9aa9bb", width=5)]
    gates = [
        (150, "G0", "scope", BLUE),
        (330, "G4", "laboratory", CYAN),
        (510, "G8", "process", PURPLE),
        (690, "G12", "pilot", AMBER),
        (870, "G16", "demo", RED),
        (1050, "G18", "transfer", GREEN),
    ]
    for x, gate, name, color in gates:
        body += [
            circle(x, 340, 37, fill=color),
            text(
                x,
                347,
                gate,
                size=17,
                weight=800,
                fill=WHITE,
                anchor="middle",
            ),
            text(x, 405, name, size=16, weight=700, anchor="middle"),
        ]
    body += [
        rect(90, 175, 300, 90, fill=WHITE, stroke="#bfd1e5", radius=18),
        text(240, 211, "Evidence ledger", size=19, weight=760, anchor="middle"),
        text(
            240,
            240,
            "source · condition · value · claim",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(450, 175, 300, 90, fill=WHITE, stroke="#bfd1e5", radius=18),
        text(600, 211, "Model passport", size=19, weight=760, anchor="middle"),
        text(
            600,
            240,
            "equations · units · validity · risk",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(810, 175, 300, 90, fill=WHITE, stroke="#bfd1e5", radius=18),
        text(960, 211, "Named approval", size=19, weight=760, anchor="middle"),
        text(
            960,
            240,
            "role · decision · date · evidence",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(250, 485, 700, 96, fill="#fff1f2", stroke="#fda4af", radius=22),
        text(
            600,
            524,
            "FAIL / HOLD is a useful engineering result",
            size=21,
            weight=800,
            fill=RED,
            anchor="middle",
        ),
        text(
            600,
            557,
            "It exposes missing evidence before a weak assumption reaches equipment, safety or customer decisions",
            size=16,
            weight=520,
            fill=INK,
            anchor="middle",
        ),
    ]
    return wrap(
        "Evidence and qualification gates",
        "Evidence and qualification gate model.",
        body,
    )


def verification() -> str:
    body = header(
        "Verification pipeline",
        "Repository integrity, science-facing invariants and packaging are checked on every supported platform",
        1200,
    )
    steps = [
        (80, 200, "Compile", "Python syntax", BLUE),
        (275, 200, "Test", "unit + integration", CYAN),
        (470, 200, "Audit", "contracts + evidence", PURPLE),
        (665, 200, "Lint", "Ruff quality", AMBER),
        (860, 200, "Package", "wheel + runtime", GREEN),
    ]
    for index, (x, y, title_value, subtitle, color) in enumerate(steps):
        body += [
            circle(x + 70, y + 70, 58, fill=color),
            text(
                x + 70,
                y + 66,
                title_value,
                size=18,
                weight=800,
                fill=WHITE,
                anchor="middle",
            ),
            text(
                x + 70,
                y + 91,
                subtitle,
                size=13,
                weight=600,
                fill="#eff6ff",
                anchor="middle",
            ),
        ]
        if index < len(steps) - 1:
            body.append(
                line(
                    x + 128,
                    y + 70,
                    x + 195,
                    y + 70,
                    marker=True,
                    stroke="#8394aa",
                )
            )
    body += [
        rect(90, 410, 300, 120, fill=WHITE, stroke="#bfd1e5", radius=20),
        text(240, 451, "Platforms", size=19, weight=760, anchor="middle"),
        text(
            240,
            482,
            "Ubuntu 3.11 / 3.12",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        text(
            240,
            508,
            "Windows + macOS 3.12",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(450, 410, 300, 120, fill=WHITE, stroke="#bfd1e5", radius=20),
        text(
            600,
            451,
            "Scientific invariants",
            size=19,
            weight=760,
            anchor="middle",
        ),
        text(
            600,
            482,
            "mass / molar closure",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        text(
            600,
            508,
            "bounds / signs / units",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(810, 410, 300, 120, fill=WHITE, stroke="#bfd1e5", radius=20),
        text(
            960,
            451,
            "Release identity",
            size=19,
            weight=760,
            anchor="middle",
        ),
        text(
            960,
            482,
            "source manifest",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        text(
            960,
            508,
            "deterministic archive",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
    ]
    return wrap("Verification pipeline", "Software verification pipeline.", body)


ASSETS = {
    "tsao-process-intelligence-os.svg": hero,
    "universal-process-package.svg": lifecycle,
    "process-package-architecture.svg": architecture,
    "epdm-multiscale-chain.svg": epdm_multiscale,
    "epdm-three-level-models.svg": epdm_models,
    "epdm-process-flowsheet.svg": epdm_flowsheet,
    "evidence-gate-system.svg": evidence_gates,
    "verification-pipeline.svg": verification,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, builder in ASSETS.items():
        (OUT / filename).write_text(builder(), encoding="utf-8", newline="\n")
    print(f"generated {len(ASSETS)} README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
