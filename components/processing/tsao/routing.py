from __future__ import annotations

import re

ROUTES: dict[str, set[str]] = {
    "epdm": {
        "epdm",
        "epr",
        "ethylene propylene diene",
        "乙丙橡胶",
        "三元乙丙",
        "enb",
        "dcpd",
        "vnb",
    },
    "poe": {
        "poe",
        "polyolefin elastomer",
        "聚烯烃弹性体",
        "乙烯辛烯",
        "solution polyolefin elastomer",
    },
    "polymer-general": {
        "polymer",
        "polymerization",
        "聚合",
        "树脂",
        "橡胶",
        "分子量",
        "催化剂",
    },
    "bioprocess": {"fermentation", "bioreactor", "发酵", "enzyme", "cell culture"},
    "electrochemical": {
        "electrolysis",
        "battery",
        "fuel cell",
        "电化学",
        "电解",
        "电池",
    },
    "solids": {"crystallization", "precipitation", "powder", "结晶", "沉淀", "粉体"},
    "fine-chemical-batch": {
        "batch",
        "fine chemical",
        "pharmaceutical",
        "批式",
        "精细化工",
        "医药",
    },
    "petrochemical": {
        "refinery",
        "petrochemical",
        "olefin",
        "石化",
        "炼化",
        "裂解",
    },
}


def route(text: str) -> list[tuple[str, float]]:
    if not isinstance(text, str):
        raise TypeError("route text must be a string")
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    scores: list[tuple[str, float]] = []
    for name, terms in ROUTES.items():
        hits = sum(1 for term in terms if _term_present(normalized, term.casefold()))
        scores.append((name, hits / len(terms)))
    selected = sorted(
        (item for item in scores if item[1] > 0),
        key=lambda item: (-item[1], item[0]),
    )
    return selected or [("generic-process", 0.0)]


def _term_present(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9][a-z0-9 -]*", term):
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return term in text
