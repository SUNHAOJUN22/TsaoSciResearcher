from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")

# V2 formal contracts store physical values in declared SI units. This deliberately
# small allowlist is extended only through a versioned contract change.
SI_UNIT_DIMENSIONS: Mapping[str, str] = MappingProxyType(
    {
        "1": "dimensionless",
        "K": "temperature",
        "Pa": "pressure",
        "s": "time",
        "mol": "amount",
        "mol/s": "amount_flow",
        "kg": "mass",
        "kg/s": "mass_flow",
        "m": "length",
        "m^2": "area",
        "m^3": "volume",
        "m^3/s": "volume_flow",
        "J": "energy",
        "W": "power",
        "J/K": "heat_capacity",
        "J/mol": "molar_energy",
        "kg/mol": "molar_mass",
        "kg/m^3": "density",
        "mol/m^3": "molar_concentration",
        "mol/kg": "molality",
        "1/s": "first_order_rate",
        "m^3/(mol*s)": "second_order_rate",
        "Pa^-1*s^-1": "pressure_rate",
    }
)


class ContractValidationError(ValueError):
    """Raised when a stable V2 contract violates a frozen invariant."""


class CatalystFamily(StrEnum):
    VANADIUM_ZN = "VANADIUM_ZN"
    METALLOCENE = "METALLOCENE"
    OTHER_COORDINATION = "OTHER_COORDINATION"


class SiteModel(StrEnum):
    SINGLE_SITE = "SINGLE_SITE"
    EFFECTIVE_MULTISITE = "EFFECTIVE_MULTISITE"


class EvidenceSourceType(StrEnum):
    LITERATURE = "LITERATURE"
    LAB_FIT = "LAB_FIT"
    PILOT_FIT = "PILOT_FIT"
    PLANT_FIT = "PLANT_FIT"
    ASSUMED = "ASSUMED"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class EvidenceStatus(StrEnum):
    REPORTED = "REPORTED"
    CALCULATED = "CALCULATED"
    QUALIFIED = "QUALIFIED"
    HOLD = "HOLD"
    SUPERSEDED = "SUPERSEDED"
    RETRACTED = "RETRACTED"


class ParameterMaturity(StrEnum):
    ASSUMED = "ASSUMED"
    LITERATURE_PRIOR = "LITERATURE_PRIOR"
    LAB_CALIBRATED = "LAB_CALIBRATED"
    PILOT_CALIBRATED = "PILOT_CALIBRATED"
    PLANT_CALIBRATED = "PLANT_CALIBRATED"
    INDEPENDENTLY_VALIDATED = "INDEPENDENTLY_VALIDATED"
    APPROVED = "APPROVED"


class ModelGeneration(StrEnum):
    V1_LUMPED_REFERENCE = "V1_LUMPED_REFERENCE"
    V2_TERMINAL_MOMENT = "V2_TERMINAL_MOMENT"
    V2_HYBRID_CONSTRAINED = "V2_HYBRID_CONSTRAINED"


class GateDecision(StrEnum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QualificationStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    HOLD = "HOLD"
    CONDITIONAL = "CONDITIONAL"
    PASS = "PASS"
    FAIL = "FAIL"


class ScientificResultStatus(StrEnum):
    CALCULATED_REFERENCE_ONLY = "CALCULATED_REFERENCE_ONLY"
    CALIBRATED = "CALIBRATED"
    VALIDATED = "VALIDATED"
    BLOCKED_BY_THERMODYNAMICS = "BLOCKED_BY_THERMODYNAMICS"
    HOLD_EXTRAPOLATION = "HOLD_EXTRAPOLATION"
    HOLD_IDENTIFIABILITY = "HOLD_IDENTIFIABILITY"
    HOLD_DATA_QUALITY = "HOLD_DATA_QUALITY"
    HOLD = "HOLD"
    FAIL = "FAIL"


class GateReasonCode(StrEnum):
    NONE = "NONE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INVALID_UNIT_BASIS = "INVALID_UNIT_BASIS"
    BLOCKED_BY_THERMODYNAMICS = "BLOCKED_BY_THERMODYNAMICS"
    EXTRAPOLATION = "EXTRAPOLATION"
    NONIDENTIFIABLE = "NONIDENTIFIABLE"
    NONCONVERGED = "NONCONVERGED"
    NUMERICAL_CONSERVATION = "NUMERICAL_CONSERVATION"
    UNSUPPORTED_TOPOLOGY = "UNSUPPORTED_TOPOLOGY"
    DATA_LEAKAGE = "DATA_LEAKAGE"
    APPROVAL_MISSING = "APPROVAL_MISSING"
    OUT_OF_TRAINING_DOMAIN = "OUT_OF_TRAINING_DOMAIN"
    SEMANTIC_REFERENCE_UNRESOLVED = "SEMANTIC_REFERENCE_UNRESOLVED"
    SOLVER_CAPABILITY_MISMATCH = "SOLVER_CAPABILITY_MISMATCH"
    EVENT_LOCALIZATION_UNSUPPORTED = "EVENT_LOCALIZATION_UNSUPPORTED"
    MODEL_SELECTION_INCONCLUSIVE = "MODEL_SELECTION_INCONCLUSIVE"
    ILLEGAL_PARAMETER_BINDING = "ILLEGAL_PARAMETER_BINDING"
    MIXED_STATE_BASIS = "MIXED_STATE_BASIS"


class QualificationLayer(StrEnum):
    SOFTWARE = "SOFTWARE"
    THERMODYNAMIC = "THERMODYNAMIC"
    KINETIC_CALIBRATION = "KINETIC_CALIBRATION"
    INDEPENDENT_VALIDATION = "INDEPENDENT_VALIDATION"
    ENGINEERING_USE = "ENGINEERING_USE"


class StateBasis(StrEnum):
    EXTENSIVE_REACTOR_AMOUNT = "EXTENSIVE_REACTOR_AMOUNT"
    AXIAL_MOLAR_FLOW = "AXIAL_MOLAR_FLOW"
    INTENSIVE_REFERENCE_FIXTURE = "INTENSIVE_REFERENCE_FIXTURE"


class EnergyFormulation(StrEnum):
    TOTAL_ENTHALPY = "TOTAL_ENTHALPY"
    INTERNAL_ENERGY = "INTERNAL_ENERGY"
    ISOTHERMAL = "ISOTHERMAL"
    DIRECT_TEMPERATURE_REFERENCE = "DIRECT_TEMPERATURE_REFERENCE"


class TemperatureParameterForm(StrEnum):
    CONSTANT = "CONSTANT"
    ARRHENIUS_KREF = "ARRHENIUS_KREF"
    ARRHENIUS_PREEXPONENTIAL = "ARRHENIUS_PREEXPONENTIAL"


class DieneIdentity(StrEnum):
    ENB = "ENB"
    DCPD = "DCPD"
    VNB = "VNB"
    OTHER = "OTHER"


class ParameterScope(StrEnum):
    GLOBAL = "GLOBAL"
    SITE = "SITE"
    GRADE_CORRECTION = "GRADE_CORRECTION"
    REACTOR_CORRECTION = "REACTOR_CORRECTION"


class ParameterTransform(StrEnum):
    LINEAR = "LINEAR"
    LOG = "LOG"
    LOGIT = "LOGIT"


class DataRole(StrEnum):
    CALIBRATION = "CALIBRATION"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"
    TUTORIAL = "TUTORIAL"
    DIAGNOSTIC = "DIAGNOSTIC"


class ThermoBackendKind(StrEnum):
    REFERENCE_IDEAL = "REFERENCE_IDEAL"
    TABULATED = "TABULATED"
    EXTERNAL_SIMULATOR = "EXTERNAL_SIMULATOR"


class ReactorType(StrEnum):
    BATCH = "BATCH"
    SEMIBATCH = "SEMIBATCH"
    CSTR = "CSTR"
    CSTR_SERIES = "CSTR_SERIES"
    PFR = "PFR"
    HSBR_CSTR_SERIES = "HSBR_CSTR_SERIES"
    GAS_PHASE_FBR_REFERENCE = "GAS_PHASE_FBR_REFERENCE"
    SOLUTION_CSTR = "SOLUTION_CSTR"


class IntegratorKind(StrEnum):
    RK4_FIXED = "RK4_FIXED"
    RK45_ADAPTIVE = "RK45_ADAPTIVE"
    BDF_OPTIONAL = "BDF_OPTIONAL"
    RADAU_OPTIONAL = "RADAU_OPTIONAL"


class ReactionFamily(StrEnum):
    ACT_SPON = "ACT_SPON"
    ACT_COCAT = "ACT_COCAT"
    ACT_H2 = "ACT_H2"
    CHAIN_INI = "CHAIN_INI"
    PROPAGATION = "PROPAGATION"
    CHAT_MON = "CHAT_MON"
    CHAT_H2 = "CHAT_H2"
    CHAT_AGENT = "CHAT_AGENT"
    DEACT_SPON = "DEACT_SPON"
    DEACT_POISON = "DEACT_POISON"
    INH_H2_FORWARD = "INH_H2_FORWARD"
    INH_H2_REVERSE = "INH_H2_REVERSE"
    TDB_GENERATION = "TDB_GENERATION"
    TDB_POLY = "TDB_POLY"


class StoredQuantityKind(StrEnum):
    K_REF = "K_REF"
    PREEXPONENTIAL_FACTOR = "PREEXPONENTIAL_FACTOR"
    ACTIVATION_ENERGY = "ACTIVATION_ENERGY"
    DIMENSIONLESS = "DIMENSIONLESS"


class ConcentrationBasis(StrEnum):
    MOLARITY = "MOLARITY"
    MOLALITY = "MOLALITY"
    FUGACITY = "FUGACITY"
    PARTIAL_PRESSURE = "PARTIAL_PRESSURE"


class RateOutputBasis(StrEnum):
    PER_REACTOR_VOLUME = "PER_REACTOR_VOLUME"
    PER_CATALYST_MASS = "PER_CATALYST_MASS"
    PER_ACTIVE_SITE = "PER_ACTIVE_SITE"


class ActiveSiteBasis(StrEnum):
    MEASURED = "MEASURED"
    CALIBRATED = "CALIBRATED"
    LITERATURE_PRIOR = "LITERATURE_PRIOR"
    ASSUMED = "ASSUMED"


class SimulatorComponentStatus(StrEnum):
    REAL_COMPONENT = "REAL_COMPONENT"
    SIMULATOR_PLACEHOLDER_COMPONENT = "SIMULATOR_PLACEHOLDER_COMPONENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CalibrationStageKind(StrEnum):
    THERMO_RESIDENCE = "THERMO_RESIDENCE"
    SINGLE_SITE_GLOBAL = "SINGLE_SITE_GLOBAL"
    MOLECULAR_WEIGHT = "MOLECULAR_WEIGHT"
    GPC_DECONVOLUTION = "GPC_DECONVOLUTION"
    MULTISITE_GLOBAL = "MULTISITE_GLOBAL"
    INDEPENDENT_VALIDATION = "INDEPENDENT_VALIDATION"


def _require_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ContractValidationError(f"{label} must be a non-empty stable identifier")


def _require_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractValidationError(f"{label} must be finite numeric")


def _require_ids(values: tuple[str, ...], label: str, *, allow_empty: bool = False) -> None:
    if not allow_empty and not values:
        raise ContractValidationError(f"{label} must not be empty")
    for value in values:
        _require_identifier(value, label)
    if len(values) != len(set(values)):
        raise ContractValidationError(f"{label} must contain unique identifiers")


def validate_si_unit(unit: str, *, expected_dimension: str | None = None) -> None:
    if unit not in SI_UNIT_DIMENSIONS:
        raise ContractValidationError(f"unit is outside the V2 SI allowlist: {unit!r}")
    if expected_dimension is not None and SI_UNIT_DIMENSIONS[unit] != expected_dimension:
        raise ContractValidationError(
            f"unit {unit!r} has dimension {SI_UNIT_DIMENSIONS[unit]!r}, "
            f"expected {expected_dimension!r}"
        )


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_id: str
    source_type: EvidenceSourceType
    source_id: str
    locator: str
    dataset_id: str | None = None
    sha256: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.evidence_id, "evidence_id")
        _require_identifier(self.source_id, "source_id")
        if not self.locator.strip():
            raise ContractValidationError("locator must not be empty")
        if (
            self.source_type
            in {
                EvidenceSourceType.LAB_FIT,
                EvidenceSourceType.PILOT_FIT,
                EvidenceSourceType.PLANT_FIT,
            }
            and not self.dataset_id
        ):
            raise ContractValidationError("fitted evidence requires dataset_id")
        if self.dataset_id is not None:
            _require_identifier(self.dataset_id, "dataset_id")
        if self.sha256 is not None and not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ContractValidationError("sha256 must contain 64 hexadecimal characters")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    reference: EvidenceReference
    status: EvidenceStatus
    applicability_domain_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ids(
            self.applicability_domain_ids,
            "applicability_domain_ids",
            allow_empty=True,
        )


@dataclass(frozen=True, slots=True)
class QuantityValue:
    value: float
    unit: str
    basis: str | None = None
    standard_uncertainty: float | None = None
    uncertainty_unit: str | None = None

    def __post_init__(self) -> None:
        _require_finite(self.value, "value")
        validate_si_unit(self.unit)
        if self.standard_uncertainty is not None:
            _require_finite(self.standard_uncertainty, "standard_uncertainty")
            if self.standard_uncertainty < 0:
                raise ContractValidationError("standard_uncertainty must be non-negative")
            if self.uncertainty_unit is None:
                raise ContractValidationError("uncertainty_unit is required with uncertainty")
            validate_si_unit(self.uncertainty_unit)
        elif self.uncertainty_unit is not None:
            raise ContractValidationError("uncertainty_unit requires standard_uncertainty")


@dataclass(frozen=True, slots=True)
class ValidationCriterion:
    criterion_id: str
    metric: str
    comparison: str
    threshold_low: float | None
    threshold_high: float | None
    unit: str | None
    minimum_sample_count: int | None
    dataset_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.criterion_id, "criterion_id")
        if not self.metric.strip():
            raise ContractValidationError("metric must not be empty")
        if self.comparison not in {"LE", "LT", "GE", "GT", "BETWEEN"}:
            raise ContractValidationError("comparison is not supported")
        for label, value in (
            ("threshold_low", self.threshold_low),
            ("threshold_high", self.threshold_high),
        ):
            if value is not None:
                _require_finite(value, label)
        if self.comparison == "BETWEEN":
            if self.threshold_low is None or self.threshold_high is None:
                raise ContractValidationError("BETWEEN requires both thresholds")
            if self.threshold_low > self.threshold_high:
                raise ContractValidationError("threshold_low exceeds threshold_high")
        elif self.threshold_low is None and self.threshold_high is None:
            raise ContractValidationError("criterion requires a threshold")
        if self.unit is not None:
            validate_si_unit(self.unit)
        if self.minimum_sample_count is not None and self.minimum_sample_count < 1:
            raise ContractValidationError("minimum_sample_count must be positive")
        _require_ids(self.dataset_ids, "dataset_ids")


@dataclass(frozen=True, slots=True)
class CatalystPassport:
    catalyst_id: str
    display_name: str
    family: CatalystFamily
    site_model: SiteModel
    metal: str
    cocatalyst: str | None
    catalyst_lot_id: str | None
    site_capacity: QuantityValue | None
    site_capacity_basis: str | None
    active_site_basis: ActiveSiteBasis
    simulator_component_status: SimulatorComponentStatus
    applicability_domain_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.catalyst_id, "catalyst_id")
        _require_identifier(self.applicability_domain_id, "applicability_domain_id")
        if not self.display_name.strip() or not self.metal.strip():
            raise ContractValidationError("display_name and metal are required")
        if self.site_capacity is not None:
            if self.site_capacity.value <= 0:
                raise ContractValidationError("site_capacity must be positive")
            if self.site_capacity_basis not in {
                "PER_MASS_CATALYST",
                "PER_MASS_METAL",
                "PER_MOLE_METAL",
                "OTHER_DECLARED",
            }:
                raise ContractValidationError("site_capacity_basis is missing or invalid")
        elif self.site_capacity_basis is not None:
            raise ContractValidationError("site_capacity_basis requires site_capacity")
        _require_ids(self.evidence_ids, "evidence_ids")


@dataclass(frozen=True, slots=True)
class DienePassport:
    diene_id: str
    identity: DieneIdentity
    canonical_name: str
    cas_number: str
    registry_version: str
    molecular_weight: QuantityValue
    repeat_segment_id: str
    retained_double_bond_segment_id: str | None
    second_insertion_supported: bool
    terminal_model_supported: bool
    thermo_parameter_source_id: str | None
    kinetic_parameter_source_id: str | None
    applicability_domain_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("diene_id", self.diene_id),
            ("repeat_segment_id", self.repeat_segment_id),
            ("applicability_domain_id", self.applicability_domain_id),
        ):
            _require_identifier(value, label)
        if self.retained_double_bond_segment_id is not None:
            _require_identifier(
                self.retained_double_bond_segment_id,
                "retained_double_bond_segment_id",
            )
        if not self.canonical_name.strip() or not self.cas_number.strip():
            raise ContractValidationError("canonical_name and cas_number are required")
        validate_si_unit(self.molecular_weight.unit, expected_dimension="molar_mass")
        _require_ids(self.evidence_ids, "evidence_ids")


@dataclass(frozen=True, slots=True)
class RateLawDefinition:
    rate_law_id: str
    expression_id: str
    reactant_orders: Mapping[str, float]
    concentration_basis: ConcentrationBasis
    rate_output_basis: RateOutputBasis
    temperature_form: TemperatureParameterForm
    parameter_roles: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_identifier(self.rate_law_id, "rate_law_id")
        _require_identifier(self.expression_id, "expression_id")
        orders = dict(self.reactant_orders)
        if not orders:
            raise ContractValidationError("reactant_orders must not be empty")
        for key, value in orders.items():
            _require_identifier(key, "reactant_order key")
            _require_finite(value, f"reactant order {key}")
            if value < 0:
                raise ContractValidationError("reactant orders must be non-negative")
        roles = dict(self.parameter_roles)
        if not roles or any(not key or not value for key, value in roles.items()):
            raise ContractValidationError("parameter_roles must be non-empty")
        object.__setattr__(self, "reactant_orders", MappingProxyType(orders))
        object.__setattr__(self, "parameter_roles", MappingProxyType(roles))


@dataclass(frozen=True, slots=True)
class KineticParameter:
    parameter_id: str
    reaction_id: str
    rate_law_id: str
    parameter_role: str
    value: float
    unit: str
    stored_quantity_kind: StoredQuantityKind
    reference_temperature_K: float | None
    lower_bound: float
    upper_bound: float
    evidence_id: str
    estimated: bool
    scope: ParameterScope
    maturity: ParameterMaturity
    applicability_domain_id: str
    standard_error: float | None = None
    confidence_interval_95: tuple[float, float] | None = None
    covariance_group_id: str | None = None
    uncertainty_method: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("parameter_id", self.parameter_id),
            ("reaction_id", self.reaction_id),
            ("rate_law_id", self.rate_law_id),
            ("evidence_id", self.evidence_id),
            ("applicability_domain_id", self.applicability_domain_id),
        ):
            _require_identifier(value, label)
        if not self.parameter_role.strip():
            raise ContractValidationError("parameter_role must not be empty")
        for label, value in (
            ("value", self.value),
            ("lower_bound", self.lower_bound),
            ("upper_bound", self.upper_bound),
        ):
            _require_finite(value, label)
        if not self.lower_bound <= self.value <= self.upper_bound:
            raise ContractValidationError("parameter value is outside declared bounds")
        validate_si_unit(self.unit)
        if self.stored_quantity_kind == StoredQuantityKind.ACTIVATION_ENERGY:
            validate_si_unit(self.unit, expected_dimension="molar_energy")
        elif self.stored_quantity_kind == StoredQuantityKind.DIMENSIONLESS:
            validate_si_unit(self.unit, expected_dimension="dimensionless")
        elif self.reference_temperature_K is None or self.reference_temperature_K <= 0:
            raise ContractValidationError(
                "kinetic rate parameters require positive reference_temperature_K"
            )
        if self.reference_temperature_K is not None:
            _require_finite(self.reference_temperature_K, "reference_temperature_K")
        if self.standard_error is not None:
            _require_finite(self.standard_error, "standard_error")
            if self.standard_error < 0:
                raise ContractValidationError("standard_error must be non-negative")
        if self.confidence_interval_95 is not None:
            low, high = self.confidence_interval_95
            _require_finite(low, "confidence interval low")
            _require_finite(high, "confidence interval high")
            if low > high:
                raise ContractValidationError("confidence interval is inverted")


@dataclass(frozen=True, slots=True)
class ApplicabilityDomain:
    applicability_domain_id: str
    temperature_K: tuple[float, float]
    pressure_Pa: tuple[float, float]
    ethylene_fraction: tuple[float, float]
    propylene_fraction: tuple[float, float]
    diene_fraction: tuple[float, float]
    hydrogen_ratio: tuple[float, float]
    reactor_types: tuple[ReactorType, ...]
    catalyst_ids: tuple[str, ...]
    diene_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.applicability_domain_id, "applicability_domain_id")
        for label, bounds in (
            ("temperature_K", self.temperature_K),
            ("pressure_Pa", self.pressure_Pa),
            ("ethylene_fraction", self.ethylene_fraction),
            ("propylene_fraction", self.propylene_fraction),
            ("diene_fraction", self.diene_fraction),
            ("hydrogen_ratio", self.hydrogen_ratio),
        ):
            if len(bounds) != 2:
                raise ContractValidationError(f"{label} must contain two bounds")
            low, high = bounds
            _require_finite(low, f"{label} low")
            _require_finite(high, f"{label} high")
            if low > high:
                raise ContractValidationError(f"{label} bounds are inverted")
        if self.temperature_K[0] <= 0 or self.pressure_Pa[0] < 0:
            raise ContractValidationError("temperature and pressure bounds are invalid")
        for bounds in (self.ethylene_fraction, self.propylene_fraction, self.diene_fraction):
            if bounds[0] < 0 or bounds[1] > 1:
                raise ContractValidationError("composition bounds must lie in [0, 1]")
        if not self.reactor_types:
            raise ContractValidationError("reactor_types must not be empty")
        _require_ids(self.catalyst_ids, "catalyst_ids")
        _require_ids(self.diene_ids, "diene_ids")


@dataclass(frozen=True, slots=True)
class ThermoPassport:
    thermo_passport_id: str
    method_id: str
    method_family: str
    parameter_set_id: str
    fitted_components: tuple[str, ...]
    temperature_range_K: tuple[float, float]
    pressure_range_Pa: tuple[float, float]
    evidence_ids: tuple[str, ...]
    validation_dataset_ids: tuple[str, ...]
    backend_type: ThermoBackendKind
    simulator_version: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("thermo_passport_id", self.thermo_passport_id),
            ("method_id", self.method_id),
            ("parameter_set_id", self.parameter_set_id),
        ):
            _require_identifier(value, label)
        if not self.method_family.strip() or not self.fitted_components:
            raise ContractValidationError("method_family and fitted_components are required")
        if (
            self.temperature_range_K[0] <= 0
            or self.temperature_range_K[0] > self.temperature_range_K[1]
        ):
            raise ContractValidationError("temperature_range_K is invalid")
        if self.pressure_range_Pa[0] < 0 or self.pressure_range_Pa[0] > self.pressure_range_Pa[1]:
            raise ContractValidationError("pressure_range_Pa is invalid")
        _require_ids(self.evidence_ids, "evidence_ids")
        _require_ids(self.validation_dataset_ids, "validation_dataset_ids", allow_empty=True)
        if self.backend_type == ThermoBackendKind.EXTERNAL_SIMULATOR and not self.simulator_version:
            raise ContractValidationError("external simulator backend requires simulator_version")


@dataclass(frozen=True, slots=True)
class OperatingCondition:
    variable: str
    quantity: QuantityValue
    statistic: str

    def __post_init__(self) -> None:
        _require_identifier(self.variable, "variable")
        if self.statistic not in {"SETPOINT", "TIME_AVERAGE", "INITIAL", "FINAL", "PROFILE"}:
            raise ContractValidationError("unsupported operating-condition statistic")


@dataclass(frozen=True, slots=True)
class CalibrationTarget:
    target_id: str
    observation_id: str
    experiment_id: str
    experiment_group_id: str
    dataset_id: str
    reactor_id: str
    grade_id: str
    variable: str
    measured: QuantityValue
    uncertainty_model_id: str
    explicit_weight: float | None
    evidence_id: str
    use: DataRole

    def __post_init__(self) -> None:
        for label, value in (
            ("target_id", self.target_id),
            ("observation_id", self.observation_id),
            ("experiment_id", self.experiment_id),
            ("experiment_group_id", self.experiment_group_id),
            ("dataset_id", self.dataset_id),
            ("reactor_id", self.reactor_id),
            ("grade_id", self.grade_id),
            ("variable", self.variable),
            ("uncertainty_model_id", self.uncertainty_model_id),
            ("evidence_id", self.evidence_id),
        ):
            _require_identifier(value, label)
        if self.explicit_weight is not None:
            _require_finite(self.explicit_weight, "explicit_weight")
            if self.explicit_weight <= 0:
                raise ContractValidationError("explicit_weight must be positive")


@dataclass(frozen=True, slots=True)
class KineticDataset:
    dataset_id: str
    description: str
    catalyst_id: str
    diene_id: str
    experiment_ids: tuple[str, ...]
    operating_conditions: tuple[OperatingCondition, ...]
    targets: tuple[CalibrationTarget, ...]
    preprocessing_record_id: str
    split_manifest_id: str
    evidence_ids: tuple[str, ...]
    role: DataRole

    def __post_init__(self) -> None:
        for label, value in (
            ("dataset_id", self.dataset_id),
            ("catalyst_id", self.catalyst_id),
            ("diene_id", self.diene_id),
            ("preprocessing_record_id", self.preprocessing_record_id),
            ("split_manifest_id", self.split_manifest_id),
        ):
            _require_identifier(value, label)
        if not self.description.strip():
            raise ContractValidationError("description must not be empty")
        _require_ids(self.experiment_ids, "experiment_ids")
        _require_ids(self.evidence_ids, "evidence_ids")


@dataclass(frozen=True, slots=True)
class ParameterBinding:
    parameter_id: str
    scope: ParameterScope
    transform: ParameterTransform
    regularization_strength: float | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.parameter_id, "parameter_id")
        if self.regularization_strength is not None:
            _require_finite(self.regularization_strength, "regularization_strength")
            if self.regularization_strength < 0:
                raise ContractValidationError("regularization_strength must be non-negative")


@dataclass(frozen=True, slots=True)
class CalibrationStage:
    stage_id: str
    stage_kind: CalibrationStageKind
    target_ids: tuple[str, ...]
    varied_parameter_ids: tuple[str, ...]
    fixed_parameter_ids: tuple[str, ...]
    prerequisite_gate_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.stage_id, "stage_id")
        _require_ids(self.target_ids, "target_ids", allow_empty=True)
        _require_ids(self.varied_parameter_ids, "varied_parameter_ids", allow_empty=True)
        _require_ids(self.fixed_parameter_ids, "fixed_parameter_ids", allow_empty=True)
        _require_ids(self.prerequisite_gate_ids, "prerequisite_gate_ids", allow_empty=True)
        overlap = set(self.varied_parameter_ids) & set(self.fixed_parameter_ids)
        if overlap:
            raise ContractValidationError(
                f"parameters cannot be both fixed and varied: {sorted(overlap)}"
            )


@dataclass(frozen=True, slots=True)
class CalibrationPlan:
    calibration_plan_id: str
    stages: tuple[CalibrationStage, ...]
    parameter_bindings: tuple[ParameterBinding, ...]
    allow_grade_specific_parameters: bool = False
    allow_reactor_specific_parameters: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.calibration_plan_id, "calibration_plan_id")
        if not self.stages:
            raise ContractValidationError("stages must not be empty")
        if len({stage.stage_id for stage in self.stages}) != len(self.stages):
            raise ContractValidationError("stage IDs must be unique")
        if len({binding.parameter_id for binding in self.parameter_bindings}) != len(
            self.parameter_bindings
        ):
            raise ContractValidationError("parameter bindings must be unique")


@dataclass(frozen=True, slots=True)
class StateVariableSpec:
    variable_id: str
    description: str
    unit: str
    basis: StateBasis
    level_minimum: int
    site_family_indexed: bool
    terminal_indexed: bool
    conserved_inventory_id: str | None

    def __post_init__(self) -> None:
        _require_identifier(self.variable_id, "variable_id")
        if not self.description.strip():
            raise ContractValidationError("description must not be empty")
        validate_si_unit(self.unit)
        if self.level_minimum not in {1, 2, 3}:
            raise ContractValidationError("level_minimum must be 1, 2, or 3")
        if self.conserved_inventory_id is not None:
            _require_identifier(self.conserved_inventory_id, "conserved_inventory_id")


@dataclass(frozen=True, slots=True)
class StateDefinition:
    state_definition_id: str
    version: str
    basis: StateBasis
    energy_formulation: EnergyFormulation
    variables: tuple[StateVariableSpec, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.state_definition_id, "state_definition_id")
        if not self.version.strip() or not self.variables:
            raise ContractValidationError("version and variables are required")
        if len({variable.variable_id for variable in self.variables}) != len(self.variables):
            raise ContractValidationError("state variable IDs must be unique")
        if any(variable.basis != self.basis for variable in self.variables):
            raise ContractValidationError("mixed state basis is prohibited")


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_id: str
    layer: QualificationLayer
    decision: GateDecision
    reason_code: GateReasonCode
    applicable: bool
    mandatory: bool
    criterion_id: str | None
    measured_metrics: Mapping[str, QuantityValue] = field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()
    message: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.gate_id, "gate_id")
        if self.criterion_id is not None:
            _require_identifier(self.criterion_id, "criterion_id")
        _require_ids(self.evidence_ids, "evidence_ids", allow_empty=True)
        metrics = dict(self.measured_metrics)
        object.__setattr__(self, "measured_metrics", MappingProxyType(metrics))
        if self.applicable and self.decision == GateDecision.NOT_APPLICABLE:
            raise ContractValidationError("applicable gate cannot be NOT_APPLICABLE")
        if not self.applicable and self.decision != GateDecision.NOT_APPLICABLE:
            raise ContractValidationError("non-applicable gate must be NOT_APPLICABLE")
        if self.decision == GateDecision.PASS and self.reason_code != GateReasonCode.NONE:
            raise ContractValidationError("PASS gate must use reason code NONE")
        if (
            self.decision in {GateDecision.HOLD, GateDecision.FAIL}
            and self.reason_code == GateReasonCode.NONE
        ):
            raise ContractValidationError("HOLD/FAIL gate requires a reason code")


@dataclass(frozen=True, slots=True)
class ModelQualification:
    software_status: QualificationStatus
    thermodynamic_status: QualificationStatus
    kinetic_calibration_status: QualificationStatus
    independent_validation_status: QualificationStatus
    engineering_use_status: QualificationStatus
    gate_results: tuple[GateResult, ...]
    model_generation: ModelGeneration = ModelGeneration.V2_TERMINAL_MOMENT
