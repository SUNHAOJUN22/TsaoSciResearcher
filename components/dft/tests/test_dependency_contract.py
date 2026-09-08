from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_dependency_validator():
    path = ROOT / "scripts" / "validate_dependencies.py"
    spec = importlib.util.spec_from_file_location("tsao_validate_dependencies", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate_dependencies = load_dependency_validator()

BASE_PYPROJECT = """[project]
name = "fixture"
version = "0.4.0a1"
requires-python = ">=3.10"
dependencies = ["PyYAML>=6,<7"]

[project.optional-dependencies]
dev = [
  "ruff==0.15.22",
  "tomli>=2,<3; python_version < '3.11'",
]

[tool.ruff]
target-version = "py310"
"""


class DependencyContractTests(unittest.TestCase):
    def write_fixture(self, root: Path, *, pyproject: str = BASE_PYPROJECT) -> None:
        (root / "requirements.txt").write_text("PyYAML>=6,<7\n", encoding="utf-8")
        (root / "requirements-dev.txt").write_text(
            '-r requirements.txt\nruff==0.15.22\ntomli>=2,<3; python_version < "3.11"\n',
            encoding="utf-8",
        )
        (root / "VERSION").write_text("0.4.0-alpha.1\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    def test_current_repository_contract(self):
        self.assertEqual(validate_dependencies.validate(ROOT), [])

    def test_runtime_dependency_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_fixture(root)
            (root / "requirements.txt").write_text("PyYAML>=6,<7\nnumpy>=1.24,<3\n", encoding="utf-8")
            failures = validate_dependencies.validate(root)
            self.assertIn("requirements.txt and project.dependencies differ", failures)

    def test_dev_dependency_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pyproject = BASE_PYPROJECT.replace(
                "  \"tomli>=2,<3; python_version < '3.11'\",\n",
                "",
            )
            self.write_fixture(root, pyproject=pyproject)
            failures = validate_dependencies.validate(root)
            self.assertIn("requirements-dev.txt and project.optional-dependencies.dev differ", failures)

    def test_python_floor_and_ruff_target_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_fixture(
                root,
                pyproject=BASE_PYPROJECT.replace('target-version = "py310"', 'target-version = "py311"'),
            )
            failures = validate_dependencies.validate(root)
            self.assertTrue(any(item.startswith("Ruff target 3.11") for item in failures), failures)


if __name__ == "__main__":
    unittest.main()
