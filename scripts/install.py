#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, atomic_write_text

INSTALL_MARKER = ".tsao-sci-researcher-install.json"
EXCLUDED = (
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    "build",
    "dist",
    "*.zip",
    ".tsao-research",
)


def destination(agent: str, scope: str, target: str | None) -> Path:
    if target:
        return Path(target).expanduser().resolve(strict=False)
    base = Path.cwd() if scope == "project" else Path.home()
    mapping = {
        ("codex", "user"): Path.home() / ".codex/skills/TsaoSciResearcher",
        ("codex", "project"): base / ".codex/skills/TsaoSciResearcher",
        ("claude", "user"): Path.home() / ".claude/skills/TsaoSciResearcher",
        ("claude", "project"): base / ".claude/skills/TsaoSciResearcher",
        ("open-agent", "user"): Path.home() / ".agents/skills/TsaoSciResearcher",
        ("open-agent", "project"): base / ".agents/skills/TsaoSciResearcher",
    }
    return mapping[(agent, scope)].resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_destination(path: Path) -> None:
    resolved = path.resolve(strict=False)
    dangerous = {Path(resolved.anchor), Path.home().resolve(), Path.cwd().resolve(), ROOT.resolve()}
    if resolved in dangerous:
        raise ValueError(f"refusing dangerous install target: {resolved}")
    if _is_relative_to(resolved, ROOT.resolve()) or _is_relative_to(ROOT.resolve(), resolved):
        raise ValueError(f"install target overlaps source repository: {resolved}")
    if path.is_symlink():
        raise ValueError(f"install target cannot be a symbolic link: {path}")


def validate_source() -> None:
    required = [ROOT / "SKILL.md", ROOT / "manifest.json", ROOT / "capability-index/capabilities.json"]
    missing = [str(path) for path in required if not path.is_file() or path.is_symlink()]
    if missing:
        raise ValueError(f"source validation failed: {missing}")


def _marker_payload(agent: str, scope: str) -> str:
    version = (ROOT / "VERSION").read_text(encoding="utf-8", errors="strict").strip()
    return (
        json.dumps(
            {
                "schema_version": "1.0",
                "canonical_name": "TsaoSciResearcher",
                "version": version,
                "agent": agent,
                "scope": scope,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def _is_managed_install(path: Path) -> bool:
    marker = path / INSTALL_MARKER
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8", errors="strict"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("canonical_name") == "TsaoSciResearcher"


def _unique_backup(path: Path) -> Path:
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.name}.backup-{index:04d}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
    raise RuntimeError("unable to allocate unique backup path")


def install(dst: Path, *, agent: str, scope: str, force: bool) -> None:
    validate_destination(dst)
    validate_source()
    dst.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{dst.name}.stage-", dir=dst.parent))
    backup: Path | None = None
    try:
        shutil.rmtree(stage)
        ignore = shutil.ignore_patterns(*EXCLUDED)
        shutil.copytree(ROOT, stage, ignore=ignore, symlinks=False)
        atomic_write_text(stage / INSTALL_MARKER, _marker_payload(agent, scope))
        if dst.exists():
            if not force:
                raise FileExistsError(f"{dst} exists; use --force")
            if not _is_managed_install(dst):
                raise ValueError(f"refusing to replace unmanaged directory: {dst}")
            backup = _unique_backup(dst)
            os.replace(dst, backup)
        os.replace(stage, dst)
        if backup is not None:
            shutil.rmtree(backup)
    except Exception:
        if backup is not None and backup.exists() and not dst.exists():
            os.replace(backup, dst)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def uninstall(dst: Path) -> None:
    validate_destination(dst)
    if not dst.exists():
        return
    if not _is_managed_install(dst):
        raise ValueError(f"refusing to remove unmanaged directory: {dst}")
    tombstone = _unique_backup(dst)
    os.replace(dst, tombstone)
    try:
        shutil.rmtree(tombstone)
    except Exception:
        if not dst.exists() and tombstone.exists():
            os.replace(tombstone, dst)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["codex", "claude", "open-agent"], default="codex")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--target")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    dst = destination(args.agent, args.scope, args.target)
    validate_destination(dst)
    if args.validate:
        validate_source()
    if args.dry_run:
        action = "remove" if args.uninstall else "install"
        print(f"Would {action} {dst}")
        return
    if args.uninstall:
        uninstall(dst)
        print(f"Removed {dst}")
        return
    install(dst, agent=args.agent, scope=args.scope, force=args.force)
    print(f"Installed TsaoSciResearcher to {dst}")


if __name__ == "__main__":
    main()
