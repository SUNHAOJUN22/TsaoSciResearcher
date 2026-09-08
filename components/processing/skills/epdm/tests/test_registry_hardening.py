from __future__ import annotations

import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from skills.epdm.contracts import (
    ActiveSiteBasis,
    ApplicabilityDomain,
    CatalystFamily,
    CatalystPassport,
    ConcentrationBasis,
    DataRole,
    DieneIdentity,
    DienePassport,
    EvidenceRecord,
    EvidenceReference,
    EvidenceSourceType,
    EvidenceStatus,
    KineticDataset,
    KineticParameter,
    ParameterMaturity,
    ParameterScope,
    QuantityValue,
    RateLawDefinition,
    RateOutputBasis,
    ReactorType,
    SimulatorComponentStatus,
    SiteModel,
    StoredQuantityKind,
    TemperatureParameterForm,
    ThermoBackendKind,
    ThermoPassport,
    ValidationCriterion,
)
from skills.epdm.registry import (
    ContractRegistry,
    CrossRegistryReferenceError,
    DuplicateRegistryIdError,
    IndexedRegistry,
    RegistryIdentifierError,
    RegistryItemTypeError,
    UnresolvedRegistryIdError,
    registry_from_pairs,
)
from tsao.provenance import canonical_identity


def evidence(identifier: str, locator: str = "fixture") -> EvidenceRecord:
    return EvidenceRecord(
        reference=EvidenceReference(
            evidence_id=identifier,
            source_type=EvidenceSourceType.SYNTHETIC_FIXTURE,
            source_id=f"SRC-{identifier}",
            locator=locator,
        ),
        status=EvidenceStatus.QUALIFIED,
    )


def domain(identifier: str = "AD-1") -> ApplicabilityDomain:
    return ApplicabilityDomain(
        applicability_domain_id=identifier,
        temperature_K=(300.0, 360.0),
        pressure_Pa=(100_000.0, 2_000_000.0),
        ethylene_fraction=(0.0, 1.0),
        propylene_fraction=(0.0, 1.0),
        diene_fraction=(0.0, 0.1),
        hydrogen_ratio=(0.0, 0.2),
        reactor_types=(ReactorType.CSTR,),
        catalyst_ids=("CAT-1",),
        diene_ids=("DIENE-1",),
    )


def catalyst() -> CatalystPassport:
    return CatalystPassport(
        catalyst_id="CAT-1",
        display_name="Synthetic catalyst",
        family=CatalystFamily.METALLOCENE,
        site_model=SiteModel.SINGLE_SITE,
        metal="Zr",
        cocatalyst=None,
        catalyst_lot_id=None,
        site_capacity=QuantityValue(0.6, "mol/kg"),
        site_capacity_basis="PER_MASS_CATALYST",
        active_site_basis=ActiveSiteBasis.CALIBRATED,
        simulator_component_status=SimulatorComponentStatus.NOT_APPLICABLE,
        applicability_domain_id="AD-1",
        evidence_ids=("EV-CAT",),
    )


def diene() -> DienePassport:
    return DienePassport(
        diene_id="DIENE-1",
        identity=DieneIdentity.ENB,
        canonical_name="ENB",
        cas_number="16219-75-3",
        registry_version="2.0.0",
        molecular_weight=QuantityValue(0.12019, "kg/mol"),
        repeat_segment_id="SEG-ENB",
        retained_double_bond_segment_id="SEG-ENB-DB",
        second_insertion_supported=False,
        terminal_model_supported=True,
        thermo_parameter_source_id="SRC-THERMO-ENB",
        kinetic_parameter_source_id="SRC-KINETIC-ENB",
        applicability_domain_id="AD-1",
        evidence_ids=("EV-DIENE",),
    )


def rate_law(parameter_role: str = "PROPAGATION_RATE") -> RateLawDefinition:
    return RateLawDefinition(
        rate_law_id="RL-1",
        expression_id="LIVE_SITE_TIMES_ETHYLENE",
        reactant_orders={"LIVE_SITE": 1.0, "ETHYLENE": 1.0},
        concentration_basis=ConcentrationBasis.MOLARITY,
        rate_output_basis=RateOutputBasis.PER_REACTOR_VOLUME,
        temperature_form=TemperatureParameterForm.ARRHENIUS_KREF,
        parameter_roles={"KP-1": parameter_role},
    )


def parameter(parameter_role: str = "PROPAGATION_RATE") -> KineticParameter:
    return KineticParameter(
        parameter_id="KP-1",
        reaction_id="RXN-1",
        rate_law_id="RL-1",
        parameter_role=parameter_role,
        value=0.002,
        unit="m^3/(mol*s)",
        stored_quantity_kind=StoredQuantityKind.K_REF,
        reference_temperature_K=323.15,
        lower_bound=1e-6,
        upper_bound=1.0,
        evidence_id="EV-RATE",
        estimated=True,
        scope=ParameterScope.GLOBAL,
        maturity=ParameterMaturity.LAB_CALIBRATED,
        applicability_domain_id="AD-1",
    )


def dataset() -> KineticDataset:
    return KineticDataset(
        dataset_id="DS-1",
        description="Synthetic registry fixture",
        catalyst_id="CAT-1",
        diene_id="DIENE-1",
        experiment_ids=("EXP-1",),
        operating_conditions=(),
        targets=(),
        preprocessing_record_id="PREP-1",
        split_manifest_id="SPLIT-1",
        evidence_ids=("EV-DATA",),
        role=DataRole.VALIDATION,
    )


def thermo() -> ThermoPassport:
    return ThermoPassport(
        thermo_passport_id="THERMO-1",
        method_id="IDEAL-1",
        method_family="REFERENCE_IDEAL",
        parameter_set_id="TP-1",
        fitted_components=("ETHYLENE", "PROPYLENE", "ENB"),
        temperature_range_K=(300.0, 360.0),
        pressure_range_Pa=(100_000.0, 2_000_000.0),
        evidence_ids=("EV-THERMO",),
        validation_dataset_ids=("DS-1",),
        backend_type=ThermoBackendKind.REFERENCE_IDEAL,
    )


def criterion() -> ValidationCriterion:
    return ValidationCriterion(
        criterion_id="CRIT-1",
        metric="RELATIVE_ERROR",
        comparison="LE",
        threshold_low=None,
        threshold_high=0.08,
        unit="1",
        minimum_sample_count=1,
        dataset_ids=("DS-1",),
    )


def valid_contract_registry() -> ContractRegistry:
    registry = ContractRegistry()
    for identifier in ("EV-CAT", "EV-DIENE", "EV-RATE", "EV-DATA", "EV-THERMO"):
        registry.evidence.register(identifier, evidence(identifier))
    registry.applicability_domains.register("AD-1", domain())
    registry.catalysts.register("CAT-1", catalyst())
    registry.dienes.register("DIENE-1", diene())
    registry.rate_laws.register("RL-1", rate_law())
    registry.kinetic_parameters.register("KP-1", parameter())
    registry.datasets.register("DS-1", dataset())
    registry.thermo_passports.register("THERMO-1", thermo())
    registry.criteria.register("CRIT-1", criterion())
    return registry


def manifest_digest(payload: dict[str, object]) -> str:
    clean = dict(payload)
    clean.pop("content_sha256")
    encoded = json.dumps(
        clean,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_unknown_lookup_fails_closed_and_find_is_explicitly_optional() -> None:
    registry: IndexedRegistry[EvidenceRecord] = IndexedRegistry("evidence")
    for lookup in (registry.get, registry.require):
        with pytest.raises(UnresolvedRegistryIdError, match="unresolved evidence ID"):
            lookup("EV-MISSING")
    assert registry.find("EV-MISSING") is None


@pytest.mark.parametrize("identifier", ["", " whitespace", "bad/id", 42, None])
def test_invalid_registry_identifier_is_contractized(identifier: object) -> None:
    registry: IndexedRegistry[EvidenceRecord] = IndexedRegistry("evidence")
    with pytest.raises(RegistryIdentifierError, match="stable identifier"):
        registry.require(identifier)  # type: ignore[arg-type]


def test_wrong_object_type_is_rejected_for_bound_and_contract_registries() -> None:
    generic: IndexedRegistry[EvidenceRecord] = IndexedRegistry("evidence")
    generic.register("EV-1", evidence("EV-1"))
    with pytest.raises(RegistryItemTypeError, match="EvidenceRecord"):
        generic.register("EV-2", domain())  # type: ignore[arg-type]

    contracts = ContractRegistry()
    with pytest.raises(RegistryItemTypeError, match="EvidenceRecord"):
        contracts.evidence.register("EV-1", domain())  # type: ignore[arg-type]


def test_registry_key_must_match_embedded_contract_identifier() -> None:
    registry = ContractRegistry()
    with pytest.raises(RegistryIdentifierError, match="does not match"):
        registry.evidence.register("EV-WRONG", evidence("EV-1"))


def test_duplicate_registration_is_audited_and_never_overwrites() -> None:
    registry = ContractRegistry().evidence
    first = registry.register("EV-1", evidence("EV-1", "first"))
    with pytest.raises(DuplicateRegistryIdError, match="existing_sha256=.*attempted_sha256"):
        registry.register("EV-1", evidence("EV-1", "second"))
    assert registry.require("EV-1").reference.locator == "first"
    assert registry.version == 1
    assert first.registry_version == 1
    assert not hasattr(registry, "replace")


def test_registration_is_snapshot_isolated_from_original_and_returned_objects() -> None:
    registry = ContractRegistry().evidence
    original = evidence("EV-1", "original")
    registry.register("EV-1", original)

    object.__setattr__(original.reference, "locator", "mutated-original")
    first = registry.require("EV-1")
    assert first.reference.locator == "original"

    object.__setattr__(first.reference, "locator", "mutated-return")
    assert registry.require("EV-1").reference.locator == "original"
    with pytest.raises(TypeError):
        registry.as_mapping()["EV-2"] = evidence("EV-2")  # type: ignore[index]


def test_registration_order_and_serialization_are_deterministic() -> None:
    forward = IndexedRegistry("evidence", EvidenceRecord, "reference.evidence_id")
    reverse = IndexedRegistry("evidence", EvidenceRecord, "reference.evidence_id")
    for identifier in ("EV-A", "EV-Z"):
        forward.register(identifier, evidence(identifier))
    for identifier in ("EV-Z", "EV-A"):
        reverse.register(identifier, evidence(identifier))

    assert forward.identifiers() == ("EV-A", "EV-Z")
    assert list(reverse.as_mapping()) == ["EV-A", "EV-Z"]
    assert forward.to_json() == reverse.to_json()
    manifest = dict(forward.manifest())
    assert manifest["content_sha256"] == manifest_digest(manifest)


def test_registry_from_pairs_preserves_legacy_construction_with_hardening() -> None:
    registry = registry_from_pairs(
        "evidence",
        (("EV-B", evidence("EV-B")), ("EV-A", evidence("EV-A"))),
        item_type=EvidenceRecord,
        identifier_path="reference.evidence_id",
    )
    assert registry.identifiers() == ("EV-A", "EV-B")
    assert registry.version == 2


def test_concurrent_unique_writes_have_no_lost_updates() -> None:
    registry = ContractRegistry().evidence
    identifiers = tuple(f"EV-{index:04d}" for index in range(200))
    with ThreadPoolExecutor(max_workers=16) as executor:
        receipts = list(
            executor.map(
                lambda identifier: registry.register(identifier, evidence(identifier)),
                identifiers,
            )
        )
    assert len(registry) == len(identifiers)
    assert registry.version == len(identifiers)
    assert registry.identifiers() == tuple(sorted(identifiers))
    assert len({receipt.item_sha256 for receipt in receipts}) == len(identifiers)


def test_concurrent_duplicate_writes_have_exactly_one_winner() -> None:
    registry = ContractRegistry().evidence

    def register(index: int) -> tuple[str, str]:
        locator = f"writer-{index}"
        try:
            registry.register("EV-RACE", evidence("EV-RACE", locator))
        except DuplicateRegistryIdError:
            return "duplicate", locator
        return "registered", locator

    with ThreadPoolExecutor(max_workers=32) as executor:
        outcomes = list(executor.map(register, range(64)))
    winners = [locator for outcome, locator in outcomes if outcome == "registered"]
    assert len(winners) == 1
    assert sum(outcome == "duplicate" for outcome, _ in outcomes) == 63
    assert registry.version == 1
    assert registry.require("EV-RACE").reference.locator == winners[0]


def test_concurrent_read_write_snapshots_are_complete_and_hash_consistent() -> None:
    registry = ContractRegistry().evidence
    start = Event()

    def writer(offset: int) -> None:
        start.wait(timeout=5)
        for index in range(20):
            identifier = f"EV-{offset + index:04d}"
            registry.register(identifier, evidence(identifier))

    def reader() -> None:
        start.wait(timeout=5)
        for _ in range(20):
            manifest = dict(registry.manifest())
            entries = manifest["entries"]
            assert isinstance(entries, list)
            identifiers = [entry["identifier"] for entry in entries]
            assert manifest["entry_count"] == len(entries)
            assert identifiers == sorted(set(identifiers))
            assert manifest["content_sha256"] == manifest_digest(manifest)
            mapping = registry.as_mapping()
            assert list(mapping) == sorted(mapping)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(writer, offset) for offset in (0, 20, 40, 60)]
        futures.extend(executor.submit(reader) for _ in range(4))
        start.set()
        for future in futures:
            future.result(timeout=30)
    assert len(registry) == 80


def test_cross_registry_references_validate_for_complete_snapshot() -> None:
    registry = valid_contract_registry()
    registry.validate_references()
    manifest = dict(registry.manifest())
    assert manifest["content_sha256"] == manifest_digest(manifest)
    assert list(manifest["registries"]) == sorted(manifest["registries"])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda registry: registry.catalysts.register("CAT-1", catalyst()),
            r"catalysts\[CAT-1\].applicability_domain_id",
        ),
        (
            lambda registry: registry.applicability_domains.register("AD-1", domain()),
            r"applicability_domains\[AD-1\].catalyst_ids",
        ),
        (
            lambda registry: registry.kinetic_parameters.register("KP-1", parameter()),
            r"kinetic_parameters\[KP-1\].rate_law_id",
        ),
        (
            lambda registry: registry.criteria.register("CRIT-1", criterion()),
            r"criteria\[CRIT-1\].dataset_ids",
        ),
    ],
)
def test_cross_registry_unknown_references_fail_closed(mutate: object, message: str) -> None:
    registry = ContractRegistry()
    mutate(registry)  # type: ignore[operator]
    with pytest.raises(CrossRegistryReferenceError, match=message):
        registry.validate_references()


def test_rate_law_and_parameter_role_contradiction_fails_closed() -> None:
    registry = valid_contract_registry()
    contradictory = ContractRegistry()
    for name in ("evidence", "applicability_domains", "catalysts", "dienes", "datasets"):
        source = getattr(registry, name)
        target = getattr(contradictory, name)
        for identifier, item in source.as_mapping().items():
            target.register(identifier, item)
    contradictory.rate_laws.register("RL-1", rate_law("ACTIVATION_ENERGY"))
    contradictory.kinetic_parameters.register("KP-1", parameter("PROPAGATION_RATE"))
    with pytest.raises(CrossRegistryReferenceError, match="disagrees"):
        contradictory.validate_references()


def test_registry_source_and_tests_are_bound_to_release_provenance() -> None:
    root = Path(__file__).resolve().parents[3]
    records: dict[str, dict[str, str]] = {}
    for relative in ("reports/SOURCE_CORE_MANIFEST.tsv", "reports/SOURCE_CORE_OVERLAY.tsv"):
        with (root / relative).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                records[row["path"]] = row
    for relative in (
        "skills/epdm/registry.py",
        "skills/epdm/tests/test_registry_hardening.py",
    ):
        digest, size = canonical_identity(root / relative)
        assert records[relative]["sha256"] == digest
        assert int(records[relative]["bytes"]) == size
