from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorInventory,
    AcceleratorLibraryEvidence,
    PlacementTarget,
    SolverCapabilityEvidence,
    load_solver_capability_evidence,
    plan_acceleration,
)
from tsao_computation.cli import main
from tsao_computation.errors import ContractError


def _inventory(*, library: bool = False) -> AcceleratorInventory:
    libraries = (
        (
            AcceleratorLibraryEvidence(
                slug="cufft",
                modules=("cupy",),
                version="12.0",
                detected=True,
                qualified=False,
                qualification="detected-only fixture",
            ),
        )
        if library
        else ()
    )
    return AcceleratorInventory(
        logical_cpu_count=8,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=32.0,
        backends=(AcceleratorBackend.CPU,),
        libraries=libraries,
        placements=(PlacementTarget.LOCAL,),
    )


def _evidence(
    *,
    adapter_slug: str = "gromacs",
    binary_sha256: str = "a" * 64,
    detected: bool = True,
    missing_modules: tuple[str, ...] = (),
    status: str = "version-probed-unqualified",
) -> SolverCapabilityEvidence:
    if not detected:
        return SolverCapabilityEvidence(
            adapter_slug=adapter_slug,
            declared_executables=("gmx",),
            detected=False,
            qualification_status="candidate-only",
            reason="fixture executable is absent",
        )
    if missing_modules and status == "version-probed-unqualified":
        status = "detected-incomplete"
    has_version = status in {"version-probed-unqualified", "detected-incomplete"}
    return SolverCapabilityEvidence(
        adapter_slug=adapter_slug,
        declared_executables=("gmx",),
        detected=True,
        executable_name="gmx",
        executable_path="/opt/gromacs/bin/gmx",
        executable_sha256=binary_sha256,
        executable_size_bytes=4096,
        required_python_modules=missing_modules,
        missing_python_modules=missing_modules,
        version_arguments=("--version",) if has_version else (),
        version_returncode=0 if has_version else None,
        version_text_sha256="b" * 64 if has_version else None,
        version_excerpt="GROMACS fixture build" if has_version else None,
        qualification_status=status,
        reason="fixture fingerprint and bounded version output",
    )


def _resources() -> dict[str, object]:
    return {
        "accelerator_policy": "disabled",
        "preferred_backends": ["cpu"],
        "cpu_cores": 4,
    }


def test_plan_binds_solver_fingerprint_without_claiming_execution_qualification() -> None:
    evidence = _evidence()
    plan = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(),
        solver_evidence=evidence,
    )
    assert plan.solver_applicable is True
    assert plan.solver_bound is True
    assert plan.solver_detected is True
    assert plan.solver_binary_sha256 == "a" * 64
    assert plan.solver_version_text_sha256 == "b" * 64
    assert plan.solver_evidence_sha256 == evidence.evidence_sha256
    assert plan.execution_qualification_status == "evidence-bound-unqualified"
    assert plan.solver_status == "version-probed-unqualified"
    assert "speedup" not in plan.reason.casefold()


def test_solver_and_library_evidence_remain_separate_regression() -> None:
    plan = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(library=True),
        solver_evidence=_evidence(),
    )
    assert plan.library_detected == ()  # CPU selection makes cuFFT inapplicable.
    assert plan.solver_executable_name == "gmx"
    assert plan.solver_status == "version-probed-unqualified"
    assert plan.execution_qualification_status == "evidence-bound-unqualified"


def test_plan_identity_changes_with_solver_binary() -> None:
    first = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(),
        solver_evidence=_evidence(binary_sha256="1" * 64),
    )
    second = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(),
        solver_evidence=_evidence(binary_sha256="2" * 64),
    )
    assert first.solver_evidence_sha256 != second.solver_evidence_sha256
    assert first.acceleration_plan_sha256 != second.acceleration_plan_sha256


def test_missing_solver_evidence_stays_on_external_hold() -> None:
    plan = plan_acceleration("gromacs", _resources(), inventory=_inventory())
    assert plan.solver_applicable is True
    assert plan.solver_bound is False
    assert plan.solver_status == "candidate-only"
    assert plan.execution_qualification_status == "external-hold"
    assert any("solver evidence is not bound" in item for item in plan.unmet_requirements)


def test_required_solver_evidence_fails_closed() -> None:
    with pytest.raises(ContractError, match="solver evidence is required"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            require_solver_evidence=True,
        )
    with pytest.raises(ContractError, match="was not detected"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            solver_evidence=_evidence(detected=False),
            require_solver_evidence=True,
        )
    with pytest.raises(ContractError, match="modules are incomplete"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            solver_evidence=_evidence(missing_modules=("gmxapi",)),
            require_solver_evidence=True,
        )
    with pytest.raises(ContractError, match="version evidence is incomplete"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            solver_evidence=_evidence(status="fingerprinted-unqualified"),
            require_solver_evidence=True,
        )


def test_solver_evidence_adapter_mismatch_is_rejected() -> None:
    with pytest.raises(ContractError, match="does not match"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            solver_evidence=_evidence(adapter_slug="orca"),
        )


def test_solver_evidence_file_rejects_tampering_and_unknown_fields(tmp_path: Path) -> None:
    evidence = _evidence()
    path = tmp_path / "solver-evidence.json"
    payload = evidence.to_dict()
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_solver_capability_evidence(path).evidence_sha256 == evidence.evidence_sha256

    payload["executable_sha256"] = "c" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContractError, match="does not match its content"):
        load_solver_capability_evidence(path)

    payload = evidence.to_dict()
    payload["unknown"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContractError, match="unknown solver evidence fields"):
        load_solver_capability_evidence(path)


def test_boolean_contracts_and_conflicting_probe_sources_fail_closed() -> None:
    with pytest.raises(ContractError, match="probe_solver must be a boolean"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            probe_solver=1,  # type: ignore[arg-type]
        )
    with pytest.raises(ContractError, match="require_solver_evidence must be a boolean"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            require_solver_evidence=1,  # type: ignore[arg-type]
        )
    with pytest.raises(ContractError, match="not both"):
        plan_acceleration(
            "gromacs",
            _resources(),
            inventory=_inventory(),
            solver_evidence=_evidence(),
            probe_solver=True,
        )


def test_plan_schema_validates_solver_bound_plan() -> None:
    plan = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(),
        solver_evidence=_evidence(),
    ).to_dict()
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas/acceleration-plan.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema).validate(plan)


def test_cli_binds_evidence_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "tsao_computation.accelerators.planner.probe_accelerators",
        lambda: _inventory(),
    )
    evidence_path = tmp_path / "solver-evidence.json"
    evidence_path.write_text(json.dumps(_evidence().to_dict()), encoding="utf-8")
    resources_path = tmp_path / "resources.json"
    resources_path.write_text(json.dumps(_resources()), encoding="utf-8")
    assert (
        main(
            [
                "plan-acceleration",
                "gromacs",
                "--resources",
                str(resources_path),
                "--solver-evidence",
                str(evidence_path),
                "--require-solver-evidence",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["solver_bound"] is True
    assert payload["execution_qualification_status"] == "evidence-bound-unqualified"


def test_solver_evidence_mapping_rejects_missing_and_invalid_scalar_types() -> None:
    with pytest.raises(ContractError, match="must be an object"):
        SolverCapabilityEvidence.from_mapping([])  # type: ignore[arg-type]
    with pytest.raises(ContractError, match="missing solver evidence fields"):
        SolverCapabilityEvidence.from_mapping({"adapter_slug": "gromacs"})

    payload = _evidence().to_dict()
    payload.pop("evidence_sha256")
    payload["executable_size_bytes"] = True
    with pytest.raises(ContractError, match="executable_size_bytes must be an integer"):
        SolverCapabilityEvidence.from_mapping(payload)

    payload = _evidence().to_dict()
    payload.pop("evidence_sha256")
    payload["version_returncode"] = True
    with pytest.raises(ContractError, match="version_returncode must be an integer"):
        SolverCapabilityEvidence.from_mapping(payload)


def test_load_solver_evidence_rejects_invalid_json_and_non_object(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(ContractError, match="cannot read solver capability evidence"):
        load_solver_capability_evidence(invalid)

    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    with pytest.raises(ContractError, match="must be an object"):
        load_solver_capability_evidence(array)


def test_incomplete_evidence_without_strict_mode_stays_external_hold() -> None:
    plan = plan_acceleration(
        "gromacs",
        _resources(),
        inventory=_inventory(),
        solver_evidence=_evidence(status="fingerprinted-unqualified"),
    )
    assert plan.execution_qualification_status == "external-hold"
    assert any("version evidence is incomplete" in item for item in plan.unmet_requirements)
