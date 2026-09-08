from __future__ import annotations

import argparse
import os
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

_COVERAGE_MINIMUM = 95.0


def coverage_json_path() -> Path:
    configured = os.environ.get("TSAO_COVERAGE_JSON")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "tsao-current-coverage.json"


def _write_coverage_evidence(output: Path) -> int:
    # Coverage is an optional validation dependency and remains lazily imported so
    # ordinary non-coverage test runs preserve the zero-runtime-dependency contract.
    from coverage import Coverage

    output.parent.mkdir(parents=True, exist_ok=True)
    coverage = Coverage()
    coverage.load()
    total = float(coverage.json_report(outfile=str(output)))
    print(f"Total coverage: {total:.2f}% (required: {_COVERAGE_MINIMUM:.2f}%)")
    if total < _COVERAGE_MINIMUM:
        print(
            f"Coverage failure: total of {total:.2f}% is below {_COVERAGE_MINIMUM:.2f}%",
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--marker")
    args = parser.parse_args()

    pytest_command = [sys.executable, "-m", "pytest", "-vv" if args.verbose else "-q"]
    if args.marker:
        pytest_command.extend(["-m", args.marker])
    if not args.coverage:
        return subprocess.run(pytest_command, check=False).returncode  # nosec B603

    coverage_command = [sys.executable, "-m", "coverage", "run", "--branch", "-m", "pytest", "-q"]
    if args.marker:
        coverage_command.extend(["-m", args.marker])
    result = subprocess.run(coverage_command, check=False)  # nosec B603
    if result.returncode != 0:
        return result.returncode

    return _write_coverage_evidence(coverage_json_path())


if __name__ == "__main__":
    raise SystemExit(main())
