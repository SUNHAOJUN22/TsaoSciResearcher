"""TsaoSciResearcher runtime package with a lightweight top-level import."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .version import __version__

_LAZY_EXPORTS = {
    "advise_computation_strategy": (".strategy", "advise_computation_strategy"),
    "create_handoff": (".handoff", "create_handoff"),
    "export_capsule": (".capsule", "export_capsule"),
    "initialize": (".state", "initialize"),
    "load_capabilities": (".capabilities", "load_capabilities"),
    "record_receipt": (".receipts", "record_receipt"),
    "route": (".router", "route"),
    "search_capabilities": (".capabilities", "search_capabilities"),
    "transition": (".state", "transition"),
    "verify": (".state", "verify"),
    "verify_capsule": (".capsule", "verify_capsule"),
    "verify_receipts": (".receipts", "verify_receipts"),
}

__all__ = ["__version__", *_LAZY_EXPORTS]


def __getattr__(name: str) -> Any:
    """Resolve public runtime functions on first access and cache the result."""

    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
