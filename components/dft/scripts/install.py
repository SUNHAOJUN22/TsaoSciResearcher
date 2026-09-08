#!/usr/bin/env python3
"""Install, validate, or uninstall TsaoDFT Agent Skills safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext, suppress
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
AVAILABLE = sorted(path.name for path in SKILLS_DIR.iterdir() if path.is_dir() and (path / "SKILL.md").exists())
REPOSITORY = "https://github.com/SUNHAOJUN22/TsaoDFT_skill"
OWNERSHIP_DIR = ".tsao-skill-ownership"
MARKER_SCHEMA = 1
INSTALL_LOCK = ".tsao-install.lock"
IGNORED_COPY_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


class InstallSafetyError(RuntimeError):
    """Raised when an installation operation cannot prove it is safe."""


@contextmanager
def install_lock(target: Path) -> Iterator[None]:
    target.mkdir(parents=True, exist_ok=True)
    lock = target / INSTALL_LOCK
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallSafetyError(f"another TsaoDFT install operation holds {lock}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        yield
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            lock.unlink()


def default_target(agent: str, scope: str) -> Path:
    if scope == "project":
        mapping = {
            "codex": Path.cwd() / ".codex/skills",
            "claude-code": Path.cwd() / ".claude/skills",
            "open-agent": Path.cwd() / ".agents/skills",
        }
    else:
        mapping = {
            "codex": Path.home() / ".codex/skills",
            "claude-code": Path.home() / ".claude/skills",
            "open-agent": Path.home() / ".agents/skills",
        }
    return mapping[agent]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude-code", "open-agent"], default="codex")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--skill", action="append", dest="skills", choices=[*AVAILABLE, "all"], default=[])
    parser.add_argument("--method", choices=["copy", "symlink"], default="copy")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--backup-existing",
        action="store_true",
        help="With --force, atomically retain an owned destination as <skill>.backup before replacement",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--list", action="store_true")
    return parser.parse_args()


def validate_source(skill: str) -> list[str]:
    failures: list[str] = []
    source = SKILLS_DIR / skill
    for rel in ["SKILL.md", "manifest.yaml", "agents/openai.yaml"]:
        if not (source / rel).is_file():
            failures.append(f"{skill}: missing {rel}")
    return failures


def safe_target(target: Path) -> Path:
    resolved = target.expanduser().resolve()
    forbidden = {Path(resolved.anchor), Path.home().resolve(), ROOT.resolve()}
    if resolved in forbidden:
        raise InstallSafetyError(f"unsafe target root refused: {resolved}")
    return resolved


def ownership_path(target: Path, skill: str) -> Path:
    return target / OWNERSHIP_DIR / f"{skill}.json"


def iter_tree_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED_COPY_NAMES for part in relative.parts):
            continue
        if path.is_file() and path.suffix != ".pyc":
            yield path, relative


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path, relative in iter_tree_files(root):
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def read_marker(target: Path, skill: str) -> dict[str, Any] | None:
    marker = ownership_path(target, skill)
    if not marker.is_file():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallSafetyError(f"invalid ownership record for {skill}: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallSafetyError(f"invalid ownership record for {skill}: root must be an object")
    return data


def validate_owned_destination(
    target: Path,
    skill: str,
    source: Path,
    destination: Path,
) -> dict[str, Any]:
    marker = read_marker(target, skill)
    if marker is None:
        raise InstallSafetyError(
            f"refusing to modify unowned destination: {destination}; no {OWNERSHIP_DIR}/{skill}.json record"
        )
    expected = {
        "schema_version": MARKER_SCHEMA,
        "repository": REPOSITORY,
        "skill": skill,
        "destination": str(destination),
    }
    for key, value in expected.items():
        if marker.get(key) != value:
            raise InstallSafetyError(f"ownership record mismatch for {skill}: {key}")
    method = marker.get("method")
    if method not in {"copy", "symlink"}:
        raise InstallSafetyError(f"ownership record has unsupported method for {skill}: {method!r}")
    if method == "symlink":
        if not destination.is_symlink():
            raise InstallSafetyError(f"owned symlink destination was replaced by a non-symlink: {destination}")
        if destination.resolve() != source.resolve():
            raise InstallSafetyError(f"owned symlink target changed: {destination}")
    elif not destination.is_dir() or destination.is_symlink():
        raise InstallSafetyError(f"owned copy destination has unexpected type: {destination}")
    return marker


def write_marker(target: Path, skill: str, payload: dict[str, Any]) -> None:
    marker_dir = target / OWNERSHIP_DIR
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{skill}.json"
    temporary = marker.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, marker)


def remove_marker(target: Path, skill: str) -> None:
    marker = ownership_path(target, skill)
    if marker.exists():
        marker.unlink()
    marker_dir = marker.parent
    if marker_dir.is_dir() and not any(marker_dir.iterdir()):
        marker_dir.rmdir()


def remove_owned_destination(destination: Path) -> None:
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    elif destination.is_dir():
        shutil.rmtree(destination)
    else:
        raise InstallSafetyError(f"destination disappeared or has unsupported type: {destination}")


def stage_copy(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.install-", dir=destination.parent))
    temporary.rmdir()
    try:
        shutil.copytree(
            source,
            temporary,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache"),
        )
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return temporary


def backup_destination(destination: Path) -> Path:
    backup = destination.with_name(f"{destination.name}.backup")
    if backup.exists() or backup.is_symlink():
        raise InstallSafetyError(f"backup destination already exists: {backup}")
    os.replace(destination, backup)
    return backup


def install_skill(
    target: Path,
    skill: str,
    method: str,
    *,
    force: bool,
    backup_existing: bool,
    dry_run: bool,
) -> None:
    source = (SKILLS_DIR / skill).resolve()
    destination = target / skill
    existing = destination.exists() or destination.is_symlink()
    marker: dict[str, Any] | None = None
    if existing:
        if not force:
            raise InstallSafetyError(f"destination exists: {destination}; use --force only for a TsaoDFT-owned install")
        marker = validate_owned_destination(target, skill, source, destination)
        if marker["method"] == "copy":
            current_digest = tree_digest(destination)
            if current_digest != marker.get("installed_digest") and not backup_existing:
                raise InstallSafetyError(
                    f"owned copy was modified: {destination}; use --backup-existing with --force to preserve it"
                )
    elif read_marker(target, skill) is not None:
        raise InstallSafetyError(f"stale ownership record exists for missing destination: {destination}")

    print(f"install ({method}): {source} -> {destination}")
    if dry_run:
        return

    target.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    backup: Path | None = None
    rollback: Path | None = None
    try:
        if method == "copy":
            staged = stage_copy(source, destination)
        if existing:
            if backup_existing:
                backup = backup_destination(destination)
            else:
                rollback = Path(tempfile.mkdtemp(prefix=f".{destination.name}.rollback-", dir=destination.parent))
                rollback.rmdir()
                os.replace(destination, rollback)
        if method == "symlink":
            destination.symlink_to(source, target_is_directory=True)
            installed_digest = tree_digest(source)
        else:
            if staged is None:
                raise InstallSafetyError("internal error: copy installation was not staged")
            os.replace(staged, destination)
            staged = None
            installed_digest = tree_digest(destination)
        write_marker(
            target,
            skill,
            {
                "schema_version": MARKER_SCHEMA,
                "repository": REPOSITORY,
                "skill": skill,
                "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
                "method": method,
                "source": str(source),
                "destination": str(destination),
                "source_digest": tree_digest(source),
                "installed_digest": installed_digest,
                "backup": str(backup) if backup is not None else None,
            },
        )
        if rollback is not None and rollback.exists():
            remove_owned_destination(rollback)
    except Exception:
        if staged is not None and staged.exists():
            shutil.rmtree(staged)
        original = backup if backup is not None else rollback
        if original is not None and original.exists():
            if destination.exists() or destination.is_symlink():
                remove_owned_destination(destination)
            os.replace(original, destination)
        raise


def uninstall_skill(target: Path, skill: str, *, force: bool, dry_run: bool) -> None:
    source = (SKILLS_DIR / skill).resolve()
    destination = target / skill
    if not destination.exists() and not destination.is_symlink():
        if read_marker(target, skill) is not None:
            raise InstallSafetyError(f"stale ownership record exists for missing destination: {destination}")
        print(f"uninstall: already absent: {destination}")
        return
    marker = validate_owned_destination(target, skill, source, destination)
    if marker["method"] == "copy":
        current_digest = tree_digest(destination)
        if current_digest != marker.get("installed_digest") and not force:
            raise InstallSafetyError(f"owned copy was modified: {destination}; use --force to remove the owned copy")
    print(f"uninstall: {destination}")
    if dry_run:
        return
    remove_owned_destination(destination)
    remove_marker(target, skill)


def main() -> int:
    args = parse_args()
    if args.backup_existing and not args.force:
        print("FAIL: --backup-existing requires --force", file=sys.stderr)
        return 2
    if args.list:
        print("\n".join(AVAILABLE))
        return 0
    selected = AVAILABLE if not args.skills or "all" in args.skills else list(dict.fromkeys(args.skills))
    failures = [item for skill in selected for item in validate_source(skill)]
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1
    if args.validate and not args.uninstall:
        checks = [
            [sys.executable, str(ROOT / "scripts" / "validate_catalog.py")],
            [sys.executable, str(ROOT / "scripts" / "validate_repo.py"), "--strict"],
        ]
        for command in checks:
            completed = subprocess.run(command, cwd=ROOT, check=False)
            if completed.returncode:
                return completed.returncode
        print(f"Validated repository and {len(selected)} source skill(s): {', '.join(selected)}")
        if args.dry_run:
            return 0
    try:
        target = safe_target(args.target or default_target(args.agent, args.scope))
        lock_context = nullcontext() if args.dry_run else install_lock(target)
        with lock_context:
            for skill in selected:
                if args.uninstall:
                    uninstall_skill(target, skill, force=args.force, dry_run=args.dry_run)
                else:
                    install_skill(
                        target,
                        skill,
                        args.method,
                        force=args.force,
                        backup_existing=args.backup_existing,
                        dry_run=args.dry_run,
                    )
    except (InstallSafetyError, OSError, shutil.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
