from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATURITY = {"A0", "A1", "A2", "A3", "A4", "A5"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    source_path = root / "registry" / "adapters.json"
    packaged_path = root / "tsao_computation" / "data" / "registry" / "adapters.json"
    try:
        records = _load(source_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"invalid adapter registry: {exc}"]
    if not isinstance(records, list):
        return ["adapter registry must be an array"]
    if not packaged_path.is_file() or source_path.read_bytes() != packaged_path.read_bytes():
        problems.append("packaged adapter registry is not synchronized")

    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            problems.append(f"adapter entry {index} is not an object")
            continue
        slug = record.get("slug")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            problems.append(f"adapter entry {index} has an invalid slug")
            continue
        if slug in seen:
            problems.append(f"duplicate adapter slug: {slug}")
        seen.add(slug)

        executables = record.get("executables")
        if not isinstance(executables, list) or any(
            not isinstance(item, str) or not item for item in executables
        ):
            problems.append(f"adapter {slug} has invalid executable declarations")
            executables = []
        modules = record.get("python_modules")
        if modules is not None and (
            not isinstance(modules, list)
            or not modules
            or any(not isinstance(item, str) or not item for item in modules)
        ):
            problems.append(f"adapter {slug} has invalid Python module declarations")
        if "python" in executables and not modules:
            problems.append(f"adapter {slug} uses Python but declares no required modules")

        maturity = record.get("maturity")
        certification = record.get("certification")
        if maturity not in MATURITY:
            problems.append(f"adapter {slug} has invalid maturity")
        if not isinstance(certification, dict):
            problems.append(f"adapter {slug} lacks structured certification")
        else:
            if certification.get("level") != maturity:
                problems.append(f"adapter {slug} certification level differs from maturity")
            if certification.get("live_solver_execution") != record.get("live_execution_verified"):
                problems.append(f"adapter {slug} live certification flags disagree")
            try:
                date.fromisoformat(str(certification.get("last_verified")))
            except ValueError:
                problems.append(f"adapter {slug} has invalid certification date")
            if maturity == "A5":
                if not record.get("live_execution_verified"):
                    problems.append(f"adapter {slug} A5 requires live execution evidence")
                if not certification.get("solver_versions"):
                    problems.append(f"adapter {slug} A5 requires solver versions")
                if not certification.get("fixture_hashes"):
                    problems.append(f"adapter {slug} A5 requires fixture hashes")
            elif record.get("live_execution_verified"):
                problems.append(f"adapter {slug} live execution requires A5 maturity")

        adapter_path = root / "adapters" / slug / "adapter.yaml"
        try:
            adapter_payload = _load(adapter_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            problems.append(f"adapter {slug} has invalid adapter.yaml: {exc}")
        else:
            if adapter_payload != record:
                problems.append(f"adapter {slug} metadata is not synchronized")
    return problems


def main() -> int:
    problems = validate()
    print(json.dumps({"passed": not problems, "problems": problems}, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
