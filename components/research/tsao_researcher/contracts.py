"""Dependency-light shared runtime contracts."""

from __future__ import annotations

RESEARCH_TYPES = frozenset(
    {"descriptive", "explanatory", "predictive", "causal", "design", "mechanistic", "mixed"}
)
