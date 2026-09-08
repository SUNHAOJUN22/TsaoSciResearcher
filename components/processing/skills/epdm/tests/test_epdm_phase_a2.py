from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from skills.epdm.contracts import ContractValidationError, GateDecision, ReactionFamily
from skills.epdm.reaction_network import (
    A2NumericalExecutionError,
    ReactionNetworkOptions,
    StoichiometricTerm,
    audit_reaction_network,
    build_reaction_network,
    reaction_network_rhs,
)
from skills.epdm.state_generator import generate_state_definition
from skills.epdm.validation_v2 import validate_schema_instance, validate_v2_project

ROOT = Path(__file__).resolve().parents[1]


def _fixture(name: str) -> dict[str, object]:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_level2_state_generation_is_deterministic_and_digest_locked():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    assert state.size == 20
    assert state.state_ids[:7] == (
        "N_E",
        "N_P",
        "N_D",
        "N_H2",
        "N_SOLVENT",
        "N_COCATALYST",
        "N_POISON",
    )
    assert state.index_of("LAMBDA0:SITE-A:E") < state.index_of("LAMBDA1:SITE-A:E")
    assert (
        state.digest_sha256_without_self
        == "718abd62985f3bf7224c41ed633c402f6dc5283b079f5d974dbd07ca22fed810"
    )


def test_multisite_state_generation_expands_without_hard_coded_indices():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A", "SITE-B"),
    )
    assert state.size == 33
    assert state.index_of("N_SITE_VACANT:SITE-A") != state.index_of("N_SITE_VACANT:SITE-B")
    assert state.index_of("LAMBDA0:SITE-B:D") == 22


def test_state_vector_pack_unpack_and_nonnegative_gate():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    vector = state.pack({"N_E": 2.0, "N_P": 1.0}, fill_missing=0.0)
    unpacked = state.unpack(vector)
    assert unpacked["N_E"] == 2.0
    assert unpacked["N_P"] == 1.0
    negative = list(vector)
    negative[state.index_of("N_E")] = -1.0
    with pytest.raises(ContractValidationError, match="non-negative"):
        state.validate_vector(negative)


def test_duplicate_site_or_unknown_terminal_is_rejected():
    with pytest.raises(ContractValidationError, match="unique"):
        generate_state_definition(
            source_state_definition_id="STATE-EXTENSIVE-L2-1",
            model_level=2,
            site_family_ids=("SITE-A", "SITE-A"),
        )
    with pytest.raises(ContractValidationError, match="subset"):
        generate_state_definition(
            source_state_definition_id="STATE-EXTENSIVE-L2-1",
            model_level=2,
            site_family_ids=("SITE-A",),
            terminal_ids=("E", "X"),
        )


def test_default_level2_network_is_deterministic_and_structurally_qualified():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    audit = audit_reaction_network(network, state)
    assert network.matrix_shape == (20, 41)
    assert len(network.channels) == 41
    assert network.family_counts[ReactionFamily.PROPAGATION.value] == 9
    assert (
        network.digest_sha256 == "18daec20b3d2fde28b7fa924b33442a9fcd68fc2bc0637a8db31934b90e7e73a"
    )
    assert audit.decision == GateDecision.PASS
    assert audit.metrics["max_site_inventory_residual"] == 0.0


def test_propagation_matrix_is_exact_site_terminal_incoming_cartesian_product():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A", "SITE-B"),
    )
    network = build_reaction_network(state)
    propagation = [
        channel for channel in network.channels if channel.family == ReactionFamily.PROPAGATION
    ]
    observed = {
        (channel.site_family_id, channel.terminal_id, channel.incoming_monomer_id)
        for channel in propagation
    }
    expected = {
        (site, terminal, incoming)
        for site in ("SITE-A", "SITE-B")
        for terminal in ("E", "P", "D")
        for incoming in ("E", "P", "D")
    }
    assert observed == expected
    assert network.matrix_shape == (33, 82)


def test_mechanism_families_remain_separate():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    families = {channel.family for channel in network.channels}
    assert ReactionFamily.ACT_SPON in families
    assert ReactionFamily.CHAIN_INI in families
    assert ReactionFamily.CHAT_H2 in families
    assert ReactionFamily.INH_H2_FORWARD in families
    assert ReactionFamily.INH_H2_REVERSE in families
    assert ReactionFamily.DEACT_SPON in families
    assert ReactionFamily.DEACT_POISON in families


def test_transfer_channels_cover_enabled_monomers_hydrogen_and_agents():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    assert network.family_counts[ReactionFamily.CHAT_MON.value] == 9
    assert network.family_counts[ReactionFamily.CHAT_H2.value] == 3
    assert network.family_counts[ReactionFamily.CHAT_AGENT.value] == 6


def test_tdb_pathways_require_level3_and_are_paired():
    level2 = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    with pytest.raises(ContractValidationError, match="level 3"):
        build_reaction_network(level2, options=ReactionNetworkOptions(enable_tdb=True))

    level3 = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L3-1",
        model_level=3,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(
        level3,
        options=ReactionNetworkOptions(enable_tdb=True),
    )
    assert level3.size == 27
    assert network.family_counts[ReactionFamily.TDB_GENERATION.value] == 3
    assert network.family_counts[ReactionFamily.TDB_POLY.value] == 3
    assert audit_reaction_network(network, level3).decision == GateDecision.PASS


def test_site_conservation_audit_detects_tampered_channel():
    state = generate_state_definition(
        source_state_definition_id="STATE-EXTENSIVE-L2-1",
        model_level=2,
        site_family_ids=("SITE-A",),
    )
    network = build_reaction_network(state)
    channel = network.channel("ACT_SPON:SITE-A")
    tampered = replace(
        channel,
        stoichiometry=(
            StoichiometricTerm("N_SITE_POTENTIAL:SITE-A", -1.0),
            StoichiometricTerm("N_SITE_VACANT:SITE-A", 2.0),
        ),
    )
    channels = (tampered,) + network.channels[1:]
    broken = replace(network, channels=channels)
    audit = audit_reaction_network(broken, state)
    assert audit.decision == GateDecision.FAIL
    assert any("SITE_TOTAL:SITE-A" in error for error in audit.errors)


def test_a2_state_and_network_fixtures_validate_strict_schemas():
    state = _fixture("v2_phase_a2_reference_state.json")
    network = _fixture("v2_phase_a2_reference_network.json")
    assert not validate_schema_instance(state, "generated-state-definition.schema.json")
    assert not validate_schema_instance(network, "reaction-network-v2.schema.json")
    invalid = copy.deepcopy(network)
    invalid["unknown_field"] = True
    assert validate_schema_instance(invalid, "reaction-network-v2.schema.json")


def test_a1_and_a2_reference_projects_both_remain_valid():
    a1 = validate_v2_project(_fixture("v2_phase_a1_reference_project.json"))
    a2 = validate_v2_project(_fixture("v2_phase_a2_reference_project.json"))
    assert a1.decision == GateDecision.PASS
    assert a1.as_dict()["v2_numerical_execution"] == "NOT_IMPLEMENTED_PHASE_A1"
    assert a2.decision == GateDecision.PASS
    assert a2.as_dict()["v2_numerical_execution"] == "NOT_IMPLEMENTED_PHASE_A2"


def test_project_semantics_detect_digest_and_network_reference_tampering():
    project = _fixture("v2_phase_a2_reference_project.json")
    project["generated_state_definitions"][0]["digest_sha256"] = "0" * 64
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("digest" in issue.message for issue in result.errors)

    project = _fixture("v2_phase_a2_reference_project.json")
    project["cases"][0]["reaction_network_id"] = "MISSING-NETWORK"
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("reaction-network" in issue.message for issue in result.errors)


def test_project_semantics_detect_incomplete_propagation_matrix():
    project = _fixture("v2_phase_a2_reference_project.json")
    network = project["reaction_networks"][0]
    remove_index = next(
        index
        for index, channel in enumerate(network["channels"])
        if channel["family"] == "PROPAGATION"
    )
    network["channels"].pop(remove_index)
    for row in network["stoichiometric_matrix"]:
        row.pop(remove_index)
    network["matrix_shape"][1] -= 1
    result = validate_v2_project(project)
    assert result.decision == GateDecision.FAIL
    assert any("propagation matrix" in issue.message for issue in result.errors)


def test_phase_a2_explicitly_refuses_numerical_rhs_execution():
    with pytest.raises(A2NumericalExecutionError, match="structure only"):
        reaction_network_rhs()


def test_requirement_and_module_catalogs_record_a2_without_claiming_numerics():
    requirements = json.loads((ROOT / "data/requirements_v2.json").read_text(encoding="utf-8"))
    statuses = {
        item["requirement_id"]: item["implementation_status"] for item in requirements["items"]
    }
    for requirement_id in (
        "ARCH-003",
        "RXN-001",
        "RXN-002",
        "RXN-003",
        "RXN-004",
        "RXN-005",
        "RXN-006",
        "STATE-002",
        "STATE-003",
    ):
        assert statuses[requirement_id] == "SOFTWARE_VERIFIED_PHASE_A2"

    modules = json.loads((ROOT / "data/module_contracts_v2.json").read_text(encoding="utf-8"))
    indexed = {item["module"]: item for item in modules["items"]}
    assert indexed["state_generator.py"]["status"] == "DETERMINISTIC_STATE_GENERATOR_IMPLEMENTED"
    assert indexed["reaction_network.py"]["status"] == "STRUCTURAL_NETWORK_IMPLEMENTED"
    assert indexed["reaction_network.py"]["numerical_execution"] is False
