from __future__ import annotations

import logging
import os
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest

_IGNORED_ENV_KEYS = {"PYTEST_CURRENT_TEST"}


def _stable_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in _IGNORED_ENV_KEYS}


@pytest.fixture(autouse=True)
def reject_global_state_leaks() -> Iterator[None]:
    """Fail tests that leak process-global state and restore it before reporting."""
    before_path = tuple(sys.path)
    before_environment = _stable_environment()
    before_cwd = Path.cwd()
    before_handlers = tuple(logging.root.handlers)
    before_warning_filters = tuple(warnings.filters)

    yield

    after_path = tuple(sys.path)
    after_environment = _stable_environment()
    after_cwd = Path.cwd()
    after_handlers = tuple(logging.root.handlers)
    after_warning_filters = tuple(warnings.filters)

    problems: list[str] = []
    if after_path != before_path:
        problems.append("sys.path")
        sys.path[:] = before_path
    if after_environment != before_environment:
        problems.append("os.environ")
        for key in set(os.environ) - set(before_environment) - _IGNORED_ENV_KEYS:
            os.environ.pop(key, None)
        os.environ.update(before_environment)
    if after_cwd != before_cwd:
        problems.append("cwd")
        os.chdir(before_cwd)
    if after_handlers != before_handlers:
        problems.append("logging.root.handlers")
        logging.root.handlers[:] = list(before_handlers)
    if after_warning_filters != before_warning_filters:
        problems.append("warnings.filters")
        warnings.filters[:] = list(before_warning_filters)

    assert not problems, "test leaked global state: " + ", ".join(problems)
