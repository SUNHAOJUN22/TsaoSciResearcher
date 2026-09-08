from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tsao_computation.scientific_quantity import (
    AcceptanceEnvelope,
    ScientificQuantity,
    acceptance_is_verified,
)


def test_scientific_quantity_rejects_bare_or_dimensionless_payloads() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        ScientificQuantity.from_mapping({"value": 12.0})
    with pytest.raises(ValueError, match="dimension"):
        ScientificQuantity(value=Decimal("12"), unit="MPa", dimension=(), source_id="run-1")


def test_quantity_conversion_requires_dimension_compatibility() -> None:
    value = ScientificQuantity(
        value=Decimal("1.25"),
        unit="MPa",
        dimension=(-1, 1, -2, 0, 0, 0, 0),
        source_id="solver-output:42",
        uncertainty=Decimal("0.05"),
    )
    converted = value.convert(
        factor=Decimal("1000000"),
        unit="Pa",
        dimension=value.dimension,
    )
    assert converted.value == Decimal("1250000.00")
    assert converted.uncertainty == Decimal("50000.00")
    with pytest.raises(ValueError, match="incompatible"):
        value.convert(factor=1, unit="K", dimension=(0, 0, 0, 1, 0, 0, 0))


def test_boolean_self_attestation_is_always_held() -> None:
    assert not acceptance_is_verified({"accepted": True})
    assert not acceptance_is_verified({"accepted": True}, verifier=lambda *_: True)


def test_acceptance_requires_external_signature_verification() -> None:
    payload = {
        "decision": "ACCEPTED",
        "reviewer_id": "reviewer:qualified:7",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_digest": "a" * 64,
        "signature": "external-signature",
        "signature_scheme": "EXTERNAL-DETACHED-V1",
    }
    assert not acceptance_is_verified(payload)
    assert acceptance_is_verified(
        payload,
        verifier=lambda message, signature, reviewer: (
            bool(message)
            and signature == "external-signature"
            and reviewer == "reviewer:qualified:7"
        ),
    )
    envelope = AcceptanceEnvelope.from_mapping(payload)
    assert envelope.decision == "ACCEPTED"
