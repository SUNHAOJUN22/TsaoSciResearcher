#!/usr/bin/env python3
"""Generate injection-resistant local/Slurm/PBS job scripts from structured argv."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from shell_contract import render_argv  # noqa: E402 -- standalone Skill import contract
from validate_hpc_manifest import validate as validate_manifest  # noqa: E402 -- standalone Skill import contract


def q(value: Any) -> str:
    return shlex.quote(str(value))


def ps_literal(value: Any) -> str:
    """Return one PowerShell single-quoted literal."""

    return "'" + str(value).replace("'", "''") + "'"


def metadata_comment(value: Any) -> str:
    """Render metadata into a single non-executable comment line."""

    return str(value).replace("\r", " ").replace("\n", " ")


def render_powershell_argv(value: list[str]) -> str:
    if not value:
        raise ValueError("argv must not be empty")
    return "@(" + ", ".join(ps_literal(item) for item in value) + ")"


def approval_guard(manifest: dict[str, Any]) -> list[str]:
    approval = str(manifest.get("approval", "pending"))
    if approval in {"approved", "not_required"}:
        return []
    return [f'echo "TsaoDFT execution blocked: manifest approval is {approval}" >&2', "exit 64"]


def powershell_approval_guard(manifest: dict[str, Any]) -> list[str]:
    approval = str(manifest.get("approval", "pending"))
    if approval in {"approved", "not_required"}:
        return []
    message = ps_literal(f"TsaoDFT execution blocked: manifest approval is {approval}")
    return [f"[Console]::Error.WriteLine({message})", "exit 64"]


def launcher_argv(manifest: dict[str, Any]) -> list[str]:
    """Return the validated launcher as structured argv."""

    launcher = manifest.get("launcher")
    if isinstance(launcher, dict):
        return [str(item) for item in launcher["argv"]]
    if launcher != "auto":
        return []
    resources = manifest["resources"]
    if manifest["scheduler"] != "slurm":
        raise ValueError("launcher=auto is supported only for Slurm")
    nodes = int(resources["nodes"])
    tasks_per_node = int(resources["tasks_per_node"])
    options = [
        "srun",
        f"--ntasks={nodes * tasks_per_node}",
        f"--ntasks-per-node={tasks_per_node}",
        f"--cpus-per-task={int(resources['cpus_per_task'])}",
        "--kill-on-bad-exit=1",
    ]
    acceleration = manifest.get("acceleration") or {}
    if acceleration.get("enabled") is True:
        if int(acceleration.get("ranks_per_gpu", 1)) == 1:
            options.append("--gpus-per-task=1")
        for flag, key in (("--cpu-bind", "cpu_bind"), ("--gpu-bind", "gpu_bind")):
            value = str(acceleration.get(key, "none"))
            if value != "none":
                options.append(f"{flag}={value}")
    return options


def launcher_prefix(manifest: dict[str, Any]) -> str:
    argv = launcher_argv(manifest)
    return render_argv(argv) + " " if argv else ""


def engine_argv(manifest: dict[str, Any]) -> list[str]:
    engine = manifest["engine"]
    executable = str(manifest["executable"])
    input_path = str(manifest["input"])
    if engine == "gaussian":
        return [executable]
    if engine == "vasp":
        return [executable]
    if engine == "quantum-espresso":
        return [executable, "-in", input_path]
    if engine == "cp2k":
        return [executable, "-i", input_path, "-o", str(manifest.get("stdout") or "cp2k.out")]
    return [executable, input_path]


def execution_argv(manifest: dict[str, Any]) -> list[str]:
    """Return launcher and engine execution as one structured argv vector."""

    return [*launcher_argv(manifest), *engine_argv(manifest)]


def engine_command(manifest: dict[str, Any]) -> str:
    engine = manifest["engine"]
    input_path = q(manifest["input"])
    stdout = q(manifest.get("stdout") or (Path(str(manifest["input"])).stem + ".stdout"))
    stderr = q(manifest.get("stderr") or (Path(str(manifest["input"])).stem + ".stderr"))
    prefix = launcher_prefix(manifest)
    command = render_argv(engine_argv(manifest))
    if engine == "gaussian":
        return f"{prefix}{command} < {input_path} > {stdout} 2> {stderr}"
    if engine == "cp2k":
        return f"{prefix}{command} 2> {stderr}"
    return f"{prefix}{command} > {stdout} 2> {stderr}"


def runtime_provenance(manifest: dict[str, Any]) -> list[str]:
    acceleration = manifest.get("acceleration") or {}
    if acceleration.get("enabled") is not True or acceleration.get("record_runtime", True) is False:
        return []
    record = q(acceleration.get("runtime_record", "tsao-acceleration-runtime.txt"))
    lines = [
        f'printf "profile_id=%s\\n" {q(acceleration.get("profile_id", "unknown"))} > {record}',
        f'printf "build_fingerprint_id=%s\\n" {q(acceleration.get("build_fingerprint_id", "unknown"))} >> {record}',
        f'printf "benchmark_plan_id=%s\\n" {q(acceleration.get("benchmark_plan_id", "unknown"))} >> {record}',
        f'printf "SLURM_JOB_ID=%s\\n" "${{SLURM_JOB_ID:-}}" >> {record}',
        f'printf "SLURM_LOCALID=%s\\n" "${{SLURM_LOCALID:-}}" >> {record}',
        f'printf "CUDA_VISIBLE_DEVICES=%s\\n" "${{CUDA_VISIBLE_DEVICES:-}}" >> {record}',
        f'printf "ROCR_VISIBLE_DEVICES=%s\\n" "${{ROCR_VISIBLE_DEVICES:-}}" >> {record}',
        f'printf "ZE_AFFINITY_MASK=%s\\n" "${{ZE_AFFINITY_MASK:-}}" >> {record}',
    ]
    if acceleration.get("gpu_vendor") == "nvidia":
        inventory = q(acceleration.get("device_inventory", "tsao-nvidia-gpu-inventory.csv"))
        lines.extend(
            [
                "if command -v nvidia-smi >/dev/null 2>&1; then",
                "  nvidia-smi --query-gpu=name,uuid,pci.bus_id,driver_version,memory.total "
                f"--format=csv,noheader > {inventory}",
                "else",
                f'  echo "nvidia-smi unavailable" > {inventory}',
                "fi",
            ]
        )
    return lines


def powershell_runtime_provenance(manifest: dict[str, Any]) -> list[str]:
    acceleration = manifest.get("acceleration") or {}
    if acceleration.get("enabled") is not True or acceleration.get("record_runtime", True) is False:
        return []
    record = ps_literal(acceleration.get("runtime_record", "tsao-acceleration-runtime.txt"))
    fixed = (
        f"profile_id={acceleration.get('profile_id', 'unknown')}",
        f"build_fingerprint_id={acceleration.get('build_fingerprint_id', 'unknown')}",
        f"benchmark_plan_id={acceleration.get('benchmark_plan_id', 'unknown')}",
    )
    lines = [
        "$runtimeLines = [System.Collections.Generic.List[string]]::new()",
        *[f"$runtimeLines.Add({ps_literal(item)})" for item in fixed],
        '$runtimeLines.Add("SLURM_JOB_ID=$($env:SLURM_JOB_ID)")',
        '$runtimeLines.Add("SLURM_LOCALID=$($env:SLURM_LOCALID)")',
        '$runtimeLines.Add("CUDA_VISIBLE_DEVICES=$($env:CUDA_VISIBLE_DEVICES)")',
        '$runtimeLines.Add("ROCR_VISIBLE_DEVICES=$($env:ROCR_VISIBLE_DEVICES)")',
        '$runtimeLines.Add("ZE_AFFINITY_MASK=$($env:ZE_AFFINITY_MASK)")',
        f"$runtimeLines | Set-Content -LiteralPath {record} -Encoding utf8NoBOM",
    ]
    if acceleration.get("gpu_vendor") == "nvidia":
        inventory = ps_literal(acceleration.get("device_inventory", "tsao-nvidia-gpu-inventory.csv"))
        lines.extend(
            [
                "$nvidiaSmi = Get-Command -Name 'nvidia-smi' -CommandType Application -ErrorAction SilentlyContinue",
                "if ($null -ne $nvidiaSmi) {",
                "  & $nvidiaSmi.Source '--query-gpu=name,uuid,pci.bus_id,driver_version,memory.total' "
                f"'--format=csv,noheader' | Set-Content -LiteralPath {inventory} -Encoding utf8NoBOM",
                "  if ($LASTEXITCODE -ne 0) { throw 'nvidia-smi inventory failed' }",
                "} else {",
                f"  'nvidia-smi unavailable' | Set-Content -LiteralPath {inventory} -Encoding utf8NoBOM",
                "}",
            ]
        )
    return lines


def build_posix(manifest: dict[str, Any]) -> str:
    resources = manifest["resources"]
    scheduler = manifest["scheduler"]
    lines = ["#!/usr/bin/env bash", "set -euo pipefail"]
    headers: list[str] = []
    if scheduler == "slurm":
        headers = [
            f"#SBATCH --job-name={manifest['job_id']}",
            f"#SBATCH --nodes={resources['nodes']}",
            f"#SBATCH --ntasks-per-node={resources['tasks_per_node']}",
            f"#SBATCH --cpus-per-task={resources['cpus_per_task']}",
            f"#SBATCH --mem={resources['memory_gb']}G",
            f"#SBATCH --time={resources['walltime']}",
        ]
        if resources.get("partition"):
            headers.append(f"#SBATCH --partition={resources['partition']}")
        gpus = int(resources.get("gpus_per_node", resources.get("gpus", 0)))
        if gpus:
            headers.append(f"#SBATCH --gpus-per-node={gpus}")
    elif scheduler == "pbs":
        select = (
            f"select={resources['nodes']}:"
            f"ncpus={int(resources['tasks_per_node']) * int(resources['cpus_per_task'])}:"
            f"mem={resources['memory_gb']}gb"
        )
        gpus = int(resources.get("gpus_per_node", resources.get("gpus", 0)))
        if gpus:
            select += f":ngpus={gpus}"
        headers = [f"#PBS -N {manifest['job_id']}", f"#PBS -l {select}", f"#PBS -l walltime={resources['walltime']}"]
        if resources.get("queue"):
            headers.append(f"#PBS -q {resources['queue']}")
    lines[1:1] = headers
    lines += [
        "",
        f"# engine: {metadata_comment(manifest['engine'])} "
        f"{metadata_comment(manifest.get('engine_version', 'unknown'))}",
        f"# method_fingerprint_id: {metadata_comment(manifest.get('method_fingerprint_id', 'unknown'))}",
        f"# support_level: {metadata_comment(manifest.get('support_level', 'unknown'))}",
        f"# approval: {metadata_comment(manifest.get('approval', 'pending'))}",
    ]
    environment = manifest.get("environment") or {}
    for module in environment.get("modules", []):
        lines.append(f"module load {q(module)}")
    for source in environment.get("source", []):
        lines.append(f"source {q(source)}")
    variables = environment.get("variables") or {}
    for key, value in variables.items():
        lines.append(f"export {key}={q(value)}")
    acceleration = manifest.get("acceleration") or {}
    if (
        acceleration.get("enabled")
        and acceleration.get("gpu_vendor") == "nvidia"
        and acceleration.get("device_order") == "pci_bus_id"
        and "CUDA_DEVICE_ORDER" not in variables
    ):
        lines.append("export CUDA_DEVICE_ORDER=PCI_BUS_ID")
    scratch = manifest.get("scratch") or {}
    if scratch.get("path"):
        lines.append(f"mkdir -p {q(scratch['path'])}")
        if manifest["engine"] == "gaussian":
            lines.append(f"export GAUSS_SCRDIR={q(scratch['path'])}")
    lines += ["", f"cd {q(manifest['workdir'])}"]
    lines.extend(approval_guard(manifest))
    lines.extend(['echo "TsaoDFT job start: $(date -Is)"', 'echo "Host: $(hostname)"'])
    lines.extend(runtime_provenance(manifest))
    preflight = manifest["preflight"]
    lines.append(f"# preflight: {render_argv(preflight['argv'])}")
    if preflight.get("run_in_job") is True:
        lines.append(render_argv(preflight["argv"]))
    lines.extend(["set +e", engine_command(manifest), "rc=$?", "set -e"])
    lines.append('echo "TsaoDFT job end: $(date -Is) rc=${rc}"')
    parser_contract = manifest["parser"]
    lines.append("parser_rc=0")
    if parser_contract.get("run_in_job") is True:
        lines.extend(
            [
                "set +e",
                render_argv(parser_contract["argv"]),
                "parser_rc=$?",
                "set -e",
                'echo "TsaoDFT parser end: $(date -Is) rc=${parser_rc}"',
            ]
        )
    lines.extend(
        [
            'if [ "${rc}" -ne 0 ]; then',
            '  exit "${rc}"',
            "fi",
            'exit "${parser_rc}"',
        ]
    )
    return "\n".join(lines) + "\n"


def _powershell_process_function() -> list[str]:
    return [
        "function Invoke-TsaoProcess {",
        "  [CmdletBinding()]",
        "  param(",
        "    [Parameter(Mandatory = $true)][string[]]$Argv,",
        "    [string]$StandardInputPath = '',",
        "    [string]$StandardOutputPath = '',",
        "    [string]$StandardErrorPath = ''",
        "  )",
        "  if ($Argv.Count -lt 1) { throw 'argv must not be empty' }",
        "  $startInfo = [System.Diagnostics.ProcessStartInfo]::new()",
        "  $startInfo.FileName = $Argv[0]",
        "  $startInfo.UseShellExecute = $false",
        "  $startInfo.CreateNoWindow = $true",
        "  for ($index = 1; $index -lt $Argv.Count; $index++) {",
        "    $null = $startInfo.ArgumentList.Add($Argv[$index])",
        "  }",
        "  $startInfo.RedirectStandardInput = $StandardInputPath.Length -gt 0",
        "  $startInfo.RedirectStandardOutput = $StandardOutputPath.Length -gt 0",
        "  $startInfo.RedirectStandardError = $StandardErrorPath.Length -gt 0",
        "  $process = [System.Diagnostics.Process]::new()",
        "  $process.StartInfo = $startInfo",
        "  $inputStream = $null",
        "  $outputStream = $null",
        "  $errorStream = $null",
        "  $outputTask = $null",
        "  $errorTask = $null",
        "  try {",
        "    if ($startInfo.RedirectStandardInput) {",
        "      $inputStream = [System.IO.File]::OpenRead($StandardInputPath)",
        "    }",
        "    if ($startInfo.RedirectStandardOutput) {",
        "      $outputStream = [System.IO.File]::Open(",
        "        $StandardOutputPath, [System.IO.FileMode]::Create,",
        "        [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read",
        "      )",
        "    }",
        "    if ($startInfo.RedirectStandardError) {",
        "      $errorStream = [System.IO.File]::Open(",
        "        $StandardErrorPath, [System.IO.FileMode]::Create,",
        "        [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read",
        "      )",
        "    }",
        "    if (-not $process.Start()) { throw 'process failed to start' }",
        "    if ($null -ne $outputStream) {",
        "      $outputTask = $process.StandardOutput.BaseStream.CopyToAsync($outputStream)",
        "    }",
        "    if ($null -ne $errorStream) {",
        "      $errorTask = $process.StandardError.BaseStream.CopyToAsync($errorStream)",
        "    }",
        "    if ($null -ne $inputStream) {",
        "      $inputStream.CopyTo($process.StandardInput.BaseStream)",
        "      $process.StandardInput.Close()",
        "    }",
        "    $process.WaitForExit()",
        "    $tasks = [System.Collections.Generic.List[System.Threading.Tasks.Task]]::new()",
        "    if ($null -ne $outputTask) { $tasks.Add($outputTask) }",
        "    if ($null -ne $errorTask) { $tasks.Add($errorTask) }",
        "    if ($tasks.Count -gt 0) {",
        "      [System.Threading.Tasks.Task]::WaitAll($tasks.ToArray())",
        "    }",
        "    return [int]$process.ExitCode",
        "  } finally {",
        "    if ($null -ne $inputStream) { $inputStream.Dispose() }",
        "    if ($null -ne $outputStream) { $outputStream.Dispose() }",
        "    if ($null -ne $errorStream) { $errorStream.Dispose() }",
        "    $process.Dispose()",
        "  }",
        "}",
    ]


def build_powershell(manifest: dict[str, Any]) -> str:
    if manifest.get("scheduler") != "local":
        raise ValueError("PowerShell job scripts support only scheduler=local")
    environment = manifest.get("environment") or {}
    if environment.get("modules"):
        raise ValueError("PowerShell local backend does not support environment.modules")
    if environment.get("source"):
        raise ValueError("PowerShell local backend does not support environment.source")

    lines = [
        "#requires -Version 7.0",
        "Set-StrictMode -Version Latest",
        "$ErrorActionPreference = 'Stop'",
        "",
        f"# engine: {metadata_comment(manifest['engine'])} "
        f"{metadata_comment(manifest.get('engine_version', 'unknown'))}",
        f"# method_fingerprint_id: {metadata_comment(manifest.get('method_fingerprint_id', 'unknown'))}",
        f"# support_level: {metadata_comment(manifest.get('support_level', 'unknown'))}",
        f"# approval: {metadata_comment(manifest.get('approval', 'pending'))}",
        *_powershell_process_function(),
        "",
    ]
    variables = environment.get("variables") or {}
    for key, value in variables.items():
        lines.append(f"$env:{key} = {ps_literal(value)}")
    acceleration = manifest.get("acceleration") or {}
    if (
        acceleration.get("enabled")
        and acceleration.get("gpu_vendor") == "nvidia"
        and acceleration.get("device_order") == "pci_bus_id"
        and "CUDA_DEVICE_ORDER" not in variables
    ):
        lines.append("$env:CUDA_DEVICE_ORDER = 'PCI_BUS_ID'")
    scratch = manifest.get("scratch") or {}
    if scratch.get("path"):
        scratch_path = ps_literal(scratch["path"])
        lines.append(f"$null = New-Item -ItemType Directory -Force -LiteralPath {scratch_path}")
        if manifest["engine"] == "gaussian":
            lines.append(f"$env:GAUSS_SCRDIR = {scratch_path}")
    lines += ["", f"Set-Location -LiteralPath {ps_literal(manifest['workdir'])}"]
    lines.extend(powershell_approval_guard(manifest))
    lines.append("Write-Output \"TsaoDFT job start: $((Get-Date).ToString('o'))\"")
    lines.extend(powershell_runtime_provenance(manifest))

    preflight = manifest["preflight"]
    lines.append(f"# preflight: {render_powershell_argv(preflight['argv'])}")
    if preflight.get("run_in_job") is True:
        lines.extend(
            [
                f"$preflightArgv = {render_powershell_argv(preflight['argv'])}",
                "$preflightRc = Invoke-TsaoProcess -Argv $preflightArgv",
                "if ($preflightRc -ne 0) { exit $preflightRc }",
            ]
        )

    engine = manifest["engine"]
    stdout = str(manifest.get("stdout") or (Path(str(manifest["input"])).stem + ".stdout"))
    stderr = str(manifest.get("stderr") or (Path(str(manifest["input"])).stem + ".stderr"))
    lines.append(f"$engineArgv = {render_powershell_argv(execution_argv(manifest))}")
    invoke = ["$engineRc = Invoke-TsaoProcess -Argv $engineArgv"]
    if engine == "gaussian":
        invoke.append(f"-StandardInputPath {ps_literal(manifest['input'])}")
    if engine != "cp2k":
        invoke.append(f"-StandardOutputPath {ps_literal(stdout)}")
    invoke.append(f"-StandardErrorPath {ps_literal(stderr)}")
    lines.append(" `\n  ".join(invoke))
    lines.append("Write-Output \"TsaoDFT job end: $((Get-Date).ToString('o')) rc=$engineRc\"")

    parser_contract = manifest["parser"]
    lines.append("$parserRc = 0")
    if parser_contract.get("run_in_job") is True:
        lines.extend(
            [
                f"$parserArgv = {render_powershell_argv(parser_contract['argv'])}",
                "$parserRc = Invoke-TsaoProcess -Argv $parserArgv",
                "Write-Output \"TsaoDFT parser end: $((Get-Date).ToString('o')) rc=$parserRc\"",
            ]
        )
    lines.extend(["if ($engineRc -ne 0) { exit $engineRc }", "exit $parserRc"])
    return "\n".join(lines) + "\n"


def build(manifest: dict[str, Any], *, shell: str = "posix") -> str:
    if shell == "posix":
        return build_posix(manifest)
    if shell == "powershell":
        return build_powershell(manifest)
    raise ValueError("shell must be posix or powershell")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--approval-root", type=Path)
    parser.add_argument("--shell", choices=("posix", "powershell"), default="posix")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    loaded = yaml.safe_load(args.manifest.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        print(json.dumps({"ok": False, "errors": ["manifest root must be a mapping"]}, indent=2))
        return 1
    errors, warnings = validate_manifest(loaded, approval_root=args.approval_root or args.manifest.parent)
    if errors:
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, indent=2))
        return 1
    try:
        script = build_posix(loaded) if args.shell == "posix" else build_powershell(loaded)
    except ValueError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)], "warnings": warnings}, indent=2))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(script)
    if args.shell == "posix":
        args.out.chmod(0o755)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
