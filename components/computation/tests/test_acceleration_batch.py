from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tsao_computation.adapters.base import CommandPlan
from tsao_computation.execution import authorize_plan, run_plan_batch


def test_batch_execution_preserves_order_and_failure_indices(tmp_path: Path) -> None:
    plans = [
        CommandPlan((sys.executable, "-c", "print('first')"), tmp_path, {}, "test"),
        CommandPlan((sys.executable, "-c", "raise SystemExit(4)"), tmp_path, {}, "test"),
        CommandPlan((sys.executable, "-c", "print('third')"), tmp_path, {}, "test"),
    ]
    authorizations = [
        authorize_plan(
            plan,
            authorized_by="pytest",
            purpose="repository execution test",
            explicit_authorization=True,
        )
        for plan in plans
    ]
    result = run_plan_batch(plans, authorizations=authorizations, timeout=10, max_workers=2)
    assert len(result.records) == 3
    assert [record.returncode for record in result.records] == [0, 4, 0]
    assert result.completed is False
    assert result.failed_indices == (1,)


def test_empty_batch_and_worker_validation() -> None:
    result = run_plan_batch([])
    assert result.completed is True
    assert result.records == ()
    with pytest.raises(ValueError, match="positive"):
        plan = CommandPlan((sys.executable, "-c", "pass"), Path("."), {}, "test")
        run_plan_batch(
            [plan],
            authorizations=[
                authorize_plan(
                    plan,
                    authorized_by="pytest",
                    purpose="worker validation",
                    explicit_authorization=True,
                )
            ],
            max_workers=0,
        )


def test_resource_broker_prevents_cpu_oversubscription(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading
    import time
    from types import SimpleNamespace

    from tsao_computation.execution import (
        ExecutionResourceCapacity,
        ExecutionResourceClaim,
    )
    from tsao_computation.execution import batch as batch_module

    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def fake_run_plan(*_: object, **__: object) -> object:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return SimpleNamespace(completed=True, returncode=0)

    monkeypatch.setattr(batch_module, "run_plan", fake_run_plan)
    plans = [
        CommandPlan((sys.executable, "-c", "pass"), tmp_path, {}, "test"),
        CommandPlan((sys.executable, "-c", "pass"), tmp_path, {}, "test"),
    ]
    claims = [ExecutionResourceClaim(cpu_cores=2), ExecutionResourceClaim(cpu_cores=2)]
    capacity = ExecutionResourceCapacity(cpu_cores=2)
    result = run_plan_batch(
        plans,
        authorizations=[object(), object()],  # type: ignore[list-item]
        max_workers=2,
        resource_claims=claims,
        resource_capacity=capacity,
    )
    assert result.completed is True
    assert maximum_active == 1
    assert result.resource_capacity_sha256 == capacity.sha256
    assert result.resource_claim_sha256s == tuple(item.sha256 for item in claims)


def test_resource_broker_validates_gpu_binding_and_capacity(tmp_path: Path) -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import (
        ExecutionResourceCapacity,
        ExecutionResourceClaim,
    )

    plan = CommandPlan(
        (sys.executable, "-c", "pass"),
        tmp_path,
        {"CUDA_VISIBLE_DEVICES": "0"},
        "test",
    )
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="resource binding",
        explicit_authorization=True,
    )
    with pytest.raises(SecurityError, match="does not match"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[ExecutionResourceClaim(gpu_devices=(1,))],
            resource_capacity=ExecutionResourceCapacity(cpu_cores=1, gpu_devices=(0, 1)),
        )
    with pytest.raises(SecurityError, match="license capacity"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[
                ExecutionResourceClaim(
                    gpu_devices=(0,),
                    license_tokens=(("solver", 2),),
                )
            ],
            resource_capacity=ExecutionResourceCapacity(
                cpu_cores=1,
                gpu_devices=(0,),
                license_tokens=(("solver", 1),),
            ),
        )
    with pytest.raises(SecurityError, match="provided together"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[ExecutionResourceClaim()],
        )


def test_resource_value_validation_and_binding_errors() -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import (
        ExecutionResourceCapacity,
        ExecutionResourceClaim,
        validate_resource_binding,
    )

    with pytest.raises(ValueError, match="positive integer"):
        ExecutionResourceClaim(cpu_cores=0)
    with pytest.raises(ValueError, match="non-negative integers"):
        ExecutionResourceClaim(gpu_devices=(-1,))
    with pytest.raises(ValueError, match="unique"):
        ExecutionResourceClaim(gpu_devices=(0, 0))
    with pytest.raises(ValueError, match="non-empty strings"):
        ExecutionResourceClaim(license_tokens=((" ", 1),))
    with pytest.raises(ValueError, match="positive integer"):
        ExecutionResourceClaim(license_tokens=(("solver", 0),))
    with pytest.raises(ValueError, match="unique"):
        ExecutionResourceCapacity(
            cpu_cores=1,
            license_tokens=(("solver", 1), ("solver", 1)),
        )

    claim = ExecutionResourceClaim(gpu_devices=(0,))
    with pytest.raises(SecurityError, match="requires a bound"):
        validate_resource_binding({}, claim)
    with pytest.raises(SecurityError, match="comma-separated integer"):
        validate_resource_binding({"CUDA_VISIBLE_DEVICES": "gpu0"}, claim)
    validate_resource_binding({"CUDA_VISIBLE_DEVICES": "0"}, claim)
    validate_resource_binding({}, ExecutionResourceClaim())


def test_resource_broker_serializes_gpu_and_license_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading
    import time
    from types import SimpleNamespace

    from tsao_computation.execution import (
        ExecutionResourceCapacity,
        ExecutionResourceClaim,
    )
    from tsao_computation.execution import batch as batch_module

    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def fake_run_plan(*_: object, **__: object) -> object:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return SimpleNamespace(completed=True, returncode=0)

    monkeypatch.setattr(batch_module, "run_plan", fake_run_plan)
    plans = [
        CommandPlan(
            (sys.executable, "-c", "pass"),
            tmp_path,
            {"CUDA_VISIBLE_DEVICES": "0"},
            "test",
        ),
        CommandPlan(
            (sys.executable, "-c", "pass"),
            tmp_path,
            {"CUDA_VISIBLE_DEVICES": "0"},
            "test",
        ),
    ]
    claims = [
        ExecutionResourceClaim(gpu_devices=(0,), license_tokens=(("solver", 1),)),
        ExecutionResourceClaim(gpu_devices=(0,), license_tokens=(("solver", 1),)),
    ]
    result = run_plan_batch(
        plans,
        authorizations=[object(), object()],  # type: ignore[list-item]
        max_workers=2,
        resource_claims=claims,
        resource_capacity=ExecutionResourceCapacity(
            cpu_cores=2,
            gpu_devices=(0,),
            license_tokens=(("solver", 1),),
        ),
    )
    assert result.completed is True
    assert maximum_active == 1


def test_resource_claim_rejects_unavailable_capacity_and_count_mismatch(tmp_path: Path) -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import (
        ExecutionResourceCapacity,
        ExecutionResourceClaim,
    )

    plan = CommandPlan(
        (sys.executable, "-c", "pass"),
        tmp_path,
        {"CUDA_VISIBLE_DEVICES": "1"},
        "test",
    )
    authorization = authorize_plan(
        plan,
        authorized_by="pytest",
        purpose="resource capacity validation",
        explicit_authorization=True,
    )
    with pytest.raises(SecurityError, match="unavailable GPU"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[ExecutionResourceClaim(gpu_devices=(1,))],
            resource_capacity=ExecutionResourceCapacity(cpu_cores=1, gpu_devices=(0,)),
        )
    with pytest.raises(SecurityError, match="one matching resource claim"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[],
            resource_capacity=ExecutionResourceCapacity(cpu_cores=1),
        )
    with pytest.raises(SecurityError, match="CPU capacity"):
        run_plan_batch(
            [plan],
            authorizations=[authorization],
            resource_claims=[ExecutionResourceClaim(cpu_cores=2, gpu_devices=(1,))],
            resource_capacity=ExecutionResourceCapacity(
                cpu_cores=1,
                gpu_devices=(1,),
            ),
        )


def test_resource_binding_rejects_unclaimed_visible_gpu() -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import ExecutionResourceClaim, validate_resource_binding

    with pytest.raises(SecurityError, match="matching GPU resource claim"):
        validate_resource_binding(
            {"CUDA_VISIBLE_DEVICES": "0"},
            ExecutionResourceClaim(),
        )


def test_resource_binding_checks_every_present_visibility_alias() -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import ExecutionResourceClaim, validate_resource_binding

    claim = ExecutionResourceClaim(gpu_devices=(0,))
    with pytest.raises(SecurityError, match="ROCR_VISIBLE_DEVICES"):
        validate_resource_binding(
            {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "1"},
            claim,
        )
    with pytest.raises(SecurityError, match="comma-separated integer"):
        validate_resource_binding(
            {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "gpu1"},
            claim,
        )


def test_resource_binding_accepts_consistent_aliases_and_empty_gpu_hiding() -> None:
    from tsao_computation.execution import ExecutionResourceClaim, validate_resource_binding

    validate_resource_binding(
        {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "0"},
        ExecutionResourceClaim(gpu_devices=(0,)),
    )
    validate_resource_binding(
        {"CUDA_VISIBLE_DEVICES": ""},
        ExecutionResourceClaim(),
    )


@pytest.mark.parametrize("raw", ["0,,1", "0,-1", "0,0"])
def test_resource_binding_rejects_noncanonical_device_lists(raw: str) -> None:
    from tsao_computation.errors import SecurityError
    from tsao_computation.execution import ExecutionResourceClaim, validate_resource_binding

    claim = ExecutionResourceClaim(gpu_devices=(0, 1))
    with pytest.raises(SecurityError):
        validate_resource_binding({"CUDA_VISIBLE_DEVICES": raw}, claim)
