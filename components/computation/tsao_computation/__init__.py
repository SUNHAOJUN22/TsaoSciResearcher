from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

__all__ = ["__version__"]

try:
    __version__ = version("tsao-scicomputation")
except PackageNotFoundError:
    __version__ = (
        (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
    )

if __package__:
    from .execution_boundary import (
        BoundedOutputAccumulator as BoundedOutputAccumulator,
    )
    from .execution_boundary import (
        ConcurrentProvenanceLedger as ConcurrentProvenanceLedger,
    )
    from .execution_boundary import (
        ExecutionBudget as ExecutionBudget,
    )
    from .execution_boundary import (
        ExternalExecutionCapability as ExternalExecutionCapability,
    )
    from .execution_boundary import (
        SignedExecutionReceipt as SignedExecutionReceipt,
    )
    from .scientific_quantity import (
        AcceptanceEnvelope as AcceptanceEnvelope,
    )
    from .scientific_quantity import (
        ScientificQuantity as ScientificQuantity,
    )
    from .scientific_quantity import (
        acceptance_is_verified as acceptance_is_verified,
    )
    from .scientific_quantity import (
        require_verified_acceptance as require_verified_acceptance,
    )

    __all__ += [
        "BoundedOutputAccumulator",
        "ConcurrentProvenanceLedger",
        "ExecutionBudget",
        "ExternalExecutionCapability",
        "SignedExecutionReceipt",
        "AcceptanceEnvelope",
        "ScientificQuantity",
        "acceptance_is_verified",
        "require_verified_acceptance",
    ]
