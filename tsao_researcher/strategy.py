"""First-principles scientific reasoning for computation and simulation strategy advice.

This module selects and explains a *method hierarchy*.  It never runs a solver and
never treats an advisory plan as execution evidence.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from typing import Any

from .errors import ValidationError
from .io import canonical_json

MAX_QUESTION_CHARS = 20_000
MAX_ITEMS = 64
MAX_ITEM_CHARS = 2_000


@dataclass(frozen=True, slots=True)
class MethodTemplate:
    family: str
    methods: tuple[str, ...]
    targets: tuple[str, ...]
    rationale: str
    assumptions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    validation: tuple[str, ...]
    falsification: tuple[str, ...]
    uncertainty: tuple[str, ...]
    escalate_if: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Regime:
    slug: str
    name_zh: str
    name_en: str
    triggers: tuple[str, ...]
    degrees_of_freedom: tuple[str, ...]
    governing_principles: tuple[str, ...]
    conserved_quantities: tuple[str, ...]
    symmetries_and_constraints: tuple[str, ...]
    state_variables: tuple[str, ...]
    thermodynamic_potential: tuple[str, ...]
    ensemble: tuple[str, ...]
    equilibrium_status: str
    length_scales: tuple[str, ...]
    time_scales: tuple[str, ...]
    scale_tests: tuple[str, ...]
    reduction_assumptions: tuple[str, ...]
    methods: tuple[MethodTemplate, ...]


def _method(
    family: str,
    methods: tuple[str, ...],
    targets: tuple[str, ...],
    rationale: str,
    assumptions: tuple[str, ...],
    required_inputs: tuple[str, ...],
    validation: tuple[str, ...],
    falsification: tuple[str, ...],
    uncertainty: tuple[str, ...],
    escalate_if: tuple[str, ...],
) -> MethodTemplate:
    return MethodTemplate(
        family,
        methods,
        targets,
        rationale,
        assumptions,
        required_inputs,
        validation,
        falsification,
        uncertainty,
        escalate_if,
    )


REGIMES: tuple[Regime, ...] = (
    Regime(
        slug="electronic-structure",
        name_zh="电子结构、缺陷与界面量子态",
        name_en="Electronic structure, defects, and interfacial quantum states",
        triggers=(
            "band gap",
            "bandgap",
            "defect state",
            "trap depth",
            "orbital",
            "charge density",
            "work function",
            "fermi",
            "dos",
            "pdos",
            "能带",
            "缺陷态",
            "陷阱深度",
            "轨道",
            "电荷密度",
            "功函数",
            "费米能级",
            "电子结构",
            "excited state",
            "optical excitation",
            "absorption spectrum",
            "photophysics",
            "quasiparticle",
            "electron-hole",
            "激发态",
            "光激发",
            "吸收光谱",
            "光物理",
            "准粒子",
            "电子-空穴",
        ),
        degrees_of_freedom=("electronic density", "spin", "ionic coordinates", "defect occupancy"),
        governing_principles=(
            "Born-Oppenheimer separation where valid",
            "electronic variational principle",
            "Pauli exclusion and electrostatics",
            "crystal or molecular symmetry",
        ),
        conserved_quantities=("total charge", "electron number within the chosen charge state", "energy"),
        symmetries_and_constraints=(
            "space-group or molecular symmetry",
            "spin state",
            "charge neutrality or explicit charge compensation",
        ),
        state_variables=("electron density", "ionic geometry", "occupation", "electrostatic potential"),
        thermodynamic_potential=(
            "ground-state energy",
            "Helmholtz or Gibbs free energy when finite-temperature corrections matter",
        ),
        ensemble=(
            "fixed composition and charge state",
            "grand-canonical treatment only when exchange with reservoirs is explicit",
        ),
        equilibrium_status="equilibrium unless excited-state or transport observables are requested",
        length_scales=("ångström-scale local chemistry", "nanometre supercell for defects and interfaces"),
        time_scales=("electronic relaxation", "ionic relaxation; explicit dynamics only when required"),
        scale_tests=(
            "supercell-size convergence",
            "k-point and basis convergence",
            "localisation length versus cell dimensions",
        ),
        reduction_assumptions=(
            "adiabatic electronic response",
            "chosen exchange-correlation or wavefunction approximation is adequate",
        ),
        methods=(
            _method(
                "symmetry, charge-state, and thermodynamic bookkeeping",
                ("electron counting", "symmetry analysis", "defect formation-energy cycle"),
                ("allowed states", "charge compensation", "qualitative level ordering"),
                "Use exact constraints and thermodynamic cycles before selecting an electronic solver.",
                ("relevant chemical identities and charge states are known",),
                ("composition", "structure", "charge/spin hypotheses", "reference chemical potentials"),
                ("limiting cases", "charge neutrality", "known symmetry degeneracies"),
                ("predicted state violates charge, spin, or symmetry constraints",),
                ("reference-state choice", "chemical-potential range"),
                ("quantitative level positions, forces, or barriers are decision-critical",),
            ),
            _method(
                "ground-state electronic structure",
                (
                    "periodic or cluster DFT",
                    "hybrid-functional DFT when localisation or gap accuracy is critical",
                ),
                ("energies", "geometries", "charge density", "bands", "defect levels"),
                "Resolve electronic degrees of freedom when the observable depends on bonding, charge localisation, or quantum states.",
                (
                    "single-reference ground-state description is adequate",
                    "finite-size treatment is controlled",
                ),
                (
                    "atomic structure",
                    "composition",
                    "boundary model",
                    "charge/spin state",
                    "convergence plan",
                ),
                (
                    "basis and k-point convergence",
                    "supercell convergence",
                    "benchmark against known structures or spectroscopy",
                ),
                (
                    "state ordering changes under reasonable functional or cell choices",
                    "localisation is not stable",
                ),
                ("functional choice", "finite size", "vibrational and temperature corrections"),
                (
                    "strong correlation, excited states, nonadiabatic dynamics, or quasiparticle gaps dominate",
                ),
            ),
            _method(
                "beyond-standard electronic structure",
                (
                    "multireference wavefunction methods",
                    "TDDFT",
                    "GW/BSE",
                    "embedding",
                    "nonadiabatic or excited-state dynamics",
                ),
                (
                    "correlated states",
                    "quasiparticle gaps",
                    "optical excitations",
                    "charge-transfer dynamics",
                ),
                "Escalate only when standard ground-state approximations cannot represent the controlling quantum physics.",
                ("a tractable active space, embedding, or excited-state model can be justified",),
                ("reference states", "active space or screening model", "benchmark observables"),
                ("cross-method benchmark", "spectroscopic comparison", "state-character analysis"),
                ("qualitative conclusions depend on uncontrolled active-space or screening choices",),
                ("truncation", "screening", "state tracking"),
                ("the higher-level calculation remains non-identifiable or unaffordable for the decision",),
            ),
        ),
    ),
    Regime(
        slug="reaction-kinetics",
        name_zh="反应路径、催化机理与动力学",
        name_en="Reaction pathways, catalytic mechanisms, and kinetics",
        triggers=(
            "reaction pathway",
            "activation barrier",
            "transition state",
            "rate constant",
            "selectivity",
            "microkinetic",
            "catalytic mechanism",
            "反应路径",
            "活化能",
            "过渡态",
            "速率常数",
            "选择性",
            "微观动力学",
            "催化机理",
        ),
        degrees_of_freedom=(
            "electronic structure",
            "nuclear coordinates",
            "surface coverage",
            "reaction-network populations",
        ),
        governing_principles=(
            "energy conservation",
            "detailed balance",
            "transition-state theory limits",
            "mass-action kinetics",
        ),
        conserved_quantities=("elements", "charge", "site balance", "total probability"),
        symmetries_and_constraints=(
            "stoichiometry",
            "surface-site conservation",
            "spin and charge conservation where applicable",
        ),
        state_variables=(
            "species populations",
            "surface coverage",
            "temperature",
            "pressure or chemical potential",
        ),
        thermodynamic_potential=(
            "Gibbs free energy for open reactive systems",
            "Helmholtz free energy for fixed-volume models",
        ),
        ensemble=("canonical or grand-canonical depending on reservoirs and coverage",),
        equilibrium_status="non-equilibrium kinetics constrained by equilibrium thermodynamics",
        length_scales=(
            "reaction-coordinate scale",
            "active-site environment",
            "mesoscopic catalyst domain when transport couples",
        ),
        time_scales=("vibrational attempt time", "elementary-reaction time", "residence and transport times"),
        scale_tests=(
            "barrier uncertainty versus kBT",
            "Damköhler number",
            "transport time versus reaction time",
        ),
        reduction_assumptions=(
            "Markovian elementary steps",
            "separation of fast equilibration and rate-limiting processes",
        ),
        methods=(
            _method(
                "reaction-network and thermodynamic consistency",
                ("stoichiometric analysis", "thermodynamic cycle", "degree-of-rate-control screening"),
                ("feasible pathways", "rate-limiting hypotheses", "consistency constraints"),
                "Eliminate impossible mechanisms and identify decision-sensitive steps before expensive calculations.",
                ("candidate intermediates and products are enumerated",),
                ("stoichiometry", "operating conditions", "candidate network", "reference thermochemistry"),
                ("mass/site balance", "detailed-balance consistency", "limiting-rate checks"),
                ("network cannot reproduce observed orders or selectivity under any plausible parameters",),
                ("network completeness", "thermochemical references"),
                ("elementary-step energetics control the remaining uncertainty",),
            ),
            _method(
                "quantum reaction energetics",
                (
                    "DFT or wavefunction reaction-path search",
                    "NEB/string methods",
                    "transition-state optimisation",
                ),
                ("barriers", "reaction energies", "intermediate structures"),
                "Resolve bond-making and bond-breaking when elementary-step energetics determine the macroscopic outcome.",
                (
                    "chosen electronic method describes the relevant states",
                    "reaction coordinate is sufficiently sampled",
                ),
                ("reactant/product structures", "environment model", "charge/spin", "coverage assumptions"),
                ("transition-state connectivity", "method and cell convergence", "benchmark chemistry"),
                ("imaginary modes or path connectivity contradict the assigned elementary step",),
                ("electronic method", "entropy model", "environment and coverage"),
                ("collective solvent, surface, or rare-event effects dominate",),
            ),
            _method(
                "statistical kinetics and reactor-scale propagation",
                (
                    "transition-state theory",
                    "microkinetic modelling",
                    "kinetic Monte Carlo",
                    "reaction-transport coupling",
                ),
                ("rates", "coverage", "selectivity", "turnover", "apparent activation energy"),
                "Propagate elementary uncertainties to observable kinetics and expose which assumptions control the decision.",
                ("elementary steps form an adequate coarse-grained state model",),
                (
                    "free-energy barriers",
                    "prefactors",
                    "operating conditions",
                    "transport parameters if coupled",
                ),
                (
                    "reaction orders",
                    "isotope effects",
                    "temperature/pressure trends",
                    "independent kinetic data",
                ),
                ("no parameter region reproduces multiple independent observables",),
                ("barrier covariance", "prefactors", "network structure", "transport"),
                ("spatial correlations, restructuring, or non-Markovian effects control behaviour",),
            ),
        ),
    ),
    Regime(
        slug="molecular-thermodynamics",
        name_zh="分子热力学、构象与自由能",
        name_en="Molecular thermodynamics, conformations, and free energies",
        triggers=(
            "free energy",
            "solvation",
            "partition coefficient",
            "binding free energy",
            "conformation",
            "phase equilibrium",
            "chemical potential",
            "自由能",
            "溶剂化",
            "分配系数",
            "结合自由能",
            "构象",
            "相平衡",
            "化学势",
        ),
        degrees_of_freedom=("molecular coordinates", "momenta", "composition", "collective variables"),
        governing_principles=(
            "Boltzmann statistics",
            "ergodic sampling assumptions",
            "free-energy minimisation",
            "detailed balance",
        ),
        conserved_quantities=("mass", "charge", "energy in isolated dynamics", "probability"),
        symmetries_and_constraints=("molecular topology", "holonomic constraints", "periodicity where used"),
        state_variables=("temperature", "pressure or volume", "composition", "collective variables"),
        thermodynamic_potential=(
            "Helmholtz free energy",
            "Gibbs free energy",
            "grand potential for open composition",
        ),
        ensemble=("NVE/NVT/NPT", "grand-canonical or semi-grand ensemble when composition exchanges"),
        equilibrium_status="equilibrium unless driven transport or relaxation is the target",
        length_scales=("molecular interactions", "solvation shell", "simulation box and correlation length"),
        time_scales=("vibrations", "conformational relaxation", "diffusion and rare-event times"),
        scale_tests=(
            "correlation length versus box size",
            "integrated autocorrelation time",
            "barrier height versus kBT",
        ),
        reduction_assumptions=(
            "effective interaction model is transferable",
            "sampled collective variables resolve metastability",
        ),
        methods=(
            _method(
                "statistical-thermodynamic model selection",
                ("partition-function reasoning", "equation of state", "lattice or association model"),
                ("chemical potential", "phase tendency", "limiting behaviour"),
                "Use ensembles and thermodynamic identities to determine the minimum state description and required observables.",
                ("relevant species and phases are defined",),
                ("composition", "temperature", "pressure/volume", "interaction hypotheses"),
                ("known limits", "thermodynamic consistency", "phase-rule checks"),
                ("model violates convexity, stability, or limiting behaviour",),
                ("parameter identifiability", "model form"),
                ("molecular structure or fluctuations dominate the unresolved observable",),
            ),
            _method(
                "molecular sampling and free-energy estimation",
                (
                    "classical molecular dynamics",
                    "Monte Carlo",
                    "umbrella sampling",
                    "metadynamics",
                    "alchemical free energy",
                ),
                ("ensemble averages", "free-energy profiles", "diffusion", "structure", "solvation"),
                "Resolve molecular fluctuations when the target is an ensemble property rather than a single minimum-energy structure.",
                ("force field and sampling coordinates are adequate", "equilibration can be demonstrated"),
                ("molecular model", "thermodynamic state", "sampling plan", "collective variables"),
                (
                    "replica agreement",
                    "autocorrelation/effective sample size",
                    "cycle closure",
                    "experimental thermodynamics",
                ),
                ("free-energy estimates depend strongly on starting basin or path",),
                ("force field", "finite size", "sampling", "collective-variable choice"),
                ("bond rearrangement, polarisation, or electronic effects control the result",),
            ),
            _method(
                "quantum-informed or coarse-grained extension",
                (
                    "ab initio molecular dynamics",
                    "QM/MM",
                    "force-field reparameterisation",
                    "coarse-grained simulation",
                ),
                ("reactive solvation", "polarisation", "larger-scale thermodynamics and dynamics"),
                "Escalate upward for electronic rearrangement or downward in resolution for inaccessible length and time scales.",
                ("the bridge variables and calibration targets are explicit",),
                ("reference quantum/experimental data", "mapping", "validation observables"),
                (
                    "cross-resolution consistency",
                    "hold-out state points",
                    "structural and thermodynamic targets",
                ),
                ("coarse-graining or quantum corrections fail outside the calibration envelope",),
                ("mapping", "state dependence", "reference-data uncertainty"),
                ("no single resolution can answer all decision-critical observables",),
            ),
        ),
    ),
    Regime(
        slug="soft-matter-polymer",
        name_zh="软物质、高分子形貌与多尺度结构",
        name_en="Soft matter, polymer morphology, and multiscale structure",
        triggers=(
            "polymer morphology",
            "crystallization",
            "phase separation",
            "lamella",
            "entanglement",
            "coarse grain",
            "mesoscale",
            "高分子形貌",
            "结晶",
            "相分离",
            "片晶",
            "缠结",
            "粗粒化",
            "介观",
        ),
        degrees_of_freedom=(
            "chain conformation",
            "composition field",
            "crystallinity/order parameter",
            "interfaces and topology",
        ),
        governing_principles=(
            "entropy-energy competition",
            "free-energy minimisation",
            "mass conservation",
            "chain connectivity",
        ),
        conserved_quantities=(
            "polymer mass",
            "component composition",
            "topological constraints where relevant",
        ),
        symmetries_and_constraints=(
            "chain connectivity",
            "incompressibility approximation when justified",
            "processing-imposed anisotropy",
        ),
        state_variables=(
            "composition",
            "order parameters",
            "temperature",
            "strain/flow history",
            "molecular-weight distribution",
        ),
        thermodynamic_potential=("coarse-grained Helmholtz or Gibbs free-energy functional",),
        ensemble=(
            "canonical/semi-grand",
            "field-theoretic ensemble",
            "driven non-equilibrium under processing",
        ),
        equilibrium_status="mixed; processing often creates long-lived non-equilibrium structures",
        length_scales=("segment", "chain/lamella", "domain", "specimen and process scale"),
        time_scales=(
            "segmental motion",
            "reptation",
            "crystallisation/phase separation",
            "processing and ageing",
        ),
        scale_tests=(
            "chain size versus domain size",
            "Péclet/Weissenberg/Deborah numbers",
            "nucleation versus process time",
        ),
        reduction_assumptions=(
            "chosen order parameters retain the structure-property mechanism",
            "coarse-grained interactions remain state-relevant",
        ),
        methods=(
            _method(
                "scaling and free-energy functional analysis",
                ("Flory-Huggins-type thermodynamics", "scaling theory", "self-consistent field theory"),
                ("phase tendency", "domain scale", "conformation and segregation"),
                "Identify dominant entropy, interaction, and connectivity terms before selecting a numerical representation.",
                ("a small set of order parameters represents the dominant physics",),
                (
                    "composition",
                    "molecular architecture",
                    "interaction parameters",
                    "temperature/process history",
                ),
                ("phase boundaries", "limiting scaling", "independent structural data"),
                ("predicted morphology is inconsistent with symmetry, composition, or observed scaling",),
                ("interaction parameters", "order-parameter choice", "finite-chain corrections"),
                ("fluctuations, kinetics, or topology determine the observable",),
            ),
            _method(
                "mesoscopic structure evolution",
                (
                    "coarse-grained molecular dynamics",
                    "dissipative particle dynamics",
                    "phase-field/Cahn-Hilliard",
                    "kinetic Monte Carlo",
                ),
                ("domain evolution", "morphology", "interface dynamics", "processing response"),
                "Resolve collective structure and kinetics at the lowest resolution that retains chain, interface, and transport physics.",
                ("mapping and mobility models are calibrated", "finite-size and rate effects are controlled"),
                (
                    "coarse-grained potential or free-energy functional",
                    "initial morphology",
                    "mobility",
                    "processing conditions",
                ),
                (
                    "structure factor",
                    "domain-size kinetics",
                    "morphology statistics",
                    "hold-out processing histories",
                ),
                ("the same parameters cannot reproduce both equilibrium structure and kinetics",),
                ("mapping", "mobility", "finite size", "initial conditions"),
                ("local chemistry or macroscopic stress/transport controls the remaining question",),
            ),
            _method(
                "cross-scale polymer strategy",
                (
                    "quantum-informed interactions",
                    "atomistic calibration",
                    "homogenisation",
                    "process-structure continuum coupling",
                ),
                ("chemistry-to-morphology-to-property linkage",),
                "Bridge scales only through measurable state variables and propagate uncertainty across each reduction step.",
                ("bridge variables are observable and sufficiently informative",),
                ("reference chemistry", "mapping targets", "morphology descriptors", "property model"),
                (
                    "cross-scale closure tests",
                    "independent structure and property data",
                    "sensitivity analysis",
                ),
                (
                    "different parameter sets give indistinguishable intermediate structure but divergent properties",
                ),
                ("cross-scale closure", "parameter transfer", "structural heterogeneity"),
                ("bridge variables are not identifiable or the scale separation fails",),
            ),
        ),
    ),
    Regime(
        slug="continuum-transport",
        name_zh="流动、传热传质与连续介质输运",
        name_en="Flow, heat/mass transfer, and continuum transport",
        triggers=(
            "pressure drop",
            "fluid flow",
            "heat transfer",
            "mass transfer",
            "mixing",
            "temperature field",
            "non-newtonian",
            "cfd",
            "压降",
            "流场",
            "传热",
            "传质",
            "混合",
            "温度场",
            "非牛顿",
            "计算流体力学",
        ),
        degrees_of_freedom=("velocity", "pressure", "temperature", "species concentration", "phase fraction"),
        governing_principles=(
            "mass conservation",
            "momentum balance",
            "energy balance",
            "species conservation",
            "constitutive laws",
        ),
        conserved_quantities=("mass", "momentum", "energy", "species"),
        symmetries_and_constraints=(
            "geometry",
            "boundary conditions",
            "incompressibility or compressibility",
            "constitutive objectivity",
        ),
        state_variables=("density", "velocity", "pressure", "temperature", "composition", "stress"),
        thermodynamic_potential=(
            "local-equilibrium thermodynamic closure when justified",
            "entropy production for irreversible transport",
        ),
        ensemble=("not an equilibrium ensemble; continuum fields describe local averages",),
        equilibrium_status="non-equilibrium",
        length_scales=("mean free path or microstructure", "boundary layer", "device/reactor geometry"),
        time_scales=("diffusion", "advection", "relaxation", "forcing/process time"),
        scale_tests=(
            "Knudsen number",
            "Reynolds number",
            "Péclet number",
            "Deborah/Weissenberg number",
            "Biot number where relevant",
        ),
        reduction_assumptions=(
            "continuum hypothesis",
            "closure relation is valid",
            "unresolved fluctuations are not decision-critical",
        ),
        methods=(
            _method(
                "conservation-law scaling and reduced-order analysis",
                (
                    "control-volume balances",
                    "dimensional analysis",
                    "lubrication/plug-flow/1D models",
                    "network models",
                ),
                ("dominant resistances", "pressure drop", "heat/mass-transfer limits", "regime map"),
                "Start from conservation laws and dimensionless groups; use the cheapest model that can resolve the target observable.",
                ("geometry and constitutive regime permit reduction",),
                ("geometry", "material properties", "boundary/initial conditions", "source terms"),
                ("analytical limits", "global balances", "mesh-independent reference cases"),
                ("neglected gradients or couplings are comparable to retained terms",),
                ("property uncertainty", "closure correlations", "boundary conditions"),
                (
                    "three-dimensional, transient, multiphase, turbulent, or strongly coupled fields control the decision",
                ),
            ),
            _method(
                "continuum field simulation",
                (
                    "finite volume CFD",
                    "finite element transport",
                    "spectral or lattice methods when justified",
                ),
                (
                    "spatial fields",
                    "fluxes",
                    "mixing",
                    "residence time",
                    "thermal or concentration gradients",
                ),
                "Resolve continuum fields when lumped balances cannot represent the controlling gradients and couplings.",
                (
                    "continuum and constitutive assumptions remain valid",
                    "numerical discretisation is controlled",
                ),
                (
                    "geometry",
                    "mesh strategy",
                    "constitutive model",
                    "boundary/initial conditions",
                    "solver tolerances",
                ),
                (
                    "global conservation",
                    "mesh/time-step convergence",
                    "benchmark flow",
                    "independent field or integral data",
                ),
                ("solution violates balances or changes qualitatively with reasonable mesh/model choices",),
                ("mesh", "closure", "boundary conditions", "material properties"),
                ("microstructure, rarefaction, molecular effects, or unresolved multiphysics dominates",),
            ),
            _method(
                "multiphysics and sub-continuum escalation",
                (
                    "conjugate multiphysics",
                    "Eulerian-Lagrangian or population-balance coupling",
                    "mesoscale/particle-informed closure",
                ),
                ("coupled reaction-flow-heat-mass behaviour", "particle or microstructure effects"),
                "Add physics only when sensitivity or validation shows that a missing coupling controls the observable.",
                ("coupling variables and timescales are explicit",),
                ("submodel closures", "coupling interface", "calibration and validation data"),
                ("component-wise benchmarks", "coupled conservation", "cross-regime validation"),
                ("coupled model improves fit only through non-identifiable compensation",),
                ("coupling closure", "scale separation", "parameter covariance"),
                ("no validated closure exists for the relevant regime",),
            ),
        ),
    ),
    Regime(
        slug="solid-mechanics",
        name_zh="固体力学、断裂与多物理场失效",
        name_en="Solid mechanics, fracture, and multiphysics failure",
        triggers=(
            "stress concentration",
            "fracture",
            "crack",
            "fatigue",
            "deformation",
            "modulus",
            "failure",
            "finite element",
            "应力集中",
            "断裂",
            "裂纹",
            "疲劳",
            "变形",
            "模量",
            "失效",
            "有限元",
        ),
        degrees_of_freedom=(
            "displacement",
            "strain",
            "stress",
            "damage or crack phase field",
            "internal variables",
        ),
        governing_principles=(
            "linear/angular momentum balance",
            "energy balance",
            "constitutive thermodynamics",
            "fracture energetics",
        ),
        conserved_quantities=("momentum", "energy subject to dissipation"),
        symmetries_and_constraints=("frame indifference", "material symmetry", "kinematic constraints"),
        state_variables=("strain", "stress", "temperature", "damage", "history variables"),
        thermodynamic_potential=("strain-energy density", "free energy with dissipative internal variables"),
        ensemble=("not an equilibrium ensemble; deterministic or stochastic boundary-value problem",),
        equilibrium_status="quasi-static or dynamic depending on inertia and loading rate",
        length_scales=("microstructural flaw", "process zone", "component geometry"),
        time_scales=("wave propagation", "viscoelastic relaxation", "fatigue cycles", "loading time"),
        scale_tests=(
            "inertial versus loading time",
            "process-zone size versus mesh/component",
            "Deborah number for viscoelasticity",
        ),
        reduction_assumptions=(
            "constitutive law and damage variables capture the mechanism",
            "representative volume exists for homogenisation",
        ),
        methods=(
            _method(
                "mechanics scaling and constitutive selection",
                (
                    "free-body and energy analysis",
                    "beam/shell or homogenised models",
                    "constitutive identifiability study",
                ),
                ("load path", "dominant stress/strain", "failure-mode screening"),
                "Use balances, energy, and material symmetry to identify the minimum kinematics and constitutive complexity.",
                ("dominant deformation mode is known",),
                ("geometry", "loads", "constraints", "material data", "history"),
                ("analytical limits", "energy consistency", "independent material tests"),
                ("predicted mode contradicts observed localisation or rate dependence",),
                ("material parameters", "boundary conditions", "geometry"),
                ("local fields, nonlinear contact, fracture, or coupled physics control the decision",),
            ),
            _method(
                "finite-element field analysis",
                (
                    "linear/nonlinear FEM",
                    "viscoelastic/plastic constitutive simulation",
                    "cohesive-zone or phase-field fracture",
                ),
                ("stress/strain fields", "deformation", "damage initiation and growth"),
                "Resolve spatial fields when geometry, constraints, material nonlinearity, or fracture invalidates reduced models.",
                (
                    "constitutive and fracture parameters are identifiable",
                    "mesh-objectivity treatment is appropriate",
                ),
                ("geometry", "mesh", "loads", "contact", "material law", "failure parameters"),
                ("mesh and time-step convergence", "energy balance", "coupon and component validation"),
                ("failure path or load response changes under admissible constitutive/mesh choices",),
                ("constitutive model", "defect population", "mesh regularisation", "load history"),
                ("microstructure explicitly controls crack nucleation or macroscopic closure fails",),
            ),
            _method(
                "microstructure-informed mechanics",
                (
                    "representative-volume homogenisation",
                    "crystal plasticity",
                    "multiscale fracture or stochastic defect models",
                ),
                ("anisotropy", "heterogeneity", "scale-dependent damage"),
                "Escalate when the macroscopic law cannot reproduce path, anisotropy, or defect-sensitive failure.",
                ("representative microstructure and bridge variables are defined",),
                (
                    "microstructure statistics",
                    "local constitutive laws",
                    "boundary ensemble",
                    "validation hierarchy",
                ),
                (
                    "RVE convergence",
                    "cross-scale energy consistency",
                    "independent microstructure/property data",
                ),
                ("no representative scale exists or predictions are dominated by unobserved defects",),
                ("microstructure sampling", "local laws", "boundary ensemble"),
                (
                    "decision requires direct experimental characterisation rather than further model complexity",
                ),
            ),
        ),
    ),
    Regime(
        slug="charge-transport-dielectric",
        name_zh="电荷输运、介电响应与击穿",
        name_en="Charge transport, dielectric response, and breakdown",
        triggers=(
            "space charge",
            "charge transport",
            "dielectric",
            "breakdown",
            "hopping",
            "conductivity",
            "electric field",
            "空间电荷",
            "电荷输运",
            "介电",
            "击穿",
            "跳跃",
            "电导",
            "电场",
        ),
        degrees_of_freedom=(
            "electronic/trap states",
            "carrier populations",
            "polarisation",
            "electric and thermal fields",
        ),
        governing_principles=(
            "charge conservation",
            "Poisson equation",
            "detailed balance for hopping",
            "electrothermal energy balance",
        ),
        conserved_quantities=(
            "total charge including electrodes/reservoirs",
            "energy in coupled electrothermal models",
        ),
        symmetries_and_constraints=(
            "electrode geometry",
            "electrostatic boundary conditions",
            "charge neutrality or injection law",
        ),
        state_variables=(
            "carrier density",
            "trap occupancy",
            "potential",
            "polarisation",
            "temperature",
            "microstructure descriptors",
        ),
        thermodynamic_potential=(
            "electrochemical potential",
            "free-energy landscape for carriers and polarisation",
        ),
        ensemble=("open carrier reservoirs with driven non-equilibrium transport",),
        equilibrium_status="non-equilibrium under applied field; local equilibrium assumptions require justification",
        length_scales=("electronic localisation", "trap spacing and morphology", "insulation thickness"),
        time_scales=(
            "electronic transition",
            "hopping/trapping",
            "polarisation relaxation",
            "space-charge and thermal evolution",
        ),
        scale_tests=(
            "localisation length versus trap spacing",
            "carrier transit versus trapping time",
            "electrical versus thermal runaway time",
        ),
        reduction_assumptions=(
            "selected trap/transport states form an adequate coarse-grained network",
            "field and temperature coupling is represented",
        ),
        methods=(
            _method(
                "electronic and electrostatic state analysis",
                (
                    "electronic-structure defect/interface analysis",
                    "electrostatic barrier and image-force analysis",
                ),
                ("trap energetics", "injection barriers", "localisation", "dielectric response origins"),
                "Start from states and electrochemical driving forces when microscopic trapping or injection controls the observable.",
                ("representative chemistry and morphology are available",),
                ("local structures/interfaces", "charge states", "electrode model", "dielectric environment"),
                ("spectroscopy", "thermally stimulated measurements", "functional/supercell sensitivity"),
                ("calculated state hierarchy cannot explain temperature/field trends",),
                ("structural ensemble", "electronic method", "interface model"),
                ("mesoscopic carrier statistics and field redistribution dominate",),
            ),
            _method(
                "mesoscopic carrier transport",
                (
                    "master-equation or hopping model",
                    "kinetic Monte Carlo",
                    "multiple-trapping model",
                    "drift-diffusion-Poisson",
                ),
                ("mobility", "space charge", "current", "trap occupancy", "transients"),
                "Propagate microscopic states into observable transport while enforcing charge conservation and field self-consistency.",
                (
                    "transport states and transition rates are sufficient",
                    "injection and recombination laws are specified",
                ),
                (
                    "state distribution",
                    "rate model",
                    "electrode conditions",
                    "geometry",
                    "temperature and field history",
                ),
                (
                    "current-voltage-temperature trends",
                    "transient charge profiles",
                    "limiting laws",
                    "independent mobility data",
                ),
                ("one parameter set cannot reproduce both steady and transient observables",),
                ("state density", "rates", "injection", "morphology", "finite size"),
                ("collective polarisation, morphology evolution, or thermal feedback becomes controlling",),
            ),
            _method(
                "coupled electrothermal and failure strategy",
                (
                    "electrothermal drift-diffusion",
                    "phase-field/electrical-tree model",
                    "stochastic weakest-link or defect-network model",
                ),
                ("runaway", "field localisation", "breakdown probability and path"),
                "Add failure physics only after charge, heat, and defect couplings are independently constrained.",
                ("failure criterion and defect statistics are evidence-based",),
                (
                    "thermal/electrical properties",
                    "defect statistics",
                    "boundary conditions",
                    "failure observations",
                ),
                ("energy and charge balance", "thickness/temperature scaling", "hold-out breakdown data"),
                ("model fits only through unconstrained defect or threshold parameters",),
                ("defect population", "failure criterion", "electrothermal coupling"),
                ("failure remains dominated by unknown manufacturing defects requiring new measurement",),
            ),
        ),
    ),
    Regime(
        slug="process-kinetics-population",
        name_zh="工艺动力学、反应器与群体平衡",
        name_en="Process kinetics, reactors, and population balances",
        triggers=(
            "molecular weight distribution",
            "population balance",
            "reactor",
            "residence time distribution",
            "polymerization kinetics",
            "process simulation",
            "digital twin",
            "分子量分布",
            "群体平衡",
            "反应器",
            "停留时间分布",
            "聚合动力学",
            "流程模拟",
            "数字孪生",
        ),
        degrees_of_freedom=(
            "species inventories",
            "population distribution",
            "temperature/pressure",
            "reactor and controller states",
        ),
        governing_principles=(
            "mass and energy balances",
            "reaction kinetics",
            "population balance",
            "transport and residence-time closure",
        ),
        conserved_quantities=(
            "elements",
            "mass",
            "energy",
            "population moments subject to birth/death terms",
        ),
        symmetries_and_constraints=(
            "stoichiometry",
            "non-negative populations",
            "equipment and control constraints",
        ),
        state_variables=(
            "conversion",
            "composition",
            "temperature",
            "pressure",
            "population moments/distribution",
            "residence time",
        ),
        thermodynamic_potential=(
            "Gibbs free energy for equilibrium constraints",
            "entropy production for irreversible process steps",
        ),
        ensemble=("open, driven process system",),
        equilibrium_status="non-equilibrium process dynamics with possible local-equilibrium closures",
        length_scales=("molecular event", "particle/chain population", "reactor and plant"),
        time_scales=("elementary/chain kinetics", "mixing and residence", "thermal/control response"),
        scale_tests=(
            "reaction versus mixing time",
            "heat-removal versus generation time",
            "moment-closure adequacy",
        ),
        reduction_assumptions=(
            "kinetic network and population coordinates capture product quality",
            "lumped mixing/transport closure is justified",
        ),
        methods=(
            _method(
                "balance and identifiability analysis",
                ("stoichiometric balances", "lumped kinetic model", "moment and sensitivity analysis"),
                ("conversion", "selectivity", "heat release", "identifiable kinetic combinations"),
                "Use exact balances and identifiability to avoid over-parameterised process models.",
                ("measured inputs/outputs and operating histories are defined",),
                (
                    "flows",
                    "composition",
                    "temperature/pressure",
                    "candidate kinetics",
                    "measurement uncertainty",
                ),
                ("closure of balances", "parameter identifiability", "limiting operating cases"),
                ("model violates balances or parameters are structurally non-identifiable",),
                ("measurement error", "kinetic form", "parameter covariance"),
                ("product distribution or spatial gradients are decision-critical",),
            ),
            _method(
                "population and reactor modelling",
                (
                    "population-balance equation",
                    "method of moments/sections",
                    "CSTR/PFR/network dynamic model",
                ),
                (
                    "molecular-weight/particle distribution",
                    "conversion",
                    "reactor transients",
                    "product quality",
                ),
                "Resolve distributions and residence history when averages cannot answer the quality or mechanism question.",
                ("birth, growth, aggregation, breakage, or chain-event kernels are specified",),
                (
                    "kinetic kernels",
                    "feed and operating history",
                    "initial distribution",
                    "mixing/residence model",
                ),
                ("moment closure", "distribution measurements", "mass balance", "multi-condition validation"),
                ("one kernel set cannot reproduce both moments and full distributions",),
                ("kernel form", "closure", "residence distribution", "measurement resolution"),
                ("three-dimensional transport or control interactions dominate",),
            ),
            _method(
                "integrated process and uncertainty model",
                (
                    "reactor-CFD coupling",
                    "flowsheet/dynamic process model",
                    "Bayesian calibration or digital-twin surrogate",
                ),
                ("spatial non-uniformity", "plant dynamics", "operating policy and uncertainty"),
                "Integrate higher-fidelity process physics only after kinetic and balance models are constrained.",
                ("coupling and calibration data cover the operating envelope",),
                ("validated submodels", "equipment geometry", "control logic", "calibration/hold-out data"),
                ("component and integrated validation", "forecast calibration", "conservation and stability"),
                ("apparent accuracy comes from compensating non-identifiable submodels",),
                ("submodel discrepancy", "operating extrapolation", "sensor uncertainty"),
                ("the decision requires new experiments rather than further model complexity",),
            ),
        ),
    ),
    Regime(
        slug="multiscale-general",
        name_zh="跨尺度、混合机制或尚未充分定义的问题",
        name_en="Cross-scale, mixed-mechanism, or under-specified problem",
        triggers=(
            "multiscale",
            "multi-scale",
            "多尺度",
            "跨尺度",
            "first principles",
            "第一性原理",
            "simulation strategy",
            "仿真策略",
            "计算策略",
        ),
        degrees_of_freedom=("decision-specific microscopic, mesoscopic, and macroscopic variables",),
        governing_principles=(
            "conservation laws",
            "symmetry",
            "thermodynamic consistency",
            "causal link from model state to observable",
        ),
        conserved_quantities=("problem-dependent mass, charge, momentum, energy, and probability",),
        symmetries_and_constraints=(
            "problem geometry",
            "material symmetry",
            "boundary and admissibility constraints",
        ),
        state_variables=("only variables needed to predict the declared observable",),
        thermodynamic_potential=(
            "select from energy/free-energy/electrochemical potentials after the system and reservoirs are defined",
        ),
        ensemble=(
            "select from isolated, canonical, isothermal-isobaric, grand-canonical, or driven non-equilibrium descriptions",
        ),
        equilibrium_status="underdetermined until forcing, reservoirs, and observation time are specified",
        length_scales=("microscopic mechanism", "correlation or domain scale", "device/process scale"),
        time_scales=("fast local relaxation", "collective evolution", "observation/decision horizon"),
        scale_tests=(
            "separation of scales",
            "sensitivity of observable to unresolved degrees of freedom",
            "identifiability of bridge variables",
        ),
        reduction_assumptions=(
            "retain only degrees of freedom that are necessary for the declared observable",
        ),
        methods=(
            _method(
                "problem formulation and identifiability",
                (
                    "observable definition",
                    "dimensional analysis",
                    "causal/mechanistic diagram",
                    "sensitivity and identifiability analysis",
                ),
                ("minimum state description", "decision-sensitive mechanisms", "missing evidence"),
                "Do not choose a solver until the observable, reservoirs, scales, and falsification target are explicit.",
                ("the decision and acceptance criteria can be stated",),
                ("question", "observable", "conditions", "constraints", "available evidence"),
                ("unit/limit checks", "alternative mechanism comparison", "information-gap analysis"),
                ("multiple incompatible physical frames remain equally plausible",),
                ("model-class uncertainty", "missing observables", "scale ambiguity"),
                ("one physical regime becomes dominant and testable",),
            ),
            _method(
                "lowest-sufficient model",
                (
                    "analytical or reduced-order model",
                    "minimal statistical or continuum model",
                    "targeted quantum or molecular calculation if indispensable",
                ),
                ("the declared observable and discriminating trends",),
                "Choose the lowest-cost model whose state variables causally determine the observable and whose assumptions can be tested.",
                ("a falsifiable minimum model is available",),
                ("calibration data", "boundary conditions", "uncertainty model", "validation cases"),
                ("limiting cases", "hold-out data", "conservation and sensitivity"),
                ("model cannot distinguish competing mechanisms or misses decision-critical trends",),
                ("parameters", "model form", "boundary conditions"),
                ("validation identifies a specific missing scale or mechanism",),
            ),
            _method(
                "validated multiscale hierarchy",
                (
                    "sequential parameter passing",
                    "concurrent coupling only when necessary",
                    "surrogate or homogenised bridge",
                ),
                ("cross-scale mechanism and uncertainty propagation",),
                "Couple models through measurable bridge variables; never infer a scale link solely from visual agreement.",
                ("each model is validated at its own scale", "bridge variables are identifiable"),
                (
                    "scale-specific inputs",
                    "bridge definitions",
                    "uncertainty covariance",
                    "cross-scale validation data",
                ),
                ("closure tests", "uncertainty propagation", "independent cross-scale observables"),
                ("coupled predictions depend on unvalidated bridge variables or hidden calibration",),
                ("scale-transfer discrepancy", "surrogate error", "parameter covariance"),
                ("scale separation fails or evidence cannot constrain the bridge",),
            ),
        ),
    ),
)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _clean_items(values: list[str] | tuple[str, ...] | None, *, field: str) -> list[str]:
    if values is None:
        return []
    if len(values) > MAX_ITEMS:
        raise ValidationError(f"{field} has more than {MAX_ITEMS} items")
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{field} items must be strings")
        text = " ".join(value.split())
        if not text:
            continue
        if len(text) > MAX_ITEM_CHARS:
            raise ValidationError(f"{field} item exceeds {MAX_ITEM_CHARS} characters")
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _score(regime: Regime, text: str, observables: list[str]) -> int:
    score = 0
    observable_text = " ".join(_normalize(value) for value in observables)
    for trigger in regime.triggers:
        normalized = _normalize(trigger)
        if normalized in text:
            score += 4 if " " in normalized or any(ord(char) > 127 for char in normalized) else 3
        if normalized in observable_text:
            score += 3
    return score


def _equilibrium_status(primary: Regime, text: str) -> str:
    non_equilibrium = (
        "non-equilibrium",
        "nonequilibrium",
        "transient",
        "driven",
        "flow",
        "transport",
        "kinetic",
        "非平衡",
        "瞬态",
        "驱动",
        "流动",
        "输运",
        "动力学",
    )
    equilibrium = ("equilibrium", "phase equilibrium", "平衡", "相平衡")
    if any(marker in text for marker in non_equilibrium):
        return "non-equilibrium or mixed; forcing and observation time must be explicit"
    if any(marker in text for marker in equilibrium):
        return "equilibrium, subject to metastability and sampling checks"
    return primary.equilibrium_status


def _method_record(template: MethodTemplate, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "role": "minimum-sufficient" if rank == 1 else "escalation",
        "family": template.family,
        "representative_methods": list(template.methods),
        "target_observables": list(template.targets),
        "rationale": template.rationale,
        "assumptions": list(template.assumptions),
        "required_inputs": list(template.required_inputs),
        "validation": list(template.validation),
        "falsification": list(template.falsification),
        "uncertainty": list(template.uncertainty),
        "escalate_if": list(template.escalate_if),
    }


def advise_computation_strategy(
    question: str,
    observables: list[str] | tuple[str, ...] | None = None,
    conditions: list[str] | tuple[str, ...] | None = None,
    constraints: list[str] | tuple[str, ...] | None = None,
    available_evidence: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, first-principles method strategy without executing a solver."""

    if not isinstance(question, str):
        raise TypeError("question must be a string")
    clean_question = " ".join(question.split())
    if len(clean_question) < 3:
        raise ValidationError("question must contain at least three characters")
    if len(clean_question) > MAX_QUESTION_CHARS:
        raise ValidationError(f"question exceeds {MAX_QUESTION_CHARS} characters")
    clean_observables = _clean_items(observables, field="observables")
    clean_conditions = _clean_items(conditions, field="conditions")
    clean_constraints = _clean_items(constraints, field="constraints")
    clean_evidence = _clean_items(available_evidence, field="available_evidence")
    combined = _normalize(
        " ".join([clean_question, *clean_observables, *clean_conditions, *clean_constraints])
    )

    scored = sorted(
        ((regime, _score(regime, combined, clean_observables)) for regime in REGIMES),
        key=lambda item: (-item[1], item[0].slug),
    )
    positive = [(regime, score) for regime, score in scored if score > 0]
    if not positive:
        primary = next(regime for regime in REGIMES if regime.slug == "multiscale-general")
        primary_score = 1
        secondary: list[tuple[Regime, int]] = []
    else:
        primary, primary_score = positive[0]
        secondary = [
            (regime, score) for regime, score in positive[1:] if score >= max(3, int(primary_score * 0.5))
        ][:2]

    selected = [(primary, primary_score), *secondary]
    selected_slugs = [regime.slug for regime, _ in selected]
    ambiguous = primary.slug == "multiscale-general" or not clean_observables
    if len(positive) > 1 and positive[0][1] == positive[1][1]:
        ambiguous = True

    frame = {
        "degrees_of_freedom": list(primary.degrees_of_freedom),
        "governing_principles": list(primary.governing_principles),
        "conserved_quantities": list(primary.conserved_quantities),
        "symmetries_and_constraints": list(primary.symmetries_and_constraints),
        "state_variables": list(primary.state_variables),
        "thermodynamic_potential": list(primary.thermodynamic_potential),
        "statistical_ensemble": list(primary.ensemble),
        "equilibrium_status": _equilibrium_status(primary, combined),
        "length_scales": list(primary.length_scales),
        "time_scales": list(primary.time_scales),
        "dimensionless_or_scale_tests": list(primary.scale_tests),
        "reduction_assumptions": list(primary.reduction_assumptions),
    }

    ladder = [_method_record(template, rank) for rank, template in enumerate(primary.methods, 1)]
    intrinsically_multiscale = primary.slug in {
        "charge-transport-dielectric",
        "soft-matter-polymer",
        "process-kinetics-population",
        "multiscale-general",
    }
    bridge_variables: list[str] = (
        list(dict.fromkeys([*primary.state_variables[:4], *clean_observables]))
        if intrinsically_multiscale
        else []
    )
    if secondary:
        bridge_variables = list(
            dict.fromkeys(
                [*primary.state_variables[:3], *secondary[0][0].state_variables[:3], *clean_observables]
            )
        )
        ladder.append(
            {
                "rank": len(ladder) + 1,
                "role": "cross-regime-bridge",
                "family": f"bridge {primary.slug} with {secondary[0][0].slug}",
                "representative_methods": [
                    "sequential parameter passing with validation at each scale",
                    "joint inference only when bridge variables are identifiable",
                ],
                "target_observables": clean_observables or ["declared decision observable"],
                "rationale": "The question activates more than one physical regime; coupling must use measurable bridge variables and propagate uncertainty.",
                "assumptions": ["each submodel is independently valid in its regime"],
                "required_inputs": [
                    "scale-specific inputs",
                    "bridge-variable definitions",
                    "cross-scale validation data",
                ],
                "validation": [
                    "closure tests",
                    "uncertainty propagation",
                    "independent cross-regime observables",
                ],
                "falsification": [
                    "coupled result depends on an unvalidated or non-identifiable bridge variable"
                ],
                "uncertainty": ["model discrepancy at each scale", "bridge-variable covariance"],
                "escalate_if": ["scale separation fails or concurrent coupling is demonstrably required"],
            }
        )

    request = {
        "question": clean_question,
        "observables": clean_observables,
        "conditions": clean_conditions,
        "constraints": clean_constraints,
        "available_evidence": clean_evidence,
    }
    digest = hashlib.sha256(canonical_json(request).encode("utf-8")).hexdigest()[:16]
    selected_scores = {regime.slug: score for regime, score in selected}
    clarification = (
        ["Define the decision-critical observable, unit, acceptable error, and comparison baseline."]
        if ambiguous
        else []
    )
    if not clean_conditions:
        clarification.append(
            "Specify temperature, pressure, composition, geometry, forcing, and observation time where relevant."
        )
    if not clean_evidence:
        clarification.append(
            "Identify existing measurements or literature that can calibrate and falsify the proposed models."
        )

    return {
        "schema_version": "1.0",
        "strategy_id": f"FPS-{digest}",
        "status": "advisory-only",
        "question": clean_question,
        "observables": clean_observables,
        "conditions": clean_conditions,
        "constraints": clean_constraints,
        "available_evidence": clean_evidence,
        "classification": {
            "primary_regime": primary.slug,
            "primary_name_zh": primary.name_zh,
            "primary_name_en": primary.name_en,
            "selected_regimes": selected_slugs,
            "scores": selected_scores,
            "clarification_required": ambiguous,
            "clarification_questions": clarification,
        },
        "first_principles_frame": frame,
        "method_ladder": ladder,
        "cross_scale_plan": {
            "required": bool(secondary) or intrinsically_multiscale,
            "secondary_regimes": [regime.slug for regime, _ in secondary],
            "bridge_variables": bridge_variables,
            "coupling_rule": "Prefer sequential, uncertainty-aware coupling; use concurrent coupling only when scale separation fails and validation data exist.",
        },
        "validation_plan": list(
            dict.fromkeys(
                [
                    "test conservation laws, symmetries, units, and limiting cases",
                    "demonstrate numerical and model convergence appropriate to the method",
                    "validate against independent experiment, benchmark, or higher/lower-fidelity model",
                    "compare at least one plausible competing mechanism",
                    *[item for method in ladder[:2] for item in method["validation"][:2]],
                ]
            )
        ),
        "uncertainty_plan": list(
            dict.fromkeys(
                [
                    "separate parameter, numerical, sampling, boundary-condition, and model-form uncertainty",
                    "propagate uncertainty to the declared observable and decision threshold",
                    "report extrapolation beyond the calibration and validation domain",
                    *[item for method in ladder[:2] for item in method["uncertainty"][:2]],
                ]
            )
        ),
        "decision_rules": [
            "start with the lowest-fidelity method that can predict the declared observable and be falsified",
            "escalate resolution only when a failed validation identifies a missing degree of freedom or scale",
            "do not treat agreement with one dataset as mechanism proof",
            "retain negative, null, and contradictory results in the evidence record",
            "do not convert a planned strategy into a completed, checked, validated, or accepted result without execution evidence",
        ],
        "human_review": [
            "qualified domain review of governing physics, assumptions, and method hierarchy before external execution",
            "approval of computational cost, data egress, software licence, safety, and acceptance criteria where applicable",
        ],
        "execution_boundary": {
            "solver_executed": False,
            "external_execution_required": True,
            "statement": "TsaoSciResearcher generated an advisory strategy only; no DFT, MD, FEM, CFD, process simulation, or other solver was run.",
            "next_step": "Convert an approved strategy into a checksum-bound external handoff, then review returned receipts and results separately.",
        },
    }


__all__ = ["REGIMES", "advise_computation_strategy"]
