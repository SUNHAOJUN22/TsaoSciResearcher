#!/usr/bin/env python3
"""Compatibility CLI for the canonical public-distribution policy.

All parsing, classification and decision semantics live in
``tsao.distribution_policy``.  Keeping this file as a thin wrapper preserves the
historic script entry point without maintaining a second policy engine.
"""

from __future__ import annotations

from tsao.distribution_policy import (
    BLOCKED_STATUS,
    SCHEMA_VERSION,
    PolicyContractError,
    evaluate_public_distribution,
    public_distribution_policy_main,
)

evaluate = evaluate_public_distribution
main = public_distribution_policy_main

__all__ = [
    "BLOCKED_STATUS",
    "SCHEMA_VERSION",
    "PolicyContractError",
    "evaluate",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
