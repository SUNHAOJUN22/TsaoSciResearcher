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
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{escape(value)}</text>'
    )


def rect(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    fill: str = WHITE,
    stroke: str = "#d7e0ea",
    radius: int = 18,
    stroke_width: int = 2,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{stroke_width}"/>'
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
    marker_end = ' marker-end="url(#arrow)"' if marker else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"'
        f"{extra}{marker_end}/>"
    )


def circle(
    center_x: int,
    center_y: int,
    radius: int,
    *,
    fill: str,
    stroke: str = WHITE,
    stroke_width: int = 4,
) -> str:
    return (
        f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def pill(x: int, y: int, width: int, label: str, color: str) -> str:
    return rect(
        x,
        y,
        width,
        38,
        fill=f"{color}18",
        stroke=f"{color}55",
        radius=19,
        stroke_width=1,
    ) + text(
        x + width // 2,
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
    definitions = """
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#f8fbff"/>
        <stop offset="100%" stop-color="#eef4fb"/>
      </linearGradient>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3"
              orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#52647a"/>
      </marker>
    </defs>
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        f"<title>{escape(title_value)}</title>"
        f"<desc>{escape(description)}</desc>{definitions}"
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>' + "".join(body) + "</svg>\n"
    )


def process_package_data_model() -> str:
    body = header(
        "Universal process-package data model",
        "A connected engineering object graph — not a pile of independent documents",
        1200,
    )
    body += [
        rect(470, 165, 260, 88, fill="#eff6ff", stroke="#93c5fd", radius=22),
        text(600, 202, "Design basis", size=23, weight=780, anchor="middle"),
        text(
            600, 230, "scope · capacity · components · limits", size=14, fill=MUTED, anchor="middle"
        ),
    ]
    nodes = [
        (70, 300, 190, "Streams", "composition · T/P · enthalpy", CYAN),
        (290, 300, 190, "Equipment", "type · duty · envelope", PURPLE),
        (510, 300, 190, "Balances", "mass · component · energy", BLUE),
        (730, 300, 190, "Control", "loops · alarms · interlocks", AMBER),
        (950, 300, 180, "HSE", "hazards · safeguards · relief", RED),
    ]
    for x, y, width, title_value, subtitle, color in nodes:
        body += [
            rect(x, y, width, 120, fill=WHITE, stroke=f"{color}66", radius=20),
            rect(x, y, width, 12, fill=color, stroke=color, radius=6),
            text(x + width // 2, y + 52, title_value, size=19, weight=760, anchor="middle"),
            text(x + width // 2, y + 84, subtitle, size=13, fill=MUTED, anchor="middle"),
            line(600, 253, x + width // 2, y, stroke="#8294aa", marker=True),
        ]
    body += [
        rect(170, 490, 360, 96, fill="#f0fdfa", stroke="#5eead4", radius=22),
        text(350, 529, "Evidence ledger", size=21, weight=780, fill=TEAL, anchor="middle"),
        text(
            350,
            560,
            "source · condition · claim · uncertainty",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        rect(670, 490, 360, 96, fill="#f0fdf4", stroke="#86efac", radius=22),
        text(850, 529, "Acceptance & approvals", size=21, weight=780, fill=GREEN, anchor="middle"),
        text(
            850,
            560,
            "criterion · evidence ID · role · decision",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
        line(530, 538, 670, 538, stroke="#8294aa", marker=True),
        line(600, 420, 350, 490, stroke="#8294aa", marker=True),
        line(600, 420, 850, 490, stroke="#8294aa", marker=True),
    ]
    return wrap(
        "Universal process-package data model",
        "Connected objects used by the universal process-package validator.",
        body,
    )


def epdm_catalyst_kinetics_network() -> str:
    body = header(
        "EPDM catalyst-to-architecture network",
        "Catalyst identity matters only through evidenced active sites and measurable chain outcomes",
        1200,
    )
    catalysts = [
        (90, "Vanadium benchmark", BLUE),
        (355, "Ziegler–Natta", CYAN),
        (620, "Metallocene", PURPLE),
        (885, "Other qualified family", SLATE),
    ]
    for x, label, color in catalysts:
        body += [
            rect(x, 170, 225, 74, fill=WHITE, stroke=f"{color}66", radius=18),
            circle(x + 34, 207, 15, fill=color, stroke=color, stroke_width=0),
            text(x + 62, 214, label, size=16, weight=720),
            line(x + 112, 244, 600, 305, stroke="#8294aa", marker=True),
        ]
    body += [
        rect(430, 305, 340, 92, fill="#eff6ff", stroke="#93c5fd", radius=24),
        text(600, 342, "Evidenced active-site population", size=22, weight=800, anchor="middle"),
        text(
            600,
            372,
            "site fraction · activity · poison sensitivity",
            size=15,
            fill=MUTED,
            anchor="middle",
        ),
    ]
    reactions = [
        (80, 455, "E insertion", BLUE),
        (270, 455, "P insertion", CYAN),
        (460, 455, "Diene insertion", PURPLE),
        (650, 455, "Chain transfer", AMBER),
        (840, 455, "Deactivation", RED),
    ]
    for x, y, label, color in reactions:
        body += [
            rect(x, y, 160, 70, fill=WHITE, stroke=f"{color}66", radius=18),
            text(x + 80, y + 43, label, size=16, weight=730, anchor="middle"),
            line(600, 397, x + 80, y, stroke="#8294aa", marker=True),
        ]
    body += [
        rect(205, 570, 790, 62, fill="#fff7ed", stroke="#fdba74", radius=20),
        text(
            600,
            608,
            "sequence · MWD/CCD · retained unsaturation · branching · gel risk",
            size=19,
            weight=760,
            fill=AMBER,
            anchor="middle",
        ),
        line(160, 525, 420, 570, stroke="#8294aa", marker=True),
        line(350, 525, 500, 570, stroke="#8294aa", marker=True),
        line(540, 525, 580, 570, stroke="#8294aa", marker=True),
        line(730, 525, 680, 570, stroke="#8294aa", marker=True),
        line(920, 525, 780, 570, stroke="#8294aa", marker=True),
    ]
    return wrap(
        "EPDM catalyst-to-architecture network",
        "EPDM catalyst, active-site, reaction and architecture relationships.",
        body,
    )


def epdm_reactor_mode_map() -> str:
    body = header(
        "EPDM reactor-mode decision map",
        "Select model topology from the operating mode, mixing regime, data density and decision risk",
        1200,
    )
    modes = [
        (70, "Batch", "initial inventory\ntime trajectory", BLUE),
        (345, "Semibatch", "scheduled feed\nmaterial-energy step", CYAN),
        (620, "Continuous CSTR", "steady inventory\nresidence-time closure", PURPLE),
        (895, "Reactor cascade", "stage composition\ngrade transition", AMBER),
    ]
    for x, title_value, subtitle, color in modes:
        body += [
            rect(x, 175, 235, 150, fill=WHITE, stroke=f"{color}66", radius=24),
            circle(x + 118, 220, 28, fill=color),
            text(x + 118, 273, title_value, size=20, weight=780, anchor="middle"),
        ]
        for index, item in enumerate(subtitle.split("\n")):
            body.append(text(x + 118, 301 + 22 * index, item, size=14, fill=MUTED, anchor="middle"))
    body += [
        line(188, 325, 188, 395, stroke="#8294aa", marker=True),
        line(463, 325, 463, 395, stroke="#8294aa", marker=True),
        line(738, 325, 738, 395, stroke="#8294aa", marker=True),
        line(1013, 325, 1013, 395, stroke="#8294aa", marker=True),
    ]
    levels = [
        (65, 400, 330, "Level 1 — screening", "constant-site rates · rapid ranking", BLUE),
        (435, 400, 330, "Level 2 — engineering", "Arrhenius · balances · heat/mixing", AMBER),
        (
            805,
            400,
            330,
            "Level 3 — detailed reference",
            "site families · moments · phase/gel",
            PURPLE,
        ),
    ]
    for x, y, width, title_value, subtitle, color in levels:
        body += [
            rect(x, y, width, 100, fill=WHITE, stroke=f"{color}66", radius=22),
            text(
                x + width // 2,
                y + 42,
                title_value,
                size=19,
                weight=780,
                fill=color,
                anchor="middle",
            ),
            text(x + width // 2, y + 72, subtitle, size=14, fill=MUTED, anchor="middle"),
        ]
    body += [
        rect(170, 550, 860, 70, fill="#fff1f2", stroke="#fda4af", radius=20),
        text(600, 579, "Promotion rule", size=18, weight=800, fill=RED, anchor="middle"),
        text(
            600,
            605,
            "Higher fidelity requires identifiable parameters, qualified data and a decision benefit",
            size=15,
            weight=560,
            anchor="middle",
        ),
    ]
    return wrap(
        "EPDM reactor-mode decision map",
        "Mapping of EPDM reactor modes to model fidelity levels.",
        body,
    )


def recovery_recycle_risk_loop() -> str:
    body = header(
        "EPDM recovery, recycle and impurity-risk loop",
        "A recycle stream is acceptable only when volatile closure, poison memory and purge are finite",
        1200,
    )
    units = [
        (70, 265, 180, "Reactor effluent", PURPLE),
        (300, 265, 180, "Quench / deash", AMBER),
        (530, 265, 180, "Devolatilization", RED),
        (760, 265, 180, "Recovery", CYAN),
        (990, 265, 150, "Product", GREEN),
    ]
    for index, (x, y, width, label, color) in enumerate(units):
        body += [
            rect(x, y, width, 92, fill=WHITE, stroke=f"{color}66", radius=20),
            rect(x, y, width, 10, fill=color, stroke=color, radius=5),
            text(x + width // 2, y + 55, label, size=17, weight=750, anchor="middle"),
        ]
        if index < len(units) - 1:
            next_x = units[index + 1][0]
            body.append(line(x + width, y + 46, next_x, y + 46, stroke="#8294aa", marker=True))
    body += [
        rect(610, 445, 250, 90, fill="#ecfeff", stroke="#67e8f9", radius=20),
        text(735, 480, "Guard bed + purge", size=19, weight=780, fill=CYAN, anchor="middle"),
        text(735, 508, "removal · purge fraction · limit", size=14, fill=MUTED, anchor="middle"),
        line(850, 357, 735, 445, stroke="#8294aa", marker=True),
        line(610, 490, 180, 357, stroke=CYAN, dash="9 7", marker=True),
        pill(80, 555, 210, "finite poison steady state", RED),
        pill(315, 555, 210, "non-equilibrium devol", PURPLE),
        pill(550, 555, 210, "solvent/monomer closure", CYAN),
        pill(785, 555, 210, "emissions & purge", AMBER),
    ]
    body += [
        circle(735, 205, 43, fill=RED),
        text(735, 201, "HOLD", size=17, weight=820, fill=WHITE, anchor="middle"),
        text(735, 224, "if unclosed", size=12, weight=650, fill=WHITE, anchor="middle"),
        line(735, 248, 735, 265, stroke=RED, marker=True),
    ]
    return wrap(
        "EPDM recovery, recycle and impurity-risk loop",
        "EPDM recovery and recycle loop with fail-closed impurity controls.",
        body,
    )


EXTRA_ASSETS = {
    "process-package-data-model.svg": process_package_data_model,
    "epdm-catalyst-kinetics-network.svg": epdm_catalyst_kinetics_network,
    "epdm-reactor-mode-map.svg": epdm_reactor_mode_map,
    "recovery-recycle-risk-loop.svg": recovery_recycle_risk_loop,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, builder in EXTRA_ASSETS.items():
        (OUT / filename).write_text(builder(), encoding="utf-8", newline="\n")
    print(f"generated {len(EXTRA_ASSETS)} extended README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
