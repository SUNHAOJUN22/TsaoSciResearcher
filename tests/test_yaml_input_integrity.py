"""YAML input must preserve the same integrity boundary as JSON input."""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.common import load_data
from tsao_researcher.state import initialize, load_project, verify

ROOT = Path(__file__).resolve().parents[1]


def _read(consumer: str, project: Path) -> Any:
    if consumer == "script-yaml":
        return load_data(project / "project.yaml")
    if consumer == "project-load":
        return load_project(project)
    return verify(project)


@pytest.mark.parametrize("consumer", ["script-yaml", "project-load", "project-verify"])
@pytest.mark.parametrize(
    "prefix",
    [
        "status: accepted\n",
        "measurement: {value: 1, value: 2}\n",
        "measurement: [{unit: Pa, unit: MPa}]\n",
        "measurement: {<<: {value: 1, value: 2}}\n",
        "measurement: {<<: {value: 1}, <<: {value: 2}}\n",
        "measurement: 1.0e-400\n",
        "measurement: -1.0e-400\n",
        "measurement: 2.0e-324\n",
        "measurement: 1.0e+400\n",
        "measurement: .nan\n",
        "measurement: .inf\n",
        "measurement: -.inf\n",
    ],
)
def test_public_yaml_consumers_reject_ambiguous_or_unrepresentable_values(
    tmp_path: Path, consumer: str, prefix: str
) -> None:
    project = initialize("yaml integrity", "Which evidence is valid?", tmp_path)
    path = project / "project.yaml"
    original = path.read_text(encoding="utf-8")
    path.write_text(prefix + original, encoding="utf-8")
    with pytest.raises(ValueError, match=r"duplicate|underflow|non-finite"):
        _read(consumer, project)
    assert path.read_text(encoding="utf-8") == prefix + original


@pytest.mark.parametrize("consumer", ["script-yaml", "project-load"])
@pytest.mark.parametrize("token", ["0.0e-9999", "-0.0e-9999", "5.0e-324", "-5.0e-324", "1.0e+300"])
def test_yaml_readers_preserve_representable_floats(tmp_path: Path, consumer: str, token: str) -> None:
    project = initialize("yaml values", "Which values are preserved?", tmp_path)
    path = project / "project.yaml"
    path.write_text("measurement: " + token + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    value = _read(consumer, project)["measurement"]
    assert type(value) is float
    assert value == float(token)
    assert math.copysign(1.0, value) == math.copysign(1.0, float(token))


def test_yaml_reader_preserves_strings_large_integers_aliases_and_merge_overrides(tmp_path: Path) -> None:
    path = tmp_path / "valid.yaml"
    path.write_text(
        'base: &base {unit: Pa, value: 2, text: "1.0e-400"}\n'
        "measurement: {<<: *base, value: 9007199254740993}\n"
        "first: &first {unit: K}\n"
        "second: &second {unit: Pa, value: 3}\n"
        "priority: {<<: [*first, *second]}\n"
        "same_scope_is_separate: {value: 4}\n"
        "quoted_nonfinite: '.nan'\n",
        encoding="utf-8",
    )
    value = load_data(path)
    assert value["measurement"] == {"unit": "Pa", "value": 9007199254740993, "text": "1.0e-400"}
    assert type(value["measurement"]["value"]) is int
    assert value["priority"] == {"unit": "K", "value": 3}
    assert value["quoted_nonfinite"] == ".nan"


def test_yaml_value_keys_and_malformed_inputs_keep_safe_loader_behavior(tmp_path: Path) -> None:
    path = tmp_path / "value.yaml"
    path.write_text("=: 1\n", encoding="utf-8")
    assert load_data(path) == {"=": 1}
    for text in ("x: [\n", "[a, b]: 1\n", "x: !!python/object:builtins.object {}\n"):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match="YAML"):
            load_data(path)


@pytest.mark.parametrize("script", ["validate_project.py", "validate_figure.py"])
def test_actual_yaml_validation_cli_rejects_duplicate_contract_keys(tmp_path: Path, script: str) -> None:
    if script == "validate_project.py":
        project = initialize("yaml cli", "Which project is valid?", tmp_path)
        path = project / "project.yaml"
        path.write_text("status: accepted\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        path = tmp_path / "figure.yaml"
        data = load_data(ROOT / "examples/figure-contract.json")
        path.write_text("title: Ambiguous title\n" + yaml.safe_dump(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/" + script, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout
    assert "duplicate" in result.stderr
