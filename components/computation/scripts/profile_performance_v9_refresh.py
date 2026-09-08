from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess  # nosec B404
import sys
import tempfile
import textwrap
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import _bootstrap  # noqa: F401
from scripts.measure_command_v9 import measure_command

CLAIM_BOUNDARY = (
    "Same-host repository orchestration, parsing, validation, memory and I/O telemetry only; "
    "external scientific solvers and production HPC execution are not measured."
)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize(values: Sequence[float]) -> dict[str, float]:
    samples = [float(value) for value in values]
    if not samples:
        raise ValueError("performance samples must not be empty")
    mean = statistics.fmean(samples)
    return {
        "median": statistics.median(samples),
        "min": min(samples),
        "p90": _percentile(samples, 0.90),
        "mean": mean,
        "stdev": statistics.pstdev(samples),
        "cv": statistics.pstdev(samples) / mean if mean else 0.0,
    }


def _python_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(root) if not existing else os.pathsep.join((str(root), existing))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


def _run_json(root: Path, code: str, *args: str) -> dict[str, Any]:
    output = subprocess.check_output(  # nosec B603
        [sys.executable, "-c", textwrap.dedent(code), *args],
        cwd=root,
        env=_python_env(root),
        text=True,
    )
    payload = json.loads(output)
    if not isinstance(payload, dict):
        raise ValueError("performance worker must return a JSON object")
    return cast(dict[str, Any], payload)


def _measure_subprocess(
    root: Path, argv: Sequence[str], *, warmups: int, repeats: int
) -> dict[str, Any]:
    if warmups < 0 or repeats < 1:
        raise ValueError("warmups must be non-negative and repeats must be positive")
    env = _python_env(root)
    for _ in range(warmups):
        subprocess.run(  # nosec B603
            list(argv),
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    wall: list[float] = []
    cpu: list[float] = []
    for _ in range(repeats):
        wall_started = time.perf_counter()
        cpu_started = time.process_time()
        subprocess.run(  # nosec B603
            list(argv),
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        wall.append(time.perf_counter() - wall_started)
        cpu.append(time.process_time() - cpu_started)
    return {"wall_seconds": summarize(wall), "parent_cpu_seconds": summarize(cpu)}


def startup_profile(root: Path) -> dict[str, Any]:
    commands = {
        "import_package": (sys.executable, "-c", "import tsao_computation"),
        "import_cli": (sys.executable, "-c", "import tsao_computation.cli"),
        "cli_version": (sys.executable, "-m", "tsao_computation", "--version"),
        "cli_route": (
            sys.executable,
            "-m",
            "tsao_computation",
            "route",
            "OpenFOAM non-Newtonian polymer extrusion",
        ),
        "cli_list": (sys.executable, "-m", "tsao_computation", "list", "capabilities"),
        "cli_probe": (sys.executable, "-m", "tsao_computation", "probe", "--workers", "1"),
    }
    return {
        name: _measure_subprocess(root, argv, warmups=2, repeats=9)
        for name, argv in commands.items()
    }


def registry_and_routing_profile(root: Path) -> dict[str, Any]:
    return _run_json(
        root,
        r"""
        import json
        import statistics
        import time
        import tracemalloc

        from tsao_computation.adapters import get_adapter, list_adapters
        from tsao_computation.registries import adapters, capabilities, clear_registry_caches, units, workflows
        from tsao_computation.routing import route_question
        from tsao_computation.routing.router import _route_cached

        def percentile(values, percentile):
            ordered=sorted(values); position=(len(ordered)-1)*percentile
            lower=int(position); upper=min(lower+1,len(ordered)-1); fraction=position-lower
            return ordered[lower]*(1-fraction)+ordered[upper]*fraction

        def measure(operation, repeats=9, loops=1, warmups=2):
            for _ in range(warmups): operation()
            values=[]
            tracemalloc.start()
            for _ in range(repeats):
                started=time.perf_counter()
                for _ in range(loops): operation()
                values.append((time.perf_counter()-started)/loops)
            _, peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
            mean=statistics.fmean(values)
            return {
                'median_seconds': statistics.median(values), 'min_seconds': min(values),
                'p90_seconds': percentile(values,0.90), 'stdev_seconds': statistics.pstdev(values),
                'cv': statistics.pstdev(values)/mean if mean else 0.0,
                'peak_tracemalloc_bytes': peak,
            }

        def cold(loader):
            def operation(): clear_registry_caches(); return loader()
            return measure(operation, warmups=1)

        questions={
            'english':'OpenFOAM non-Newtonian polymer extrusion and carbon-black transport',
            'chinese':'使用分子动力学和有限元研究聚合物界面导电与热机械耦合',
            'mixed':'DFT 到 MD 再到 CFD 的多尺度 polymer interface workflow',
            'no_match':'What should be calculated for this new system?',
            'long':('polymer interface molecular dynamics diffusion rheology multiscale ' * 500).strip(),
        }
        route={}
        for name, question in questions.items():
            clear_registry_caches()
            route[name+'_cold']=measure(lambda q=question: route_question(q), repeats=7, warmups=1)
            route_question(question)
            route[name+'_warm']=measure(lambda q=question: route_question(q), loops=1000)

        batches={}
        for count in (100,1000,10000):
            corpus=[questions['english'] if index % 3 == 0 else questions['chinese'] if index % 3 == 1 else questions['mixed'] for index in range(count)]
            clear_registry_caches()
            batches[str(count)]=measure(lambda values=corpus: tuple(route_question(value) for value in values), repeats=5, warmups=1)

        clear_registry_caches()
        route_question(questions['english'])
        cache_info=_route_cached.cache_info()
        result={
            'registries':{
                'capabilities_cold':cold(capabilities),'adapters_cold':cold(adapters),
                'workflows_cold':cold(workflows),'units_cold':cold(units),
                'capabilities_cached':measure(capabilities,loops=2000),
                'adapter_list_cached':measure(list_adapters,loops=2000),
                'adapter_lookup_cached':measure(lambda:get_adapter('orca'),loops=2000),
                'cache_clear_and_rebuild':measure(lambda:(clear_registry_caches(),capabilities(),adapters(),workflows(),units()),repeats=7,warmups=1),
            },
            'routing':route,
            'routing_batches':batches,
            'route_cache':{'maxsize':cache_info.maxsize,'currsize':cache_info.currsize},
        }
        print(json.dumps(result,sort_keys=True))
        """,
    )


def adapter_profile(root: Path) -> dict[str, Any]:
    return _run_json(
        root,
        r"""
        import json, statistics, time, tracemalloc
        from tsao_computation.adapters import get_adapter, list_adapters, probe_all
        def p90(values):
            ordered=sorted(values); pos=(len(ordered)-1)*.9; low=int(pos); high=min(low+1,len(ordered)-1); f=pos-low
            return ordered[low]*(1-f)+ordered[high]*f
        def measure(operation,repeats=7,warmups=1):
            for _ in range(warmups): operation()
            values=[]; tracemalloc.start()
            for _ in range(repeats):
                started=time.perf_counter(); operation(); values.append(time.perf_counter()-started)
            _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); mean=statistics.fmean(values)
            return {'median_seconds':statistics.median(values),'min_seconds':min(values),'p90_seconds':p90(values),'stdev_seconds':statistics.pstdev(values),'cv':statistics.pstdev(values)/mean if mean else 0.0,'peak_tracemalloc_bytes':peak}
        result={'list_adapters':measure(list_adapters),'get_adapter':measure(lambda:get_adapter('orca'),repeats=9,warmups=2),'single_probe':measure(lambda:get_adapter('orca').probe(),repeats=5,warmups=1)}
        for workers in (1,2,4,8): result[f'probe_all_{workers}']=measure(lambda w=workers:probe_all(w),repeats=3,warmups=1)
        print(json.dumps(result,sort_keys=True))
        """,
    )


def parser_profile(root: Path) -> dict[str, Any]:
    return _run_json(
        root,
        r"""
        import json, statistics, sys, time, tracemalloc
        from tsao_computation.adapters import get_adapter
        adapter=get_adapter('orca')
        def p90(values):
            ordered=sorted(values); pos=(len(ordered)-1)*.9; low=int(pos); high=min(low+1,len(ordered)-1); f=pos-low
            return ordered[low]*(1-f)+ordered[high]*f
        def measure(payload,repeats):
            for _ in range(2): adapter.parse(payload)
            values=[]; tracemalloc.start()
            for _ in range(repeats):
                started=time.perf_counter(); result=adapter.parse(payload); values.append(time.perf_counter()-started)
            _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); mean=statistics.fmean(values)
            return {'median_seconds':statistics.median(values),'min_seconds':min(values),'p90_seconds':p90(values),'stdev_seconds':statistics.pstdev(values),'cv':statistics.pstdev(values)/mean if mean else 0.0,'peak_tracemalloc_bytes':peak,'result':result}
        sizes={'1kib':1024,'1mib':1024*1024,'5mib':5*1024*1024,'50mib':50*1024*1024}
        cases={}
        templates={
            'success_start':'normal termination converged\n{fill}',
            'success_middle':'{half}\nnormal termination converged\n{half}',
            'success_end':'{fill}\nnormal termination converged',
            'failure':'{fill}\ncompleted with errors\nfailed to converge',
            'nonconverged':'{fill}\nnormal termination\nnot converged',
            'none':'{fill}',
            'mixed_case':'{fill}\nNoRmAl TeRmInAtIoN CoNvErGeD',
            'crlf':'{fill}\r\nnormal termination\r\nconverged',
        }
        for size_name,size in sizes.items():
            fill=('iteration data 1234567890\n' * (size//25+2))[:size]
            half=fill[:size//2]
            repeats=9 if size<=1024*1024 else 5 if size<=5*1024*1024 else 3
            for case,template in templates.items():
                payload=template.format(fill=fill,half=half)
                cases[f'{size_name}_{case}']=measure(payload,repeats)
        print(json.dumps(cases,sort_keys=True))
        """,
    )


def repository_profile(root: Path) -> dict[str, Any]:
    return _run_json(
        root,
        r"""
        import json, statistics, time, tracemalloc
        from pathlib import Path
        from scripts.security_scan import scan
        from tsao_computation.provenance.manifest import file_manifest, iter_repository_entries
        from tsao_computation.repository_audit import audit_repository
        root=Path('.').resolve()
        def p90(values):
            ordered=sorted(values); pos=(len(ordered)-1)*.9; low=int(pos); high=min(low+1,len(ordered)-1); f=pos-low
            return ordered[low]*(1-f)+ordered[high]*f
        def measure(operation,repeats=5,warmups=1):
            for _ in range(warmups): operation()
            values=[]; tracemalloc.start()
            for _ in range(repeats):
                started=time.perf_counter(); result=operation(); values.append(time.perf_counter()-started)
            _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); mean=statistics.fmean(values)
            return {'median_seconds':statistics.median(values),'min_seconds':min(values),'p90_seconds':p90(values),'stdev_seconds':statistics.pstdev(values),'cv':statistics.pstdev(values)/mean if mean else 0.0,'peak_tracemalloc_bytes':peak,'result_size':len(result) if hasattr(result,'__len__') else None}
        entries=tuple(iter_repository_entries(root)); file_bytes=sum(path.stat().st_size for path in entries if path.is_file() and not path.is_symlink())
        result={
            'tree':{'entries':len(entries),'file_bytes':file_bytes},
            'enumeration':measure(lambda:tuple(iter_repository_entries(root)),repeats=7),
            'manifest':measure(lambda:file_manifest(root)),
            'security_scan':measure(lambda:scan(root),repeats=3),
            'repository_audit':measure(lambda:audit_repository(root),repeats=3),
        }
        print(json.dumps(result,sort_keys=True))
        """,
    )


def profile_hot_functions(root: Path) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    workloads = {
        "parser_50mib": "from tsao_computation.adapters import get_adapter; p=('iteration converged completed\\n'*1900000)[:50*1024*1024]; get_adapter('orca').parse(p)",
        "manifest": "from pathlib import Path; from tsao_computation.provenance.manifest import file_manifest; file_manifest(Path('.'))",
        "security_scan": "from pathlib import Path; from scripts.security_scan import scan; scan(Path('.'))",
        "repository_audit": "from pathlib import Path; from tsao_computation.repository_audit import audit_repository; audit_repository(Path('.'))",
    }
    env = _python_env(root)
    with tempfile.TemporaryDirectory(prefix="tsao-v9-profile-") as temporary:
        temporary_root = Path(temporary)
        for name, code in workloads.items():
            profile_path = temporary_root / f"{name}.prof"
            workload_path = temporary_root / f"{name}.py"
            workload_path.write_text(code + "\n", encoding="utf-8", newline="\n")
            subprocess.run(  # nosec B603
                [sys.executable, "-m", "cProfile", "-o", str(profile_path), str(workload_path)],
                cwd=root,
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            profiles[name] = _run_json(
                root,
                r"""
                import json,pstats,sys
                stats=pstats.Stats(sys.argv[1])
                rows=[]
                for (filename,line,function),(cc,nc,tt,ct,callers) in sorted(stats.stats.items(),key=lambda item:item[1][3],reverse=True)[:20]:
                    rows.append({'file':filename,'line':line,'function':function,'primitive_calls':cc,'calls':nc,'total_seconds':tt,'cumulative_seconds':ct})
                print(json.dumps({'total_calls':stats.total_calls,'primitive_calls':stats.prim_calls,'total_seconds':stats.total_tt,'top_cumulative':rows},sort_keys=True))
                """,
                str(profile_path),
            )
    return profiles


def end_to_end_profile(root: Path, *, repeats: int) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for profile in ("quality", "core", "package", "all"):
        profiles[profile] = measure_command(
            root,
            (sys.executable, "scripts/verify_all.py", "--profile", profile),
            warmups=1 if profile == "all" else 0,
            repeats=repeats if profile == "all" else max(2, repeats - 1),
        )
    profiles["pytest"] = measure_command(
        root,
        (sys.executable, "-m", "pytest", "-q"),
        warmups=0,
        repeats=max(2, repeats - 1),
    )
    return profiles


def build_report(
    root: Path, *, baseline_sha: str, include_end_to_end: bool, repeats: int
) -> dict[str, Any]:
    resolved = root.resolve()
    report: dict[str, Any] = {
        "schema_version": "2.0",
        "baseline_sha": baseline_sha,
        "root": str(resolved),
        "python": sys.version,
        "platform": sys.platform,
        "claim_boundary": CLAIM_BOUNDARY,
        "methodology": {
            "same_host_required_for_comparison": True,
            "warmups": "2 for microbenchmarks; 1 for verify_all all",
            "statistics": ["median", "min", "p90", "stdev", "cv"],
            "resource_metrics": ["wall", "CPU", "peak RSS", "filesystem input/output"],
        },
        "startup": startup_profile(resolved),
        "registry_and_routing": registry_and_routing_profile(resolved),
        "adapters": adapter_profile(resolved),
        "parsing": parser_profile(resolved),
        "repository": repository_profile(resolved),
        "profiles": profile_hot_functions(resolved),
    }
    if include_end_to_end:
        report["end_to_end"] = end_to_end_profile(resolved, repeats=repeats)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile TsaoSciComputation V9 hot paths.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-end-to-end", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repeats < 2:
        raise ValueError("repeats must be at least two")
    report = build_report(
        args.root,
        baseline_sha=args.baseline_sha,
        include_end_to_end=args.include_end_to_end,
        repeats=args.repeats,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps({"output": str(args.output), "baseline_sha": args.baseline_sha}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
