"""Preserve domain CLI access from the single repository entry point."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from .workspace import root, component_paths, component_registry


def forward(component: str, arguments: list[str]) -> int:
    paths = component_paths()
    if component not in paths:
        raise ValueError("unknown component")
    args = arguments[1:] if arguments[:1] == ["--"] else arguments
    folder = paths[component]
    modules = {key: row["entry_module"] for key, row in component_registry().items() if row["kind"] == "module"}
    if component in modules:
        command = [sys.executable, "-m", modules[component], *args]
    elif component == "resindb":
        if not args or args[0] not in {"dev", "build", "preview", "test", "typecheck", "lint", "validate:ci"}:
            raise ValueError("resindb requires a declared package command")
        command = ["npm.cmd" if os.name == "nt" else "npm", "run", args[0], "--", *args[1:]]
    else:
        if len(args) < 2 or args[0] != "script":
            raise ValueError("dft/reasoning: component NAME -- script RELATIVE_SCRIPT.py [arguments]")
        source = (folder / args[1]).resolve()
        if not source.is_relative_to(folder) or source.suffix != ".py" or not source.is_file() or "scripts" not in source.relative_to(folder).parts:
            raise ValueError("script must be a retained domain script inside this component")
        command = [sys.executable, str(source), *args[2:]]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(root()), str(folder), str(folder / "src")])
    # This explicit CLI handoff retains the component's own authorization checks.
    return subprocess.run(command, cwd=folder, env=environment, check=False).returncode
