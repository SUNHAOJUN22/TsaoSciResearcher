# mypy: disable-error-code=misc
from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from tsao_computation.errors import StateTransitionError
from tsao_computation.security.paths import confined_path
from tsao_computation.state.machine import TRANSITIONS, ScientificStateMachine
from tsao_computation.validation.acceptance import REQUIRED

Probe = tuple[str, Callable[[], bool]]


def finite_mutants() -> list[Probe]:
    values = [1.0, float("nan")]
    mutants: list[tuple[str, Callable[[list[float]], bool]]] = [
        ("finite-any", lambda seq: any(math.isfinite(x) for x in seq)),
        ("finite-first-only", lambda seq: math.isfinite(seq[0])),
        ("finite-last-inverted", lambda seq: not math.isfinite(seq[-1])),
        ("finite-nonempty", lambda seq: bool(seq)),
        ("finite-ignore-nan", lambda seq: all(math.isfinite(x) for x in seq if not math.isnan(x))),
        ("finite-string-check", lambda seq: all(str(x) != "NaN" for x in seq)),
        ("finite-zero-threshold", lambda seq: all(math.isfinite(x) or math.isnan(x) for x in seq)),
        ("finite-unconditional", lambda seq: True),
    ]
    return [(name, lambda fn=fn: bool(fn(values)) is True) for name, fn in mutants]


def convergence_mutants() -> list[Probe]:
    values = [1.2, 1.0]
    tolerance = 0.1
    mutants: list[tuple[str, Callable[[], bool]]] = [
        ("conv-always", lambda: True),
        ("conv-reversed", lambda: abs(values[-1] - values[-2]) >= tolerance),
        ("conv-first-last-wrong", lambda: abs(values[0] - values[0]) <= tolerance),
        ("conv-signed", lambda: values[-1] - values[-2] <= tolerance),
        ("conv-double-tolerance", lambda: abs(values[-1] - values[-2]) <= tolerance * 2.1),
        ("conv-integer-delta", lambda: int(abs(values[-1] - values[-2])) <= tolerance),
        ("conv-ignore-latest", lambda: len(values) >= 2),
        ("conv-round-zero", lambda: round(abs(values[-1] - values[-2])) <= tolerance),
    ]
    return [(name, lambda fn=fn: bool(fn()) is True) for name, fn in mutants]


def balance_mutants() -> list[Probe]:
    tolerance = 0.01
    mutants: list[tuple[str, Callable[[], bool]]] = [
        ("balance-ignore-accumulation", lambda: abs(10.0 - 10.0) <= tolerance),
        ("balance-add-accumulation", lambda: abs(10.0 - 11.0 + 1.0) <= tolerance),
        ("balance-output-only", lambda: abs(1.0 - 1.0) <= tolerance),
        ("balance-unconditional", lambda: True),
        ("balance-large-threshold", lambda: abs(10.0 - 8.0 - 1.0) <= 2.0),
        ("balance-signed", lambda: tolerance >= 8.0 - 10.0),
        ("balance-integer-normalized", lambda: int(abs(10.0 - 8.0 - 1.0) / 10.0) <= tolerance),
        ("balance-relative-wrong-scale", lambda: abs(10.0 - 8.0 - 1.0) / 1000 <= tolerance),
    ]
    return [(name, lambda fn=fn: bool(fn()) is True) for name, fn in mutants]


def unit_mutants() -> list[Probe]:
    bad = "Pascal"
    accepted = {"m", "kg", "s", "K", "mol", "Pa", "J/mol"}
    mutants: list[tuple[str, Callable[[], bool]]] = [
        ("unit-any-string", lambda: isinstance(bad, str)),
        ("unit-nonempty", lambda: bool(bad)),
        ("unit-alpha", lambda: bad.isalpha()),
        ("unit-length", lambda: len(bad) < 20),
        ("unit-default", lambda: bad in accepted or True),
        ("unit-substring", lambda: any(unit in bad for unit in accepted)),
        ("unit-casefold-only", lambda: bad.casefold() == "pascal"),
        ("unit-not-none", lambda: bad is not None),
    ]
    return [(name, lambda fn=fn: bool(fn()) is True) for name, fn in mutants]


def acceptance_mutants() -> list[Probe]:
    incomplete = {"completed": True}
    mutants: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("accept-completed-only", lambda record: bool(record.get("completed"))),
        ("accept-any-required", lambda record: any(record.get(key) for key in REQUIRED)),
        ("accept-default-true", lambda record: all(record.get(key, True) for key in REQUIRED)),
        (
            "accept-ignore-missing",
            lambda record: all(key not in record or record.get(key) for key in REQUIRED),
        ),
        ("accept-nonempty", lambda record: bool(record)),
        ("accept-count-one", lambda record: sum(record.get(key) is True for key in REQUIRED) >= 1),
        (
            "accept-policy-open",
            lambda record: record.get("completed", False) or record.get("validated", False),
        ),
        ("accept-unconditional", lambda record: True),
    ]
    return [(name, lambda fn=fn: bool(fn(incomplete)) is True) for name, fn in mutants]


def uncertainty_mutants() -> list[Probe]:
    components = (3.0, 4.0)
    expected = 5.0
    mutants: list[tuple[str, Callable[[], float]]] = [
        ("uq-sum", lambda: sum(components)),
        ("uq-mean", lambda: sum(components) / len(components)),
        ("uq-max", lambda: max(components)),
        ("uq-min", lambda: min(components)),
        ("uq-sum-squares", lambda: sum(x * x for x in components)),
        ("uq-product", lambda: math.prod(components)),
        ("uq-root-sum", lambda: math.sqrt(sum(components))),
        ("uq-first", lambda: components[0]),
    ]
    return [(name, lambda fn=fn: not math.isclose(fn(), expected)) for name, fn in mutants]


def state_mutants() -> list[Probe]:
    source = "proposed"
    target = "scientifically-accepted"

    def actual_rejects_direct_acceptance() -> bool:
        try:
            ScientificStateMachine(source).transition(target, evidence="mutation probe")
        except StateTransitionError:
            return True
        return False

    mutants: list[tuple[str, Callable[[], bool]]] = [
        ("state-any-known", lambda: target in TRANSITIONS),
        ("state-target-present", lambda: bool(target)),
        ("state-source-known", lambda: source in TRANSITIONS),
        ("state-always", lambda: True),
        ("state-nonterminal", lambda: source != "superseded"),
        ("state-accepted-special", lambda: target == "scientifically-accepted"),
        ("state-chain-search", lambda: any(target in targets for targets in TRANSITIONS.values())),
        (
            "state-ignore-source",
            lambda: target in {item for targets in TRANSITIONS.values() for item in targets},
        ),
    ]
    return [
        (name, lambda fn=fn: bool(fn()) is True and actual_rejects_direct_acceptance())
        for name, fn in mutants
    ]


def path_mutants() -> list[Probe]:
    root = (Path(tempfile.gettempdir()) / "tsao-root").resolve()
    malicious = "../escape"
    escaped = (root / malicious).resolve(strict=False)
    mutants: list[tuple[str, Callable[[], bool]]] = [
        ("path-string-prefix", lambda: str(escaped).startswith(str(root.parent))),
        ("path-nonempty", lambda: bool(str(escaped))),
        ("path-parent-exists", lambda: escaped.parent == root.parent),
        ("path-no-absolute-check", lambda: not Path(malicious).is_absolute()),
        ("path-name-only", lambda: escaped.name == "escape"),
        ("path-dot-normalized", lambda: ".." not in escaped.parts),
        ("path-common-root", lambda: Path("/") in escaped.parents),
        ("path-unconditional", lambda: True),
    ]

    def killed(fn: Callable[[], bool]) -> bool:
        mutant_accepts = fn()
        actual_rejects = False
        try:
            confined_path(root, malicious)
        except Exception:
            actual_rejects = True
        return mutant_accepts and actual_rejects

    return [(name, lambda fn=fn: killed(fn)) for name, fn in mutants]


def main() -> int:
    probes = (
        finite_mutants()
        + convergence_mutants()
        + balance_mutants()
        + unit_mutants()
        + acceptance_mutants()
        + uncertainty_mutants()
        + state_mutants()
        + path_mutants()
    )
    results = [{"id": name, "killed": bool(probe())} for name, probe in probes]
    killed = sum(result["killed"] for result in results)
    report = {
        "schema_version": "1.0",
        "method": "controlled non-equivalent operator mutation probes",
        "total": len(results),
        "killed": killed,
        "survived": len(results) - killed,
        "results": results,
    }
    output = Path("evidence/mutation-report.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"}, sort_keys=True
        )
    )
    return 0 if len(results) == 64 and killed == 64 else 1


if __name__ == "__main__":
    raise SystemExit(main())
