"""Public EPDM contracts with strict, fail-closed runtime guards."""

from . import _contracts_core as _core
from ._contracts_core import *  # noqa: F403
from .contract_hardening import harden_contracts

harden_contracts(_core)

del harden_contracts
