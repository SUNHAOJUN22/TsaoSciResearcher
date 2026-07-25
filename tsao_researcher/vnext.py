"""Compatibility facade for the v2 runtime API."""

from __future__ import annotations

from .capsule import export_capsule, verify_capsule
from .handoff import create_handoff as handoff
from .receipts import record_receipt, verify_receipts
from .router import route
from .state import initialize as init
from .state import transition, verify

__all__ = [
    "export_capsule",
    "handoff",
    "init",
    "record_receipt",
    "route",
    "transition",
    "verify",
    "verify_capsule",
    "verify_receipts",
]
