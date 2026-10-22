"""Observe public pytest reports without changing collection or test outcomes."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

SCHEMA = "tsao.pytest-events/v1"


def pytest_addoption(parser):
    parser.addoption("--tsao-event-report", help="Absolute path of a fresh acceptance witness")


def pytest_configure(config):
    output = config.getoption("--tsao-event-report")
    if not output or not Path(output).is_absolute():
        raise pytest.UsageError("--tsao-event-report must be an absolute path")
    config.pluginmanager.register(EventWitness(config, Path(output)), "tsao-acceptance-event-witness")


class EventWitness:
    def __init__(self, config, output):
        self.config = config
        self.output = output
        self.events = []
        self.selected = []

    def append(self, event):
        event["sequence"] = len(self.events)
        self.events.append(event)

    def pytest_collection_finish(self, session):
        self.selected = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report):
        self.append(
            {"kind": "collection", "nodeid": report.nodeid, "phase": "collect", "outcome": report.outcome}
        )

    def pytest_runtest_logreport(self, report):
        context = getattr(report, "context", None)
        event = {
            "kind": "subtest" if context is not None else "test",
            "nodeid": report.nodeid,
            "phase": report.when,
            "outcome": report.outcome,
            "report_type": f"{type(report).__module__}.{type(report).__qualname__}",
            "wasxfail": hasattr(report, "wasxfail"),
        }
        if context is not None:
            # Observational representations do not replace test objects or alter reports.
            event["context"] = {
                "message": repr(context.msg),
                "parameters": {str(key): repr(value) for key, value in context.kwargs.items()},
            }
        self.append(event)

    def pytest_internalerror(self, excrepr):
        self.append({"kind": "internal_error", "outcome": "failed", "message": str(excrepr)})

    def pytest_sessionfinish(self, session, exitstatus):
        payload = {
            "schema": SCHEMA,
            "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "pytest_version": pytest.__version__,
            "pytest_argv": list(self.config.invocation_params.args),
            "junit_prefix": self.config.getoption("junitprefix"),
            "junit_family": self.config.getini("junit_family"),
            "cwd": os.getcwd(),
            "python_executable": sys.executable,
            "exit_code": int(exitstatus),
            "tests_collected": session.testscollected,
            "selected_nodeids": self.selected,
            "events": self.events,
        }
        if self.output.exists():
            raise pytest.UsageError("refusing to overwrite an acceptance event witness")
        temporary = self.output.with_suffix(self.output.suffix + ".tmp")
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
        temporary.replace(self.output)
