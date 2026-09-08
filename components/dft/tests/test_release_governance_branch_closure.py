from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(relative: str, name: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseGovernanceBranchClosureTests(unittest.TestCase):
    bandit: Any
    ai: Any
    links: Any
    claims: Any
    periodic_utils: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.bandit = load_script("scripts/run_bandit.py", "release_branch_bandit")
        cls.ai = load_script("scripts/validate_ai_assets.py", "release_branch_ai")
        cls.links = load_script("scripts/validate_readme_links.py", "release_branch_links")
        cls.claims = load_script("scripts/validate_capability_claims.py", "release_branch_claims")
        cls.periodic_utils = load_script(
            "skills/tsao-periodic-dft-materials/scripts/utils.py",
            "release_branch_periodic_utils",
        )

    def test_periodic_utils_mapping_hash_dump_and_render_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.yaml"
            source.write_text("a: 1\n", encoding="utf-8")
            self.assertEqual(self.periodic_utils.load_yaml(source), {"a": 1})
            source.write_text("- bad\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.periodic_utils.load_yaml(source)

            destination = root / "nested" / "out.yaml"
            self.periodic_utils.dump_yaml({"a": 1}, destination)
            self.assertEqual(yaml.safe_load(destination.read_text(encoding="utf-8")), {"a": 1})
            self.assertRegex(self.periodic_utils.sha256_file(destination), r"^[0-9a-f]{64}$")

            with redirect_stdout(io.StringIO()) as stdout:
                self.periodic_utils.print_result({"ok": True}, as_json=True)
            self.assertTrue(json.loads(stdout.getvalue())["ok"])
            with redirect_stdout(io.StringIO()) as stdout:
                self.periodic_utils.print_result({"ok": True}, as_json=False)
            self.assertIn("ok: True", stdout.getvalue())

    def test_bandit_allowlist_runner_validation_and_cli_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            allowlist = root / "allowlist.yaml"

            invalid_documents: list[Any] = [
                [],
                {"schema_version": 2, "entries": []},
                {"schema_version": 1, "entries": {}},
                {"schema_version": 1, "entries": ["bad"]},
                {"schema_version": 1, "entries": [{"path": "", "test_id": "B1", "reason": "x"}]},
                {"schema_version": 1, "entries": [{"path": "a.py", "test_id": "", "reason": "x"}]},
                {"schema_version": 1, "entries": [{"path": "a.py", "test_id": "B1", "reason": ""}]},
                {
                    "schema_version": 1,
                    "entries": [
                        {"path": "a.py", "test_id": "B1", "reason": "x"},
                        {"path": "a.py", "test_id": "B1", "reason": "y"},
                    ],
                },
            ]
            for document in invalid_documents:
                allowlist.write_text(yaml.safe_dump(document), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.bandit.load_allowlist(allowlist)

            allowlist.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "entries": [{"path": "scripts/a.py", "test_id": "B1", "reason": "reviewed"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                self.bandit.load_allowlist(allowlist),
                {("scripts/a.py", "B1"): "reviewed"},
            )
            self.assertEqual(self.bandit.normalize_filename(str(ROOT / "scripts" / "a.py")), "scripts/a.py")
            self.assertTrue(self.bandit.normalize_filename("/outside/a.py").endswith("/outside/a.py"))

            def completed_with(payload: Any, create_report: bool = True) -> Any:
                def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
                    if create_report:
                        Path(command[-1]).write_text(json.dumps(payload), encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0, stdout="out", stderr="err")

                return run

            with patch.object(
                self.bandit.subprocess,
                "run",
                side_effect=completed_with({"results": [{"test_id": "B1"}, "bad"]}),
            ):
                findings, output = self.bandit.run_bandit()
            self.assertEqual(findings, [{"test_id": "B1"}])
            self.assertEqual(output, "outerr")

            with (
                patch.object(
                    self.bandit.subprocess,
                    "run",
                    side_effect=completed_with({"results": {}}, create_report=True),
                ),
                self.assertRaises(RuntimeError),
            ):
                self.bandit.run_bandit()
            with (
                patch.object(
                    self.bandit.subprocess,
                    "run",
                    side_effect=completed_with({}, create_report=False),
                ),
                self.assertRaises(RuntimeError),
            ):
                self.bandit.run_bandit()

        findings = [
            {
                "filename": str(ROOT / "scripts" / "a.py"),
                "test_id": "B1",
                "issue_severity": "LOW",
                "line_number": 1,
            },
            {
                "filename": str(ROOT / "scripts" / "b.py"),
                "test_id": "B2",
                "issue_severity": "MEDIUM",
                "line_number": 2,
            },
            {
                "filename": str(ROOT / "scripts" / "c.py"),
                "test_id": "B3",
                "issue_severity": "LOW",
                "line_number": 3,
            },
        ]
        with (
            patch.object(
                self.bandit,
                "load_allowlist",
                return_value={
                    ("scripts/a.py", "B1"): "reviewed",
                    ("scripts/stale.py", "B9"): "stale",
                },
            ),
            patch.object(self.bandit, "run_bandit", return_value=(findings, "")),
        ):
            failures, observed = self.bandit.validate()
        self.assertEqual(observed, findings)
        self.assertTrue(any("MEDIUM" in item for item in failures))
        self.assertTrue(any("unexplained" in item for item in failures))
        self.assertTrue(any("stale" in item for item in failures))

        validation_cases: tuple[tuple[bool, tuple[list[str], list[dict[str, Any]]], int], ...] = (
            (True, ([], []), 0),
            (False, (["bad"], []), 1),
        )
        for json_output, validation, expected in validation_cases:
            argv = ["run_bandit.py", *(["--json"] if json_output else [])]
            with (
                patch.object(sys, "argv", argv),
                patch.object(self.bandit, "validate", return_value=validation),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.bandit.main(), expected)
        with (
            patch.object(sys, "argv", ["run_bandit.py", "--json"]),
            patch.object(self.bandit, "validate", side_effect=ValueError("boom")),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(self.bandit.main(), 1)
        self.assertIn("boom", stdout.getvalue())

    def test_readme_link_helper_validation_and_cli_branches(self) -> None:
        stripped = self.links.strip_fenced_code("before\n```py\n[bad](missing)\n```\nafter")
        self.assertNotIn("missing", stripped)
        self.assertEqual(self.links.markdown_target('<target.md> "title"'), "target.md")
        self.assertEqual(self.links.markdown_target("target.md title"), "target.md")
        self.assertEqual(self.links.github_slug("`Hello`, <em>World</em>!"), "hello-world")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.md"
            target.write_text('# Heading\n# Heading\n<a id="explicit"></a>\n', encoding="utf-8")
            self.assertEqual(
                self.links.markdown_anchors(target),
                {"heading", "heading-1", "explicit"},
            )
            source = root / "README.md"
            source.write_text(
                "\n".join(
                    (
                        "[external](https://example.com)",
                        "[protocol](ftp://example.com/a)",
                        "[unsafe](../escape.md)",
                        "[missing](missing.md)",
                        "[valid](target.md#heading)",
                        "[bad-anchor](target.md#missing)",
                        '<a href="//cdn.example.com/a">cdn</a>',
                    )
                ),
                encoding="utf-8",
            )
            missing_readme = root / "MISSING.md"
            failures, checked, external = self.links.validate(
                root=root,
                readme_files=(source, missing_readme),
            )
            self.assertEqual(len(checked), 1)
            self.assertEqual(external, 2)
            self.assertTrue(any("unsupported link scheme" in item for item in failures))
            self.assertTrue(any("unsafe local link" in item for item in failures))
            self.assertTrue(any("missing local link target" in item for item in failures))
            self.assertTrue(any("missing Markdown anchor" in item for item in failures))
            self.assertTrue(any("missing README file" in item for item in failures))

        for json_output, result, expected in (
            (True, ([], [{"source": "README.md", "target": "x"}], 1), 0),
            (False, (["bad"], [], 0), 1),
        ):
            argv = ["validate_readme_links.py", *(["--json"] if json_output else [])]
            with (
                patch.object(sys, "argv", argv),
                patch.object(self.links, "validate", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.links.main(), expected)

    def write_ai_fixture(self, root: Path) -> tuple[Path, dict[str, Any]]:
        (root / "assets" / "ai" / "hero").mkdir(parents=True, exist_ok=True)
        (root / "assets" / "ai").mkdir(parents=True, exist_ok=True)
        (root / "VERSION").write_text("1.0\n", encoding="utf-8")
        cover = root / "assets" / "ai" / "hero" / "cover.svg"
        cover.write_text(
            '<svg width="100" height="50" aria-label="AI-generated conceptual illustration">'
            "<text>NOT SCIENTIFIC DATA</text></svg>",
            encoding="utf-8",
        )
        prompt = root / "assets" / "ai" / "prompt.txt"
        prompt.write_text("prompt", encoding="utf-8")
        for name in ("README.md", "README_EN.md"):
            (root / name).write_text(
                "assets/ai/hero/cover.svg\nAI-GENERATED CONCEPTUAL ILLUSTRATION\n",
                encoding="utf-8",
            )
        manifest = {
            "release": "1.0",
            "assets": [
                {
                    "role": "hero",
                    "path": "assets/ai/hero/cover.svg",
                    "width_px": 100,
                    "height_px": 50,
                    "sha256": self.ai.digest(cover),
                    "ai_generated": True,
                    "illustrative_only": True,
                    "quantitative": False,
                    "computed_surface": False,
                    "source_prompt": "assets/ai/prompt.txt",
                    "source_generation_id": "GEN-1",
                    "allowed_uses": ["cover"],
                    "forbidden_uses": ["data"],
                }
            ],
        }
        manifest_path = root / "assets" / "ai" / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
        return manifest_path, manifest

    def test_ai_asset_validation_and_cli_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest = self.write_ai_fixture(root)
            with (
                patch.object(self.ai, "ROOT", root),
                patch.object(
                    self.ai,
                    "README_NAMES",
                    ("README.md", "README_EN.md"),
                ),
            ):
                self.assertEqual(self.ai.validate(manifest_path), [])

                manifest_path.write_text("[", encoding="utf-8")
                self.assertTrue(self.ai.validate(manifest_path))
                manifest_path.write_text("- bad\n", encoding="utf-8")
                self.assertIn("manifest root must be a mapping", self.ai.validate(manifest_path))

                variants: list[dict[str, Any]] = []
                for mutate in (
                    lambda value: value.update({"release": "2.0"}),
                    lambda value: value.update({"assets": []}),
                    lambda value: value.update({"assets": ["bad"]}),
                ):
                    variant = json.loads(json.dumps(manifest))
                    mutate(variant)
                    variants.append(variant)
                for variant in variants:
                    manifest_path.write_text(yaml.safe_dump(variant), encoding="utf-8")
                    self.assertTrue(self.ai.validate(manifest_path))

                item_variants: list[dict[str, Any]] = []
                for key, value in (
                    ("role", "other"),
                    ("path", ""),
                    ("path", "../escape.svg"),
                    ("path", "assets/ai/hero/missing.svg"),
                    ("path", "assets/ai/hero/cover.png"),
                    ("width_px", 101),
                    ("sha256", "0" * 64),
                    ("ai_generated", False),
                    ("illustrative_only", False),
                    ("quantitative", True),
                    ("computed_surface", True),
                    ("source_prompt", "missing.txt"),
                    ("source_generation_id", ""),
                    ("allowed_uses", []),
                    ("forbidden_uses", []),
                ):
                    variant = json.loads(json.dumps(manifest))
                    variant["assets"][0][key] = value
                    item_variants.append(variant)
                (root / "assets" / "ai" / "hero" / "cover.png").write_text("not-svg", encoding="utf-8")
                for variant in item_variants:
                    manifest_path.write_text(yaml.safe_dump(variant), encoding="utf-8")
                    self.assertTrue(self.ai.validate(manifest_path))

                invalid_svg = json.loads(json.dumps(manifest))
                cover = root / "assets" / "ai" / "hero" / "cover.svg"
                cover.write_text("<svg>", encoding="utf-8")
                invalid_svg["assets"][0]["sha256"] = self.ai.digest(cover)
                manifest_path.write_text(yaml.safe_dump(invalid_svg), encoding="utf-8")
                self.assertTrue(self.ai.validate(manifest_path))

                _, manifest = self.write_ai_fixture(root)
                manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
                (root / "README_EN.md").unlink()
                self.assertTrue(self.ai.validate(manifest_path))

        for result, expected in (([], 0), (["bad"], 1)):
            with (
                patch.object(sys, "argv", ["validate_ai_assets.py", "--manifest", "x"]),
                patch.object(self.ai, "validate", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.ai.main(), expected)

    def write_claim_fixture(self, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        (root / "docs").mkdir(parents=True)
        (root / "skills" / "alpha" / "scripts").mkdir(parents=True)
        (root / "VERSION").write_text("1.0\n", encoding="utf-8")
        (root / "skills" / "alpha" / "scripts" / "tool.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "skills" / "alpha" / "SKILL.md").write_text("skill\n", encoding="utf-8")
        for name in ("README.md", "README_EN.md"):
            (root / name).write_text("L2_VALIDATED_ADAPTER L3_EXECUTION_TESTED\n", encoding="utf-8")
        policy = {
            "release": "1.0",
            "support_levels": [
                "L0_REFERENCE",
                "L1_HANDOFF",
                "L2_VALIDATED_ADAPTER",
                "L3_EXECUTION_TESTED",
            ],
            "l3_required_evidence": ["engine", "version", "site", "run_id", "artifact_sha256"],
            "forbidden_claim_phrases": [
                "forbidden-one",
                "forbidden-two",
                "forbidden-three",
                "forbidden-four",
                "forbidden-five",
            ],
        }
        capability = {
            "release": "1.0",
            "capabilities": [
                {
                    "id": "cap-1",
                    "skill": "alpha",
                    "support_level": "L2_VALIDATED_ADAPTER",
                    "scripts": ["tool.py"],
                }
            ],
        }
        return capability, policy

    def write_claim_documents(
        self,
        root: Path,
        capability: dict[str, Any],
        policy: dict[str, Any],
    ) -> None:
        (root / "docs" / "CAPABILITY_STATUS.yaml").write_text(
            yaml.safe_dump(capability),
            encoding="utf-8",
        )
        (root / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml").write_text(
            yaml.safe_dump(policy),
            encoding="utf-8",
        )

    def test_capability_claim_contract_failure_branches_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capability, policy = self.write_claim_fixture(root)
            self.write_claim_documents(root, capability, policy)
            self.assertEqual(self.claims.validate(root), [])

            bad_yaml = root / "bad.yaml"
            bad_yaml.write_text("[", encoding="utf-8")
            self.assertIsNotNone(self.claims.load_mapping(bad_yaml)[1])
            bad_yaml.write_text("- bad\n", encoding="utf-8")
            self.assertIsNotNone(self.claims.load_mapping(bad_yaml)[1])

            variants: list[tuple[dict[str, Any], dict[str, Any]]] = []
            cap = json.loads(json.dumps(capability))
            cap["release"] = "2.0"
            variants.append((cap, policy))
            pol = json.loads(json.dumps(policy))
            pol["support_levels"] = []
            variants.append((capability, pol))
            pol = json.loads(json.dumps(policy))
            pol["l3_required_evidence"] = []
            variants.append((capability, pol))
            pol = json.loads(json.dumps(policy))
            pol["forbidden_claim_phrases"] = []
            variants.append((capability, pol))
            cap = json.loads(json.dumps(capability))
            cap["capabilities"] = []
            variants.append((cap, policy))
            cap = json.loads(json.dumps(capability))
            cap["capabilities"] = ["bad"]
            variants.append((cap, policy))
            for cap_value, policy_value in variants:
                self.write_claim_documents(root, cap_value, policy_value)
                self.assertTrue(self.claims.validate(root))

            entry_variants: list[dict[str, Any]] = []
            for mutation in (
                lambda entry: entry.update({"id": ""}),
                lambda entry: entry.update({"support_level": "BAD"}),
                lambda entry: entry.update({"scripts": []}),
                lambda entry: entry.update({"scripts": ["missing.py"]}),
                lambda entry: entry.update({"skill": None}),
                lambda entry: entry.update({"execution_evidence": {}}),
            ):
                cap = json.loads(json.dumps(capability))
                mutation(cap["capabilities"][0])
                entry_variants.append(cap)
            duplicate = json.loads(json.dumps(capability))
            duplicate["capabilities"].append(json.loads(json.dumps(duplicate["capabilities"][0])))
            entry_variants.append(duplicate)
            l3_missing = json.loads(json.dumps(capability))
            l3_missing["capabilities"][0]["support_level"] = "L3_EXECUTION_TESTED"
            entry_variants.append(l3_missing)
            l3_bad_digest = json.loads(json.dumps(l3_missing))
            l3_bad_digest["capabilities"][0]["execution_evidence"] = {
                "engine": "vasp",
                "version": "1",
                "site": "site",
                "run_id": "run",
                "artifact_sha256": "bad",
            }
            entry_variants.append(l3_bad_digest)
            for cap_value in entry_variants:
                self.write_claim_documents(root, cap_value, policy)
                self.assertTrue(self.claims.validate(root))

            self.write_claim_documents(root, capability, policy)
            (root / "README.md").write_text("forbidden-one\n", encoding="utf-8")
            self.assertTrue(self.claims.validate(root))
            (root / "README.md").unlink()
            self.assertTrue(self.claims.validate(root))
            (root / "docs" / "CAPABILITY_STATUS.yaml").unlink()
            self.assertTrue(self.claims.validate(root))

        for json_output, failures, expected in ((True, [], 0), (False, ["bad"], 1)):
            argv = ["validate_capability_claims.py", *(["--json"] if json_output else [])]
            with (
                patch.object(sys, "argv", argv),
                patch.object(self.claims, "validate", return_value=failures),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.claims.main(), expected)


if __name__ == "__main__":
    unittest.main()
