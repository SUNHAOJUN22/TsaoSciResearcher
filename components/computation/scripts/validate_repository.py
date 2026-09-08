from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.provenance.manifest import iter_repository_entries
from tsao_computation.repository_audit import audit_repository


def main() -> int:
    root = Path(".").resolve()
    with tempfile.TemporaryDirectory(prefix="tsao-repository-audit-") as temporary:
        audit_root = Path(temporary) / "repository"
        symlinks: list[str] = []
        for path in iter_repository_entries(root):
            relative = path.relative_to(root)
            if path.is_symlink():
                symlinks.append(relative.as_posix())
                continue
            if not path.is_file():
                continue
            destination = audit_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)

        if symlinks:
            report: dict[str, object] = {
                "schema_version": "1.0",
                "passed": False,
                "problems": [f"symlinks are forbidden in the release tree: {sorted(symlinks)}"],
                "counts": {},
            }
        else:
            report = audit_repository(audit_root)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
