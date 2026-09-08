#!/usr/bin/env python3
"""Audit language roles and evidence-bounded acceleration candidates."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
EXCLUDED_PARTS = {
    ".git",
    ".audit-snapshot",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}
LANGUAGES = {
    ".py": "Python",
    ".ps1": "PowerShell",
    ".sh": "Shell",
    ".bash": "Shell",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".hpp": "C/C++ Header",
    ".cu": "CUDA C++",
    ".cuh": "CUDA C++ Header",
    ".f": "Fortran",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".f08": "Fortran",
    ".rs": "Rust",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".csv": "CSV",
    ".svg": "SVG",
}
CODE_LANGUAGES = {
    "Python",
    "PowerShell",
    "Shell",
    "C",
    "C/C++ Header",
    "C++",
    "CUDA C++",
    "CUDA C++ Header",
    "Fortran",
    "Rust",
}
NATIVE_LANGUAGES = {
    "C",
    "C/C++ Header",
    "C++",
    "CUDA C++",
    "CUDA C++ Header",
    "Fortran",
    "Rust",
}
CONTROL_IMPORTS = {
    "argparse",
    "csv",
    "hashlib",
    "importlib",
    "json",
    "os",
    "pathlib",
    "shutil",
    "subprocess",
    "tomllib",
    "xml",
    "yaml",
}
NUMERIC_IMPORTS = {"jax", "math", "matplotlib", "numpy", "scipy", "torch"}
GPU_IMPORTS = {"cudf", "cupy", "cuequivariance", "jax", "numba", "torch"}
PARALLEL_IMPORTS = {
    "concurrent",
    "dask",
    "joblib",
    "mpi4py",
    "multiprocessing",
    "ray",
    "threading",
}
ENGINE_TOKENS = {
    "cp2k",
    "g16",
    "g09",
    "gaussian",
    "pw.x",
    "quantum-espresso",
    "srun",
    "sbatch",
    "vasp",
}


class SignalVisitor(ast.NodeVisitor):
    """Collect conservative static signals without claiming a bottleneck."""

    def __init__(self) -> None:
        self.imports: set[str] = set()
        self.loops = 0
        self.nested_loops = 0
        self.subprocess_calls = 0
        self.file_reads = 0
        self._loop_depth = 0

    @staticmethod
    def call_name(node: ast.AST) -> str:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name.split(".", 1)[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.add(node.module.split(".", 1)[0])

    def _visit_loop(self, node: ast.For | ast.AsyncFor | ast.While) -> None:
        self.loops += 1
        self.nested_loops += int(self._loop_depth > 0)
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_loop(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self.call_name(node.func)
        self.subprocess_calls += int(name.startswith(("subprocess.", "os.system")))
        self.file_reads += int(name.endswith(("read_text", "read_bytes", "read", "readlines")))
        self.generic_visit(node)


def _tracked_paths(root: Path) -> list[Path]:
    git_executable = shutil.which("git")
    completed = None
    if git_executable is not None:
        try:
            completed = subprocess.run(
                [git_executable, "ls-files", "-z"],
                cwd=root,
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            completed = None
    if completed is not None and completed.returncode == 0:
        candidates = [root / item for item in completed.stdout.decode("utf-8").split("\0") if item]
    else:
        candidates = list(root.rglob("*"))
    return sorted(
        (
            path
            for path in candidates
            if path.is_file() and not EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
        ),
        key=lambda path: path.as_posix(),
    )


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
        if b"\0" in data:
            return None
        return data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _contains(text: str, tokens: set[str]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in tokens)


def _candidate(path: str, signals: SignalVisitor, numeric: bool) -> dict[str, Any] | None:
    reasons: list[str] = []
    score = 0
    if signals.nested_loops:
        reasons.append(f"{signals.nested_loops} nested loop(s)")
        score += 4 * signals.nested_loops
    elif signals.loops >= 3:
        reasons.append(f"{signals.loops} explicit loop(s)")
        score += signals.loops
    if signals.file_reads >= 3:
        reasons.append(f"{signals.file_reads} file-read call(s)")
        score += min(signals.file_reads, 6)
    if signals.subprocess_calls >= 2:
        reasons.append(f"{signals.subprocess_calls} external-process call(s)")
        score += signals.subprocess_calls
    if numeric and signals.loops:
        reasons.append("numeric imports combined with Python loops")
        score += 4
    if score < 4:
        return None
    action = "profile-before-native-migration"
    if signals.subprocess_calls >= 2 and not signals.nested_loops:
        action = "parallelize-independent-processes-with-bounded-workers"
    elif signals.file_reads >= 3 and not numeric:
        action = "batch-or-stream-io-before-changing-language"
    return {
        "path": path,
        "score": score,
        "reasons": reasons,
        "recommended_action": action,
    }


def build_report(root: Path) -> dict[str, Any]:
    """Build a deterministic, machine-readable repository audit."""
    root = root.resolve()
    if not root.is_dir():
        return {
            "ok": False,
            "schema_version": SCHEMA_VERSION,
            "errors": [f"not a directory: {root}"],
        }

    language_files: Counter[str] = Counter()
    language_lines: Counter[str] = Counter()
    python_roles: Counter[str] = Counter()
    parse_failures: list[dict[str, str]] = []
    candidates: list[dict[str, Any]] = []
    external_files: set[str] = set()
    parallel_files: set[str] = set()
    gpu_files: set[str] = set()
    text_files = 0

    for path in _tracked_paths(root):
        text = _read_text(path)
        if text is None:
            continue
        text_files += 1
        language = LANGUAGES.get(path.suffix.lower(), "Other text")
        language_files[language] += 1
        language_lines[language] += len(text.splitlines())
        relative = path.relative_to(root).as_posix()
        if language != "Python":
            if language in CODE_LANGUAGES and _contains(text, ENGINE_TOKENS):
                external_files.add(relative)
            continue

        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            parse_failures.append({"path": relative, "error": f"line {exc.lineno or 0}: {exc.msg}"})
            continue
        signals = SignalVisitor()
        signals.visit(tree)
        control = bool(signals.imports & CONTROL_IMPORTS) or signals.subprocess_calls > 0
        numeric = bool(signals.imports & NUMERIC_IMPORTS)
        if control and numeric:
            role = "mixed-control-and-numeric"
        elif control:
            role = "control-plane"
        elif numeric or signals.nested_loops:
            role = "numeric-candidate"
        else:
            role = "general"
        python_roles[role] += 1
        if signals.subprocess_calls or _contains(text, ENGINE_TOKENS):
            external_files.add(relative)
        if signals.imports & PARALLEL_IMPORTS or _contains(
            text,
            {"processpoolexecutor", "threadpoolexecutor", "mpirun", "job array"},
        ):
            parallel_files.add(relative)
        if signals.imports & GPU_IMPORTS or _contains(
            text,
            {"__dlpack__", "array_api", "cuda", "hip", "sycl"},
        ):
            gpu_files.add(relative)
        candidate = _candidate(relative, signals, numeric)
        if candidate:
            candidates.append(candidate)

    source_files = sum(language_files[name] for name in CODE_LANGUAGES)
    source_lines = sum(language_lines[name] for name in CODE_LANGUAGES)
    native_files = sum(language_files[name] for name in NATIVE_LANGUAGES)
    native_lines = sum(language_lines[name] for name in NATIVE_LANGUAGES)
    python_lines = language_lines["Python"]
    python_share = round(100.0 * python_lines / source_lines, 2) if source_lines else 0.0
    native_share = round(100.0 * native_lines / source_lines, 2) if source_lines else 0.0
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    numeric_roles = python_roles["numeric-candidate"] + python_roles["mixed-control-and-numeric"]
    conclusion = (
        "Python is predominantly the orchestration, validation, parsing and evidence "
        "control plane; external DFT engines remain the compute plane."
    )
    if numeric_roles > python_roles["control-plane"]:
        conclusion = (
            "Python has a material numerical surface in addition to orchestration; "
            "profile ranked candidates before selecting native implementations."
        )

    return {
        "ok": not parse_failures,
        "schema_version": SCHEMA_VERSION,
        "scope": "tracked UTF-8 files; caches, generated snapshots and binaries excluded",
        "summary": {
            "text_files": text_files,
            "source_files": source_files,
            "source_lines": source_lines,
            "python_files": language_files["Python"],
            "python_lines": python_lines,
            "python_source_line_percent": python_share,
            "native_files": native_files,
            "native_lines": native_lines,
            "native_source_line_percent": native_share,
        },
        "languages": [
            {
                "language": name,
                "files": language_files[name],
                "lines": language_lines[name],
            }
            for name in sorted(
                language_files,
                key=lambda item: (-language_lines[item], item),
            )
        ],
        "architecture": {
            "python_roles": dict(sorted(python_roles.items())),
            "external_engine_boundary_files": sorted(external_files),
            "parallel_or_distributed_files": sorted(parallel_files),
            "gpu_or_array_interface_files": sorted(gpu_files),
            "conclusion": conclusion,
        },
        "ranked_static_candidates": candidates[:40],
        "parse_failures": parse_failures,
        "recommended_sequence": [
            "Keep Python for orchestration, schemas, provenance, CLI and engine adapters.",
            "Use engine-native GPU builds before injecting CUDA-X into packaged DFT engines.",
            "Parallelize independent jobs and parsers with bounded pools or scheduler arrays.",
            "Use Array API and DLPack at tensor boundaries to avoid lock-in and copies.",
            "Move only measured kernels to a narrow C ABI/C++20 core with Python bindings.",
            "Require equivalence, transfer-cost and device-memory gates for GPU kernels.",
            "Use edge devices for validated surrogate inference and remote-DFT orchestration.",
        ],
        "non_claims": [
            "Static ranking is not runtime profiling and does not establish a bottleneck.",
            "Library mentions do not prove installation, execution, correctness or speedup.",
            "C++ or GPU migration requires representative benchmark evidence.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the audit as a concise human-readable report."""
    if not report.get("ok"):
        failures = report.get("errors") or report.get("parse_failures") or []
        detail = json.dumps(failures, ensure_ascii=False, indent=2)
        return f"# Compute Architecture Audit\n\nAudit failed.\n\n```json\n{detail}\n```\n"
    summary = report["summary"]
    lines = [
        "# Executable Compute Architecture Audit",
        "",
        f"Schema: `{report['schema_version']}`",
        "",
        "## Repository composition",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Audited UTF-8 text files | {summary['text_files']} |",
        f"| Source files | {summary['source_files']} |",
        f"| Source lines | {summary['source_lines']} |",
        f"| Python files | {summary['python_files']} |",
        f"| Python source-line share | {summary['python_source_line_percent']}% |",
        f"| Native-language files | {summary['native_files']} |",
        f"| Native source-line share | {summary['native_source_line_percent']}% |",
        "",
        "## Architecture conclusion",
        "",
        str(report["architecture"]["conclusion"]),
        "",
        "## Language inventory",
        "",
        "| Language | Files | Lines |",
        "|---|---:|---:|",
    ]
    for item in report["languages"]:
        lines.append(f"| {item['language']} | {item['files']} | {item['lines']} |")
    lines.extend(
        [
            "",
            "## Highest static candidates",
            "",
            "These entries require runtime profiling before migration.",
            "",
        ]
    )
    candidates = report["ranked_static_candidates"][:20]
    if candidates:
        lines.extend(["| Path | Score | Evidence | Action |", "|---|---:|---|---|"])
        for item in candidates:
            evidence = "; ".join(item["reasons"]).replace("|", "\\|")
            lines.append(f"| `{item['path']}` | {item['score']} | {evidence} | `{item['recommended_action']}` |")
    else:
        lines.append("No static candidate crossed the conservative threshold.")
    lines.extend(["", "## Required implementation sequence", ""])
    for index, item in enumerate(report["recommended_sequence"], start=1):
        lines.append(f"{index}. {item}")
    lines.extend(["", "## Non-claims", ""])
    lines.extend(f"- {item}" for item in report["non_claims"])
    return "\n".join(lines) + "\n"


def _write(path: Path | None, text: str) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()
    report = build_report(args.root)
    rendered_json = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    _write(args.json_out, rendered_json)
    _write(args.markdown_out, render_markdown(report))
    if args.json_output:
        print(rendered_json, end="")
    else:
        summary = report.get("summary", {})
        print(
            "Compute architecture audit: "
            f"{'PASS' if report.get('ok') else 'FAIL'}; "
            f"Python={summary.get('python_source_line_percent', 'n/a')}%; "
            f"native={summary.get('native_source_line_percent', 'n/a')}%; "
            f"candidates={len(report.get('ranked_static_candidates', []))}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
