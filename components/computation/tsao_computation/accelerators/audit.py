from __future__ import annotations

import ast
import hashlib
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

_CLAIM_BOUNDARY: Final = (
    "Static source evidence only. A candidate does not establish that code is a material hotspot, "
    "that an accelerator is available, or that performance, numerical equivalence, convergence, "
    "physical validity, applicability, energy use, or deployment safety will improve."
)
_EXCLUDED_DIRS: Final = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "venv",
        "wheelhouse",
    }
)
_LANGUAGE_SUFFIXES: Final = {
    ".py": "python",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".cu": "cuda",
    ".cuh": "cuda",
    ".f": "fortran",
    ".f90": "fortran",
    ".f95": "fortran",
    ".for": "fortran",
    ".rs": "rust",
    ".jl": "julia",
}


@dataclass(frozen=True, slots=True)
class AccelerationOpportunity:
    candidate_id: str
    path: str
    line: int
    symbol: str
    file_scope: str
    source_sha256: str
    category: str
    score: int
    confidence: str
    current_pattern: str
    first_action: str
    backend_candidates: tuple[str, ...]
    library_candidates: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    blockers: tuple[str, ...]
    runtime_status: str = "unprofiled"
    decision: str = "profile"
    claim_boundary: str = _CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["backend_candidates"] = list(self.backend_candidates)
        payload["library_candidates"] = list(self.library_candidates)
        payload["evidence_requirements"] = list(self.evidence_requirements)
        payload["blockers"] = list(self.blockers)
        return payload


@dataclass(frozen=True, slots=True)
class RepositoryAccelerationAudit:
    root: str
    scope: str
    source_tree_sha256: str
    source_files: int
    source_lines: int
    language_files: tuple[tuple[str, int], ...]
    language_lines: tuple[tuple[str, int], ...]
    python_files_analyzed: int
    python_files_excluded: int
    parse_failures: tuple[str, ...]
    file_scope_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    opportunities: tuple[AccelerationOpportunity, ...]
    claim_boundary: str = _CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "scope": self.scope,
            "source_tree_sha256": self.source_tree_sha256,
            "source_files": self.source_files,
            "source_lines": self.source_lines,
            "language_files": dict(self.language_files),
            "language_lines": dict(self.language_lines),
            "python_files_analyzed": self.python_files_analyzed,
            "python_files_excluded": self.python_files_excluded,
            "parse_failures": list(self.parse_failures),
            "file_scope_counts": dict(self.file_scope_counts),
            "category_counts": dict(self.category_counts),
            "opportunity_count": len(self.opportunities),
            "opportunities": [item.to_dict() for item in self.opportunities],
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True, slots=True)
class _Rule:
    category: str
    score: int
    confidence: str
    current_pattern: str
    first_action: str
    backends: tuple[str, ...]
    libraries: tuple[str, ...]
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]


_RULES: Final = (
    (
        ("e3nn.", "mace.", "nequip.", "allegro."),
        _Rule(
            "equivariant-ml",
            98,
            "high",
            "equivariant neural-network operator",
            "bind the exact model/framework version, then benchmark cuEquivariance end to end",
            ("cuda",),
            ("cuequivariance", "cutensor"),
            ("CPU/framework reference", "model-output equivalence", "end-to-end timing and memory"),
            ("framework or model incompatibility", "precision drift", "unsupported operator graph"),
        ),
    ),
    (
        ("numpy.einsum", "numpy.tensordot", "numpy.matmul", "torch.einsum"),
        _Rule(
            "tensor-contraction",
            95,
            "high",
            "explicit tensor contraction or matrix product",
            "profile shapes and layouts, then compare framework-native kernels with cuTENSOR",
            ("cpu", "openmp", "cuda"),
            ("cutensor", "nvmath-python", "cupy"),
            (
                "scalar or CPU reference",
                "shape/layout inventory",
                "numerical-equivalence tolerance",
            ),
            ("transfer overhead", "layout conversion", "temporary-memory growth"),
        ),
    ),
    (
        ("scipy.sparse.", "petsc4py.", "pyamg."),
        _Rule(
            "sparse-linear-algebra",
            94,
            "high",
            "sparse assembly, factorization, or iterative solve",
            "classify the matrix and preconditioner before testing cuSPARSE, cuDSS, or AmgX",
            ("cpu", "openmp", "mpi", "cuda"),
            ("cusparse", "cudss", "amgx", "kokkos"),
            ("matrix class", "residual history", "iteration count", "CPU reference"),
            ("unsupported sparsity pattern", "preconditioner mismatch", "convergence regression"),
        ),
    ),
    (
        ("numpy.fft.", "scipy.fft.", "scipy.fftpack."),
        _Rule(
            "fft-spectral",
            93,
            "high",
            "FFT, spectral, or particle-mesh transform",
            "measure transform sizes and batching, then compare cuFFT or nvmath-python",
            ("cpu", "openmp", "cuda"),
            ("cufft", "nvmath-python", "cupy"),
            ("normalization convention", "CPU reference", "batched-size benchmark"),
            ("small-transform launch overhead", "normalization mismatch", "device-transfer cost"),
        ),
    ),
    (
        ("numpy.linalg.", "scipy.linalg."),
        _Rule(
            "dense-linear-algebra",
            92,
            "high",
            "dense factorization, eigensolver, or linear solve",
            "profile matrix sizes and conditioning, then evaluate BLAS/cuBLAS and cuSOLVER paths",
            ("cpu", "openmp", "cuda"),
            ("nvmath-python", "cublas", "cusolver", "cupy"),
            ("condition number", "FP64 reference", "residual and observable equivalence"),
            ("ill conditioning", "mixed-precision drift", "small-matrix overhead"),
        ),
    ),
    (
        ("numpy.random.", "random.random", "random.gauss", "random.uniform"),
        _Rule(
            "stochastic-sampling",
            82,
            "high",
            "random sampling or Monte Carlo draw",
            "vectorize the CPU reference first, then test parallel cases or cuRAND-backed batching",
            ("cpu", "openmp", "mpi", "cuda"),
            ("curand", "cupy", "cupynumeric"),
            ("seed policy", "distribution tests", "statistical-equivalence bounds"),
            ("non-reproducible streams", "correlated samples", "transfer overhead"),
        ),
    ),
    (
        ("subprocess.run", "subprocess.popen", "subprocess.check_call", "subprocess.check_output"),
        _Rule(
            "external-solver-dispatch",
            68,
            "high",
            "external command or solver dispatch",
            "batch independent cases and prefer the solver's native MPI/GPU backend before custom kernels",
            ("cpu", "openmp", "mpi", "cuda", "hip", "sycl"),
            ("mpi", "nccl"),
            ("solver build features", "command provenance", "same-input end-to-end timing"),
            ("license or scheduler limits", "oversubscription", "unsupported solver backend"),
        ),
    ),
    (
        ("os.walk", "pathlib.path.rglob", "pathlib.path.glob"),
        _Rule(
            "filesystem-scan",
            45,
            "medium",
            "repository or dataset filesystem walk",
            "reduce repeated passes, cache stable metadata, and stream results; GPU migration is usually unsuitable",
            ("cpu",),
            (),
            ("I/O trace", "filesystem-pass count", "same-host latency and peak-memory baseline"),
            ("cold-cache variability", "network filesystem", "stale cache"),
        ),
    ),
)

_NUMERIC_LOOP_RULE: Final = _Rule(
    "numeric-python-loop",
    66,
    "medium",
    "arithmetic-heavy Python loop",
    "establish a vectorized CPU reference, then consider C++20/OpenMP, Kokkos, Warp, or CUDA",
    ("cpu", "openmp", "cuda", "hip", "sycl"),
    ("kokkos", "warp", "cupy"),
    (
        "scalar reference",
        "shape and stride contract",
        "sanitizer and race tests",
        "size-scaled benchmark",
    ),
    ("Python control-flow dependence", "insufficient arithmetic intensity", "precision drift"),
)


class _OpportunityVisitor(ast.NodeVisitor):
    def __init__(
        self,
        path: str,
        aliases: dict[str, str],
        *,
        file_scope: str,
        source_sha256: str,
    ) -> None:
        self.path = path
        self.aliases = aliases
        self.file_scope = file_scope
        self.source_sha256 = source_sha256
        self.symbols: list[str] = ["<module>"]
        self.loop_depth = 0
        self.items: dict[tuple[str, str], AccelerationOpportunity] = {}

    @property
    def symbol(self) -> str:
        return ".".join(item for item in self.symbols if item != "<module>") or "<module>"

    def _qualified_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id).casefold()
        if isinstance(node, ast.Attribute):
            parent = self._qualified_name(node.value)
            return f"{parent}.{node.attr.casefold()}" if parent else node.attr.casefold()
        return ""

    def _add(self, node: ast.AST, rule: _Rule, *, score_bonus: int = 0) -> None:
        score = min(100, rule.score + score_bonus)
        line = max(1, int(getattr(node, "lineno", 1)))
        identity = "\0".join((self.path, str(line), self.symbol, rule.category, self.source_sha256))
        item = AccelerationOpportunity(
            candidate_id=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            path=self.path,
            line=line,
            symbol=self.symbol,
            file_scope=self.file_scope,
            source_sha256=self.source_sha256,
            category=rule.category,
            score=score,
            confidence=rule.confidence,
            current_pattern=rule.current_pattern,
            first_action=rule.first_action,
            backend_candidates=rule.backends,
            library_candidates=rule.libraries,
            evidence_requirements=rule.evidence,
            blockers=rule.blockers,
            decision="profile" if self.file_scope == "production" else "diagnostic-only",
        )
        key = (self.symbol, rule.category)
        current = self.items.get(key)
        if current is None or (-item.score, item.line) < (-current.score, current.line):
            self.items[key] = item

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.append(node.name)
        self.generic_visit(node)
        self.symbols.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.symbols.append(node.name)
        self.generic_visit(node)
        self.symbols.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(node.name)
        self.generic_visit(node)
        self.symbols.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = self._qualified_name(node.func)
        for prefixes, rule in _RULES:
            if any(name == prefix.rstrip(".") or name.startswith(prefix) for prefix in prefixes):
                self._add(node, rule, score_bonus=min(6, self.loop_depth * 2))
                break
        if name in {"rglob", "glob"} or name.endswith(".rglob") or name.endswith(".glob"):
            self._add(node, _RULES[-1][1], score_bonus=min(6, self.loop_depth * 2))
        self.generic_visit(node)

    def _visit_loop(self, node: ast.For | ast.AsyncFor | ast.While) -> None:
        self.loop_depth += 1
        numeric_ops = sum(
            isinstance(item, (ast.BinOp, ast.UnaryOp, ast.AugAssign)) for item in ast.walk(node)
        )
        if numeric_ops >= 8 or (self.loop_depth >= 2 and numeric_ops >= 4):
            bonus = min(18, self.loop_depth * 4 + numeric_ops // 3)
            self._add(node, _NUMERIC_LOOP_RULE, score_bonus=bonus)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_loop(node)


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for item in node.names:
                if item.name == "*":
                    continue
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    aliases.setdefault("Path", "pathlib.Path")
    return aliases


_AUDIT_SCOPES: Final = frozenset({"production", "full-tree"})


def _file_scope(path: Path) -> str:
    parts = tuple(part.casefold() for part in path.parts)
    name = path.name.casefold()
    if "tests" in parts or name.startswith("test_"):
        return "test"
    if any("benchmark" in part for part in parts) or "performance" in name:
        return "benchmark"
    if parts and parts[0] in {"scripts", "examples"}:
        return "tooling"
    if name == "_bootstrap.py":
        return "tooling"
    return "production"


def _is_excluded(path: Path, *, scope: str) -> bool:
    lowered = {part.casefold() for part in path.parts}
    if lowered & _EXCLUDED_DIRS:
        return True
    return scope == "production" and _file_scope(path) != "production"


def _line_count(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n") + int(not data.endswith(b"\n"))


def audit_repository_acceleration(
    root: str | Path = ".",
    *,
    include_tests: bool = False,
    scope: str | None = None,
    limit: int = 40,
    min_score: int = 40,
    max_python_bytes: int = 2_000_000,
) -> RepositoryAccelerationAudit:
    selected_scope = "full-tree" if include_tests else (scope or "production")
    if selected_scope not in _AUDIT_SCOPES:
        raise ValueError(f"scope must be one of {sorted(_AUDIT_SCOPES)}")
    if include_tests and scope not in {None, "full-tree"}:
        raise ValueError("include_tests conflicts with production scope")
    if limit < 1:
        raise ValueError("limit must be positive")
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")
    if max_python_bytes < 1:
        raise ValueError("max_python_bytes must be positive")

    requested_root = Path(root)
    resolved_root = requested_root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"audit root is not a directory: {requested_root}")

    language_files: Counter[str] = Counter()
    language_lines: Counter[str] = Counter()
    opportunities: list[AccelerationOpportunity] = []
    failures: list[str] = []
    file_scopes: Counter[str] = Counter()
    tree_digest = hashlib.sha256()
    analyzed = 0
    excluded = 0

    for path in sorted(resolved_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(resolved_root)
        language = _LANGUAGE_SUFFIXES.get(path.suffix.casefold())
        if language is None:
            continue
        data = path.read_bytes()
        source_sha256 = hashlib.sha256(data).hexdigest()
        tree_digest.update(relative.as_posix().encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(source_sha256.encode("ascii"))
        tree_digest.update(b"\n")
        file_scope = _file_scope(relative)
        file_scopes[file_scope] += 1
        language_files[language] += 1
        language_lines[language] += _line_count(data)
        if language != "python":
            continue
        if _is_excluded(relative, scope=selected_scope):
            excluded += 1
            continue
        if len(data) > max_python_bytes:
            failures.append(f"{relative.as_posix()}: exceeds max_python_bytes")
            continue
        try:
            text = data.decode("utf-8")
            tree = ast.parse(text, filename=relative.as_posix())
        except (SyntaxError, UnicodeDecodeError) as exc:
            failures.append(f"{relative.as_posix()}: {exc.__class__.__name__}")
            continue
        analyzed += 1
        visitor = _OpportunityVisitor(
            relative.as_posix(),
            _import_aliases(tree),
            file_scope=file_scope,
            source_sha256=source_sha256,
        )
        visitor.visit(tree)
        opportunities.extend(visitor.items.values())

    ranked = tuple(
        sorted(
            (item for item in opportunities if item.score >= min_score),
            key=lambda item: (-item.score, item.path, item.line, item.category, item.symbol),
        )[:limit]
    )
    categories = Counter(item.category for item in ranked)
    root_label = requested_root.as_posix()
    if resolved_root == Path.cwd().resolve():
        root_label = "."
    elif requested_root.is_absolute():
        root_label = requested_root.name or "."
    return RepositoryAccelerationAudit(
        root=root_label,
        scope=selected_scope,
        source_tree_sha256=tree_digest.hexdigest(),
        source_files=sum(language_files.values()),
        source_lines=sum(language_lines.values()),
        language_files=tuple(sorted(language_files.items())),
        language_lines=tuple(sorted(language_lines.items())),
        python_files_analyzed=analyzed,
        python_files_excluded=excluded,
        parse_failures=tuple(sorted(failures)),
        file_scope_counts=tuple(sorted(file_scopes.items())),
        category_counts=tuple(sorted(categories.items())),
        opportunities=ranked,
    )


audit_acceleration = audit_repository_acceleration
