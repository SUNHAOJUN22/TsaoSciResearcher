from __future__ import annotations

import json

import _bootstrap  # noqa: F401
from tsao_computation.adapters import get_adapter


def main() -> int:
    size = 50 * 1024 * 1024
    prefix = "normal termination; converged\n"
    suffix = "\nfailed to converge"
    payload = prefix + ("x" * (size - len(prefix) - len(suffix))) + suffix
    parsed = get_adapter("orca").parse(payload)
    passed = (
        parsed["completed"] is True
        and parsed["converged"] is False
        and parsed["raw_length"] == size
    )
    report = {
        "schema_version": "1.0",
        "input_bytes": size,
        "completed": parsed["completed"],
        "converged": parsed["converged"],
        "raw_length": parsed["raw_length"],
        "passed": passed,
        "claim_boundary": (
            "Synthetic parser regression only; no external solver execution or throughput claim."
        ),
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
