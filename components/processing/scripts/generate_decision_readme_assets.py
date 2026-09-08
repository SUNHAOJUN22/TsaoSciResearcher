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
    size: int = 18,
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
    width: int,
    height: int,
    *,
    fill: str = WHITE,
    stroke: str = "#d7e0ea",
    radius: int = 18,
    stroke_width: int = 2,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
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
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round"{extra}{marker_end}/>'
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
        f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def header(title_value: str, subtitle: str, width: int = 1200) -> list[str]:
    return [
        text(54, 68, title_value, size=34, weight=760),
        text(54, 102, subtitle, size=17, fill=MUTED),
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
        <stop offset="0%" stop-color="#f8fbff"/><stop offset="100%" stop-color="#eef4fb"/>
      </linearGradient>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3"
              orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#52647a"/>
      </marker>
    </defs>
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f"<title>{escape(title_value)}</title><desc>{escape(description)}</desc>"
        f"{definitions}"
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>' + "".join(body) + "</svg>\n"
    )


def control_safety_chain() -> str:
    body = header(
        "Control, interlock and process-safety chain",
        "Normal control and independent protection remain connected but explicitly separated",
    )
    stages = [
        (55, "Measurement", "sensor · analyzer\nmeasurement boundary", BLUE),
        (250, "Regulatory\ncontrol", "PID · cascade\nconstraint control", CYAN),
        (445, "Alarm &\noperator", "priority · response\nabnormal procedure", AMBER),
        (640, "Interlock / SIS", "trip · permissive\nindependent function", RED),
        (835, "Relief &\ncontainment", "relief · flare\nsecondary containment", PURPLE),
        (1030, "Evidence Gate", "test · approval\nMOC · learning", GREEN),
    ]
    for index, (x, title_value, details, color) in enumerate(stages):
        body.extend(
            [
                rect(x, 190, 155, 250, stroke=f"{color}66", radius=22),
                circle(x + 77, 245, 32, fill=color),
            ]
        )
        title_lines = title_value.split("\n")
        for title_index, title_line in enumerate(title_lines):
            body.append(
                text(
                    x + 77,
                    302 + 22 * title_index,
                    title_line,
                    size=15,
                    weight=760,
                    anchor="middle",
                )
            )
        detail_start = 360 if len(title_lines) == 1 else 370
        for item_index, item in enumerate(details.split("\n")):
            body.append(
                text(
                    x + 77,
                    detail_start + 30 * item_index,
                    item,
                    size=13,
                    fill=MUTED,
                    anchor="middle",
                )
            )
        if index < len(stages) - 1:
            body.append(line(x + 155, 315, x + 195, 315, marker=True, stroke="#8394aa"))
    body.extend(
        [
            rect(135, 500, 930, 95, fill="#fff7ed", stroke="#fdba74", radius=22),
            text(
                600,
                537,
                "HAZID → HAZOP → LOPA → SIL interface",
                size=22,
                weight=780,
                fill=AMBER,
                anchor="middle",
            ),
            text(
                600,
                570,
                "Software structures evidence and actions; qualified teams own the safety decision",
                size=16,
                fill=INK,
                anchor="middle",
            ),
        ]
    )
    return wrap(
        "Control and safety chain",
        "Relationship among measurement, control, alarms, interlocks, relief and evidence gates.",
        body,
    )


def simulator_integration() -> str:
    body = header(
        "Simulator-neutral integration contract",
        "One governed design basis can feed multiple tools without allowing a simulator default to become evidence",
    )
    body.extend(
        [
            rect(60, 185, 230, 310, stroke="#60a5fa", radius=24),
            text(175, 230, "Governed inputs", size=23, weight=780, anchor="middle"),
            text(175, 275, "design basis", size=16, anchor="middle"),
            text(175, 310, "stream / equipment IDs", size=16, anchor="middle"),
            text(175, 345, "property-method basis", size=16, anchor="middle"),
            text(175, 380, "parameter provenance", size=16, anchor="middle"),
            text(175, 415, "model passport", size=16, anchor="middle"),
            rect(910, 185, 230, 310, stroke="#86efac", radius=24),
            text(1025, 230, "Qualified outputs", size=23, weight=780, anchor="middle"),
            text(1025, 275, "balances / residuals", size=16, anchor="middle"),
            text(1025, 310, "method applicability", size=16, anchor="middle"),
            text(1025, 345, "uncertainty / conflicts", size=16, anchor="middle"),
            text(1025, 380, "HOLD / PASS state", size=16, anchor="middle"),
            text(1025, 415, "named approval", size=16, anchor="middle"),
        ]
    )
    tools = [
        (390, 190, "Aspen Plus", BLUE),
        (610, 190, "Aspen HYSYS", CYAN),
        (390, 330, "DWSIM", TEAL),
        (610, 330, "Python / custom", PURPLE),
        (500, 470, "DCS / PLC exchange", AMBER),
    ]
    for x, y, label, color in tools:
        body.extend(
            [
                rect(x, y, 190, 92, stroke=f"{color}77", radius=20),
                text(
                    x + 95,
                    y + 55,
                    label,
                    size=18,
                    weight=740,
                    fill=color,
                    anchor="middle",
                ),
            ]
        )
        body.append(line(290, 340, x, y + 46, marker=True, stroke="#8394aa"))
        body.append(line(x + 190, y + 46, 910, 340, marker=True, stroke="#8394aa"))
    body.extend(
        [
            rect(260, 585, 680, 52, fill="#fff1f2", stroke="#fda4af", radius=18),
            text(
                600,
                618,
                "Simulator convergence is not scientific or engineering qualification",
                size=17,
                weight=700,
                fill=RED,
                anchor="middle",
            ),
        ]
    )
    return wrap(
        "Simulator-neutral integration",
        "Governed inputs and qualified outputs around multiple process and automation tools.",
        body,
        height=670,
    )


def epdm_identifiability() -> str:
    body = header(
        "EPDM parameter identifiability and uncertainty ladder",
        "Model fidelity advances only when the experiment can distinguish the parameters that drive the decision",
    )
    stages = [
        (75, "Data boundary", "conditions · units\nsite basis · covariance", BLUE),
        (295, "Sensitivity", "local / global\nobservable response", CYAN),
        (515, "Identifiability", "rank · correlation\nprofile likelihood", PURPLE),
        (735, "Uncertainty", "parameter / prediction\nscenario propagation", AMBER),
        (955, "Decision Gate", "experiment · model\nscale-up / HOLD", GREEN),
    ]
    for index, (x, title_value, detail, color) in enumerate(stages):
        body.extend(
            [
                rect(x, 190, 180, 265, stroke=f"{color}66", radius=24),
                circle(x + 90, 245, 34, fill=color),
                text(x + 90, 315, title_value, size=19, weight=770, anchor="middle"),
            ]
        )
        for detail_index, item in enumerate(detail.split("\n")):
            body.append(
                text(
                    x + 90,
                    360 + 31 * detail_index,
                    item,
                    size=15,
                    fill=MUTED,
                    anchor="middle",
                )
            )
        if index < len(stages) - 1:
            body.append(line(x + 180, 323, x + 220, 323, marker=True, stroke="#8394aa"))
    body.extend(
        [
            rect(115, 505, 970, 98, fill="#eef2ff", stroke="#c4b5fd", radius=22),
            text(
                600,
                542,
                "Parameter classes",
                size=20,
                weight=780,
                fill=PURPLE,
                anchor="middle",
            ),
            text(
                600,
                575,
                "measured · estimated · literature prior · nuisance · structurally fixed · not identifiable",
                size=16,
                anchor="middle",
            ),
        ]
    )
    return wrap(
        "EPDM identifiability and uncertainty",
        "Data, sensitivity, identifiability, uncertainty and decision gates for EPDM models.",
        body,
    )


def epdm_product_bridge() -> str:
    body = header(
        "EPDM raw-polymer-to-customer evidence bridge",
        "A reactor result becomes a product claim only through a controlled formulation and qualification chain",
    )
    stages = [
        (55, "Raw polymer", "composition · MWD\nMooney · gel", BLUE),
        (250, "Compound", "fixed recipe\nmixing history", CYAN),
        (445, "Cure", "rheometer\ncrosslink state", PURPLE),
        (640, "Part", "process window\nproperty durability", AMBER),
        (835, "Customer line", "trial conditions\ncapability / defects", RED),
        (1030, "Acceptance", "CQA evidence\nnamed approval", GREEN),
    ]
    for index, (x, title_value, detail, color) in enumerate(stages):
        body.extend(
            [
                rect(x, 190, 155, 260, stroke=f"{color}66", radius=22),
                circle(x + 77, 245, 31, fill=color),
                text(x + 77, 313, title_value, size=17, weight=760, anchor="middle"),
            ]
        )
        for detail_index, item in enumerate(detail.split("\n")):
            body.append(
                text(
                    x + 77,
                    360 + 31 * detail_index,
                    item,
                    size=14,
                    fill=MUTED,
                    anchor="middle",
                )
            )
        if index < len(stages) - 1:
            body.append(line(x + 155, 322, x + 195, 322, marker=True, stroke="#8394aa"))
    body.extend(
        [
            rect(150, 505, 900, 92, fill="#fff1f2", stroke="#fda4af", radius=22),
            text(
                600,
                541,
                "Causal guardrail",
                size=20,
                weight=800,
                fill=RED,
                anchor="middle",
            ),
            text(
                600,
                572,
                "No customer or durability claim may skip compound, cure, part and line evidence",
                size=16,
                anchor="middle",
            ),
        ]
    )
    return wrap(
        "EPDM product bridge",
        "Evidence chain from raw EPDM polymer through customer-line acceptance.",
        body,
    )


ASSETS = {
    "control-safety-cause-effect.svg": control_safety_chain,
    "simulation-integration-contract.svg": simulator_integration,
    "epdm-identifiability-uncertainty.svg": epdm_identifiability,
    "epdm-product-customer-bridge.svg": epdm_product_bridge,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, builder in ASSETS.items():
        (OUT / filename).write_text(builder(), encoding="utf-8", newline="\n")
    print(f"generated {len(ASSETS)} decision README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
