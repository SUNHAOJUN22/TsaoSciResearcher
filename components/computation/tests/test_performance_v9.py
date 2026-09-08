from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

from scripts.compare_performance_v9 import compare_v9
from scripts.measure_command_v9 import _gnu_time_executable, measure_command
from scripts.verify_all import run_commands_parallel, verification_workers
from scripts.verify_wheel import prepare_source_snapshot
from tsao_computation.provenance.manifest import _file_size_and_sha256
from tsao_computation.registries import clear_registry_caches
from tsao_computation.routing import route_question
from tsao_computation.routing.router import _route_cached


def test_verification_worker_policy_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TSAO_VERIFY_WORKERS", raising=False)
    assert 1 <= verification_workers(20) <= 3
    monkeypatch.setenv("TSAO_VERIFY_WORKERS", "8")
    assert verification_workers(2) == 2
    monkeypatch.setenv("TSAO_VERIFY_WORKERS", "1")
    assert verification_workers(5) == 1
    monkeypatch.setenv("TSAO_VERIFY_WORKERS", "0")
    with pytest.raises(ValueError, match="positive"):
        verification_workers(2)


def test_parallel_gate_output_is_deterministic_and_failure_propagates(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands = (
        ("first", (sys.executable, "-c", "import time; time.sleep(0.05); print('FIRST')")),
        ("second", (sys.executable, "-c", "print('SECOND'); raise SystemExit(3)")),
    )
    assert run_commands_parallel(commands, max_workers=2) == 3
    output = capsys.readouterr().out
    assert output.index("FIRST") < output.index("SECOND")


def test_repeated_route_cache_is_bounded_and_explicitly_invalidated() -> None:
    clear_registry_caches()
    question = "OpenFOAM non-Newtonian polymer extrusion"
    first = route_question(question)
    assert route_question(question) is first
    for index in range(300):
        route_question(f"OpenFOAM non-Newtonian polymer extrusion case {index}")
    assert _route_cached.cache_info().currsize == 256
    clear_registry_caches()
    assert _route_cached.cache_info().currsize == 0
    assert route_question(question) == first


def test_large_file_hashing_preserves_manifest_bytes(tmp_path: Path) -> None:
    payload = (b"TsaoSciComputation-V9\n" * 100_000) + b"tail"
    path = tmp_path / "large.bin"
    path.write_bytes(payload)
    size, digest = _file_size_and_sha256(path)
    assert size == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()


def test_wheel_source_snapshots_are_isolated_and_exclude_runtime_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "package").mkdir()
    (source / "package" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "dist").mkdir()
    (source / "dist" / "stale.whl").write_bytes(b"stale")

    first = tmp_path / "first"
    second = tmp_path / "second"
    prepare_source_snapshot(source, first)
    prepare_source_snapshot(source, second)

    assert (first / "package" / "module.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert (second / "package" / "module.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (first / "dist").exists()
    assert not (second / "dist").exists()
    (first / "package" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert (second / "package" / "module.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_gnu_time_metrics_are_linux_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    executable = Path("/test/gnu-time")
    assert _gnu_time_executable("linux", executable) == executable
    assert _gnu_time_executable("linux-gnu", executable) == executable
    assert _gnu_time_executable("darwin", executable) is None
    assert _gnu_time_executable("win32", executable) is None


def _command_measurement(wall: float, cpu: float, rss: float) -> dict[str, object]:
    return {
        "status": "PASS",
        "summary": {
            "wall_median_seconds": wall,
            "wall_min_seconds": wall * 0.98,
            "wall_p90_seconds": wall * 1.03,
            "wall_cv": 0.01,
            "cpu_median_seconds": cpu,
            "peak_rss_max_kib": rss,
        },
    }


def test_v9_comparison_requires_end_to_end_gain_and_memory_bound() -> None:
    baseline_micro = {
        "route_decision_median_ms": 0.12,
        "parser_5mib_throughput_mib_s": 20.0,
    }
    candidate_micro = {
        "route_decision_median_ms": 0.04,
        "parser_5mib_throughput_mib_s": 21.0,
    }
    report = compare_v9(
        baseline_micro,
        candidate_micro,
        _command_measurement(100.0, 90.0, 100_000.0),
        _command_measurement(85.0, 88.0, 105_000.0),
        baseline_sha="a" * 40,
        candidate_sha="b" * 40,
        audit_run=1,
    )
    assert report["status"] == "PASS"
    assert report["speedups"]["verify_all_wall"] > 1.17

    failed = compare_v9(
        baseline_micro,
        candidate_micro,
        _command_measurement(100.0, 90.0, 100_000.0),
        _command_measurement(96.0, 88.0, 120_000.0),
        baseline_sha="a" * 40,
        candidate_sha="b" * 40,
        audit_run=1,
    )
    assert failed["status"] == "FAIL"


def test_command_measurement_records_repeat_statistics(tmp_path: Path) -> None:
    report = measure_command(
        tmp_path,
        (sys.executable, "-c", "print('ok')"),
        warmups=0,
        repeats=2,
    )
    assert report["status"] == "PASS"
    assert report["summary"]["wall_median_seconds"] > 0
    assert len(report["samples"]) == 2
