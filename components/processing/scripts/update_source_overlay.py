from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsao.provenance import canonical_identity, classify_path  # noqa: E402

FIELDS = ["path", "sha256", "bytes", "specialist", "artifact_class", "license_scope"]
ALLOWED_TARGETS = {
    "reports/SOURCE_CORE_OVERLAY.tsv",
    "reports/SOURCE_ACCEPTANCE_OVERLAY.tsv",
}


def _normalized_relative(value: str) -> str:
    normalized = Path(value).as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    pure = PurePosixPath(normalized)
    if (
        not normalized
        or "\\" in normalized
        or normalized.startswith("/")
        or pure.is_absolute()
        or ".." in pure.parts
        or (pure.parts and pure.parts[0].endswith(":"))
    ):
        raise ValueError(f"unsafe repository-relative path: {value}")
    return normalized


def update_overlay(
    root: Path,
    paths: list[str],
    *,
    target_relative: str = "reports/SOURCE_CORE_OVERLAY.tsv",
) -> int:
    root = root.resolve()
    target_relative = _normalized_relative(target_relative)
    if target_relative not in ALLOWED_TARGETS:
        allowed = ", ".join(sorted(ALLOWED_TARGETS))
        raise ValueError(f"unsupported overlay target {target_relative!r}; allowed: {allowed}")
    target = root / target_relative
    records: dict[str, dict[str, object]] = {}
    if target.is_file():
        with target.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError(f"overlay header is incomplete: {target_relative}")
            for row_number, row in enumerate(reader, start=2):
                relative = _normalized_relative(str(row.get("path") or ""))
                if relative in records:
                    raise ValueError(
                        f"duplicate overlay path in {target_relative} row {row_number}: {relative}"
                    )
                records[relative] = {field: str(row.get(field) or "") for field in FIELDS}
    for relative in paths:
        normalized = _normalized_relative(relative)
        path = root / normalized
        if not path.is_file():
            raise FileNotFoundError(f"overlay path is not a file: {normalized}")
        digest, size = canonical_identity(path)
        specialist, artifact_class, license_scope = classify_path(normalized)
        records[normalized] = {
            "path": normalized,
            "sha256": digest,
            "bytes": size,
            "specialist": specialist,
            "artifact_class": artifact_class,
            "license_scope": license_scope,
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records[key] for key in sorted(records))
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--target",
        choices=sorted(ALLOWED_TARGETS),
        default="reports/SOURCE_CORE_OVERLAY.tsv",
    )
    args = parser.parse_args(argv)
    print(
        update_overlay(
            args.root,
            args.paths,
            target_relative=args.target,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
