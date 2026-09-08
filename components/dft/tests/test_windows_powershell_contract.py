from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY_GATE = ROOT / "scripts/quality_gate.ps1"
WINDOWS_INVENTORY = ROOT / "skills/tsao-dft-hpc-provenance/scripts/inspect_windows_environment.ps1"


class WindowsPowerShellContractTests(unittest.TestCase):
    def test_quality_gate_wrapper_is_structured_and_preserves_exit_code(self) -> None:
        text = QUALITY_GATE.read_text(encoding="utf-8")
        required = (
            "Set-StrictMode -Version Latest",
            '$ErrorActionPreference = "Stop"',
            "$PSScriptRoot",
            "Resolve-Path",
            'Get-Command -Name "python" -CommandType Application -All',
            "Select-Object -First 1",
            "$PythonExecutable = [string]$PythonCommand.Source",
            "& $PythonExecutable @Arguments",
            "$LASTEXITCODE",
            "Push-Location -LiteralPath",
            "Pop-Location",
            "exit [int]$ExitCode",
            '"--skip-tests"',
            '"--json"',
            '"--timeout"',
        )
        for fragment in required:
            self.assertIn(fragment, text)
        for forbidden in (
            "& $PythonCommand.Source @Arguments",
            "Invoke-Expression",
            "Start-Process",
            "cmd.exe",
            "cmd /c",
            "powershell.exe -Command",
            "iex ",
        ):
            self.assertNotIn(forbidden, text)

    def test_windows_inventory_is_read_only_private_and_nonqualifying(self) -> None:
        text = WINDOWS_INVENTORY.read_text(encoding="utf-8")
        for fragment in (
            "Win32_OperatingSystem",
            "Win32_Processor",
            "Win32_PhysicalMemory",
            "Win32_VideoController",
            "[long]$TotalPhysicalBytes = 0",
            "foreach ($Module in $MemoryModules)",
            '$TotalPhysicalBytes += [long]$Module["capacity_bytes"]',
            "total_physical_bytes = $TotalPhysicalBytes",
            '"INVENTORY_ONLY"',
            '"NOT_PERFORMANCE_EVIDENCE"',
            '"NOT_DFT_ENGINE_EXECUTION"',
            "external_dft_engine_invoked = $false",
            'performance_qualification = "NOT_ELIGIBLE"',
            "hostname_recorded = $false",
            "username_recorded = $false",
            "home_path_recorded = $false",
            "environment_values_recorded = $false",
            "executable_paths_recorded = $false",
            "ConvertTo-Json -Depth 8",
            "Move-Item -LiteralPath $Temporary",
        ):
            self.assertIn(fragment, text)

        for forbidden in (
            "$env:COMPUTERNAME",
            "$env:USERNAME",
            "$env:USERPROFILE",
            "$HOME",
            "Get-ChildItem Env:",
            "hostname.exe",
            "whoami.exe",
            "Invoke-Expression",
            "Start-Process",
            "Measure-Object -Property capacity_bytes",
            "vasp_std",
            "pw.x",
            "cp2k.psmp",
            "g16",
            "g09",
        ):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("& $NvidiaSmi", text)

    def test_powershell_files_parse_when_pwsh_is_available(self) -> None:
        executable = shutil.which("pwsh")
        if executable is None:
            self.skipTest("pwsh is not installed on this runner")
        for path in (QUALITY_GATE, WINDOWS_INVENTORY):
            quoted_path = str(path).replace("'", "''")
            command = (
                "$parseErrors = $null; $tokens = $null; "
                "[System.Management.Automation.Language.Parser]::ParseFile("
                f"'{quoted_path}', [ref]$tokens, [ref]$parseErrors) | Out-Null; "
                "if ($parseErrors.Count -ne 0) { "
                "$parseErrors | ForEach-Object { Write-Error $_.Message }; exit 1 }; exit 0"
            )
            completed = subprocess.run(
                [executable, "-NoProfile", "-Command", command],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            with self.subTest(path=path.name):
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
