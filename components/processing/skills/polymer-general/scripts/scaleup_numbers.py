#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math


def positive(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def _complete(values: dict[str, float | None], names: tuple[str, ...]) -> bool:
    return all(values.get(name) is not None for name in names)


def calculate(**values: float | None) -> dict[str, float | str]:
    clean = {name: positive(value, name) for name, value in values.items()}
    out: dict[str, float | str] = {}

    reynolds = ("rho", "mu", "velocity", "length")
    prandtl = ("cp", "mu", "k")
    schmidt = ("mu", "rho", "diffusivity")
    damkohler = ("reaction_time", "mixing_time")

    if _complete(clean, reynolds):
        out["Re"] = clean["rho"] * clean["velocity"] * clean["length"] / clean["mu"]  # type: ignore[operator]
    if _complete(clean, prandtl):
        out["Pr"] = clean["cp"] * clean["mu"] / clean["k"]  # type: ignore[operator]
    if _complete(clean, schmidt):
        out["Sc"] = clean["mu"] / (clean["rho"] * clean["diffusivity"])  # type: ignore[operator]
    if _complete(clean, damkohler):
        out["Da_mixing"] = clean["mixing_time"] / clean["reaction_time"]  # type: ignore[operator]

    if not out:
        raise ValueError(
            "insufficient inputs: provide a complete Re, Pr, Sc or Da_mixing parameter set"
        )

    out["warning"] = (
        "Definitions and characteristic scales are process-specific; "
        "expert review is required before design use."
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "rho",
        "mu",
        "velocity",
        "length",
        "cp",
        "k",
        "diffusivity",
        "reaction_time",
        "mixing_time",
    ):
        parser.add_argument(f"--{name}", type=float)
    args = parser.parse_args(argv)
    try:
        out = calculate(**vars(args))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
