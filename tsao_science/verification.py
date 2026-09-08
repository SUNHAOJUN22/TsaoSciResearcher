"""Verify imported records without executing code or granting scientific approval."""
from __future__ import annotations
import re
from typing import Any
from .core.canonical import digest
from .core.jsonio import strict_dumps, strict_loads
from .contracts import validate_payload, enforce_lineage, data_dependencies

_SHA = re.compile(r"^[0-9a-f]{64}$")


def verify_record(value: Any) -> dict[str, Any]:
    from .engine import plan, _resolve, validation_verdict
    record = strict_loads(strict_dumps(value))
    if not isinstance(record, dict):
        raise ValueError("result must be an object")
    expected = record.pop("record_digest", None)
    if not isinstance(expected, str) or not _SHA.fullmatch(expected) or expected != digest(record):
        raise ValueError("result record digest mismatch")
    version = record.get("schema_version")
    if version not in {"tsao.run/1", "tsao.run/2"}:
        raise ValueError("unsupported result schema")
    if record.get("external_solver_executed") is not False or record.get("scientific_approval") != "NOT_EVALUATED":
        raise ValueError("local results cannot claim external execution or scientific approval")
    if record.get("execution") not in {"SUCCEEDED", "FAILED"} or not isinstance(record.get("tasks"), dict):
        raise ValueError("invalid terminal result state")
    tasks = record["tasks"]
    observations = []
    for task in tasks.values():
        if not isinstance(task, dict) or "result" not in task or digest(task["result"]) != task.get("output_digest"):
            raise ValueError("task output digest mismatch")
    if version == "tsao.run/2":
        planned = plan(record.get("workflow"))
        if planned["id"] != record.get("id") or planned["workflow_digest"] != record.get("workflow_digest"):
            raise ValueError("workflow identity mismatch")
        if planned["blocked_capabilities"]:
            raise ValueError("local record contains unqualified external execution")
        known = [row["id"] for row in planned["tasks"]]
        if set(tasks) - set(known):
            raise ValueError("result includes an unplanned task")
        completed = {}
        stopped = False
        for row in planned["tasks"]:
            key, capability = row["id"], row["capability"]
            if key not in tasks:
                stopped = True
                continue
            if stopped:
                raise ValueError("execution resumed after a missing or failed predecessor")
            task = tasks[key]
            if task.get("capability") != capability or task.get("depends_on") != row["depends_on"]:
                raise ValueError("task declaration disagrees with workflow")
            if task.get("execution") != "SUCCEEDED" or task.get("scientific_approval") != "NOT_EVALUATED":
                raise ValueError("invalid local task qualification")
            payload = _resolve(row["payload"], completed)
            validate_payload(capability, payload)
            if task.get("input_digest") != digest(payload) or task.get("input") != payload:
                raise ValueError("resolved task input binding mismatch")
            enforce_lineage(capability, payload, {k: completed[k] for k in data_dependencies(row["payload"])})
            validate_payload(capability, task["result"], output=True)
            verdict = validation_verdict(capability, task["result"])
            if task.get("validation") != verdict:
                raise ValueError("recorded domain validation disagrees with actual output")
            kind = payload["observation"]["evidence_kind"] if capability == "materials.observation" else "reference"
            if task.get("evidence_kind") != kind:
                raise ValueError("evidence-kind binding mismatch")
            if capability == "materials.observation":
                if task["result"]["observation"] != payload["observation"]:
                    raise ValueError("observation output is not the validated input")
                observations.append(task["result"]["observation"])
            completed[key] = task
            if verdict["state"] in {"FAIL", "HOLD"}:
                stopped = True
        if record["execution"] == "SUCCEEDED" and (len(completed) != len(known) or stopped):
            raise ValueError("successful run lacks a completed admissible task graph")
    return {"integrity": "PASS", "execution": record["execution"], "schema_version": version,
            "workflow_binding": "PASS" if version == "tsao.run/2" else "UNAVAILABLE_LEGACY_RECORD",
            "ledger_integrity": "NOT_CHECKED", "source_authenticity": "NOT_AUTHENTICATED",
            "scientific_approval": "NOT_EVALUATED", "external_solver_executed": False,
            "observations": observations, "scope": "self-consistency; not proof of an experiment or independent approval"}
