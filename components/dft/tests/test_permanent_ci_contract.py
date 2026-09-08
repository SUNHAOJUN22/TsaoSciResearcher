from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PermanentCIContractTests(unittest.TestCase):
    def test_only_permanent_ci_workflow_is_present(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        self.assertEqual(
            sorted(path.name for path in workflows.iterdir() if path.is_file()),
            ["ci.yml"],
        )

    def test_permanent_ci_is_read_only_and_complete(self) -> None:
        path = ROOT / ".github" / "workflows" / "ci.yml"
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        self.assertEqual(data["name"], "TsaoDFT quality and security gates")
        self.assertEqual(data["permissions"], {"contents": "read"})
        self.assertEqual(data["concurrency"]["cancel-in-progress"], True)
        self.assertEqual(
            set(data["jobs"]),
            {"quality-gate", "windows-control-plane", "supply-chain", "codeql"},
        )
        self.assertEqual(data["jobs"]["quality-gate"]["timeout-minutes"], 25)
        self.assertEqual(data["jobs"]["windows-control-plane"]["timeout-minutes"], 40)
        self.assertEqual(data["jobs"]["supply-chain"]["timeout-minutes"], 25)
        self.assertEqual(data["jobs"]["codeql"]["timeout-minutes"], 30)
        matrix = data["jobs"]["quality-gate"]["strategy"]["matrix"]["include"]
        versions = [item["python-version"] for item in matrix]
        constraints = [item["constraint"] for item in matrix]
        self.assertEqual(versions, ["3.10", "3.12", "3.13"])
        self.assertEqual(
            constraints,
            [
                "constraints/py310.txt",
                "constraints/py312.txt",
                "constraints/py313.txt",
            ],
        )
        self.assertFalse(data["jobs"]["quality-gate"]["strategy"]["fail-fast"])
        self.assertIn("python scripts/quality_gate.py", text)
        self.assertIn("scripts\\quality_gate.ps1", text)
        self.assertIn("inspect_windows_environment.ps1", text)
        self.assertIn("coverage-report.json", text)
        self.assertIn("pip_audit", text)
        self.assertIn("cyclonedx-json", text)
        self.assertIn("security-extended", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("Invoke-Expression", text)
        self.assertNotIn("Start-Process", text)

    def test_windows_control_plane_is_real_private_and_evidence_preserving(
        self,
    ) -> None:
        path = ROOT / ".github" / "workflows" / "ci.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        job = data["jobs"]["windows-control-plane"]
        self.assertEqual(job["runs-on"], "windows-latest")
        self.assertEqual(job["permissions"], {"contents": "read", "statuses": "write"})
        steps = job["steps"]
        by_name = {step["name"]: step for step in steps}

        gate = by_name["Run complete PowerShell quality gate"]
        self.assertNotIn("id", gate)
        self.assertEqual(gate["shell"], "pwsh")
        for fragment in (
            "quality_gate.ps1",
            "windows-quality-gate.log",
            "Tee-Object",
            "$LASTEXITCODE",
            "exit $LASTEXITCODE",
        ):
            self.assertIn(fragment, gate["run"])
        self.assertNotIn("GITHUB_OUTPUT", gate["run"])

        upload = by_name["Upload Windows control-plane evidence"]
        self.assertEqual(upload["if"], "always()")
        self.assertEqual(upload["with"]["if-no-files-found"], "error")
        for report in (
            "windows-environment.json",
            "windows-quality-gate.log",
            "coverage-report.json",
        ):
            self.assertIn(report, upload["with"]["path"])

        self.assertNotIn("Publish best-effort Windows compatibility summary", by_name)
        self.assertNotIn("Fail job when PowerShell quality gate fails", by_name)

    def test_supply_chain_reports_are_always_preserved_before_failure(self) -> None:
        path = ROOT / ".github" / "workflows" / "ci.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        steps = data["jobs"]["supply-chain"]["steps"]
        by_name = {step["name"]: step for step in steps}

        direct_steps = (
            ("Audit runtime dependencies", "pip-audit-runtime.json"),
            ("Audit development dependencies", "pip-audit-development.json"),
            ("Audit locked constraints", "pip-audit-locked.json"),
            ("Generate CycloneDX SBOM", "sbom.cdx.json"),
        )
        for index, (name, report) in enumerate(direct_steps):
            step = by_name[name]
            if index:
                self.assertEqual(step["if"], "always()")
            self.assertEqual(step["shell"], "bash")
            self.assertIn("set -euo pipefail", step["run"])
            self.assertIn(report, step["run"])
            self.assertNotIn("set +e", step["run"])
            self.assertNotIn("GITHUB_OUTPUT", step["run"])

        upload = by_name["Upload supply-chain evidence"]
        self.assertEqual(upload["if"], "always()")
        self.assertEqual(upload["with"]["if-no-files-found"], "error")
        for _, report in direct_steps:
            self.assertIn(report, upload["with"]["path"])

        self.assertNotIn("Capture all dependency audits and SBOM", by_name)
        self.assertNotIn("Fail job when an audit or SBOM command fails", by_name)


if __name__ == "__main__":
    unittest.main()
