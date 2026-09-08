#!/usr/bin/env python3
"""Generate one approval-gated Slurm array script and one bound JSONL task table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_job_script import (  # noqa: E402 -- script-local import follows an explicit sys.path setup
    approval_guard,
    execution_argv,
    q,
)
from shell_contract import safe_relative_path, safe_scalar, sha256_file  # noqa: E402 -- local trust contract
from validate_hpc_manifest import (  # noqa: E402 -- local validator import follows SCRIPT_DIR path setup
    validate as validate_manifest,
)

TASK_KEYS = {"task_id", "input", "workdir", "stdout", "stderr"}


def _positive_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} root must be a mapping")
    return value


def _merged_manifest(base: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged.update({key: value for key, value in task.items() if key != "task_id"})
    return merged


def load_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    campaign = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, "campaign")
    errors: list[str] = []
    for key in ("schema_version", "campaign_id", "base_manifest", "tasks"):
        if key not in campaign:
            errors.append(f"missing {key}")

    safe_scalar(campaign.get("campaign_id"), "campaign_id", errors, job_name=True)
    base_manifest = campaign.get("base_manifest")
    if not isinstance(base_manifest, str) or not base_manifest:
        errors.append("base_manifest must be a non-empty relative path")
        base_path = path.parent / "__missing_base_manifest__"
    else:
        path_errors: list[str] = []
        safe_relative_path(base_manifest, "base_manifest", path_errors, allow_dot=False)
        errors.extend(path_errors)
        base_path = path.parent / "__invalid_base_manifest__" if path_errors else path.parent / base_manifest

    if not base_path.is_file():
        errors.append(f"base_manifest not found: {base_path}")
        base: dict[str, Any] = {}
    else:
        loaded_base = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded_base, dict):
            errors.append("base manifest root must be a mapping")
            base = {}
        else:
            base = loaded_base
            manifest_errors, _ = validate_manifest(base, approval_root=base_path.parent)
            errors.extend(f"base manifest: {message}" for message in manifest_errors)

    if base.get("scheduler") != "slurm":
        errors.append("job arrays require a Slurm base manifest")
    if (base.get("preflight") or {}).get("run_in_job") or (base.get("parser") or {}).get("run_in_job"):
        errors.append("array base manifest requires preflight/parser run_in_job=false")
    if (base.get("scratch") or {}).get("path"):
        scratch_root = campaign.get("scratch_root")
        if not scratch_root:
            errors.append("scratch_root is required when the base manifest declares scratch.path")
        else:
            safe_relative_path(scratch_root, "scratch_root", errors, allow_dot=False)

    tasks = campaign.get("tasks") or []
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list")
        tasks = []
    valid_tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(tasks):
        if not isinstance(item, dict):
            errors.append(f"task {index} must be a mapping")
            continue
        task: dict[str, Any] = item
        unknown = sorted(set(task) - TASK_KEYS)
        if unknown:
            errors.append(f"task {index} contains unsupported override fields: {unknown}")
        for key in ("task_id", "input", "workdir"):
            if not isinstance(task.get(key), str) or not task.get(key):
                errors.append(f"task {index} missing or invalid {key}")
        task_id = str(task.get("task_id", ""))
        safe_scalar(task_id, f"task {index}.task_id", errors, job_name=True)
        if task_id in seen:
            errors.append(f"duplicate task_id: {task_id}")
        seen.add(task_id)
        for field in ("stdout", "stderr"):
            if field in task:
                safe_relative_path(task.get(field), f"task {index}.{field}", errors, allow_dot=False)
        if base:
            merged = _merged_manifest(base, task)
            task_errors, _ = validate_manifest(merged, approval_root=base_path.parent)
            errors.extend(f"task {index}: {message}" for message in task_errors)
        valid_tasks.append(task)

    try:
        maximum = _positive_integer(campaign.get("max_concurrent", len(valid_tasks) or 1), "max_concurrent")
    except ValueError as exc:
        errors.append(str(exc))
        maximum = 1
    campaign["max_concurrent"] = maximum
    campaign["tasks"] = valid_tasks
    if errors:
        raise ValueError("; ".join(errors))
    return campaign, base, valid_tasks


def task_record(campaign: dict[str, Any], base: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    merged = _merged_manifest(base, task)
    environment: dict[str, str] = {}
    engine = str(merged["engine"])
    input_path = str(merged["input"])
    record: dict[str, Any] = {
        "task_id": str(task["task_id"]),
        "workdir": str(merged["workdir"]),
        "argv": execution_argv(merged),
        "environment": environment,
        "stdin": input_path if engine == "gaussian" else None,
        "stdout": None if engine == "cp2k" else str(merged.get("stdout") or (Path(input_path).stem + ".stdout")),
        "stderr": str(merged.get("stderr") or (Path(input_path).stem + ".stderr")),
    }
    if (base.get("scratch") or {}).get("path"):
        scratch = Path(str(campaign["scratch_root"])) / str(task["task_id"])
        record["scratch_path"] = str(scratch)
        if base.get("engine") == "gaussian":
            environment["GAUSS_SCRDIR"] = str(scratch)
    return record


def build_array_script(
    campaign: dict[str, Any],
    base: dict[str, Any],
    task_table_name: str,
    task_table_sha256: str,
) -> str:
    resources = base["resources"]
    tasks = campaign["tasks"]
    maximum = min(int(campaign["max_concurrent"]), len(tasks))
    lines = [
        "#!/usr/bin/env bash",
        f"#SBATCH --job-name={campaign['campaign_id']}",
        f"#SBATCH --nodes={resources['nodes']}",
        f"#SBATCH --ntasks-per-node={resources['tasks_per_node']}",
        f"#SBATCH --cpus-per-task={resources['cpus_per_task']}",
        f"#SBATCH --mem={resources['memory_gb']}G",
        f"#SBATCH --time={resources['walltime']}",
        f"#SBATCH --array=0-{len(tasks) - 1}%{maximum}",
    ]
    if resources.get("partition"):
        lines.append(f"#SBATCH --partition={resources['partition']}")
    if int(resources.get("gpus_per_node", resources.get("gpus", 0))) > 0:
        lines.append(f"#SBATCH --gpus-per-node={int(resources.get('gpus_per_node', resources.get('gpus', 0)))}")
    lines += [
        "set -euo pipefail",
        "",
        f"# base method_fingerprint_id: {base.get('method_fingerprint_id', 'unknown')}",
        f"# approval: {base.get('approval', 'pending')}",
    ]
    environment = base.get("environment") or {}
    for module in environment.get("modules", []):
        lines.append(f"module load {q(module)}")
    for source in environment.get("source", []):
        lines.append(f"source {q(source)}")
    for key, value in (environment.get("variables") or {}).items():
        lines.append(f"export {key}={q(value)}")
    lines.extend(approval_guard(base))
    lines += [
        'SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)',
        f'TASK_TABLE="${{SCRIPT_DIR}}"/{q(task_table_name)}',
        f"EXPECTED_TASK_TABLE_SHA256={q(task_table_sha256)}",
        'TASK_INDEX="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}"',
        'python - "${TASK_TABLE}" "${TASK_INDEX}" "${EXPECTED_TASK_TABLE_SHA256}" <<\'PY\'',
        "import hashlib",
        "import json",
        "import os",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "table = Path(sys.argv[1]).resolve()",
        "try:",
        "    index = int(sys.argv[2])",
        "except ValueError as exc:",
        "    raise SystemExit('SLURM_ARRAY_TASK_ID must be an integer') from exc",
        "if index < 0:",
        "    raise SystemExit('SLURM_ARRAY_TASK_ID must be nonnegative')",
        "expected_sha256 = sys.argv[3]",
        "digest = hashlib.sha256()",
        "with table.open('rb') as handle:",
        "    for chunk in iter(lambda: handle.read(1024 * 1024), b''):",
        "        digest.update(chunk)",
        "if digest.hexdigest() != expected_sha256:",
        "    raise SystemExit(f'task table digest mismatch: {table}')",
        "record = None",
        "with table.open(encoding='utf-8') as handle:",
        "    for current, line in enumerate(handle):",
        "        if current == index:",
        "            record = json.loads(line)",
        "            break",
        "if not isinstance(record, dict):",
        "    raise SystemExit(f'array index {index} is outside {table}')",
        "argv = record.get('argv')",
        "if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):",
        "    raise SystemExit('task argv must be a non-empty list of strings')",
        "task_id = record.get('task_id')",
        "if not isinstance(task_id, str) or not task_id:",
        "    raise SystemExit('task_id must be a non-empty string')",
        "workdir_value = record.get('workdir')",
        "if not isinstance(workdir_value, str) or not workdir_value:",
        "    raise SystemExit('task workdir must be a non-empty string')",
        "workdir = Path(workdir_value).resolve()",
        "if not workdir.is_dir():",
        "    raise SystemExit(f'task workdir is not a directory: {workdir}')",
        "print(f'TsaoDFT array task start: {task_id}', flush=True)",
        "environment = os.environ.copy()",
        "record_environment = record.get('environment') or {}",
        "if not isinstance(record_environment, dict) or not all(",
        "    isinstance(key, str) and isinstance(value, str) for key, value in record_environment.items()",
        "):",
        "    raise SystemExit('task environment must be a string mapping')",
        "environment.update(record_environment)",
        "if record.get('scratch_path'):",
        "    scratch_path = Path(record['scratch_path']).resolve()",
        "    scratch_path.mkdir(parents=True, exist_ok=True)",
        "    if 'GAUSS_SCRDIR' in environment:",
        "        environment['GAUSS_SCRDIR'] = str(scratch_path)",
        "",
        "def io_path(field):",
        "    value = record.get(field)",
        "    if value is None:",
        "        return None",
        "    if not isinstance(value, str) or not value:",
        "        raise SystemExit(f'task {field} must be a non-empty string or null')",
        "    path = Path(value)",
        "    return path if path.is_absolute() else workdir / path",
        "",
        "handles = []",
        "try:",
        "    stdin_path = io_path('stdin')",
        "    stdout_path = io_path('stdout')",
        "    stderr_path = io_path('stderr')",
        "    stdin_handle = stdin_path.open('rb') if stdin_path is not None else None",
        "    stdout_handle = stdout_path.open('wb') if stdout_path is not None else None",
        "    stderr_handle = stderr_path.open('wb') if stderr_path is not None else None",
        "    handles.extend(handle for handle in (stdin_handle, stdout_handle, stderr_handle) if handle is not None)",
        "    completed = subprocess.run(",
        "        argv,",
        "        cwd=workdir,",
        "        shell=False,",
        "        stdin=stdin_handle,",
        "        stdout=stdout_handle,",
        "        stderr=stderr_handle,",
        "        env=environment,",
        "        check=False,",
        "    )",
        "finally:",
        "    for handle in handles:",
        "        handle.close()",
        "print(f'TsaoDFT array task end: {task_id} rc={completed.returncode}', flush=True)",
        "raise SystemExit(completed.returncode)",
        "PY",
    ]
    return "\n".join(lines) + "\n"


def generate(campaign_path: Path, script_path: Path, task_table_path: Path) -> dict[str, Any]:
    campaign, base, tasks = load_campaign(campaign_path)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    task_table_path.parent.mkdir(parents=True, exist_ok=True)
    with task_table_path.open("w", encoding="utf-8") as handle:
        for task in tasks:
            json.dump(task_record(campaign, base, task), handle, sort_keys=True)
            handle.write("\n")
    table_digest = sha256_file(task_table_path)
    script_path.write_text(
        build_array_script(campaign, base, task_table_path.name, table_digest),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return {
        "script": str(script_path),
        "task_table": str(task_table_path),
        "task_table_sha256": table_digest,
        "task_count": len(tasks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = generate(args.campaign, args.script, args.tasks)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
