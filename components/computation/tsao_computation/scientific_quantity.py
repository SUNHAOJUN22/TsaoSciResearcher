"""Dimensioned scientific quantities and fail-closed human acceptance."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Literal, TypeAlias

QuantityBasis: TypeAlias = Literal["MEASURED", "CALCULATED", "SIMULATED", "REFERENCE", "DERIVED"]
AcceptanceVerifier: TypeAlias = Callable[[bytes, str, str], bool]
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be numeric, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} is not a valid decimal quantity") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ScientificQuantity:
    value: Decimal
    unit: str
    dimension: tuple[int, ...]
    source_id: str
    basis: QuantityBasis = "MEASURED"
    uncertainty: Decimal | None = None

    def __post_init__(self) -> None:
        value = _decimal(self.value, field="value")
        unit = self.unit.strip()
        source_id = self.source_id.strip()
        if not unit:
            raise ValueError("unit must not be blank")
        if not source_id:
            raise ValueError("source_id must not be blank")
        if not self.dimension or any(
            isinstance(power, bool) or not isinstance(power, int) for power in self.dimension
        ):
            raise ValueError("dimension must be a non-empty integer exponent vector")
        if self.basis not in {"MEASURED", "CALCULATED", "SIMULATED", "REFERENCE", "DERIVED"}:
            raise ValueError(f"unsupported quantity basis: {self.basis}")
        uncertainty = None
        if self.uncertainty is not None:
            uncertainty = _decimal(self.uncertainty, field="uncertainty")
            if uncertainty < 0:
                raise ValueError("uncertainty must be non-negative")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "uncertainty", uncertainty)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ScientificQuantity:
        required = {"value", "unit", "dimension", "source_id"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"scientific quantity missing fields: {missing}")
        raw_dimension = payload["dimension"]
        if isinstance(raw_dimension, (str, bytes)) or not isinstance(raw_dimension, Sequence):
            raise TypeError("dimension must be an integer sequence")
        return cls(
            value=_decimal(payload["value"], field="value"),
            unit=str(payload["unit"]),
            dimension=tuple(raw_dimension),
            source_id=str(payload["source_id"]),
            basis=str(payload.get("basis", "MEASURED")),  # type: ignore[arg-type]
            uncertainty=(
                None
                if payload.get("uncertainty") is None
                else _decimal(payload["uncertainty"], field="uncertainty")
            ),
        )

    def convert(
        self,
        *,
        factor: Decimal | int | float | str,
        unit: str,
        dimension: Sequence[int],
        source_id: str | None = None,
    ) -> ScientificQuantity:
        target_dimension = tuple(dimension)
        if target_dimension != self.dimension:
            raise ValueError("cannot convert between incompatible dimensions")
        scale = _decimal(factor, field="factor")
        if scale <= 0:
            raise ValueError("conversion factor must be positive")
        return ScientificQuantity(
            value=self.value * scale,
            unit=unit,
            dimension=target_dimension,
            source_id=source_id or self.source_id,
            basis="DERIVED",
            uncertainty=(None if self.uncertainty is None else self.uncertainty * scale),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "value": str(self.value),
            "unit": self.unit,
            "dimension": list(self.dimension),
            "source_id": self.source_id,
            "basis": self.basis,
            "uncertainty": (None if self.uncertainty is None else str(self.uncertainty)),
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class AcceptanceEnvelope:
    decision: Literal["ACCEPTED", "REJECTED"]
    reviewer_id: str
    reviewed_at: datetime
    evidence_digest: str
    signature: str
    signature_scheme: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> AcceptanceEnvelope:
        if payload.get("accepted") is True and not payload.get("signature"):
            raise ValueError("accepted boolean is not acceptance evidence")
        reviewed_at = datetime.fromisoformat(str(payload["reviewed_at"]))
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        envelope = cls(
            decision=str(payload["decision"]),  # type: ignore[arg-type]
            reviewer_id=str(payload["reviewer_id"]).strip(),
            reviewed_at=reviewed_at.astimezone(timezone.utc),
            evidence_digest=str(payload["evidence_digest"]).casefold(),
            signature=str(payload["signature"]).strip(),
            signature_scheme=str(payload["signature_scheme"]).strip(),
        )
        if envelope.decision not in {"ACCEPTED", "REJECTED"}:
            raise ValueError("decision must be ACCEPTED or REJECTED")
        if not envelope.reviewer_id:
            raise ValueError("reviewer_id must not be blank")
        if _DIGEST.fullmatch(envelope.evidence_digest) is None:
            raise ValueError("evidence_digest must be a SHA-256 hex digest")
        if not envelope.signature or not envelope.signature_scheme:
            raise ValueError("signature and signature_scheme are required")
        return envelope

    def canonical_bytes(self) -> bytes:
        payload = {
            "decision": self.decision,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at.isoformat(),
            "evidence_digest": self.evidence_digest,
            "signature_scheme": self.signature_scheme,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


def acceptance_is_verified(
    payload: Mapping[str, object],
    *,
    verifier: AcceptanceVerifier | None = None,
) -> bool:
    if verifier is None:
        return False
    try:
        envelope = AcceptanceEnvelope.from_mapping(payload)
    except (KeyError, TypeError, ValueError):
        return False
    if envelope.decision != "ACCEPTED":
        return False
    try:
        return bool(
            verifier(
                envelope.canonical_bytes(),
                envelope.signature,
                envelope.reviewer_id,
            )
        )
    except Exception:
        return False


def require_verified_acceptance(
    payload: Mapping[str, object],
    *,
    verifier: AcceptanceVerifier | None = None,
) -> AcceptanceEnvelope:
    if not acceptance_is_verified(payload, verifier=verifier):
        raise PermissionError("cryptographically verified human acceptance is required")
    return AcceptanceEnvelope.from_mapping(payload)
