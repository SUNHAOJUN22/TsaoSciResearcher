"""One task graph, one state model and one evidence lineage for all domains."""
from __future__ import annotations
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from .core.canonical import digest
from .core.jsonio import read_json, strict_dumps, strict_loads, validate_json, MAX_JSON_BYTES
from .core.store import EvidenceStore
from .registry import capabilities
from .workspace import root
from .contracts import validate_payload, enforce_lineage, data_dependencies

_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _id(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("task/workflow IDs must be bounded identifiers, never paths")
    return value


def plan(spec: dict[str, Any]) -> dict[str, Any]:
    validate_json(spec)
    if not isinstance(spec, dict) or set(spec) != {"schema_version", "id", "tasks"}:
        raise ValueError("workflow requires exactly schema_version, id and tasks")
    if spec["schema_version"] != "tsao.workflow/1":
        raise ValueError("unsupported workflow schema")
    workflow_id = _id(spec["id"])
    tasks = spec["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 32:
        raise ValueError("workflow must contain 1..32 tasks")
    registry = capabilities()
    by_id: dict[str, dict] = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"id", "capability", "depends_on", "payload"}:
            raise ValueError("invalid task fields")
        task_id = _id(task["id"])
        if task_id in by_id:
            raise ValueError("duplicate task ID")
        cap = task["capability"]
        if not isinstance(cap, str) or cap not in registry:
            raise ValueError("unregistered capability")
        if not isinstance(task["payload"], dict):
            raise ValueError("task payload must be an object")
        deps = task["depends_on"]
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps) or len(deps) != len(set(deps)):
            raise ValueError("dependencies must be unique task identifiers")
        by_id[task_id] = task
    for task in tasks:
        if any(dep not in by_id or dep == task["id"] for dep in task["depends_on"]):
            raise ValueError("unknown or self dependency")
        _validate_references(task["payload"], set(task["depends_on"]))
        validate_payload(task["capability"], task["payload"], deferred=True)
    pending = dict(by_id)
    ordered: list[dict] = []
    done: set[str] = set()
    while pending:
        ready = sorted(key for key, task in pending.items() if set(task["depends_on"]) <= done)
        if not ready:
            raise ValueError("workflow dependency cycle")
        for key in ready:
            ordered.append(pending.pop(key))
            done.add(key)
    # Clone through strict JSON so later caller mutations cannot change the plan.
    ordered = strict_loads(strict_dumps(ordered))
    return {"schema_version": "tsao.plan/1", "id": workflow_id, "workflow_digest": digest(spec),
            "tasks": ordered, "execution": "NOT_EXECUTED",
            "external_solver_executed": False,
            "blocked_capabilities": [t["capability"] for t in ordered if registry[t["capability"]]["mode"] != "local-reference"]}


def _validate_references(value: Any, dependencies: set[str]) -> None:
    if isinstance(value, dict):
        if "$ref" in value:
            if set(value) != {"$ref"} or not isinstance(value["$ref"], str):
                raise ValueError("reference requires exactly one string $ref")
            path = value["$ref"].split(".")
            if len(path) < 2 or path[0] not in dependencies or any(not re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in path):
                raise ValueError("reference must resolve through a declared dependency")
        else:
            for child in value.values():
                _validate_references(child, dependencies)
    elif isinstance(value, list):
        for child in value:
            _validate_references(child, dependencies)


def _resolve(value: Any, results: dict[str, dict]) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            path = value["$ref"].split(".")
            current: Any = results[path[0]]["result"]
            for part in path[1:]:
                current = current[int(part)] if isinstance(current, list) and part.isdigit() else current[part]
            return strict_loads(strict_dumps(current))
        return {key: _resolve(child, results) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve(child, results) for child in value]
    return value


def source_identity() -> str:
    value = hashlib.sha256()
    for folder in ("tsao_science", "contracts", "components", "skills/reasoning"):
        for path in sorted((root() / folder).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".toml"} and "__pycache__" not in path.parts:
                relative = path.relative_to(root()).as_posix()
                value.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return value.hexdigest()


def _terminate(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def execute_local(capability: str, payload: dict[str, Any], *, timeout: float = 60) -> dict[str, Any]:
    if type(timeout) not in (int, float) or not 0 < timeout <= 300:
        raise ValueError("local timeout must be finite and within 300 seconds")
    registry = capabilities()
    if capability not in registry or registry[capability]["mode"] != "local-reference":
        raise ValueError("external execution is not authorized by a local workflow")
    validate_payload(capability, payload)
    body = strict_dumps({"capability": capability, "payload": payload}).encode("utf-8")
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("request too large")
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env.update({"PYTHONPATH": str(root()), "TSAO_WORKSPACE_ROOT": str(root()),
                "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    with tempfile.TemporaryDirectory(prefix="tsao-worker-") as directory:
        directory = Path(directory)
        input_path, output_path, error_path = (directory / name for name in ("input.json", "output.json", "error.txt"))
        input_path.write_bytes(body)
        with input_path.open("rb") as inp, output_path.open("wb") as out, error_path.open("wb") as err:
            process = subprocess.Popen([sys.executable, "-m", "tsao_science.worker"], stdin=inp, stdout=out,
                stderr=err, cwd=directory, env=env, start_new_session=os.name != "nt")
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() > deadline or output_path.stat().st_size + error_path.stat().st_size > MAX_JSON_BYTES:
                    _terminate(process)
                    raise RuntimeError("local worker exceeded its time or output budget")
                time.sleep(0.01)
        response = read_json(output_path)
        if process.returncode != 0 or not isinstance(response, dict) or response.get("ok") is not True:
            error = response.get("error", "worker rejected the task") if isinstance(response, dict) else "malformed worker output"
            raise RuntimeError(str(error))
        validate_payload(capability, response["result"], output=True)
        return response["result"]


def validation_verdict(capability: str, output: dict[str, Any]) -> dict[str, str]:
    """Prevent explicit domain failures from being promoted by process success."""
    state, scope = "NOT_EVALUATED", "no additional domain acceptance supplied"
    if capability == "reasoning.validate":
        state = "PASS" if output.get("valid_structure") is True else "FAIL"
        scope = "ledger structure only; premises are not authenticated"
    elif capability == "processing.fit_first_order":
        state = "PASS" if output.get("identifiable") is True else "HOLD"
        scope = "local single-parameter sensitivity, not model validation"
    elif capability == "aspen.classify":
        state = {"converged": "PASS", "not_converged": "FAIL"}.get(output.get("state"), "HOLD")
        scope = "supplied status classification only; no engine execution"
    return {"state": state, "scope": scope}


def run(spec: dict[str, Any], workdir: Path, *, allow_local: bool = False) -> dict[str, Any]:
    # Snapshot the workflow before planning, hashing or execution.
    spec = strict_loads(strict_dumps(spec))
    planned = plan(spec)
    if not allow_local:
        raise PermissionError("run requires explicit --execute-local; use plan for non-executing inspection")
    if planned["blocked_capabilities"]:
        raise PermissionError("workflow contains an externally unqualified capability")
    workdir = workdir.resolve()
    run_id = "run-" + uuid.uuid4().hex
    destination = workdir / run_id
    destination.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(workdir / "evidence.sqlite3")
    source = source_identity()
    results: dict[str, dict] = {}
    record = {"schema_version": "tsao.run/2", "id": planned["id"], "run_id": run_id,
              "workflow": spec, "workflow_digest": planned["workflow_digest"], "source_identity": source,
              "execution": "RUNNING", "external_solver_executed": False,
              "scientific_approval": "NOT_EVALUATED", "tasks": results}
    task_id = None
    store.append({"event": "run-started", "run_id": run_id, "source_identity": source,
                  "workflow_digest": planned["workflow_digest"]})
    try:
        for task in planned["tasks"]:
            task_id = task["id"]
            payload = _resolve(task["payload"], results)
            validate_payload(task["capability"], payload)
            enforce_lineage(task["capability"], payload, {key: results[key] for key in data_dependencies(task["payload"])})
            output = execute_local(task["capability"], payload)
            kind = payload["observation"]["evidence_kind"] if task["capability"] == "materials.observation" else "reference"
            evidence = {"capability": task["capability"], "input": payload, "input_digest": digest(payload),
                        "output_digest": digest(output), "depends_on": task["depends_on"],
                        "execution": "SUCCEEDED", "result": output, "evidence_kind": kind,
                        "validation": validation_verdict(task["capability"], output),
                        "scientific_approval": "NOT_EVALUATED"}
            results[task_id] = evidence
            evidence["event_digest"] = store.append({"run_id": run_id, "task_id": task_id,
                "source_identity": source, "input_digest": evidence["input_digest"],
                "output_digest": evidence["output_digest"], "capability": task["capability"],
                "validation": evidence["validation"], "evidence_kind": kind})
            if evidence["validation"]["state"] in {"FAIL", "HOLD"}:
                raise RuntimeError(f"domain gate {evidence['validation']['state']}: {task_id}; downstream tasks not executed")
        if source_identity() != source:
            raise RuntimeError("source changed during execution")
        record["execution"] = "SUCCEEDED"
    except Exception as exc:
        record["execution"] = "FAILED"
        record["failed_task"] = task_id
        record["error"] = str(exc)
    store.append({"event": "run-finished", "run_id": run_id, "execution": record["execution"],
                  "completed_tasks": list(results), "failed_task": record.get("failed_task")})
    record["evidence_chain"] = store.verify()
    record["record_digest"] = digest(record)
    target = destination / "result.json"
    temporary = destination / "result.json.tmp"
    temporary.write_text(strict_dumps(record, pretty=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return {**record, "result_file": str(target)}


def verify_result(path: Path, *, ledger: Path | None = None) -> dict[str, Any]:
    from .verification import verify_record
    record = read_json(path)
    result = verify_record(record)
    if ledger is not None:
        result.update(EvidenceStore(ledger, readonly=True).verify_bindings(record))
    return result
