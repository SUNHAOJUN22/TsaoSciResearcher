"""Domain-specific exceptions for TsaoSciResearcher."""

from __future__ import annotations


class TsaoResearcherError(RuntimeError):
    """Base class for recoverable TsaoSciResearcher runtime errors."""


class ValidationError(TsaoResearcherError, ValueError):
    """Raised when an input or persisted artifact violates a contract."""


class StateTransitionError(ValidationError):
    """Raised when a project state transition is illegal."""


class IntegrityError(ValidationError):
    """Raised when a hash chain, checksum, or provenance record is invalid."""


class LockTimeoutError(TsaoResearcherError, TimeoutError):
    """Raised when a project mutation lock cannot be acquired in time."""
