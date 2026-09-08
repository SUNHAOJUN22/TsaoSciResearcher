from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command: tuple[str, ...], *, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(  # nosec B603
        command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return {
        "command": list(command),
        "returncode": completed.returncode,
        "stdout_tail": "\n".join(completed.stdout.splitlines()[-80:]),
        "stderr_tail": "\n".join(completed.stderr.splitlines()[-80:]),
    }


def main() -> int:
    cmake = shutil.which("cmake")
    ctest = shutil.which("ctest")
    problems: list[str] = []
    required = (
        ROOT / "native/CMakeLists.txt",
        ROOT / "native/include/tsao/capi.h",
        ROOT / "native/src/capi.cpp",
        ROOT / "native/tests/native_smoke.cpp",
    )
    for path in required:
        if not path.is_file():
            problems.append(f"missing native source file: {path.relative_to(ROOT).as_posix()}")
    if cmake is None:
        problems.append("cmake executable is unavailable")
    if ctest is None:
        problems.append("ctest executable is unavailable")

    steps: list[dict[str, object]] = []
    if not problems and cmake is not None and ctest is not None:
        with tempfile.TemporaryDirectory(prefix="tsao-native-core-") as temporary:
            build = Path(temporary) / "build"
            commands = (
                (
                    cmake,
                    "-S",
                    str(ROOT / "native"),
                    "-B",
                    str(build),
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DBUILD_TESTING=ON",
                ),
                (cmake, "--build", str(build), "--config", "Release", "--parallel", "2"),
                (
                    ctest,
                    "--test-dir",
                    str(build),
                    "--output-on-failure",
                    "-C",
                    "Release",
                ),
            )
            for command in commands:
                result = _run(command)
                steps.append(result)
                if result["returncode"] != 0:
                    problems.append(f"native verification command failed: {' '.join(command)}")
                    break
            if not problems:
                suffixes = {".dll", ".dylib", ".so"}
                libraries = tuple(
                    path
                    for path in build.rglob("*")
                    if path.is_file()
                    and path.suffix.casefold() in suffixes
                    and "tsao_native" in path.name.casefold()
                )
                if len(libraries) != 1:
                    problems.append(f"expected one native shared library, found {len(libraries)}")
                else:
                    bridge_env = dict(os.environ)
                    bridge_env["TSAO_NATIVE_LIBRARY"] = str(libraries[0])
                    bridge_command = (
                        sys.executable,
                        "-c",
                        (
                            "from tsao_computation.accelerators import probe_native_core; "
                            "result=probe_native_core(); "
                            "assert result is not None and result.logical_cpu_count >= 1; "
                            "assert 'cpu' in {item.value for item in result.runtime_backends}"
                        ),
                    )
                    result = _run(bridge_command, env=bridge_env)
                    steps.append(result)
                    if result["returncode"] != 0:
                        problems.append("Python/native C ABI bridge verification failed")

    report = {
        "schema_version": "1.0",
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "steps": steps,
        "claim_boundary": (
            "This compiles and smoke-tests the source-only C++20 CPU/OpenMP discovery ABI, "
            "the Python C-ABI bridge, and optional CUDA Runtime discovery when the toolkit is "
            "available. It does not claim external-solver support, numerical speedup, "
            "convergence, physical validity, applicability, or authorization."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
