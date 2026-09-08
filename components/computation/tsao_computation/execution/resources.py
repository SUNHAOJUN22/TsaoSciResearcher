from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from ..errors import SecurityError
from ..hashing import canonical_json_sha256


def _positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _gpu_devices(value: tuple[int, ...], field_name: str) -> tuple[int, ...]:
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value):
        raise ValueError(f"{field_name} must contain non-negative integers")
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must be unique")
    return tuple(value)


def _license_tokens(
    value: tuple[tuple[str, int], ...],
    field_name: str,
) -> tuple[tuple[str, int], ...]:
    normalized: list[tuple[str, int]] = []
    for name, count in value:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{field_name} names must be non-empty strings")
        normalized.append((name.strip(), _positive_int(count, field_name)))
    if len({name for name, _ in normalized}) != len(normalized):
        raise ValueError(f"{field_name} names must be unique")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class ExecutionResourceClaim:
    cpu_cores: int = 1
    gpu_devices: tuple[int, ...] = ()
    license_tokens: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "cpu_cores", _positive_int(self.cpu_cores, "cpu_cores"))
        object.__setattr__(
            self,
            "gpu_devices",
            _gpu_devices(self.gpu_devices, "gpu_devices"),
        )
        object.__setattr__(
            self,
            "license_tokens",
            _license_tokens(self.license_tokens, "license_tokens"),
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["gpu_devices"] = list(self.gpu_devices)
        payload["license_tokens"] = dict(self.license_tokens)
        return payload

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExecutionResourceCapacity:
    cpu_cores: int
    gpu_devices: tuple[int, ...] = ()
    license_tokens: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "cpu_cores", _positive_int(self.cpu_cores, "cpu_cores"))
        object.__setattr__(
            self,
            "gpu_devices",
            _gpu_devices(self.gpu_devices, "gpu_devices"),
        )
        object.__setattr__(
            self,
            "license_tokens",
            _license_tokens(self.license_tokens, "license_tokens"),
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["gpu_devices"] = list(self.gpu_devices)
        payload["license_tokens"] = dict(self.license_tokens)
        return payload

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


class ExecutionResourceBroker:
    def __init__(self, capacity: ExecutionResourceCapacity) -> None:
        self.capacity = capacity
        self._available_cpu = capacity.cpu_cores
        self._available_gpus = set(capacity.gpu_devices)
        self._available_licenses = dict(capacity.license_tokens)
        self._condition = threading.Condition()

    def _assert_fits(self, claim: ExecutionResourceClaim) -> None:
        if claim.cpu_cores > self.capacity.cpu_cores:
            raise SecurityError("resource claim exceeds CPU capacity")
        if not set(claim.gpu_devices) <= set(self.capacity.gpu_devices):
            raise SecurityError("resource claim requests unavailable GPU devices")
        capacity_licenses = dict(self.capacity.license_tokens)
        for name, count in claim.license_tokens:
            if count > capacity_licenses.get(name, 0):
                raise SecurityError(f"resource claim exceeds license capacity: {name}")

    def _available(self, claim: ExecutionResourceClaim) -> bool:
        if claim.cpu_cores > self._available_cpu:
            return False
        if not set(claim.gpu_devices) <= self._available_gpus:
            return False
        return all(
            count <= self._available_licenses.get(name, 0) for name, count in claim.license_tokens
        )

    @contextmanager
    def lease(self, claim: ExecutionResourceClaim) -> Iterator[None]:
        self._assert_fits(claim)
        with self._condition:
            self._condition.wait_for(lambda: self._available(claim))
            self._available_cpu -= claim.cpu_cores
            self._available_gpus.difference_update(claim.gpu_devices)
            for name, count in claim.license_tokens:
                self._available_licenses[name] -= count
        try:
            yield
        finally:
            with self._condition:
                self._available_cpu += claim.cpu_cores
                self._available_gpus.update(claim.gpu_devices)
                for name, count in claim.license_tokens:
                    self._available_licenses[name] = self._available_licenses.get(name, 0) + count
                self._condition.notify_all()


def _parse_visible_devices(variable: str, raw: object) -> tuple[int, ...]:
    if not isinstance(raw, str):
        raise SecurityError(f"{variable} visible-device environment must be a string")
    if not raw.strip():
        return ()
    parts = tuple(item.strip() for item in raw.split(","))
    if any(not item for item in parts):
        raise SecurityError("visible-device environment is not a comma-separated integer list")
    try:
        bound = tuple(int(item) for item in parts)
    except ValueError as error:
        raise SecurityError(
            "visible-device environment is not a comma-separated integer list"
        ) from error
    if any(item < 0 for item in bound):
        raise SecurityError("visible-device environment is not a comma-separated integer list")
    if len(set(bound)) != len(bound):
        raise SecurityError("visible-device environment must contain unique device indices")
    return bound


def validate_resource_binding(
    environment: Mapping[str, str],
    claim: ExecutionResourceClaim,
) -> None:
    variables = (
        "CUDA_VISIBLE_DEVICES",
        "HIP_VISIBLE_DEVICES",
        "ROCR_VISIBLE_DEVICES",
    )
    bindings = tuple(
        (variable, _parse_visible_devices(variable, environment[variable]))
        for variable in variables
        if variable in environment
    )
    expected = tuple(claim.gpu_devices)
    if not expected:
        if any(bound for _, bound in bindings):
            raise SecurityError(
                "GPU-visible command environment requires a matching GPU resource claim"
            )
        return
    if not bindings:
        raise SecurityError("GPU resource claim requires a bound visible-device environment")
    for variable, bound in bindings:
        if bound != expected:
            raise SecurityError(
                f"GPU resource claim does not match the immutable {variable} environment"
            )
