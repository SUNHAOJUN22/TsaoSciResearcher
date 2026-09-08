from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from .model import AcceleratorBackend


@dataclass(frozen=True, slots=True)
class AccelerationLibrary:
    slug: str
    name: str
    vendor: str
    category: str
    backends: tuple[AcceleratorBackend, ...]
    workloads: tuple[str, ...]
    domains: tuple[str, ...]
    integration: str
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["backends"] = [item.value for item in self.backends]
        return payload


_BOUNDARY = (
    "Candidate integration only. Availability, license, architecture support, precision, "
    "performance, numerical equivalence, and scientific validity require deployment evidence."
)

_LIBRARIES = (
    AccelerationLibrary(
        "cutensor",
        "NVIDIA cuTENSOR",
        "NVIDIA",
        "tensor",
        (AcceleratorBackend.CUDA,),
        ("tensor-contraction", "tensor-reduction", "tensor-permutation", "block-sparse"),
        ("materials", "quantum", "machine-learning", "multiphysics"),
        "C/C++ or Python binding",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cuequivariance",
        "NVIDIA cuEquivariance",
        "NVIDIA",
        "equivariant-ml",
        (AcceleratorBackend.CUDA,),
        ("equivariant-neural-network", "segmented-tensor-product", "mace"),
        ("molecular", "materials", "proteins", "machine-learning-potential"),
        "optional PyTorch/JAX packages",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "nvmath-python",
        "NVIDIA nvmath-python",
        "NVIDIA",
        "math",
        (AcceleratorBackend.CUDA,),
        ("dense-linear-algebra", "sparse-linear-algebra", "fft", "random", "tensor"),
        ("quantum", "cfd", "finite-element", "molecular", "process"),
        "optional Python package",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cupy",
        "CuPy",
        "CuPy project",
        "array",
        (AcceleratorBackend.CUDA,),
        ("array-api", "dense-linear-algebra", "sparse-linear-algebra", "fft", "custom-kernel"),
        ("quantum", "materials", "molecular", "finite-element", "data"),
        "optional Python package with DLPack interoperability",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cublas",
        "NVIDIA cuBLAS",
        "NVIDIA",
        "dense-linear-algebra",
        (AcceleratorBackend.CUDA,),
        ("blas", "matrix-multiply", "batched-linear-algebra"),
        ("quantum", "machine-learning", "finite-element", "cfd"),
        "solver build or native C/C++",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cusolver",
        "NVIDIA cuSOLVER",
        "NVIDIA",
        "solver",
        (AcceleratorBackend.CUDA,),
        ("factorization", "eigensolver", "linear-solve"),
        ("quantum", "finite-element", "cfd", "multiphysics"),
        "solver build or native C/C++",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cusparse",
        "NVIDIA cuSPARSE",
        "NVIDIA",
        "sparse",
        (AcceleratorBackend.CUDA,),
        ("sparse-matrix", "iterative-solve", "preconditioning"),
        ("finite-element", "cfd", "multiphysics", "graph"),
        "solver build or native C/C++",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cufft",
        "NVIDIA cuFFT",
        "NVIDIA",
        "fft",
        (AcceleratorBackend.CUDA,),
        ("fft", "spectral-method", "particle-mesh"),
        ("molecular", "periodic-dft", "cfd", "signal"),
        "solver build or native C/C++",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "curand",
        "NVIDIA cuRAND",
        "NVIDIA",
        "random",
        (AcceleratorBackend.CUDA,),
        ("monte-carlo", "stochastic-simulation", "uncertainty", "sampling"),
        ("reactors", "polymers", "molecular", "uncertainty"),
        "native C/C++ or qualified framework integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "nccl",
        "NVIDIA NCCL",
        "NVIDIA",
        "communication",
        (AcceleratorBackend.CUDA,),
        ("multi-gpu-collective", "distributed-training", "domain-decomposition"),
        ("machine-learning", "molecular", "quantum", "multiphysics"),
        "solver/framework integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "nvshmem",
        "NVIDIA NVSHMEM",
        "NVIDIA",
        "communication",
        (AcceleratorBackend.CUDA,),
        ("gpu-one-sided-communication", "multi-node-gpu"),
        ("molecular", "cfd", "finite-element", "quantum"),
        "native C/C++ integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "nvcomp",
        "NVIDIA nvCOMP",
        "NVIDIA",
        "data",
        (AcceleratorBackend.CUDA,),
        ("gpu-compression", "checkpoint", "trajectory", "field-data"),
        ("molecular", "cfd", "finite-element", "digital-twin"),
        "native C/C++ or Python binding",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "gpudirect-storage",
        "NVIDIA GPUDirect Storage",
        "NVIDIA",
        "data-path",
        (AcceleratorBackend.CUDA,),
        ("direct-storage", "trajectory", "field-data", "checkpoint", "training-data"),
        ("molecular", "cfd", "finite-element", "machine-learning", "hpc"),
        "qualified Linux server/HPC deployment",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "tensorrt",
        "NVIDIA TensorRT",
        "NVIDIA",
        "edge-inference",
        (AcceleratorBackend.CUDA,),
        ("surrogate-inference", "reduced-order-model", "edge-inference"),
        ("edge", "digital-twin", "control", "machine-learning-potential"),
        "optional C++/Python runtime",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "rapids",
        "NVIDIA RAPIDS",
        "NVIDIA",
        "data-science",
        (AcceleratorBackend.CUDA,),
        ("table", "graph", "clustering", "nearest-neighbor", "dataframe"),
        ("trajectory", "materials-informatics", "uncertainty", "digital-twin"),
        "optional Python packages",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "rapids-cudf",
        "RAPIDS cuDF",
        "NVIDIA",
        "dataframe",
        (AcceleratorBackend.CUDA,),
        ("dataframe", "columnar-data", "preprocessing", "trajectory-table"),
        ("materials-informatics", "trajectory", "process", "uncertainty"),
        "optional Python package",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "rapids-cuml",
        "RAPIDS cuML",
        "NVIDIA",
        "machine-learning",
        (AcceleratorBackend.CUDA,),
        ("clustering", "regression", "nearest-neighbor", "dimensionality-reduction"),
        ("surrogates", "materials-informatics", "process", "uncertainty"),
        "optional Python package",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "warp",
        "NVIDIA Warp",
        "NVIDIA",
        "kernel-framework",
        (AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        ("particle", "mesh", "geometry", "sparse", "fem", "differentiable-simulation"),
        ("molecular", "finite-element", "multiphysics", "robotics", "digital-twin"),
        "optional Python JIT kernel package",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cudss",
        "NVIDIA cuDSS (Preview)",
        "NVIDIA",
        "sparse-direct",
        (AcceleratorBackend.CUDA,),
        ("sparse-direct-solve", "factorization", "iterative-refinement", "multi-gpu"),
        ("finite-element", "cfd", "multiphysics", "quantum"),
        "optional native C/C++ integration; preview API",
        "Preview candidate only. The cuDSS API is subject to change; versioned build, "
        "numerical-equivalence, stability, and performance evidence are required.",
    ),
    AccelerationLibrary(
        "cusparselt",
        "NVIDIA cuSPARSELt",
        "NVIDIA",
        "structured-sparse",
        (AcceleratorBackend.CUDA,),
        ("structured-sparse-matmul", "pruning", "compression", "batched-sparse-gemm"),
        ("machine-learning", "equivariant-ml", "materials", "surrogates"),
        "optional native C/C++ or qualified framework integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "amgx",
        "NVIDIA AmgX",
        "NVIDIA",
        "algebraic-multigrid",
        (AcceleratorBackend.CUDA,),
        ("linear-solver", "preconditioner", "algebraic-multigrid", "multi-gpu", "mpi"),
        ("finite-element", "cfd", "multiphysics", "implicit-solvers"),
        "optional C API with solver and MPI integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cuquantum",
        "NVIDIA cuQuantum",
        "NVIDIA",
        "quantum-simulation",
        (AcceleratorBackend.CUDA,),
        ("state-vector", "tensor-network", "density-matrix", "quantum-dynamics"),
        ("quantum-computing", "quantum-dynamics", "tensor-networks"),
        "optional C or Python APIs",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cupynumeric",
        "NVIDIA cuPyNumeric and Legate",
        "NVIDIA",
        "distributed-array",
        (AcceleratorBackend.CPU, AcceleratorBackend.CUDA, AcceleratorBackend.MPI),
        ("numpy-api", "linear-algebra", "fft", "stencil", "multi-node"),
        ("cfd", "finite-element", "uncertainty", "data", "scientific-python"),
        "optional Python/Legate runtime",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "cugraph",
        "RAPIDS cuGraph",
        "NVIDIA",
        "graph",
        (AcceleratorBackend.CUDA,),
        ("graph-analytics", "connectivity", "clustering", "centrality", "multi-gpu"),
        ("molecular", "materials", "percolation", "digital-twin", "networks"),
        "optional RAPIDS Python or C API integration",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "holoscan",
        "NVIDIA Holoscan SDK",
        "NVIDIA",
        "edge-streaming",
        (AcceleratorBackend.CPU, AcceleratorBackend.CUDA),
        ("sensor-pipeline", "streaming", "low-latency", "edge-inference", "operator-graph"),
        ("edge", "digital-twin", "control", "industrial-inspection", "sensor-processing"),
        "optional C++/Python edge SDK",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "kokkos",
        "Kokkos",
        "Kokkos project",
        "performance-portability",
        (
            AcceleratorBackend.OPENMP,
            AcceleratorBackend.CUDA,
            AcceleratorBackend.HIP,
            AcceleratorBackend.SYCL,
        ),
        ("portable-kernel", "mesh", "particle", "sparse"),
        ("finite-element", "molecular", "cfd", "multiphysics"),
        "optional C++20 native backend",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "mpi",
        "MPI",
        "MPI Forum implementations",
        "distributed",
        (AcceleratorBackend.MPI,),
        ("multi-process", "multi-node", "ensemble", "domain-decomposition"),
        ("all-scientific-domains",),
        "external launcher and solver support",
        _BOUNDARY,
    ),
    AccelerationLibrary(
        "dlpack-arrow",
        "DLPack and Arrow C Data Interface",
        "Open standards",
        "interoperability",
        (
            AcceleratorBackend.CPU,
            AcceleratorBackend.CUDA,
            AcceleratorBackend.HIP,
            AcceleratorBackend.SYCL,
        ),
        ("zero-copy-tensor", "columnar-data", "cross-language"),
        ("all-scientific-domains", "edge"),
        "stable C interfaces",
        _BOUNDARY,
    ),
)


def acceleration_libraries() -> tuple[AccelerationLibrary, ...]:
    return _LIBRARIES


def get_acceleration_library(slug: str) -> AccelerationLibrary:
    for item in _LIBRARIES:
        if item.slug == slug:
            return item
    raise KeyError(f"unknown acceleration library: {slug}")


@lru_cache(maxsize=256)
def _recommend_acceleration_libraries_cached(
    backend: AcceleratorBackend | None,
    workload: str | None,
) -> tuple[AccelerationLibrary, ...]:
    matches = tuple(
        item
        for item in _LIBRARIES
        if (backend is None or backend in item.backends)
        and (
            workload is None
            or any(workload in candidate.casefold() for candidate in item.workloads)
        )
    )
    if backend is None:
        return matches
    return tuple(sorted(matches, key=lambda item: len(item.backends)))


def recommend_acceleration_libraries(
    *,
    backend: AcceleratorBackend | str | None = None,
    workload: str | None = None,
) -> tuple[AccelerationLibrary, ...]:
    normalized_backend = (
        None
        if backend is None
        else backend
        if isinstance(backend, AcceleratorBackend)
        else AcceleratorBackend(backend)
    )
    normalized_workload = workload.casefold() if workload else None
    return _recommend_acceleration_libraries_cached(
        normalized_backend,
        normalized_workload,
    )


library_catalog = acceleration_libraries
recommend_libraries = recommend_acceleration_libraries
