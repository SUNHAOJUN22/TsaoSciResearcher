"""Compatibility facade for the v2 runtime API."""

from __future__ import annotations

from .handoff import create_handoff as handoff
from .router import route
from .state import initialize as init
from .state import transition, verify

__all__ = ["handoff", "init", "route", "transition", "verify"]
