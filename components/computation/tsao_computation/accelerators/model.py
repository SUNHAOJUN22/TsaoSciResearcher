from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from typing import TypeVar

from ..errors import ContractError


class AcceleratorBackend(str, Enum):
    CPU = "cpu"
    OPENMP = "openmp"
    MPI = "mpi"
    TASK_PARALLEL = "task-parallel"
    REMOTE = "remote"
    CUDA = "cuda"
    HIP = "hip"
    SYCL = "sycl"
    OPENCL = "opencl"
    KOKKOS = "kokkos"


class PlacementTarget(str, Enum):
    EDGE = "edge"
    LOCAL = "local"
    WORKSTATION = "workstation"
    HPC = "hpc"
    CLOUD = "cloud"


class AcceleratorPolicy(str, Enum):
    DISABLED = "disabled"
    PREFERRED = "preferred"
    REQUIRED = "required"


class PrecisionPolicy(str, Enum):
    FP64 = "fp64"
    FP32 = "fp32"
    MIXED = "mixed"
    BF16 = "bf16"
    FP16 = "fp16"


E = TypeVar("E", bound=Enum)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: object, field_name: str) -> str | None:
    return None if value is None else _required_string(value, field_name)


def _positive_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContractError(f"{field_name} must be a positive integer")
    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{field_name} must be a non-negative integer")
    return value


def _positive_float(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{field_name} must be a positive finite number")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise ContractError(f"{field_name} must be a positive finite number")
    return parsed


def _enum_value(enum_type: type[E], value: object, field_name: str) -> E:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise ContractError(f"{field_name} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        choices = [item.value for item in enum_type]
        raise ContractError(f"{field_name} must be one of {choices}") from error


def _enum_tuple(
    enum_type: type[E], value: object, field_name: str, *, non_empty: bool = True
) -> tuple[E, ...]:
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise ContractError(f"{field_name} must be an array")
    parsed = tuple(_enum_value(enum_type, item, field_name) for item in value)
    if (non_empty and not parsed) or len(set(parsed)) != len(parsed):
        raise ContractError(f"{field_name} must be non-empty and unique")
    return parsed


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise ContractError(f"{field_name} must be an array")
    parsed = tuple(_required_string(item, field_name) for item in value)
    if len(set(parsed)) != len(parsed):
        raise ContractError(f"{field_name} must be unique")
    return parsed


@dataclass(frozen=True, slots=True)
class AcceleratorDevice:
    backend: AcceleratorBackend
    index: int
    name: str
    memory_gib: float | None = None
    architecture: str | None = None
    vendor: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "backend", _enum_value(AcceleratorBackend, self.backend, "backend")
        )
        object.__setattr__(self, "index", _non_negative_int(self.index, "index"))
        object.__setattr__(self, "name", _required_string(self.name, "name"))
        object.__setattr__(self, "memory_gib", _positive_float(self.memory_gib, "memory_gib"))
        object.__setattr__(
            self, "architecture", _optional_string(self.architecture, "architecture")
        )
        object.__setattr__(self, "vendor", _optional_string(self.vendor, "vendor"))

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["backend"] = self.backend.value
        return payload


@dataclass(frozen=True, slots=True)
class AcceleratorLibraryEvidence:
    slug: str
    modules: tuple[str, ...] = ()
    version: str | None = None
    detected: bool = True
    qualified: bool = False
    qualification: str = "unqualified"

    def __post_init__(self) -> None:
        object.__setattr__(self, "slug", _required_string(self.slug, "slug"))
        object.__setattr__(self, "modules", _string_tuple(self.modules, "modules"))
        object.__setattr__(self, "version", _optional_string(self.version, "version"))
        if not isinstance(self.detected, bool) or not isinstance(self.qualified, bool):
            raise ContractError("detected and qualified must be booleans")
        if self.qualified and not self.detected:
            raise ContractError("a qualified library must be detected")
        object.__setattr__(
            self,
            "qualification",
            _required_string(self.qualification, "qualification"),
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["modules"] = list(self.modules)
        return payload


@dataclass(frozen=True, slots=True)
class AcceleratorInventory:
    logical_cpu_count: int
    architecture: str
    operating_system: str
    memory_gib: float | None
    backends: tuple[AcceleratorBackend, ...]
    devices: tuple[AcceleratorDevice, ...] = ()
    tools: tuple[str, ...] = ()
    python_modules: tuple[str, ...] = ()
    libraries: tuple[AcceleratorLibraryEvidence, ...] = ()
    placements: tuple[PlacementTarget, ...] = (PlacementTarget.LOCAL,)
    claim_boundary: str = (
        "Hardware and library detection is planning evidence only; it does not prove solver "
        "compatibility, numerical speedup, convergence, physical validity, or authorization."
    )

    def __post_init__(self) -> None:
        cpu_count = _positive_int(self.logical_cpu_count, "logical_cpu_count")
        if cpu_count is None:
            raise ContractError("logical_cpu_count must be a positive integer")
        object.__setattr__(self, "logical_cpu_count", cpu_count)
        object.__setattr__(
            self, "architecture", _required_string(self.architecture, "architecture")
        )
        object.__setattr__(
            self,
            "operating_system",
            _required_string(self.operating_system, "operating_system"),
        )
        object.__setattr__(self, "memory_gib", _positive_float(self.memory_gib, "memory_gib"))
        backends = _enum_tuple(AcceleratorBackend, self.backends, "backends")
        object.__setattr__(self, "backends", backends)
        if isinstance(self.devices, (str, bytes)) or not isinstance(self.devices, Iterable):
            raise ContractError("devices must be an array")
        devices = tuple(self.devices)
        if any(not isinstance(item, AcceleratorDevice) for item in devices):
            raise ContractError("devices must contain AcceleratorDevice records")
        if any(item.backend not in backends for item in devices):
            raise ContractError("device backends must be declared in inventory backends")
        keys = tuple((item.backend, item.index) for item in devices)
        if len(set(keys)) != len(keys):
            raise ContractError("device backend/index pairs must be unique")
        object.__setattr__(self, "devices", devices)
        object.__setattr__(self, "tools", _string_tuple(self.tools, "tools"))
        object.__setattr__(
            self, "python_modules", _string_tuple(self.python_modules, "python_modules")
        )
        if isinstance(self.libraries, (str, bytes)) or not isinstance(self.libraries, Iterable):
            raise ContractError("libraries must be an array")
        libraries = tuple(self.libraries)
        if any(not isinstance(item, AcceleratorLibraryEvidence) for item in libraries):
            raise ContractError("libraries must contain AcceleratorLibraryEvidence records")
        if len({item.slug for item in libraries}) != len(libraries):
            raise ContractError("library slugs must be unique")
        object.__setattr__(self, "libraries", libraries)
        object.__setattr__(
            self,
            "placements",
            _enum_tuple(PlacementTarget, self.placements, "placements"),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _required_string(self.claim_boundary, "claim_boundary"),
        )

    def has_backend(self, backend: AcceleratorBackend | str) -> bool:
        normalized = _enum_value(AcceleratorBackend, backend, "backend")
        return normalized in self.backends

    def devices_for(self, backend: AcceleratorBackend | str) -> tuple[AcceleratorDevice, ...]:
        normalized = _enum_value(AcceleratorBackend, backend, "backend")
        return tuple(device for device in self.devices if device.backend == normalized)

    def library_evidence_for(self, slug: str) -> AcceleratorLibraryEvidence | None:
        normalized = _required_string(slug, "slug")
        return next((item for item in self.libraries if item.slug == normalized), None)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["backends"] = [item.value for item in self.backends]
        payload["placements"] = [item.value for item in self.placements]
        payload["devices"] = [item.to_dict() for item in self.devices]
        payload["libraries"] = [item.to_dict() for item in self.libraries]
        return payload


@dataclass(frozen=True, slots=True)
class ComputeResourceRequest:
    placement: PlacementTarget = PlacementTarget.LOCAL
    accelerator_policy: AcceleratorPolicy = AcceleratorPolicy.PREFERRED
    preferred_backends: tuple[AcceleratorBackend, ...] = (
        AcceleratorBackend.CUDA,
        AcceleratorBackend.HIP,
        AcceleratorBackend.SYCL,
        AcceleratorBackend.OPENMP,
        AcceleratorBackend.MPI,
        AcceleratorBackend.TASK_PARALLEL,
        AcceleratorBackend.REMOTE,
        AcceleratorBackend.CPU,
    )
    cpu_cores: int | None = None
    memory_gib: float | None = None
    mpi_ranks: int | None = None
    threads_per_rank: int | None = None
    accelerator_count: int | None = None
    minimum_vram_gib: float | None = None
    precision: PrecisionPolicy = PrecisionPolicy.FP64
    deterministic: bool = True
    maximum_wall_seconds: float | None = None
    maximum_energy_kwh: float | None = None
    power_limit_watts: float | None = None
    allow_fallback: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "placement", _enum_value(PlacementTarget, self.placement, "placement")
        )
        object.__setattr__(
            self,
            "accelerator_policy",
            _enum_value(AcceleratorPolicy, self.accelerator_policy, "accelerator_policy"),
        )
        object.__setattr__(
            self,
            "preferred_backends",
            _enum_tuple(AcceleratorBackend, self.preferred_backends, "preferred_backends"),
        )
        for field_name in (
            "cpu_cores",
            "mpi_ranks",
            "threads_per_rank",
            "accelerator_count",
        ):
            object.__setattr__(
                self, field_name, _positive_int(getattr(self, field_name), field_name)
            )
        for field_name in (
            "memory_gib",
            "minimum_vram_gib",
            "maximum_wall_seconds",
            "maximum_energy_kwh",
            "power_limit_watts",
        ):
            object.__setattr__(
                self, field_name, _positive_float(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "precision", _enum_value(PrecisionPolicy, self.precision, "precision")
        )
        if not isinstance(self.deterministic, bool) or not isinstance(self.allow_fallback, bool):
            raise ContractError("deterministic and allow_fallback must be booleans")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> ComputeResourceRequest:
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ContractError("compute resources must be an object")
        allowed = {
            "placement",
            "accelerator_policy",
            "preferred_backends",
            "cpu_cores",
            "memory_gib",
            "mpi_ranks",
            "threads_per_rank",
            "accelerator_count",
            "minimum_vram_gib",
            "precision",
            "deterministic",
            "maximum_wall_seconds",
            "maximum_energy_kwh",
            "power_limit_watts",
            "allow_fallback",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ContractError(f"unknown compute resource fields: {unknown}")
        raw_backends = value.get(
            "preferred_backends", [item.value for item in cls().preferred_backends]
        )
        if isinstance(raw_backends, str) or not isinstance(raw_backends, (list, tuple)):
            raise ContractError("preferred_backends must be an array")
        return cls(
            placement=_enum_value(
                PlacementTarget,
                value.get("placement", PlacementTarget.LOCAL.value),
                "placement",
            ),
            accelerator_policy=_enum_value(
                AcceleratorPolicy,
                value.get("accelerator_policy", AcceleratorPolicy.PREFERRED.value),
                "accelerator_policy",
            ),
            preferred_backends=tuple(
                _enum_value(AcceleratorBackend, item, "preferred_backends") for item in raw_backends
            ),
            cpu_cores=_positive_int(value.get("cpu_cores"), "cpu_cores"),
            memory_gib=_positive_float(value.get("memory_gib"), "memory_gib"),
            mpi_ranks=_positive_int(value.get("mpi_ranks"), "mpi_ranks"),
            threads_per_rank=_positive_int(value.get("threads_per_rank"), "threads_per_rank"),
            accelerator_count=_positive_int(value.get("accelerator_count"), "accelerator_count"),
            minimum_vram_gib=_positive_float(value.get("minimum_vram_gib"), "minimum_vram_gib"),
            precision=_enum_value(
                PrecisionPolicy,
                value.get("precision", PrecisionPolicy.FP64.value),
                "precision",
            ),
            deterministic=value.get("deterministic", True),  # type: ignore[arg-type]
            maximum_wall_seconds=_positive_float(
                value.get("maximum_wall_seconds"), "maximum_wall_seconds"
            ),
            maximum_energy_kwh=_positive_float(
                value.get("maximum_energy_kwh"), "maximum_energy_kwh"
            ),
            power_limit_watts=_positive_float(value.get("power_limit_watts"), "power_limit_watts"),
            allow_fallback=value.get("allow_fallback", True),  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["placement"] = self.placement.value
        payload["accelerator_policy"] = self.accelerator_policy.value
        payload["preferred_backends"] = [item.value for item in self.preferred_backends]
        payload["precision"] = self.precision.value
        return payload


ResourceRequest = ComputeResourceRequest
HardwareInventory = AcceleratorInventory
