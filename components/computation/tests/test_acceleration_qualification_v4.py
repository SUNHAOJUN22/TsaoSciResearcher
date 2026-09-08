from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tsao_computation.accelerators import (
    AcceleratorBackend,
    AcceleratorDevice,
    AcceleratorInventory,
    AcceleratorLibraryEvidence,
    PlacementTarget,
    audit_repository_acceleration,
    plan_acceleration,
    probe_accelerators,
)
from tsao_computation.cli import main
from tsao_computation.performance import (
    WorkloadSample,
    WorkloadSpec,
    builtin_workloads,
    profile_workload,
    profile_workloads,
    select_workloads,
)


def test_production_and_full_tree_audits_have_explicit_scope(tmp_path: Path) -> None:
    (tmp_path / "core.py").write_text(
        "def calculate(a):\n    for i in range(10):\n        for j in range(10):\n            a += i * j + i - j\n    return a\n",
        encoding="utf-8",
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "tool.py").write_text(
        "from pathlib import Path\ndef scan():\n    return list(Path('.').rglob('*'))\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_scan.py").write_text(
        "from pathlib import Path\ndef test_scan():\n    assert list(Path('.').glob('*')) is not None\n",
        encoding="utf-8",
    )

    production = audit_repository_acceleration(tmp_path, scope="production", limit=50)
    full_tree = audit_repository_acceleration(tmp_path, scope="full-tree", limit=50)

    assert production.scope == "production"
    assert full_tree.scope == "full-tree"
    assert all(item.file_scope == "production" for item in production.opportunities)
    assert any(item.file_scope == "tooling" for item in full_tree.opportunities)
    assert any(item.file_scope == "test" for item in full_tree.opportunities)
    assert len(production.source_tree_sha256) == 64
    assert production.source_tree_sha256 == full_tree.source_tree_sha256
    assert all(len(item.candidate_id) == 64 for item in full_tree.opportunities)
    assert all(len(item.source_sha256) == 64 for item in full_tree.opportunities)


def test_probe_records_detected_library_versions_without_importing() -> None:
    found = {"cupy", "cuequivariance", "mpi4py"}
    versions = {
        "cupy-cuda12x": "14.0.0",
        "cuequivariance": "0.5.1",
        "mpi4py": "4.1.0",
    }
    inventory = probe_accelerators(
        which=lambda _: None,
        module_finder=lambda name: object() if name in found else None,
        version_resolver=lambda name: versions.get(name),
        edge_detector=lambda: False,
        native_probe=lambda: None,
    )
    evidence = {item.slug: item for item in inventory.libraries}
    assert evidence["cupy"].version == "14.0.0"
    assert evidence["cuequivariance"].modules == ("cuequivariance",)
    assert evidence["mpi"].detected is True
    assert all(item.qualified is False for item in evidence.values())


def test_planner_separates_candidate_detected_and_qualified_libraries() -> None:
    device = AcceleratorDevice(
        AcceleratorBackend.CUDA,
        0,
        "Qualification GPU",
        24.0,
        "9.0",
        "NVIDIA",
    )
    inventory = AcceleratorInventory(
        logical_cpu_count=16,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=64.0,
        backends=(AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        devices=(device,),
        libraries=(
            AcceleratorLibraryEvidence(
                slug="cuequivariance",
                modules=("cuequivariance",),
                version="0.5.1",
                detected=True,
                qualified=True,
                qualification="model-specific energy and force equivalence passed",
            ),
        ),
        placements=(PlacementTarget.LOCAL, PlacementTarget.WORKSTATION),
    )
    plan = plan_acceleration(
        "mace",
        {
            "accelerator_policy": "required",
            "preferred_backends": ["cuda"],
            "precision": "fp32",
        },
        inventory=inventory,
    )
    assert "cuequivariance" in plan.library_candidates
    assert plan.library_detected == ("cuequivariance",)
    assert plan.library_qualified == ("cuequivariance",)
    assert any("cutensor" in item for item in plan.unmet_requirements)
    assert plan.qualification_status == "detected-unqualified"
    assert len(plan.inventory_sha256) == 64
    assert len(plan.adapter_profile_sha256) == 64
    assert len(plan.acceleration_plan_sha256) == 64
    assert (
        plan.acceleration_plan_sha256
        == plan_acceleration(
            "mace",
            {
                "accelerator_policy": "required",
                "preferred_backends": ["cuda"],
                "precision": "fp32",
            },
            inventory=inventory,
        ).acceleration_plan_sha256
    )


def test_performance_profile_is_structured_and_schema_valid(tmp_path: Path) -> None:
    state = {"value": 0}

    def operation() -> None:
        state["value"] += sum(range(100))

    report = profile_workloads(
        (
            WorkloadSpec(
                slug="test-workload",
                description="deterministic unit-test workload",
                operation=operation,
                tags=("test",),
            ),
        ),
        repeats=3,
        warmups=1,
    ).to_dict()
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas/performance-profile.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema).validate(report)
    assert report["workloads"][0]["repeats"] == 3
    assert len(report["profile_sha256"]) == 64

    output = tmp_path / "profile.json"
    assert (
        main(
            [
                "profile-performance",
                "--root",
                str(Path(__file__).resolve().parents[1]),
                "--workload",
                "routing-hot",
                "--repeats",
                "2",
                "--warmups",
                "0",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["workloads"][0]["slug"] == "routing-hot"


def test_committed_acceleration_reports_are_current_and_scope_safe() -> None:
    from scripts.build_acceleration_audits import (
        FULL_TREE_PATH,
        PRODUCTION_PATH,
        render_all,
    )

    root = Path(__file__).resolve().parents[1]
    rendered = render_all(root)
    for relative, expected in rendered.items():
        assert (root / relative).read_text(encoding="utf-8") == expected
    production = json.loads((root / PRODUCTION_PATH).read_text(encoding="utf-8"))
    full_tree = json.loads((root / FULL_TREE_PATH).read_text(encoding="utf-8"))
    assert production["scope"] == "production"
    assert full_tree["scope"] == "full-tree"
    assert all(item["file_scope"] == "production" for item in production["opportunities"])
    assert any(item["file_scope"] != "production" for item in full_tree["opportunities"])


def test_performance_contract_rejects_invalid_inputs_and_selects_workloads(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        WorkloadSample(float("nan"), 0.0, 0, 1)
    with pytest.raises(ValueError, match="peak_bytes"):
        WorkloadSample(0.0, 0.0, -1, 1)
    with pytest.raises(ValueError, match="operations"):
        WorkloadSample(0.0, 0.0, 0, 0)

    spec = WorkloadSpec("invalid", "invalid workload", lambda: None)
    with pytest.raises(ValueError, match="repeats"):
        profile_workload(spec, repeats=0)
    with pytest.raises(ValueError, match="warmups"):
        profile_workload(spec, warmups=-1)
    with pytest.raises(ValueError, match="operations_per_sample"):
        profile_workload(
            WorkloadSpec("invalid-ops", "invalid operations", lambda: None, operations_per_sample=0)
        )
    with pytest.raises(ValueError, match="at least one"):
        profile_workloads(())
    with pytest.raises(ValueError, match="unknown workloads"):
        select_workloads(("missing",), root=tmp_path)

    selected = {item.slug: item for item in builtin_workloads(tmp_path)}
    assert {item.slug for item in select_workloads((), root=tmp_path)} == set(selected)
    for slug in ("routing-cold", "registry-cold", "acceleration-plan"):
        workload = selected[slug]
        if workload.setup is not None:
            workload.setup()
        workload.operation()


def test_library_evidence_and_inventory_reject_invalid_states() -> None:
    with pytest.raises(Exception, match="booleans"):
        AcceleratorLibraryEvidence(slug="cupy", detected=1)  # type: ignore[arg-type]
    with pytest.raises(Exception, match="must be detected"):
        AcceleratorLibraryEvidence(slug="cupy", detected=False, qualified=True)
    evidence = AcceleratorLibraryEvidence(slug="cupy", modules=("cupy",), detected=True)
    inventory = AcceleratorInventory(
        logical_cpu_count=1,
        architecture="x86_64",
        operating_system="Linux",
        memory_gib=1.0,
        backends=(AcceleratorBackend.CPU,),
        libraries=(evidence,),
    )
    assert inventory.library_evidence_for("cupy") == evidence
    assert inventory.library_evidence_for("missing") is None
    with pytest.raises(Exception, match="unique"):
        AcceleratorInventory(
            logical_cpu_count=1,
            architecture="x86_64",
            operating_system="Linux",
            memory_gib=1.0,
            backends=(AcceleratorBackend.CPU,),
            libraries=(evidence, evidence),
        )
