from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from scripts import verify_all


def test_all_profile_contains_only_deterministic_release_gates() -> None:
    assert verify_all.RELEASE_PROFILE_NAMES == ("quality", "core", "package")
    assert [step.__name__ for step in verify_all.selected_verifications("all")] == [
        "verify_quality",
        "verify_core",
        "verify_package",
    ]
    assert [step.__name__ for step in verify_all.selected_verifications("benchmark")] == [
        "verify_benchmark"
    ]


def test_run_commands_stops_after_first_failure(monkeypatch) -> None:
    labels: list[str] = []

    def fake_run(
        label: str,
        command: Sequence[str],
        *,
        env: dict[str, str] | None = None,
    ) -> int:
        del command, env
        labels.append(label)
        return 7 if label == "second" else 0

    monkeypatch.setattr(verify_all, "run", fake_run)

    result = verify_all.run_commands(
        (
            ("first", ("one",)),
            ("second", ("two",)),
            ("third", ("three",)),
        )
    )

    assert result == 7
    assert labels == ["first", "second"]


def test_quality_stages_static_checks_before_two_worker_group_and_manifest(monkeypatch) -> None:
    prechecks: list[tuple[str, Sequence[str]]] = []
    parallel: list[tuple[str, Sequence[str]]] = []
    workers: list[int | None] = []
    sequential: list[tuple[str, Sequence[str]]] = []

    def fake_run_commands(commands: Sequence[tuple[str, Sequence[str]]]) -> int:
        prechecks.extend(commands)
        return 0

    def fake_parallel(
        commands: Sequence[tuple[str, Sequence[str]]],
        *,
        env: dict[str, str] | None = None,
        max_workers: int | None = None,
    ) -> int:
        del env
        parallel.extend(commands)
        workers.append(max_workers)
        return 0

    def fake_run(
        label: str,
        command: Sequence[str],
        *,
        env: dict[str, str] | None = None,
    ) -> int:
        del env
        sequential.append((label, command))
        return 0

    monkeypatch.setattr(verify_all, "run_commands", fake_run_commands)
    monkeypatch.setattr(verify_all, "run_commands_parallel", fake_parallel)
    monkeypatch.setattr(verify_all, "run", fake_run)
    assert verify_all.verify_quality() == 0
    assert [label for label, _ in prechecks] == [
        "repository quality rules",
        "Ruff lint",
        "Ruff formatting",
    ]
    assert [label for label, _ in parallel] == [
        "Mypy",
        "Bandit",
        "repository security scan",
        "controlled mutation gate",
    ]
    assert workers == [2]
    assert sequential == [
        (
            "refresh repository manifest",
            (verify_all.PYTHON, "scripts/build_manifest.py"),
        )
    ]


def test_sha256_reads_complete_file(tmp_path: Path) -> None:
    payload = (b"TsaoSciComputation\n" * 100_000) + b"final"
    path = tmp_path / "artifact.bin"
    path.write_bytes(payload)

    assert verify_all.sha256(path) == hashlib.sha256(payload).hexdigest()
