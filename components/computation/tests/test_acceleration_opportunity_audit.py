from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsao_computation.accelerators import (
    acceleration_libraries,
    audit_repository_acceleration,
)
from tsao_computation.cli import main


def _write_fixture(root: Path) -> None:
    (root / "kernel.py").write_text(
        """import numpy as np
from scipy import sparse
import e3nn.o3 as o3


def solve(a):
    dense = np.linalg.solve(a, a[:, 0])
    spectrum = np.fft.fft(dense)
    contracted = np.einsum("ij,j->i", a, dense)
    sparse.linalg.spsolve(a, dense)
    o3.TensorProduct(None, None, None)
    for i in range(10):
        for j in range(10):
            contracted[i] += a[i, j] * dense[j] + i * j
    return spectrum, contracted
""",
        encoding="utf-8",
    )
    (root / "dispatch.py").write_text(
        """import subprocess
from pathlib import Path


def run(path):
    files = list(Path(path).rglob("*.dat"))
    return subprocess.run(["solver", str(files[0])], check=False)
""",
        encoding="utf-8",
    )
    (root / "native.cpp").write_text("int kernel() { return 0; }\n", encoding="utf-8")
    (root / "kernel.cu").write_text("__global__ void kernel() {}\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_hidden.py").write_text(
        "import numpy as np\nvalue = np.linalg.solve([[1.0]], [1.0])\n",
        encoding="utf-8",
    )


def test_audit_ranks_explicit_numerical_candidates_and_counts_languages(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    report = audit_repository_acceleration(tmp_path, min_score=40)
    categories = {item.category for item in report.opportunities}
    assert {
        "equivariant-ml",
        "tensor-contraction",
        "sparse-linear-algebra",
        "fft-spectral",
        "dense-linear-algebra",
        "numeric-python-loop",
        "external-solver-dispatch",
        "filesystem-scan",
    } <= categories
    assert dict(report.language_files) == {"cpp": 1, "cuda": 1, "python": 3}
    assert report.python_files_analyzed == 2
    assert report.python_files_excluded == 1
    assert report.parse_failures == ()
    assert report.opportunities == tuple(
        sorted(
            report.opportunities,
            key=lambda item: (-item.score, item.path, item.line, item.category, item.symbol),
        )
    )
    catalog = {item.slug for item in acceleration_libraries()}
    assert all(set(item.library_candidates) <= catalog for item in report.opportunities)


def test_audit_is_deterministic_and_test_inclusion_is_explicit(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    first = audit_repository_acceleration(tmp_path, limit=50).to_dict()
    second = audit_repository_acceleration(tmp_path, limit=50).to_dict()
    assert first == second
    assert not any(item["path"].startswith("tests/") for item in first["opportunities"])
    included = audit_repository_acceleration(tmp_path, include_tests=True, limit=50).to_dict()
    assert any(item["path"].startswith("tests/") for item in included["opportunities"])
    json.dumps(included, sort_keys=True, allow_nan=False)


def test_audit_records_parse_failures_and_validates_limits(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    report = audit_repository_acceleration(tmp_path)
    assert report.parse_failures == ("bad.py: SyntaxError",)
    with pytest.raises(ValueError, match="positive"):
        audit_repository_acceleration(tmp_path, limit=0)
    with pytest.raises(ValueError, match="between"):
        audit_repository_acceleration(tmp_path, min_score=101)
    with pytest.raises(ValueError, match="not a directory"):
        audit_repository_acceleration(tmp_path / "missing")


def test_cli_writes_machine_readable_audit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_fixture(tmp_path)
    output = tmp_path / "audit.json"
    assert (
        main(
            [
                "audit-acceleration",
                "--root",
                str(tmp_path),
                "--limit",
                "20",
                "--min-score",
                "40",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    printed = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert printed == saved
    assert saved["opportunity_count"] >= 8
    assert saved["language_files"]["cuda"] == 1
