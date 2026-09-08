from __future__ import annotations

import ast
import json
import py_compile
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.validate_skill_spec import validate_repository_skills  # noqa: E402

ROOTS = (Path("tsao_computation"), Path("scripts"), Path("tests"))


def main() -> int:
    problems: list[str] = []
    files = sorted(path for root in ROOTS for path in root.rglob("*.py"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if "\t" in line:
                problems.append(f"{path}:{line_number}: tab character")
            if line.rstrip() != line:
                problems.append(f"{path}:{line_number}: trailing whitespace")
        try:
            tree = ast.parse(text, filename=str(path))
            py_compile.compile(str(path), doraise=True)
        except (SyntaxError, py_compile.PyCompileError) as exc:
            problems.append(f"{path}: parse/compile failure: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                problems.append(f"{path}:{node.lineno}: bare except")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (
                    path.parts[0] == "tsao_computation"
                    and not node.name.startswith("_")
                    and node.returns is None
                ):
                    problems.append(
                        f"{path}:{node.lineno}: public function lacks return annotation"
                    )
                defaults = list(node.args.defaults) + [
                    value for value in node.args.kw_defaults if value
                ]
                for default in defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        problems.append(f"{path}:{node.lineno}: mutable default argument")
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                problems.append(f"{path}:{node.lineno}: wildcard import")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"eval", "exec"}
            ):
                problems.append(f"{path}:{node.lineno}: dynamic code execution")

    skill_report = validate_repository_skills(Path("."))
    skill_problems = skill_report.get("problems")
    if isinstance(skill_problems, list):
        problems.extend(str(item) for item in skill_problems)

    report = {
        "schema_version": "1.1",
        "passed": not problems,
        "python_files": len(files),
        "agent_skills": {
            "status": skill_report["status"],
            "count": skill_report["skill_count"],
        },
        "problems": problems,
    }
    output = Path("evidence/quality-check.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
