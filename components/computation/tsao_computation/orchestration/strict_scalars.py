from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, cast

from ..errors import ContractError
from ..uncertainty import combine_independent
from ..validation import convergence_check


def _invoke_convergence(payload: Mapping[str, Any]) -> object:
    result = convergence_check(**dict(payload))
    delta = result.get("delta")
    if isinstance(delta, float) and not math.isfinite(delta):
        return {
            **result,
            "delta": None,
            "reason": "invalid-or-insufficient-convergence-data",
        }
    return result


def _invoke_uncertainty(payload: Mapping[str, Any]) -> object:
    components = payload.get("components")
    if isinstance(components, (str, bytes)) or not isinstance(components, (list, tuple)):
        raise ContractError("components must be an array of finite non-negative numbers")
    values = cast(tuple[float, ...], tuple(components))
    return {"combined": combine_independent(*values)}


def install_strict_scalar_invocations() -> None:
    """Replace scalar-sensitive trusted callables with fail-closed implementations."""

    from . import planner

    replacements = {
        "convergence-check": _invoke_convergence,
        "combine-independent-uncertainty": _invoke_uncertainty,
    }
    for slug, implementation in replacements.items():
        name, _, required_inputs = planner._TRUSTED_CALLABLES[slug]
        planner._TRUSTED_CALLABLES[slug] = (name, implementation, required_inputs)
