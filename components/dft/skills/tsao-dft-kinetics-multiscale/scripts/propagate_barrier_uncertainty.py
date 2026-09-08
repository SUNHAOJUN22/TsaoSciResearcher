#!/usr/bin/env python3
"""Propagate a symmetric activation-free-energy bound into a TST rate interval."""

from __future__ import annotations

import argparse
import json

from tst_math import tst_rate_interval


def rate_unit(molecularity: int) -> str:
    if molecularity < 1:
        raise ValueError("molecularity must be a positive integer")
    if molecularity == 1:
        return "s^-1"
    if molecularity == 2:
        return "M^-1 s^-1 (standard-state convention required)"
    return f"concentration^({1 - molecularity}) s^-1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--barrier", type=float, required=True)
    parser.add_argument("--uncertainty", type=float, required=True)
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument("--kappa", type=float, default=1.0)
    parser.add_argument("--degeneracy", type=float, default=1.0)
    parser.add_argument("--molecularity", type=int, default=1)
    args = parser.parse_args()
    try:
        interval = tst_rate_interval(
            args.barrier,
            args.uncertainty,
            args.temperature,
            args.kappa,
            args.degeneracy,
        )
        unit = rate_unit(args.molecularity)
    except (ValueError, OverflowError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "barrier_kcal_mol": args.barrier,
                "uncertainty_kcal_mol": args.uncertainty,
                "temperature_K": args.temperature,
                **interval,
                "rate_unit": unit,
                "note": "Interval reflects only the declared barrier bound, not model/transport uncertainty.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
