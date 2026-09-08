from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..errors import SecurityError
from .resources import (
    ExecutionResourceBroker,
    ExecutionResourceCapacity,
    ExecutionResourceClaim,
    validate_resource_binding,
)
from .runner import ExecutionAuthorization, ExecutionRecord, run_plan
from .typing_compat import CommandPlanLike

_DEFAULT_MAX_EXTERNAL_PLANS = 4


@dataclass(frozen=True, slots=True)
class BatchExecutionResult:
    records: tuple[ExecutionRecord, ...]
    completed: bool
    failed_indices: tuple[int, ...]
    resource_capacity_sha256: str | None = None
    resource_claim_sha256s: tuple[str, ...] = ()


def _default_workers(plan_count: int) -> int:
    return min(plan_count, max(1, min(_DEFAULT_MAX_EXTERNAL_PLANS, os.cpu_count() or 1)))


def run_plan_batch(
    plans: tuple[CommandPlanLike, ...] | list[CommandPlanLike],
    *,
    authorizations: tuple[ExecutionAuthorization, ...] | list[ExecutionAuthorization] | None = None,
    timeout: float = 300.0,
    max_workers: int | None = None,
    resource_claims: tuple[ExecutionResourceClaim, ...]
    | list[ExecutionResourceClaim]
    | None = None,
    resource_capacity: ExecutionResourceCapacity | None = None,
) -> BatchExecutionResult:
    items = tuple(plans)
    if not items:
        return BatchExecutionResult((), True, ())
    if authorizations is None or len(authorizations) != len(items):
        raise SecurityError("each external command plan requires one matching authorization")
    auth_items = tuple(authorizations)
    workers = _default_workers(len(items)) if max_workers is None else max_workers
    if workers < 1:
        raise ValueError("max_workers must be positive")
    workers = min(workers, len(items))

    broker: ExecutionResourceBroker | None = None
    claim_items: tuple[ExecutionResourceClaim, ...] = ()
    if resource_claims is not None or resource_capacity is not None:
        if resource_claims is None or resource_capacity is None:
            raise SecurityError("resource claims and capacity must be provided together")
        if len(resource_claims) != len(items):
            raise SecurityError("each command plan requires one matching resource claim")
        claim_items = tuple(resource_claims)
        broker = ExecutionResourceBroker(resource_capacity)
        for plan, claim in zip(items, claim_items, strict=True):
            validate_resource_binding(plan.environment, claim)
            broker._assert_fits(claim)

    def execute(index: int) -> ExecutionRecord:
        plan = items[index]
        authorization = auth_items[index]
        if broker is None:
            return run_plan(plan, authorization=authorization, timeout=timeout)
        claim = claim_items[index]
        with broker.lease(claim):
            return run_plan(plan, authorization=authorization, timeout=timeout)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tsao-external-plan") as pool:
        futures = [pool.submit(execute, index) for index in range(len(items))]
        records = tuple(future.result() for future in futures)
    failed = tuple(index for index, record in enumerate(records) if not record.completed)
    return BatchExecutionResult(
        records,
        not failed,
        failed,
        None if resource_capacity is None else resource_capacity.sha256,
        tuple(claim.sha256 for claim in claim_items),
    )


run_plans = run_plan_batch
