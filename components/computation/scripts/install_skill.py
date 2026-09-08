from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tsao_computation.provenance.manifest import iter_repository_entries  # noqa: E402

SKILL_NAME = "tsao-scicomputation"
LEGACY_SKILL_NAME = "TsaoSciComputation"
RECEIPT_NAME = ".tsao-install.json"
AGENT_ROOTS = {
    "codex": ".codex/skills",
    "claude": ".claude/skills",
    "open-agent-skills": ".agents/skills",
}


def resolve_destination(
    agent: str,
    scope: str,
    target: Path | None,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> Path:
    if target is not None:
        expanded = target.expanduser().resolve()
        return (
            expanded if expanded.name in {SKILL_NAME, LEGACY_SKILL_NAME} else expanded / SKILL_NAME
        )
    base = (home or Path.home()) if scope == "user" else (cwd or Path.cwd())
    preferred = (base / AGENT_ROOTS[agent] / SKILL_NAME).resolve()
    legacy = (base / AGENT_ROOTS[agent] / LEGACY_SKILL_NAME).resolve()
    return legacy if not preferred.exists() and legacy.exists() else preferred


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entries(destination: Path, problems: list[str]) -> dict[str, dict[str, Any]]:
    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        problems.append(f"invalid manifest.json: {exc}")
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        problems.append("manifest.json must contain a files array")
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload["files"]):
        if not isinstance(item, dict):
            problems.append(f"manifest entry {index} is not an object")
            continue
        raw_path = item.get("path")
        byte_count = item.get("bytes")
        digest = item.get("sha256")
        if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
            problems.append(f"manifest entry {index} has an invalid path")
            continue
        relative = PurePosixPath(raw_path)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != raw_path:
            problems.append(f"manifest entry {index} escapes the installation root: {raw_path}")
            continue
        if raw_path in entries:
            problems.append(f"duplicate manifest path: {raw_path}")
            continue
        if not isinstance(byte_count, int) or byte_count < 0:
            problems.append(f"manifest entry has invalid byte count: {raw_path}")
            continue
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            problems.append(f"manifest entry has invalid SHA-256: {raw_path}")
            continue
        entries[raw_path] = item
    return entries


def validate_installation(destination: Path) -> list[str]:
    destination = destination.resolve()
    problems: list[str] = []
    if not destination.is_dir():
        return [f"installation directory does not exist: {destination}"]

    required = (
        "SKILL.md",
        "VERSION",
        "manifest.json",
        "scripts/verify_all.py",
        RECEIPT_NAME,
    )
    for relative in required:
        if not (destination / relative).is_file():
            problems.append(f"missing required file: {relative}")

    skill_path = destination / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        registered = f"name: {SKILL_NAME}" in text
        legacy_registered = (
            destination.name == LEGACY_SKILL_NAME and f"name: {LEGACY_SKILL_NAME}" in text
        )
        if not (registered or legacy_registered):
            problems.append("SKILL.md does not register a supported TsaoSciComputation identifier")

    version = None
    version_path = destination / "VERSION"
    if version_path.is_file():
        version = version_path.read_text(encoding="utf-8").strip()

    receipt_path = destination / RECEIPT_NAME
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            problems.append(f"invalid installation receipt: {exc}")
        else:
            if not isinstance(receipt, dict) or receipt.get("skill") not in {
                SKILL_NAME,
                LEGACY_SKILL_NAME,
            }:
                problems.append("installation receipt does not belong to TsaoSciComputation")
            elif version is not None and receipt.get("version") != version:
                problems.append("installation receipt version differs from VERSION")

    entries = _manifest_entries(destination, problems)
    for relative, item in entries.items():
        target = destination.joinpath(*PurePosixPath(relative).parts)
        if target.is_symlink():
            problems.append(f"installed file is a symlink: {relative}")
        elif not target.is_file():
            problems.append(f"manifest file is missing: {relative}")
        else:
            expected_bytes = int(item["bytes"])
            expected_hash = str(item["sha256"])
            if target.stat().st_size != expected_bytes:
                problems.append(f"installed file size differs from manifest: {relative}")
            if _sha256(target) != expected_hash:
                problems.append(f"installed file hash differs from manifest: {relative}")

    actual_files: set[str] = set()
    for path in iter_repository_entries(destination):
        relative = path.relative_to(destination).as_posix()
        if path.is_symlink():
            problems.append(f"installation contains a symlink: {relative}")
        elif path.is_file():
            actual_files.add(relative)
    allowed_unlisted = {"manifest.json", RECEIPT_NAME}
    extras = sorted(actual_files - entries.keys() - allowed_unlisted)
    if extras:
        problems.append(f"unlisted files are present: {extras}")
    return problems


def _source_files(source: Path, destination: Path) -> list[tuple[Path, Path]]:
    source = source.resolve()
    destination = destination.resolve()
    files: list[tuple[Path, Path]] = []
    for path in iter_repository_entries(source):
        if path == destination or destination in path.parents:
            continue
        relative = path.relative_to(source)
        if path.is_symlink():
            raise ValueError(f"source tree contains symlink: {relative.as_posix()}")
        if path.is_file():
            files.append((path, relative))
    return files


def install_skill(
    source: Path,
    destination: Path,
    *,
    agent: str,
    scope: str,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    files = _source_files(source, destination)
    if destination.exists() and not force:
        raise FileExistsError(f"destination exists; use --force: {destination}")
    if dry_run:
        print(f"DRY-RUN install {len(files)} files to {destination}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tsao-install-", dir=destination.parent) as temporary:
        staging = Path(temporary) / SKILL_NAME
        staging.mkdir()
        for source_path, relative in files:
            target_path = staging / relative
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
        receipt = {
            "agent": agent,
            "schema_version": "1.0",
            "scope": scope,
            "skill": SKILL_NAME,
            "version": (source / "VERSION").read_text(encoding="utf-8").strip(),
        }
        (staging / RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        problems = validate_installation(staging)
        if problems:
            raise ValueError(f"staged installation is invalid: {problems}")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(staging), destination)


def uninstall_skill(destination: Path, *, force: bool = False, dry_run: bool = False) -> None:
    if not destination.exists():
        raise FileNotFoundError(f"installation not found: {destination}")
    if not force:
        problems = validate_installation(destination)
        if problems:
            raise ValueError(f"refusing to remove an invalid installation; use --force: {problems}")
    if dry_run:
        print(f"DRY-RUN uninstall {destination}")
        return
    shutil.rmtree(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install or validate TsaoSciComputation.")
    parser.add_argument("--agent", choices=tuple(AGENT_ROOTS), default="codex")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--uninstall", action="store_true")
    action.add_argument("--validate", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    destination = resolve_destination(args.agent, args.scope, args.target)
    try:
        if args.uninstall:
            uninstall_skill(destination, force=args.force, dry_run=args.dry_run)
        elif args.validate:
            problems = validate_installation(destination)
            if problems:
                print(json.dumps({"destination": str(destination), "problems": problems}, indent=2))
                return 1
            print(json.dumps({"destination": str(destination), "status": "VALID"}, indent=2))
        else:
            install_skill(
                REPOSITORY_ROOT,
                destination,
                agent=args.agent,
                scope=args.scope,
                force=args.force,
                dry_run=args.dry_run,
            )
            print(json.dumps({"destination": str(destination), "status": "INSTALLED"}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
