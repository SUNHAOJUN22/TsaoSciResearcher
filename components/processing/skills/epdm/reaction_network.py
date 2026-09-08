from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from .contracts import ContractValidationError, GateDecision, ReactionFamily
from .state_generator import GeneratedStateDefinition

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MONOMER_STATE = {"E": "N_E", "P": "N_P", "D": "N_D"}
_AGENT_STATE = {"SOLVENT": "N_SOLVENT", "COCATALYST": "N_COCATALYST"}


class A2NumericalExecutionError(NotImplementedError):
    """Raised when Phase A2 structural objects are used as a numerical kernel."""


class MomentRuleKind(StrEnum):
    INITIATE_UNIT_CHAIN = "INITIATE_UNIT_CHAIN"
    PROPAGATE_TERMINAL = "PROPAGATE_TERMINAL"
    TERMINATE_TO_DEAD = "TERMINATE_TO_DEAD"
    TERMINATE_TO_TDB = "TERMINATE_TO_TDB"
    TDB_REINCORPORATION = "TDB_REINCORPORATION"


@dataclass(frozen=True, slots=True)
class ReactionNetworkOptions:
    enable_cocatalyst_activation: bool = True
    enable_hydrogen_activation: bool = False
    transfer_to_monomers: tuple[str, ...] = ("E", "P", "D")
    enable_hydrogen_transfer: bool = True
    transfer_agents: tuple[str, ...] = ("SOLVENT", "COCATALYST")
    enable_spontaneous_deactivation: bool = True
    enable_poison_deactivation: bool = True
    enable_hydrogen_inhibition: bool = True
    enable_tdb: bool = False

    def __post_init__(self) -> None:
        if len(self.transfer_to_monomers) != len(set(self.transfer_to_monomers)):
            raise ContractValidationError("transfer_to_monomers must be unique")
        if set(self.transfer_to_monomers) - set(_MONOMER_STATE):
            raise ContractValidationError("transfer_to_monomers must be a subset of E, P, D")
        if len(self.transfer_agents) != len(set(self.transfer_agents)):
            raise ContractValidationError("transfer_agents must be unique")
        if set(self.transfer_agents) - set(_AGENT_STATE):
            raise ContractValidationError(
                "transfer_agents must be a subset of SOLVENT and COCATALYST"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "enable_cocatalyst_activation": self.enable_cocatalyst_activation,
            "enable_hydrogen_activation": self.enable_hydrogen_activation,
            "transfer_to_monomers": list(self.transfer_to_monomers),
            "enable_hydrogen_transfer": self.enable_hydrogen_transfer,
            "transfer_agents": list(self.transfer_agents),
            "enable_spontaneous_deactivation": self.enable_spontaneous_deactivation,
            "enable_poison_deactivation": self.enable_poison_deactivation,
            "enable_hydrogen_inhibition": self.enable_hydrogen_inhibition,
            "enable_tdb": self.enable_tdb,
        }


@dataclass(frozen=True, slots=True)
class StoichiometricTerm:
    state_id: str
    coefficient: float

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.state_id):
            raise ContractValidationError("stoichiometric state_id is invalid")
        if isinstance(self.coefficient, bool) or not isinstance(self.coefficient, (int, float)):
            raise ContractValidationError("stoichiometric coefficient must be numeric")
        if not math.isfinite(float(self.coefficient)) or self.coefficient == 0:
            raise ContractValidationError("stoichiometric coefficient must be finite and non-zero")

    def as_dict(self) -> dict[str, object]:
        return {"state_id": self.state_id, "coefficient": float(self.coefficient)}


@dataclass(frozen=True, slots=True)
class MomentUpdateRule:
    kind: MomentRuleKind
    site_family_id: str
    source_terminal_id: str | None = None
    target_terminal_id: str | None = None
    incoming_monomer_id: str | None = None

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.site_family_id):
            raise ContractValidationError("moment-rule site_family_id is invalid")
        for label, value in (
            ("source_terminal_id", self.source_terminal_id),
            ("target_terminal_id", self.target_terminal_id),
            ("incoming_monomer_id", self.incoming_monomer_id),
        ):
            if value is not None and value not in _MONOMER_STATE:
                raise ContractValidationError(f"{label} must be E, P, or D")

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "site_family_id": self.site_family_id,
            "source_terminal_id": self.source_terminal_id,
            "target_terminal_id": self.target_terminal_id,
            "incoming_monomer_id": self.incoming_monomer_id,
        }


@dataclass(frozen=True, slots=True)
class ReactionChannel:
    reaction_id: str
    family: ReactionFamily
    site_family_id: str
    terminal_id: str | None
    incoming_monomer_id: str | None
    reactant_state_ids: tuple[str, ...]
    modifier_state_ids: tuple[str, ...]
    stoichiometry: tuple[StoichiometricTerm, ...]
    moment_rules: tuple[MomentUpdateRule, ...] = ()
    rate_law_id: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("reaction_id", self.reaction_id),
            ("site_family_id", self.site_family_id),
        ):
            if not _IDENTIFIER.fullmatch(value):
                raise ContractValidationError(f"{label} is invalid")
        if self.terminal_id is not None and self.terminal_id not in _MONOMER_STATE:
            raise ContractValidationError("terminal_id must be E, P, or D")
        if self.incoming_monomer_id is not None and self.incoming_monomer_id not in _MONOMER_STATE:
            raise ContractValidationError("incoming_monomer_id must be E, P, or D")
        for label, values in (
            ("reactant_state_ids", self.reactant_state_ids),
            ("modifier_state_ids", self.modifier_state_ids),
        ):
            if len(values) != len(set(values)):
                raise ContractValidationError(f"{label} must be unique")
            for value in values:
                if not _IDENTIFIER.fullmatch(value):
                    raise ContractValidationError(f"invalid state reference: {value}")
        state_ids = [term.state_id for term in self.stoichiometry]
        if len(state_ids) != len(set(state_ids)):
            raise ContractValidationError("stoichiometry must contain unique state IDs")
        if self.rate_law_id is not None and not _IDENTIFIER.fullmatch(self.rate_law_id):
            raise ContractValidationError("rate_law_id is invalid")

    def as_dict(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "family": self.family.value,
            "site_family_id": self.site_family_id,
            "terminal_id": self.terminal_id,
            "incoming_monomer_id": self.incoming_monomer_id,
            "reactant_state_ids": list(self.reactant_state_ids),
            "modifier_state_ids": list(self.modifier_state_ids),
            "stoichiometry": [term.as_dict() for term in self.stoichiometry],
            "moment_rules": [rule.as_dict() for rule in self.moment_rules],
            "rate_law_id": self.rate_law_id,
        }


@dataclass(frozen=True, slots=True)
class ReactionNetworkAudit:
    decision: GateDecision
    errors: tuple[str, ...]
    holds: tuple[str, ...]
    metrics: Mapping[str, int | float | str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "errors": list(self.errors),
            "holds": list(self.holds),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class ReactionNetworkDefinition:
    network_id: str
    version: str
    model_level: int
    state_definition_id: str
    generated_state_definition_id: str
    generated_state_digest_sha256: str
    site_family_ids: tuple[str, ...]
    terminal_ids: tuple[str, ...]
    options: ReactionNetworkOptions
    channels: tuple[ReactionChannel, ...]
    state_ids: tuple[str, ...]
    stoichiometric_matrix: tuple[tuple[float, ...], ...]
    _channel_index: Mapping[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.network_id):
            raise ContractValidationError("network_id is invalid")
        if not self.version.strip():
            raise ContractValidationError("version must not be empty")
        if self.model_level not in {1, 2, 3}:
            raise ContractValidationError("model_level must be 1, 2, or 3")
        if not _IDENTIFIER.fullmatch(self.state_definition_id):
            raise ContractValidationError("state_definition_id is invalid")
        if not _IDENTIFIER.fullmatch(self.generated_state_definition_id):
            raise ContractValidationError("generated_state_definition_id is invalid")
        if len(self.generated_state_digest_sha256) != 64:
            raise ContractValidationError("generated_state_digest_sha256 is invalid")
        channel_index = {channel.reaction_id: index for index, channel in enumerate(self.channels)}
        if len(channel_index) != len(self.channels):
            raise ContractValidationError("reaction IDs must be unique")
        if len(self.state_ids) != len(set(self.state_ids)):
            raise ContractValidationError("state_ids must be unique")
        if len(self.stoichiometric_matrix) != len(self.state_ids):
            raise ContractValidationError("stoichiometric matrix row count mismatch")
        if any(len(row) != len(self.channels) for row in self.stoichiometric_matrix):
            raise ContractValidationError("stoichiometric matrix column count mismatch")
        object.__setattr__(self, "_channel_index", MappingProxyType(channel_index))

    @property
    def matrix_shape(self) -> tuple[int, int]:
        return (len(self.state_ids), len(self.channels))

    @property
    def family_counts(self) -> Mapping[str, int]:
        counts = Counter(channel.family.value for channel in self.channels)
        return MappingProxyType(dict(sorted(counts.items())))

    @property
    def digest_sha256(self) -> str:
        payload = self.as_dict(include_digest=False)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def channel(self, reaction_id: str) -> ReactionChannel:
        try:
            return self.channels[self._channel_index[reaction_id]]
        except KeyError as exc:
            raise KeyError(f"unknown reaction ID: {reaction_id}") from exc

    def as_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "TSAO-EPDM-V2-REACTION-NETWORK-1",
            "network_id": self.network_id,
            "version": self.version,
            "model_level": self.model_level,
            "state_definition_id": self.state_definition_id,
            "generated_state_definition_id": self.generated_state_definition_id,
            "generated_state_digest_sha256": self.generated_state_digest_sha256,
            "site_family_ids": list(self.site_family_ids),
            "terminal_ids": list(self.terminal_ids),
            "options": self.options.as_dict(),
            "channels": [channel.as_dict() for channel in self.channels],
            "state_ids": list(self.state_ids),
            "stoichiometric_matrix": [list(row) for row in self.stoichiometric_matrix],
            "matrix_shape": list(self.matrix_shape),
            "family_counts": dict(self.family_counts),
            "numerical_execution": "NOT_IMPLEMENTED_PHASE_A2",
        }
        if include_digest:
            payload["digest_sha256"] = self.digest_sha256
        return payload


def _combine_terms(pairs: Sequence[tuple[str, float]]) -> tuple[StoichiometricTerm, ...]:
    coefficients: Counter[str] = Counter()
    for state_id, coefficient in pairs:
        coefficients[state_id] += coefficient
    return tuple(
        StoichiometricTerm(state_id, float(coefficient))
        for state_id, coefficient in sorted(coefficients.items())
        if coefficient != 0
    )


def _state_id(
    state_definition: GeneratedStateDefinition,
    base: str,
    site: str | None = None,
    terminal: str | None = None,
) -> str:
    parts = [base]
    if site is not None:
        parts.append(site)
    if terminal is not None:
        parts.append(terminal)
    state_id = ":".join(parts)
    state_definition.index_of(state_id)
    return state_id


def _make_channel(
    *,
    reaction_id: str,
    family: ReactionFamily,
    site: str,
    terminal: str | None,
    incoming: str | None,
    reactants: Sequence[str],
    modifiers: Sequence[str],
    stoichiometry: Sequence[tuple[str, float]],
    moment_rules: Sequence[MomentUpdateRule] = (),
) -> ReactionChannel:
    return ReactionChannel(
        reaction_id=reaction_id,
        family=family,
        site_family_id=site,
        terminal_id=terminal,
        incoming_monomer_id=incoming,
        reactant_state_ids=tuple(reactants),
        modifier_state_ids=tuple(modifiers),
        stoichiometry=_combine_terms(stoichiometry),
        moment_rules=tuple(moment_rules),
    )


def build_reaction_network(
    state_definition: GeneratedStateDefinition,
    *,
    network_id: str = "EPDM-V2-TERMINAL-NETWORK-1",
    options: ReactionNetworkOptions | None = None,
) -> ReactionNetworkDefinition:
    if state_definition.model_level < 2:
        raise ContractValidationError("terminal reaction network requires model_level >= 2")
    config = options or ReactionNetworkOptions()
    if config.enable_tdb and state_definition.model_level < 3:
        raise ContractValidationError("TDB pathways require model_level 3")

    channels: list[ReactionChannel] = []
    terminals = state_definition.terminal_ids
    sites = state_definition.site_family_ids

    for site in sites:
        potential = _state_id(state_definition, "N_SITE_POTENTIAL", site)
        vacant = _state_id(state_definition, "N_SITE_VACANT", site)
        inhibited = _state_id(state_definition, "N_SITE_INHIBITED_H2", site)
        poisoned = _state_id(state_definition, "N_SITE_POISONED", site)
        dead_site = _state_id(state_definition, "N_SITE_DEAD", site)
        mu0 = _state_id(state_definition, "MU0", site)

        channels.append(
            _make_channel(
                reaction_id=f"ACT_SPON:{site}",
                family=ReactionFamily.ACT_SPON,
                site=site,
                terminal=None,
                incoming=None,
                reactants=(potential,),
                modifiers=(),
                stoichiometry=((potential, -1), (vacant, 1)),
            )
        )
        if config.enable_cocatalyst_activation:
            cocatalyst = _state_id(state_definition, "N_COCATALYST")
            channels.append(
                _make_channel(
                    reaction_id=f"ACT_COCAT:{site}",
                    family=ReactionFamily.ACT_COCAT,
                    site=site,
                    terminal=None,
                    incoming=None,
                    reactants=(potential,),
                    modifiers=(cocatalyst,),
                    stoichiometry=((potential, -1), (vacant, 1)),
                )
            )
        if config.enable_hydrogen_activation:
            hydrogen = _state_id(state_definition, "N_H2")
            channels.append(
                _make_channel(
                    reaction_id=f"ACT_H2:{site}",
                    family=ReactionFamily.ACT_H2,
                    site=site,
                    terminal=None,
                    incoming=None,
                    reactants=(potential,),
                    modifiers=(hydrogen,),
                    stoichiometry=((potential, -1), (vacant, 1)),
                )
            )

        for incoming in terminals:
            monomer = _state_id(state_definition, _MONOMER_STATE[incoming])
            lambda0_incoming = _state_id(state_definition, "LAMBDA0", site, incoming)
            channels.append(
                _make_channel(
                    reaction_id=f"CHAIN_INI:{site}:{incoming}",
                    family=ReactionFamily.CHAIN_INI,
                    site=site,
                    terminal=None,
                    incoming=incoming,
                    reactants=(vacant, monomer),
                    modifiers=(),
                    stoichiometry=((vacant, -1), (monomer, -1), (lambda0_incoming, 1)),
                    moment_rules=(
                        MomentUpdateRule(
                            MomentRuleKind.INITIATE_UNIT_CHAIN,
                            site,
                            target_terminal_id=incoming,
                            incoming_monomer_id=incoming,
                        ),
                    ),
                )
            )

        for terminal in terminals:
            lambda0_terminal = _state_id(state_definition, "LAMBDA0", site, terminal)
            for incoming in terminals:
                monomer = _state_id(state_definition, _MONOMER_STATE[incoming])
                lambda0_incoming = _state_id(state_definition, "LAMBDA0", site, incoming)
                channels.append(
                    _make_channel(
                        reaction_id=f"PROPAGATION:{site}:{terminal}:{incoming}",
                        family=ReactionFamily.PROPAGATION,
                        site=site,
                        terminal=terminal,
                        incoming=incoming,
                        reactants=(lambda0_terminal, monomer),
                        modifiers=(),
                        stoichiometry=(
                            (monomer, -1),
                            (lambda0_terminal, -1),
                            (lambda0_incoming, 1),
                        ),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.PROPAGATE_TERMINAL,
                                site,
                                source_terminal_id=terminal,
                                target_terminal_id=incoming,
                                incoming_monomer_id=incoming,
                            ),
                        ),
                    )
                )

            for transfer_monomer in config.transfer_to_monomers:
                modifier = _state_id(state_definition, _MONOMER_STATE[transfer_monomer])
                channels.append(
                    _make_channel(
                        reaction_id=f"CHAT_MON:{site}:{terminal}:{transfer_monomer}",
                        family=ReactionFamily.CHAT_MON,
                        site=site,
                        terminal=terminal,
                        incoming=transfer_monomer,
                        reactants=(lambda0_terminal,),
                        modifiers=(modifier,),
                        stoichiometry=((lambda0_terminal, -1), (vacant, 1), (mu0, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_DEAD,
                                site,
                                source_terminal_id=terminal,
                                incoming_monomer_id=transfer_monomer,
                            ),
                        ),
                    )
                )

            if config.enable_hydrogen_transfer:
                hydrogen = _state_id(state_definition, "N_H2")
                channels.append(
                    _make_channel(
                        reaction_id=f"CHAT_H2:{site}:{terminal}",
                        family=ReactionFamily.CHAT_H2,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal,),
                        modifiers=(hydrogen,),
                        stoichiometry=((lambda0_terminal, -1), (vacant, 1), (mu0, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_DEAD,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )

            for agent in config.transfer_agents:
                modifier = _state_id(state_definition, _AGENT_STATE[agent])
                channels.append(
                    _make_channel(
                        reaction_id=f"CHAT_AGENT:{site}:{terminal}:{agent}",
                        family=ReactionFamily.CHAT_AGENT,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal,),
                        modifiers=(modifier,),
                        stoichiometry=((lambda0_terminal, -1), (vacant, 1), (mu0, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_DEAD,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )

            if config.enable_spontaneous_deactivation:
                channels.append(
                    _make_channel(
                        reaction_id=f"DEACT_SPON:{site}:{terminal}",
                        family=ReactionFamily.DEACT_SPON,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal,),
                        modifiers=(),
                        stoichiometry=((lambda0_terminal, -1), (dead_site, 1), (mu0, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_DEAD,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )

            if config.enable_poison_deactivation:
                poison = _state_id(state_definition, "N_POISON")
                channels.append(
                    _make_channel(
                        reaction_id=f"DEACT_POISON:LIVE:{site}:{terminal}",
                        family=ReactionFamily.DEACT_POISON,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal,),
                        modifiers=(poison,),
                        stoichiometry=((lambda0_terminal, -1), (poisoned, 1), (mu0, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_DEAD,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )

            if config.enable_tdb:
                tdb_count = _state_id(state_definition, "N_TDB_DEAD", site)
                branch_count = _state_id(state_definition, "BRANCH_EVENT_AMOUNT", site)
                channels.append(
                    _make_channel(
                        reaction_id=f"TDB_GENERATION:{site}:{terminal}",
                        family=ReactionFamily.TDB_GENERATION,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal,),
                        modifiers=(),
                        stoichiometry=((lambda0_terminal, -1), (vacant, 1), (tdb_count, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TERMINATE_TO_TDB,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )
                channels.append(
                    _make_channel(
                        reaction_id=f"TDB_POLY:{site}:{terminal}",
                        family=ReactionFamily.TDB_POLY,
                        site=site,
                        terminal=terminal,
                        incoming=None,
                        reactants=(lambda0_terminal, tdb_count),
                        modifiers=(),
                        stoichiometry=((tdb_count, -1), (branch_count, 1)),
                        moment_rules=(
                            MomentUpdateRule(
                                MomentRuleKind.TDB_REINCORPORATION,
                                site,
                                source_terminal_id=terminal,
                            ),
                        ),
                    )
                )

        if config.enable_poison_deactivation:
            poison = _state_id(state_definition, "N_POISON")
            channels.append(
                _make_channel(
                    reaction_id=f"DEACT_POISON:VACANT:{site}",
                    family=ReactionFamily.DEACT_POISON,
                    site=site,
                    terminal=None,
                    incoming=None,
                    reactants=(vacant,),
                    modifiers=(poison,),
                    stoichiometry=((vacant, -1), (poisoned, 1)),
                )
            )

        if config.enable_hydrogen_inhibition:
            hydrogen = _state_id(state_definition, "N_H2")
            channels.extend(
                (
                    _make_channel(
                        reaction_id=f"INH_H2_FORWARD:{site}",
                        family=ReactionFamily.INH_H2_FORWARD,
                        site=site,
                        terminal=None,
                        incoming=None,
                        reactants=(vacant,),
                        modifiers=(hydrogen,),
                        stoichiometry=((vacant, -1), (inhibited, 1)),
                    ),
                    _make_channel(
                        reaction_id=f"INH_H2_REVERSE:{site}",
                        family=ReactionFamily.INH_H2_REVERSE,
                        site=site,
                        terminal=None,
                        incoming=None,
                        reactants=(inhibited,),
                        modifiers=(),
                        stoichiometry=((inhibited, -1), (vacant, 1)),
                    ),
                )
            )

    state_ids = state_definition.state_ids
    state_index = {state_id: index for index, state_id in enumerate(state_ids)}
    matrix = [[0.0 for _ in channels] for _ in state_ids]
    for column, channel in enumerate(channels):
        for term in channel.stoichiometry:
            try:
                row = state_index[term.state_id]
            except KeyError as exc:
                raise ContractValidationError(
                    f"reaction {channel.reaction_id} references unknown state {term.state_id}"
                ) from exc
            matrix[row][column] = float(term.coefficient)

    return ReactionNetworkDefinition(
        network_id=network_id,
        version="2.2.0",
        model_level=state_definition.model_level,
        state_definition_id=state_definition.source_state_definition_id,
        generated_state_definition_id=state_definition.generated_state_definition_id,
        generated_state_digest_sha256=state_definition.digest_sha256_without_self,
        site_family_ids=sites,
        terminal_ids=terminals,
        options=config,
        channels=tuple(channels),
        state_ids=state_ids,
        stoichiometric_matrix=tuple(tuple(row) for row in matrix),
    )


def audit_reaction_network(
    network: ReactionNetworkDefinition,
    state_definition: GeneratedStateDefinition,
) -> ReactionNetworkAudit:
    errors: list[str] = []
    holds: list[str] = []
    if network.state_definition_id != state_definition.source_state_definition_id:
        errors.append("network state_definition_id does not match source state definition")
    if network.generated_state_definition_id != state_definition.generated_state_definition_id:
        errors.append(
            "network generated_state_definition_id does not match generated state definition"
        )
    if network.generated_state_digest_sha256 != state_definition.digest_sha256_without_self:
        errors.append("network generated-state digest does not match state definition")
    if network.state_ids != state_definition.state_ids:
        errors.append("network state ordering does not match generated state definition")

    known_states = set(state_definition.state_ids)
    for channel in network.channels:
        references = set(channel.reactant_state_ids) | set(channel.modifier_state_ids)
        references.update(term.state_id for term in channel.stoichiometry)
        missing = sorted(references - known_states)
        if missing:
            errors.append(f"reaction {channel.reaction_id} references unknown states: {missing}")

    propagation = {
        (channel.site_family_id, channel.terminal_id, channel.incoming_monomer_id)
        for channel in network.channels
        if channel.family == ReactionFamily.PROPAGATION
    }
    expected_propagation = {
        (site, terminal, incoming)
        for site in network.site_family_ids
        for terminal in network.terminal_ids
        for incoming in network.terminal_ids
    }
    if propagation != expected_propagation:
        missing = sorted(expected_propagation - propagation)
        extra = sorted(propagation - expected_propagation)
        errors.append(f"terminal propagation matrix mismatch; missing={missing}, extra={extra}")

    families = {channel.family for channel in network.channels}
    for required in (ReactionFamily.ACT_SPON, ReactionFamily.CHAIN_INI):
        if required not in families:
            errors.append(f"required reaction family is missing: {required.value}")
    if network.options.enable_hydrogen_transfer and ReactionFamily.CHAT_H2 not in families:
        errors.append("hydrogen chain transfer is enabled but absent")
    if network.options.enable_hydrogen_inhibition and not {
        ReactionFamily.INH_H2_FORWARD,
        ReactionFamily.INH_H2_REVERSE,
    }.issubset(families):
        errors.append("reversible hydrogen inhibition is incomplete")
    if (
        network.options.enable_spontaneous_deactivation
        and ReactionFamily.DEACT_SPON not in families
    ):
        errors.append("spontaneous deactivation is enabled but absent")
    if network.options.enable_poison_deactivation and ReactionFamily.DEACT_POISON not in families:
        errors.append("poison deactivation is enabled but absent")
    if network.options.enable_tdb:
        if not {ReactionFamily.TDB_GENERATION, ReactionFamily.TDB_POLY}.issubset(families):
            errors.append("TDB generation and reincorporation must be declared together")
    elif {ReactionFamily.TDB_GENERATION, ReactionFamily.TDB_POLY} & families:
        errors.append("TDB reactions exist while TDB option is disabled")

    inventory_by_state = {
        variable.state_id: variable.conserved_inventory_id
        for variable in state_definition.variables
        if variable.conserved_inventory_id is not None
    }
    max_site_residual = 0.0
    for channel in network.channels:
        residuals: Counter[str] = Counter()
        for term in channel.stoichiometry:
            inventory_id = inventory_by_state.get(term.state_id)
            if inventory_id is not None:
                residuals[inventory_id] += term.coefficient
        for inventory_id, residual in residuals.items():
            max_site_residual = max(max_site_residual, abs(float(residual)))
            if residual != 0:
                errors.append(
                    f"reaction {channel.reaction_id} violates {inventory_id} by {residual}"
                )

    decision = GateDecision.FAIL if errors else GateDecision.HOLD if holds else GateDecision.PASS
    metrics: dict[str, int | float | str] = {
        "state_count": len(network.state_ids),
        "reaction_count": len(network.channels),
        "propagation_channel_count": len(propagation),
        "expected_propagation_channel_count": len(expected_propagation),
        "max_site_inventory_residual": max_site_residual,
        "matrix_rows": network.matrix_shape[0],
        "matrix_columns": network.matrix_shape[1],
        "numerical_execution": "NOT_IMPLEMENTED_PHASE_A2",
    }
    return ReactionNetworkAudit(
        decision=decision,
        errors=tuple(sorted(set(errors))),
        holds=tuple(sorted(set(holds))),
        metrics=metrics,
    )


def reaction_network_rhs(*_: object, **__: object) -> None:
    raise A2NumericalExecutionError(
        "Phase A2 defines reaction topology and state structure only; "
        "rate evaluation and integration begin in a later qualified phase"
    )
