"""Setuptools command hooks enforcing controlled-metadata containment."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.sdist import sdist as _sdist

_POLICY_MODULE_NAME = "_tsao_distribution_policy_for_build"
_POLICY_PATH = Path(__file__).resolve().parent / "tsao" / "distribution_policy.py"
_POLICY_SPEC = importlib.util.spec_from_file_location(_POLICY_MODULE_NAME, _POLICY_PATH)
if _POLICY_SPEC is None or _POLICY_SPEC.loader is None:
    raise RuntimeError(f"unable to load distribution policy from {_POLICY_PATH}")

_distribution_policy = importlib.util.module_from_spec(_POLICY_SPEC)
# dataclasses resolves annotations through sys.modules while the module executes.
sys.modules[_POLICY_MODULE_NAME] = _distribution_policy
_POLICY_SPEC.loader.exec_module(_distribution_policy)

assert_public_distribution_allowed = _distribution_policy.assert_public_distribution_allowed


class ControlledSdist(_sdist):
    def run(self) -> None:
        assert_public_distribution_allowed(Path.cwd(), artifact_kind="public sdist")
        super().run()


cmdclass: dict[str, type] = {"sdist": ControlledSdist}

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # pragma: no cover - wheel is present in the declared build environment.
    _bdist_wheel = None

if _bdist_wheel is not None:

    class ControlledWheel(_bdist_wheel):  # type: ignore[misc,valid-type]
        def run(self) -> None:
            assert_public_distribution_allowed(Path.cwd(), artifact_kind="public wheel")
            super().run()

    cmdclass["bdist_wheel"] = ControlledWheel

setup(cmdclass=cmdclass)
