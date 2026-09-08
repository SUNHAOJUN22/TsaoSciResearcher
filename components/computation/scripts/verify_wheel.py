from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.provenance.manifest import iter_repository_entries


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_source_snapshot(root: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    for source in iter_repository_entries(root):
        relative = source.relative_to(root)
        if source.is_symlink():
            raise ValueError(f"wheel source tree contains symlink: {relative.as_posix()}")
        if not source.is_file():
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build_once(source_root: Path, output: Path, epoch: str) -> Path:
    output.mkdir(parents=True)
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = epoch
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(output),
        ],
        cwd=source_root,
        env=env,
        check=True,
    )
    wheels = list(output.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one wheel, found {len(wheels)}")
    return wheels[0]


def build_reproducible_pair(root: Path, temporary_root: Path, epoch: str) -> tuple[Path, Path]:
    source_first = temporary_root / "source-first"
    source_second = temporary_root / "source-second"
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="tsao-wheel") as pool:
        first_snapshot = pool.submit(prepare_source_snapshot, root, source_first)
        second_snapshot = pool.submit(prepare_source_snapshot, root, source_second)
        first_snapshot.result()
        second_snapshot.result()

        first_future = pool.submit(build_once, source_first, temporary_root / "first", epoch)
        second_future = pool.submit(build_once, source_second, temporary_root / "second", epoch)
        return first_future.result(), second_future.result()


def verify_target_install(wheel: Path, temporary_root: Path, expected: str) -> str:
    target = temporary_root / "target-install"
    env = dict(os.environ)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--no-compile",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=temporary_root,
        env=env,
        check=True,
    )
    script = (
        "from pathlib import Path; import sys; "
        "target=Path(sys.argv[1]).resolve(); sys.path.insert(0,str(target)); "
        "import tsao_computation; "
        "from tsao_computation import __version__; "
        "from tsao_computation.registries import capabilities,adapters,workflows; "
        "module=Path(tsao_computation.__file__).resolve(); "
        "assert target in module.parents, (target,module); "
        "print(__version__,len(capabilities()),len(adapters()),len(workflows()))"
    )
    return subprocess.check_output(  # nosec B603
        [sys.executable, "-c", script, str(target)],
        cwd=temporary_root,
        text=True,
        env=env,
    ).strip()


def main() -> int:
    root = Path(".").resolve()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    expected = f"{version} 164 27 20"
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tsao-wheel-") as temporary:
        temporary_root = Path(temporary)
        first, second = build_reproducible_pair(root, temporary_root, "1700000000")
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise SystemExit("wheel builds are not byte-identical")
        destination = dist / first.name
        shutil.copy2(first, destination)

        verification = verify_target_install(destination, temporary_root, expected)
        if verification != expected:
            raise SystemExit(f"isolated wheel verification failed: {verification}")

    report = {
        "schema_version": "1.0",
        "artifact": destination.name,
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "byte_identical_rebuild": True,
        "parallel_isolated_rebuilds": True,
        "parallel_source_snapshots": True,
        "isolated_install": True,
        "installation_mode": "pip-target-no-compile",
        "verification": expected,
    }
    (dist / "WHEEL_VERIFICATION.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
