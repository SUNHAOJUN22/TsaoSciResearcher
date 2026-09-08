from __future__ import annotations

import pytest

from tsao_computation.accelerators import ComputeResourceRequest
from tsao_computation.errors import ContractError


def test_float_resource_field_rejects_boolean() -> None:
    with pytest.raises(ContractError, match="memory_gib must be a positive finite number"):
        ComputeResourceRequest.from_mapping({"memory_gib": True})


def test_enum_resource_field_rejects_non_string() -> None:
    with pytest.raises(ContractError, match="placement must be a string"):
        ComputeResourceRequest.from_mapping({"placement": None})
