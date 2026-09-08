"""Public compatibility surface for TSAO core contracts."""

from .archive import deterministic_zip, sha256_file, validate_zip_archive
from .assurance import AssuranceGraph
from .evidence import EvidenceItem
from .gates import (
    ALLOWED_TRANSITIONS,
    ApprovalStatus,
    GateRecord,
    GateStatus,
    validate_gate_sequence,
)
from .models import ModelRecord
from .project import PROJECT_DIRS, audit_project, bootstrap_project
from .routing import ROUTES, route
from .science import balance_residual, closure_fraction, stoichiometric_rank

__all__ = [
    "ALLOWED_TRANSITIONS",
    "PROJECT_DIRS",
    "ROUTES",
    "ApprovalStatus",
    "AssuranceGraph",
    "EvidenceItem",
    "GateRecord",
    "GateStatus",
    "ModelRecord",
    "audit_project",
    "balance_residual",
    "bootstrap_project",
    "closure_fraction",
    "deterministic_zip",
    "route",
    "sha256_file",
    "stoichiometric_rank",
    "validate_gate_sequence",
    "validate_zip_archive",
]
