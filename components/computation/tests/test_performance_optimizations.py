from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_all, verify_wheel
from scripts.benchmark import median_seconds
from scripts.compare_performance import compare_performance
from scripts.run_tests import _write_coverage_evidence
from scripts.security_scan import scan
from tsao_computation.adapters import get_adapter
from tsao_computation.adapters.registry import list_adapters
from tsao_computation.provenance.manifest import file_manifest, iter_repository_entries
from tsao_computation.registries import clear_registry_caches
from tsao_computation.routing import route_question
from tsao_computation.routing.router import _routing_index


@pytest.mark.parametrize(
    ("output", "completed", "converged"),
    [
        ("Normal termination; converged", True, True),
        ("RUN COMPLETED SUCCESSFULLY; convergence achieved", True, True),
        ("completed with errors; converged", False, False),
        ("calculation completed; failed to converge", True, False),
        ("calculation did not converge; completed", True, False),
        ("not completed; convergence reached", False, False),
        ("abnormal termination; converged", False, False),
        ("job aborted; converged", False, False),
        ("never finished; convergence reached", False, False),
        ("convergence failure; completed", True, False),
        ("non-converged; completed", True, False),
        ("non converged; completed", True, False),
        ("unconverged; completed", True, False),
        ("completed\r\nconverged\r\nfatal error", False, False),
        ("unrelated text", False, False),
    ],
)
def test_parser_status_semantics_are_preserved(
    output: str, completed: bool, converged: bool
) -> None:
    parsed = get_adapter("orca").parse(output)
    assert parsed["completed"] is completed
    assert parsed["converged"] is converged
    assert parsed["raw_length"] == len(output)


def test_failure_after_early_success_remains_fail_closed() -> None:
    prefix = "COMPLETED\nCONVERGED\n"
    payload = prefix + ("neutral scientific output\n" * 10_000) + "FATAL ERROR\n"
    parsed = get_adapter("orca").parse(payload)
    assert parsed["completed"] is False
    assert parsed["converged"] is False


def test_adapter_and_routing_indexes_are_cached_and_invalidated() -> None:
    clear_registry_caches()
    first_adapters = list_adapters()
    first_index = _routing_index()
    assert list_adapters() is first_adapters
    assert _routing_index() is first_index
    assert get_adapter("orca") is get_adapter("orca")
    first_decision = route_question("OpenFOAM non-Newtonian polymer extrusion")

    clear_registry_caches()
    assert list_adapters() is not first_adapters
    assert _routing_index() is not first_index
    assert route_question("OpenFOAM non-Newtonian polymer extrusion") == first_decision


def test_scandir_repository_walk_is_globally_sorted_and_excludes_caches(
    tmp_path: Path,
) -> None:
    (tmp_path / "z").mkdir()
    (tmp_path / "z" / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "c.txt").write_text("c", encoding="utf-8")
    (tmp_path / "a.txt").write_text("prefix", encoding="utf-8")
    (tmp_path / "m.txt").write_text("m", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "ignored.pyc").write_bytes(b"x")

    paths = [path.relative_to(tmp_path).as_posix() for path in iter_repository_entries(tmp_path)]
    assert paths == ["a.txt", "a/c.txt", "m.txt", "z/b.txt"]
    assert [record["path"] for record in file_manifest(tmp_path)] == paths


def test_security_scan_combines_rules_without_losing_offsets(tmp_path: Path) -> None:
    github_token = "gh" + "p_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    aws_key = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
    dangerous_call = "ev" + "al(value)"
    shell_setting = "shell" + " = True"
    payload = "\n".join(("prefix", github_token, aws_key, dangerous_call, shell_setting, ""))
    path = tmp_path / "sample.txt"
    path.write_text(payload, encoding="utf-8")
    report = scan(tmp_path)
    findings = report["findings"]
    assert isinstance(findings, list)
    rules = {finding["rule"] for finding in findings}
    assert rules == {"github_token", "aws_key", "dangerous_eval", "shell_true"}
    assert all(finding["path"] == "sample.txt" for finding in findings)


def test_benchmark_helper_validates_controls() -> None:
    with pytest.raises(ValueError):
        median_seconds(lambda: None, repeats=0)
    with pytest.raises(ValueError):
        median_seconds(lambda: None, loops=0)
    assert median_seconds(lambda: None, repeats=1, loops=2, warmups=0) >= 0


def test_sequential_verification_records_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    verify_all._TIMING_RECORDS.clear()

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(verify_all.subprocess, "run", fake_run)
    assert verify_all.run("timed command", (sys.executable, "-V")) == 0
    assert len(verify_all._TIMING_RECORDS) == 1
    record = verify_all._TIMING_RECORDS[0]
    assert record["label"] == "timed command"
    assert record["command"] == [sys.executable, "-V"]
    assert record["mode"] == "sequential"
    assert float(record["elapsed_seconds"]) >= 0.0
    verify_all._TIMING_RECORDS.clear()


def test_coverage_json_is_generated_once_with_the_hard_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    class FakeCoverage:
        def load(self) -> None:
            calls.append("load")

        def json_report(self, *, outfile: str) -> float:
            calls.append("json")
            Path(outfile).write_text('{"totals": {"percent_covered": 97.5}}\n', encoding="utf-8")
            return 97.5

    monkeypatch.setitem(sys.modules, "coverage", SimpleNamespace(Coverage=FakeCoverage))
    output = tmp_path / "coverage.json"
    assert _write_coverage_evidence(output) == 0
    assert calls == ["load", "json"]
    assert output.is_file()


def test_coverage_threshold_remains_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class LowCoverage:
        def load(self) -> None:
            return None

        def json_report(self, *, outfile: str) -> float:
            Path(outfile).write_text("{}\n", encoding="utf-8")
            return 94.99

    monkeypatch.setitem(sys.modules, "coverage", SimpleNamespace(Coverage=LowCoverage))
    assert _write_coverage_evidence(tmp_path / "coverage.json") == 2


def test_wheel_target_install_skips_only_bytecode_compilation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "package.whl"
    wheel.write_bytes(b"wheel")
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["install_command"] = command
        captured["install_env"] = kwargs["env"]
        return SimpleNamespace(returncode=0)

    def fake_check_output(command: list[str], **kwargs: object) -> str:
        captured["verification_command"] = command
        captured["verification_env"] = kwargs["env"]
        return "3.0.2 164 27 20"

    monkeypatch.setattr(verify_wheel.subprocess, "run", fake_run)
    monkeypatch.setattr(verify_wheel.subprocess, "check_output", fake_check_output)
    assert verify_wheel.verify_target_install(wheel, tmp_path, "3.0.2 164 27 20") == (
        "3.0.2 164 27 20"
    )
    install_command = captured["install_command"]
    assert isinstance(install_command, list)
    assert "--no-index" in install_command
    assert "--no-deps" in install_command
    assert "--no-compile" in install_command
    install_env = captured["install_env"]
    assert isinstance(install_env, dict)
    assert install_env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_performance_comparison_requires_improvement_without_regression() -> None:
    baseline = {
        "cli_import_median_ms": 40.0,
        "capability_registry_cold_median_ms": 3.2,
        "adapter_registry_cold_median_ms": 0.3,
        "workflow_registry_cold_median_ms": 0.3,
        "route_decision_median_ms": 0.12,
        "parser_5mib_throughput_mib_s": 15.0,
    }
    candidate = {
        "cli_import_median_ms": 39.0,
        "capability_registry_cold_median_ms": 3.0,
        "adapter_registry_cold_median_ms": 0.25,
        "workflow_registry_cold_median_ms": 0.25,
        "route_decision_median_ms": 0.06,
        "parser_5mib_throughput_mib_s": 25.0,
    }
    report = compare_performance(baseline, candidate)
    assert report["status"] == "PASS"
    assert report["speedups"]["route_decision_median_ms"] == 2.0

    candidate["route_decision_median_ms"] = 0.2
    candidate["parser_5mib_throughput_mib_s"] = 14.0
    assert compare_performance(baseline, candidate)["status"] == "FAIL"
