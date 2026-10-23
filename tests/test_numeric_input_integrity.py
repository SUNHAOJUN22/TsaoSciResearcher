"""Public readers must not erase nonzero data or exact integer distinctions."""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import common
from tsao_researcher import io
from tsao_researcher.scientific_contracts_v16 import ContractError, compare_quantities

ROOT = Path(__file__).resolve().parents[1]
READERS = ("runtime-json", "runtime-jsonl", "script-json", "script-jsonl")


def _read(name: str, path: Path) -> Any:
    readers = {
        "runtime-json": io.load_json,
        "runtime-jsonl": io.read_jsonl,
        "script-json": common.load_data,
        "script-jsonl": common.read_jsonl,
    }
    return readers[name](path)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("token", ["1e-400", "-1e-400", "0.0001e-999", "-12.5E-999", "2e-324"])
def test_public_json_readers_reject_nonzero_underflow(tmp_path: Path, reader: str, token: str) -> None:
    path = tmp_path / "measurement.json"
    path.write_text('{"measurement": {"values": [' + token + "]}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="underflow"):
        _read(reader, path)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("token", ["0e-9999", "-0.000E-9999", "5e-324", "-5e-324", "1e-300"])
def test_public_json_readers_preserve_zero_and_subnormal_values(
    tmp_path: Path, reader: str, token: str
) -> None:
    path = tmp_path / "measurement.json"
    path.write_text('{"value":' + token + ',"count":9007199254740993}\n', encoding="utf-8")
    decoded = _read(reader, path)
    item = decoded[0] if reader.endswith("jsonl") else decoded
    assert item["value"] == float(token)
    assert math.copysign(1.0, item["value"]) == math.copysign(1.0, float(token))
    assert type(item["count"]) is int and item["count"] == 9007199254740993


@pytest.mark.parametrize(
    "suffix",
    [
        ',"kind":"causality-guard"}',
        ',"measurement":{"value":1e-400}}',
        ',"measurement":{"value":-1e-400}}',
        ',"measurement":{"value":1e999}}',
        ',"measurement":{"value":NaN}}',
    ],
)
def test_actual_quality_cli_rejects_ambiguous_or_unrepresentable_json(tmp_path: Path, suffix: str) -> None:
    request = tmp_path / "quality-request.json"
    valid = (ROOT / "examples/scientific-quality-check.json").read_text(encoding="utf-8").rstrip()
    request.write_text(valid[:-1] + suffix, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "tsao_researcher", "quality", str(request)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, result.stdout
    assert '"status": "PASS"' not in result.stdout
    assert any(term in result.stderr for term in ("duplicate", "non-finite", "underflow"))


@pytest.mark.parametrize("value", [2**53, 10**30])
@pytest.mark.parametrize("unit", ["Pa", "kPa", "MPa", "bar", "K"])
def test_quantity_comparison_preserves_distinct_large_integer_values(value: int, unit: str) -> None:
    assert not compare_quantities(value, unit, "==", value + 1, unit)
    assert compare_quantities(value, unit, "<", value + 1, unit)
    assert compare_quantities(value + 1, unit, ">", value, unit)


def test_quantity_comparison_preserves_exact_cross_unit_integers() -> None:
    value = 2**53 + 1
    assert compare_quantities(value, "bar", "==", value * 100000, "Pa")
    assert not compare_quantities(value, "bar", "==", value * 100000 + 1, "Pa")
    assert compare_quantities(0.1, "MPa", "==", 100, "kPa")
    assert not compare_quantities(2**53 + 1, "Pa", "==", float(2**53), "Pa")


def test_integer_conversion_still_rejects_values_beyond_finite_numeric_range() -> None:
    with pytest.raises(ContractError, match="finite numeric range"):
        compare_quantities(10**308, "MPa", ">", 0, "Pa")
