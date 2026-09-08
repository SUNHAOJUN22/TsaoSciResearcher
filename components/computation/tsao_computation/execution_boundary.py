"""Fail-closed external execution, resource budgets, and hash-chained provenance."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import TypeAlias

from tsao_computation.hashing import canonical_json_bytes

SignatureVerifier: TypeAlias = Callable[[bytes, str, str], bool]


class ExecutionBoundaryError(RuntimeError):
    """Base class for fail-closed execution-boundary errors."""


class OutputLimitExceeded(ExecutionBoundaryError):
    """Raised before governed output exceeds its byte budget."""


class ProcessTreeLimitExceeded(ExecutionBoundaryError):
    """Raised when a process tree exceeds its admitted size."""


class ProvenanceIntegrityError(ExecutionBoundaryError):
    """Raised when the append-only provenance chain is invalid."""


def _utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical(payload: Mapping[str, object]) -> bytes:
    return canonical_json_bytes(dict(payload), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class ExecutionBudget:
    wall_time_seconds: int
    max_processes: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    max_artifact_bytes: int
    max_memory_bytes: int

    def __post_init__(self) -> None:
        for field in (
            "wall_time_seconds",
            "max_processes",
            "max_stdout_bytes",
            "max_stderr_bytes",
            "max_artifact_bytes",
            "max_memory_bytes",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be a positive integer")

    def admit_process_tree(self, process_ids: set[int]) -> None:
        if len(process_ids) > self.max_processes:
            raise ProcessTreeLimitExceeded(
                f"process tree contains {len(process_ids)} processes; limit is {self.max_processes}"
            )


@dataclass(frozen=True, slots=True)
class ExternalExecutionCapability:
    capability_id: str
    executor_id: str
    command_digest: str
    not_before: datetime
    expires_at: datetime
    signature_scheme: str
    signature: str

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.executor_id.strip():
            raise ValueError("capability_id and executor_id are required")
        if len(self.command_digest) != 64 or any(
            char not in "0123456789abcdef" for char in self.command_digest.casefold()
        ):
            raise ValueError("command_digest must be SHA-256 hex")
        not_before = _utc(self.not_before, field="not_before")
        expires_at = _utc(self.expires_at, field="expires_at")
        if expires_at <= not_before:
            raise ValueError("expires_at must be after not_before")
        if not self.signature_scheme.strip() or not self.signature.strip():
            raise ValueError("detached signature metadata is required")
        object.__setattr__(self, "not_before", not_before)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "command_digest", self.command_digest.casefold())

    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "capability_id": self.capability_id,
                "executor_id": self.executor_id,
                "command_digest": self.command_digest,
                "not_before": self.not_before.isoformat(),
                "expires_at": self.expires_at.isoformat(),
                "signature_scheme": self.signature_scheme,
            }
        )

    def is_verified(
        self,
        *,
        verifier: SignatureVerifier | None,
        command_digest: str,
        now: datetime | None = None,
    ) -> bool:
        if verifier is None:
            return False
        current = _utc(now or datetime.now(timezone.utc), field="now")
        if current < self.not_before or current > self.expires_at:
            return False
        if command_digest.casefold() != self.command_digest:
            return False
        try:
            return bool(
                verifier(
                    self.canonical_bytes(),
                    self.signature,
                    self.executor_id,
                )
            )
        except Exception:
            return False


@dataclass(frozen=True, slots=True)
class SignedExecutionReceipt:
    request_id: str
    capability_id: str
    executor_id: str
    started_at: datetime
    ended_at: datetime
    exit_code: int
    process_tree_digest: str
    stdout_digest: str
    stderr_digest: str
    artifact_manifest_digest: str
    signature_scheme: str
    signature: str

    def __post_init__(self) -> None:
        started = _utc(self.started_at, field="started_at")
        ended = _utc(self.ended_at, field="ended_at")
        if ended < started:
            raise ValueError("ended_at must not precede started_at")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise TypeError("exit_code must be an integer")
        for field in (
            "process_tree_digest",
            "stdout_digest",
            "stderr_digest",
            "artifact_manifest_digest",
        ):
            value = str(getattr(self, field)).casefold()
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{field} must be SHA-256 hex")
            object.__setattr__(self, field, value)
        for field in (
            "request_id",
            "capability_id",
            "executor_id",
            "signature_scheme",
            "signature",
        ):
            if not str(getattr(self, field)).strip():
                raise ValueError(f"{field} is required")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "ended_at", ended)

    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "request_id": self.request_id,
                "capability_id": self.capability_id,
                "executor_id": self.executor_id,
                "started_at": self.started_at.isoformat(),
                "ended_at": self.ended_at.isoformat(),
                "exit_code": self.exit_code,
                "process_tree_digest": self.process_tree_digest,
                "stdout_digest": self.stdout_digest,
                "stderr_digest": self.stderr_digest,
                "artifact_manifest_digest": self.artifact_manifest_digest,
                "signature_scheme": self.signature_scheme,
            }
        )

    def is_verified(
        self,
        *,
        verifier: SignatureVerifier | None,
        expected_capability_id: str,
    ) -> bool:
        if verifier is None or self.capability_id != expected_capability_id:
            return False
        try:
            return bool(
                verifier(
                    self.canonical_bytes(),
                    self.signature,
                    self.executor_id,
                )
            )
        except Exception:
            return False


class BoundedOutputAccumulator:
    def __init__(self, limit_bytes: int) -> None:
        if isinstance(limit_bytes, bool) or not isinstance(limit_bytes, int):
            raise TypeError("limit_bytes must be an integer")
        if limit_bytes <= 0:
            raise ValueError("limit_bytes must be positive")
        self._limit = limit_bytes
        self._data = bytearray()

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def digest(self) -> str:
        return sha256(self._data).hexdigest()

    def append(self, chunk: bytes) -> None:
        if not isinstance(chunk, bytes):
            raise TypeError("output chunks must be bytes")
        if len(self._data) + len(chunk) > self._limit:
            raise OutputLimitExceeded(f"output would exceed {self._limit} governed bytes")
        self._data.extend(chunk)

    def bytes(self) -> bytes:
        return bytes(self._data)


@dataclass(frozen=True, slots=True)
class ProvenanceEvent:
    sequence: int
    previous_hash: str
    event_type: str
    payload: Mapping[str, object]
    event_hash: str

    def canonical_bytes(self) -> bytes:
        return _canonical(
            {
                "sequence": self.sequence,
                "previous_hash": self.previous_hash,
                "event_type": self.event_type,
                "payload": dict(self.payload),
            }
        )


class ConcurrentProvenanceLedger:
    def __init__(self, path: str | Path, *, lock_timeout: float = 10.0) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.lock_timeout = lock_timeout
        self._thread_lock = threading.Lock()

    def _acquire_file_lock(self) -> int:
        deadline = time.monotonic() + self.lock_timeout
        while True:
            try:
                return os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError("provenance ledger lock timed out") from exc
                time.sleep(0.01)

    def _release_file_lock(self, descriptor: int) -> None:
        os.close(descriptor)
        self.lock_path.unlink(missing_ok=True)

    def read(self) -> tuple[ProvenanceEvent, ...]:
        if not self.path.exists():
            return ()
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            from tsao_science.core.jsonio import strict_loads

            raw = strict_loads(line)
            if not isinstance(raw, dict) or type(raw.get("sequence")) is not int:
                raise ProvenanceIntegrityError("ledger sequence must be an integer")
            events.append(
                ProvenanceEvent(
                    sequence=int(raw["sequence"]),
                    previous_hash=str(raw["previous_hash"]),
                    event_type=str(raw["event_type"]),
                    payload=dict(raw["payload"]),
                    event_hash=str(raw["event_hash"]),
                )
            )
        return tuple(events)

    @staticmethod
    def verify(events: tuple[ProvenanceEvent, ...]) -> None:
        previous = "GENESIS"
        for sequence, event in enumerate(events):
            if event.sequence != sequence:
                raise ProvenanceIntegrityError("non-contiguous event sequence")
            if event.previous_hash != previous:
                raise ProvenanceIntegrityError("previous hash mismatch")
            expected = sha256(event.canonical_bytes()).hexdigest()
            if event.event_hash != expected:
                raise ProvenanceIntegrityError("event hash mismatch")
            previous = event.event_hash

    def append(
        self,
        event_type: str,
        payload: Mapping[str, object],
    ) -> ProvenanceEvent:
        if not event_type.strip():
            raise ValueError("event_type must not be blank")
        with self._thread_lock:
            descriptor = self._acquire_file_lock()
            try:
                events = self.read()
                self.verify(events)
                previous = events[-1].event_hash if events else "GENESIS"
                event = ProvenanceEvent(
                    sequence=len(events),
                    previous_hash=previous,
                    event_type=event_type.strip(),
                    payload=dict(payload),
                    event_hash="",
                )
                event = ProvenanceEvent(
                    sequence=event.sequence,
                    previous_hash=event.previous_hash,
                    event_type=event.event_type,
                    payload=event.payload,
                    event_hash=sha256(event.canonical_bytes()).hexdigest(),
                )
                record = {
                    "sequence": event.sequence,
                    "previous_hash": event.previous_hash,
                    "event_type": event.event_type,
                    "payload": dict(event.payload),
                    "event_hash": event.event_hash,
                }
                with self.path.open("a", encoding="utf-8") as stream:
                    stream.write(
                        json.dumps(
                            record,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
                return event
            finally:
                self._release_file_lock(descriptor)
