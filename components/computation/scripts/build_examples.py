from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def contract(
    *,
    title: str,
    question: str,
    workflow: str,
    system: dict[str, Any],
    conditions: dict[str, Any],
    observables: list[str],
    scales: list[str],
    methods: list[str],
    assumptions: list[str],
    boundary: dict[str, Any],
    initial: dict[str, Any],
    sources: list[dict[str, Any]],
    convergence: dict[str, Any],
    validation: dict[str, Any],
    uncertainty: list[str],
    resources: dict[str, Any],
    artifacts: list[str],
    approvals: list[str],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "acceptance_criteria": acceptance,
        "assumptions": assumptions,
        "boundary_conditions": boundary,
        "compute_resources": resources,
        "conditions": conditions,
        "convergence_plan": convergence,
        "expected_artifacts": artifacts,
        "human_approval_nodes": approvals,
        "initial_conditions": initial,
        "methods": methods,
        "model_object": {"description": title},
        "parameter_sources": sources,
        "question": question,
        "scales": scales,
        "schema_version": "1.0",
        "system": system,
        "target_observables": observables,
        "uncertainty_sources": uncertainty,
        "validation_plan": validation,
        "workflow": workflow,
    }


SCENARIOS: dict[str, dict[str, Any]] = {
    "organic-dft": contract(
        title="Organic-molecule DFT optimization and frequency workflow",
        question="Which conformer and electronic method give a stable optimized structure and defensible thermochemical corrections for the target organic molecule?",
        workflow="quantum-chemistry",
        system={
            "molecule": "user-supplied structure",
            "charge": "project-specific",
            "multiplicity": "project-specific",
        },
        conditions={
            "temperature_K": "project-specific",
            "solvent_model": "project-specific or not applicable",
        },
        observables=["optimized_geometry", "harmonic_frequencies", "thermal_corrections"],
        scales=["electronic", "molecular"],
        methods=["conformer screening", "DFT geometry optimization", "harmonic frequency analysis"],
        assumptions=[
            "Born-Oppenheimer approximation",
            "harmonic treatment is assessed for the intended temperature range",
        ],
        boundary={
            "molecular_boundary": "isolated or implicit-solvent model declared in the method fingerprint"
        },
        initial={"geometry": "user, experiment, or traceable conformer-search output"},
        sources=[
            {
                "parameter": "functional and basis",
                "source": "project literature and method benchmark",
            }
        ],
        convergence={
            "scf": "tight and recorded",
            "geometry": "optimizer thresholds recorded",
            "frequency": "unexpected imaginary modes rejected",
        },
        validation={
            "checks": [
                "connectivity",
                "charge and multiplicity",
                "conformer sensitivity",
                "method sensitivity",
            ]
        },
        uncertainty=[
            "conformer incompleteness",
            "electronic-method error",
            "harmonic approximation",
        ],
        resources={"cpu": "estimated after atom count", "memory": "estimated before preflight"},
        artifacts=[
            "native input and output",
            "method fingerprint",
            "geometry and frequency validation report",
        ],
        approvals=["charge/multiplicity approval", "scientific acceptance"],
        acceptance={"stable_minimum": True, "method_and_conformer_sensitivity_documented": True},
    ),
    "surface-neb": contract(
        title="Catalyst-surface adsorption and NEB workflow",
        question="What are the validated adsorption state and minimum-energy barrier for the selected elementary surface reaction?",
        workflow="reaction-path",
        system={
            "slab": "user-supplied surface model",
            "adsorbates": "declared reactant, product, and images",
        },
        conditions={"coverage": "project-specific", "reference_state": "explicitly declared"},
        observables=["adsorption_energy", "activation_barrier", "minimum_energy_path"],
        scales=["electronic", "atomistic"],
        methods=["periodic DFT", "adsorption-site screening", "climbing-image NEB"],
        assumptions=[
            "selected slab and coverage represent the active surface",
            "reference energies are consistent",
        ],
        boundary={"periodicity": "slab, vacuum, dipole treatment, and frozen layers declared"},
        initial={"images": "interpolated from validated endpoints without atomic overlap"},
        sources=[
            {
                "parameter": "pseudopotential, cutoff, and k mesh",
                "source": "solver data plus convergence studies",
            }
        ],
        convergence={
            "cutoff_and_kpoints": "independently converged",
            "endpoints": "force-converged",
            "neb": "maximum image force threshold recorded",
        },
        validation={
            "checks": [
                "endpoint identity",
                "single barrier topology",
                "transition-mode or pathway plausibility",
                "reference-state consistency",
            ]
        },
        uncertainty=["slab size", "coverage", "functional choice", "finite image count"],
        resources={
            "parallel_images": "estimated from image count",
            "walltime": "bounded by queue policy",
        },
        artifacts=["structures and native outputs", "convergence studies", "energy-path report"],
        approvals=["surface-model approval", "barrier acceptance"],
        acceptance={"converged_path": True, "reference_states_consistent": True},
    ),
    "protein-md": contract(
        title="Protein-nucleic-acid GROMACS 100 ns workflow",
        question="Is the protein-nucleic-acid complex structurally stable and sufficiently sampled over the nominal 100 ns production profile?",
        workflow="molecular-dynamics",
        system={
            "complex": "user-supplied protein and nucleic-acid structure",
            "protonation_and_parameters": "project-specific",
        },
        conditions={
            "temperature_K": "project-specific",
            "pressure_bar": "project-specific",
            "nominal_production_ns": 100,
        },
        observables=[
            "rmsd",
            "rmsf",
            "radius_of_gyration",
            "hydrogen_bonds",
            "sampling_convergence",
        ],
        scales=["atomistic", "nanosecond"],
        methods=[
            "GROMACS preparation",
            "minimization",
            "NVT/NPT equilibration",
            "replicated production MD",
        ],
        assumptions=[
            "force field and water model are qualified for the system",
            "100 ns is a starting profile, not proof of convergence",
        ],
        boundary={
            "periodic_box": "shape and padding justified",
            "electrostatics": "method and cutoff declared",
        },
        initial={
            "velocities": "seeded and recorded",
            "structure": "validated with missing atoms and clashes resolved",
        },
        sources=[
            {
                "parameter": "force field and nonstandard residues",
                "source": "validated literature or traceable parameterization",
            }
        ],
        convergence={
            "equilibration": "energy, temperature, pressure, and density stable",
            "sampling": "replicate and block convergence required",
        },
        validation={
            "checks": [
                "PBC handling",
                "trajectory integrity",
                "replicate consistency",
                "structural plausibility",
            ]
        },
        uncertainty=[
            "force-field error",
            "initial structure",
            "finite sampling",
            "replicate variability",
        ],
        resources={"gpu": "optional after probe", "storage": "estimated from trajectory frequency"},
        artifacts=["topology and run inputs", "trajectories", "convergence and analysis report"],
        approvals=["parameterization approval", "sampling acceptance"],
        acceptance={"equilibrated": True, "sampling_convergence_demonstrated": True},
    ),
    "polymer-carbon-black": contract(
        title="Polymer-carbon-black LAMMPS interface workflow",
        question="How do dispersion, selective localization, and interface interactions control the morphology of the polymer-carbon-black system?",
        workflow="polymer-composite",
        system={
            "polymer": "user-specified chemistry and molecular-weight profile",
            "filler": "carbon-black aggregate model",
        },
        conditions={
            "temperature_and_pressure": "processing-relevant and declared",
            "composition": "project-specific",
        },
        observables=[
            "dispersion_metric",
            "interfacial_adhesion",
            "cluster_statistics",
            "percolation_descriptors",
        ],
        scales=["atomistic", "mesoscale"],
        methods=["LAMMPS molecular dynamics", "interface-energy analysis", "morphology statistics"],
        assumptions=[
            "force field is qualified for polymer and filler surfaces",
            "finite cell represents the target composition",
        ],
        boundary={
            "periodicity": "declared in all directions",
            "loading": "equilibration or deformation protocol specified",
        },
        initial={"packing": "multiple independent packings with overlap checks"},
        sources=[
            {
                "parameter": "polymer-filler interactions",
                "source": "experiment, DFT handoff, or validated literature",
            }
        ],
        convergence={
            "cell_and_chain_count": "size study",
            "time_step": "stability study",
            "sampling": "independent-replica convergence",
        },
        validation={
            "checks": [
                "density",
                "energy stability",
                "radial distributions",
                "experimental morphology where available",
            ]
        },
        uncertainty=["force field", "aggregate morphology", "packing seed", "finite size"],
        resources={
            "cpu_or_gpu": "selected after LAMMPS probe",
            "replicas": "at least enough for uncertainty estimate",
        },
        artifacts=["LAMMPS data and inputs", "trajectories", "morphology and uncertainty report"],
        approvals=["interaction-model approval", "morphology acceptance"],
        acceptance={"equilibrated": True, "replica_uncertainty_reported": True},
    ),
    "polymerization-pbe": contract(
        title="Polymerization microkinetic and population-balance workflow",
        question="Which elementary kinetic parameters reproduce conversion, composition, molecular-weight distribution, and branching over the target operating window?",
        workflow="polymerization",
        system={
            "mechanism": "initiation, propagation, transfer, termination, and deactivation network",
            "reactor_context": "declared",
        },
        conditions={"temperature_pressure_composition": "operating envelope declared"},
        observables=[
            "conversion",
            "Mn",
            "Mw",
            "PDI",
            "composition_distribution",
            "branching_distribution",
        ],
        scales=["elementary reaction", "population", "reactor"],
        methods=[
            "Eyring or fitted rate constants",
            "ODE microkinetics",
            "population balance or moments",
        ],
        assumptions=[
            "mechanism closure is tested",
            "moment closure is validated against a higher-fidelity reference",
        ],
        boundary={"population_domain": "chain-length and composition bounds declared"},
        initial={"species_and_population": "feed and catalyst states declared"},
        sources=[
            {
                "parameter": "rate constants",
                "source": "DFT, experiment, or calibrated literature with uncertainty",
            }
        ],
        convergence={
            "ode": "tolerance study",
            "population_grid_or_moments": "resolution or closure study",
            "optimization": "multi-start diagnostics",
        },
        validation={
            "checks": [
                "mass balance",
                "limiting cases",
                "experimental conversion and distribution",
                "identifiability",
            ]
        },
        uncertainty=[
            "mechanism incompleteness",
            "rate constants",
            "measurement error",
            "closure approximation",
        ],
        resources={
            "solver": "stiff ODE/PBE selected after diagnostics",
            "parameter_runs": "bounded design",
        },
        artifacts=["mechanism and parameter table", "solver model", "fit and validation report"],
        approvals=["mechanism approval", "parameter identifiability review"],
        acceptance={
            "mass_balance": True,
            "distribution_validation": True,
            "identifiability_reported": True,
        },
    ),
    "pp-percolation": contract(
        title="PP semiconductor shielding percolation workflow",
        question="How do carbon-black loading, dispersion, and selective localization govern conductivity, rheology, and temperature stability in PP-based shielding material?",
        workflow="polymer-composite",
        system={
            "matrix": "PP/elastomer formulation",
            "filler": "conductive carbon black",
            "morphology": "statistical ensemble",
        },
        conditions={
            "temperature_range": "measurement and processing range declared",
            "composition": "formulation design",
        },
        observables=[
            "volume_resistivity",
            "percolation_threshold",
            "rheology",
            "temperature_stability",
        ],
        scales=["mesoscale", "continuum", "processing"],
        methods=[
            "stochastic morphology",
            "percolation network",
            "effective transport",
            "rheology-structure linkage",
        ],
        assumptions=[
            "contact/tunneling law is calibrated",
            "morphology ensemble represents processing variability",
        ],
        boundary={
            "electrodes": "geometry and contact treatment declared",
            "domain": "size convergence required",
        },
        initial={"morphologies": "multiple statistically independent realizations"},
        sources=[
            {
                "parameter": "particle and interface transport",
                "source": "experiment or validated lower-scale handoff",
            }
        ],
        convergence={
            "domain_size": "finite-size study",
            "realizations": "confidence-interval convergence",
            "mesh_or_network": "resolution study",
        },
        validation={
            "checks": [
                "resistivity curve",
                "percolation scaling",
                "rheology",
                "temperature cycling",
            ]
        },
        uncertainty=[
            "dispersion",
            "contact resistance",
            "particle morphology",
            "processing history",
        ],
        resources={
            "ensemble_size": "set by confidence target",
            "parallelism": "bounded by available resources",
        },
        artifacts=[
            "morphology ensemble",
            "network models",
            "structure-property uncertainty report",
        ],
        approvals=["transport-law approval", "formulation recommendation review"],
        acceptance={"finite_size_converged": True, "experimental_validation": True},
    ),
    "extrusion-cfd": contract(
        title="Non-Newtonian OpenFOAM extrusion eccentricity workflow",
        question="Which die, rheology, thermal, and operating conditions control pressure drop, temperature, residence time, and cable-extrusion eccentricity?",
        workflow="extrusion",
        system={
            "geometry": "screw/channel/die or cable-head geometry",
            "material": "non-Newtonian polymer melt",
        },
        conditions={"flow_rate_or_screw_speed": "declared", "thermal_conditions": "declared"},
        observables=[
            "pressure_drop",
            "temperature_field",
            "residence_time_distribution",
            "eccentricity_metric",
        ],
        scales=["continuum", "equipment"],
        methods=[
            "OpenFOAM CFD",
            "non-Newtonian constitutive model",
            "conjugate heat transfer where required",
        ],
        assumptions=[
            "continuum approximation is valid",
            "constitutive range covers simulated shear rates and temperatures",
        ],
        boundary={
            "inlets_outlets_walls": "all velocity, pressure, thermal, and moving-wall conditions declared"
        },
        initial={"fields": "bounded initialization with restart policy"},
        sources=[
            {
                "parameter": "viscosity and thermal properties",
                "source": "rheometry and traceable property data",
            }
        ],
        convergence={
            "mesh": "three-level independence",
            "time_step": "Courant/stability study",
            "residual_and_balance": "both required",
        },
        validation={
            "checks": [
                "mass and energy balance",
                "pressure data",
                "temperature data",
                "eccentricity benchmark",
            ]
        },
        uncertainty=["rheology fit", "boundary conditions", "mesh", "process variability"],
        resources={"mpi": "selected after decomposition study", "walltime": "bounded"},
        artifacts=["mesh and case files", "solver logs", "convergence and conservation report"],
        approvals=["constitutive-model approval", "equipment recommendation review"],
        acceptance={
            "mesh_independent": True,
            "mass_energy_balance": True,
            "validated_eccentricity": True,
        },
    ),
    "cable-fem": contract(
        title="Cable thermo-electro-mechanical finite-element workflow",
        question="How do coupled temperature, electric field, stress, and deformation evolve across the cable insulation and interfaces under the target duty cycle?",
        workflow="multiphysics",
        system={
            "geometry": "conductor, screens, insulation, sheath, and interfaces",
            "materials": "temperature-dependent properties",
        },
        conditions={"voltage_current_ambient_load_cycle": "declared"},
        observables=["temperature", "electric_field", "stress", "strain", "interface_response"],
        scales=["continuum", "cable component"],
        methods=["finite element", "electro-thermal coupling", "thermo-mechanical coupling"],
        assumptions=[
            "material models are qualified over the operating range",
            "coupling strategy is convergence-tested",
        ],
        boundary={
            "electrical_thermal_mechanical": "all surfaces, contacts, symmetry, and far-field conditions declared"
        },
        initial={"temperature_and_mechanical_state": "declared with preload history"},
        sources=[
            {
                "parameter": "conductivity, permittivity, thermal and mechanical properties",
                "source": "experiment or traceable literature",
            }
        ],
        convergence={
            "mesh": "field and interface refinement study",
            "time_step": "transient study",
            "coupling": "iteration tolerance study",
        },
        validation={
            "checks": [
                "charge/energy balance",
                "analytical benchmark",
                "temperature measurements",
                "mechanical plausibility",
            ]
        },
        uncertainty=[
            "material properties",
            "contact conditions",
            "geometry tolerance",
            "load history",
        ],
        resources={
            "solver": "selected by nonlinearity and coupling",
            "memory": "estimated from mesh",
        },
        artifacts=["geometry and mesh", "material and boundary data", "coupled validation report"],
        approvals=["material-model approval", "high-field and safety review"],
        acceptance={"mesh_time_coupling_converged": True, "physical_validation": True},
    ),
    "polymer-process": contract(
        title="DWSIM/IDAES polymer-process workflow",
        question="Which property method, reactor model, recycle strategy, and operating variables reproduce and optimize the polymer process flowsheet?",
        workflow="process-simulation",
        system={
            "components": "declared feed, catalyst, solvent, polymer, and byproducts",
            "units": "reactor and separation flowsheet",
        },
        conditions={"feed_and_operating_envelope": "declared"},
        observables=[
            "mass_balance",
            "energy_balance",
            "conversion",
            "product_quality",
            "energy_use",
        ],
        scales=["reactor", "flowsheet"],
        methods=[
            "DWSIM or IDAES/Pyomo",
            "property-package qualification",
            "steady-state optimization",
        ],
        assumptions=[
            "property method is valid over the composition range",
            "lumped polymer properties are documented",
        ],
        boundary={"feeds_products_utilities": "all stream and utility boundaries declared"},
        initial={"tear_streams_and_guesses": "bounded and recorded"},
        sources=[
            {
                "parameter": "properties and kinetics",
                "source": "validated data and reactor-model handoff",
            }
        ],
        convergence={
            "recycles": "tear tolerance study",
            "optimization": "constraint and multi-start checks",
            "balances": "closure thresholds",
        },
        validation={
            "checks": [
                "mass and energy balance",
                "unit benchmarks",
                "plant or pilot data",
                "property sensitivity",
            ]
        },
        uncertainty=["property package", "kinetics", "feed variability", "equipment efficiency"],
        resources={"solver_licenses": "probed before execution", "scenario_count": "bounded"},
        artifacts=[
            "flowsheet and stream table",
            "solver configuration",
            "validation and optimization report",
        ],
        approvals=[
            "property-method approval",
            "commercial-simulator license gate",
            "process recommendation review",
        ],
        acceptance={"balances_closed": True, "property_method_validated": True},
    ),
    "aspen-dynamic": contract(
        title="Aspen dynamic digital-twin handoff workflow",
        question="Can the lawful Aspen dynamic model reproduce transients and support bounded, human-reviewed digital-twin decisions?",
        workflow="digital-twin",
        system={
            "flowsheet": "user-owned Aspen Plus/Dynamics/ACM model",
            "control_structure": "declared",
        },
        conditions={"operating_region_and_disturbances": "declared"},
        observables=[
            "dynamic_response",
            "control_performance",
            "state_estimates",
            "applicability_status",
        ],
        scales=["dynamic process", "digital twin"],
        methods=[
            "lawful Aspen adapter guidance",
            "dynamic validation",
            "state estimation and drift detection",
        ],
        assumptions=[
            "user has a valid installation and license",
            "online use is bounded by an applicability domain",
        ],
        boundary={
            "inputs_outputs_controls": "tag mapping, units, timing, and actuator limits declared"
        },
        initial={"steady_state_and_controller_state": "validated before transients"},
        sources=[
            {
                "parameter": "dynamic model and controller settings",
                "source": "user-owned model and plant evidence",
            }
        ],
        convergence={
            "initialization": "steady-state reconciliation",
            "integration": "time-step study",
            "estimator": "innovation diagnostics",
        },
        validation={
            "checks": [
                "historical transients",
                "holdout scenarios",
                "drift detection",
                "fail-safe behavior",
            ]
        },
        uncertainty=[
            "sensor noise",
            "parameter drift",
            "unmodeled disturbances",
            "model-form error",
        ],
        resources={
            "license": "must pass probe",
            "execution_mode": "offline validation before online use",
        },
        artifacts=[
            "lawful handoff package",
            "tag and unit map",
            "dynamic and applicability report",
        ],
        approvals=["license approval", "control and safety review", "online-deployment approval"],
        acceptance={"dynamic_holdout_validated": True, "applicability_and_fail_safe_defined": True},
    ),
    "dft-md-cfd": contract(
        title="DFT-to-MD-to-CFD multiscale handoff workflow",
        question="Can traceable lower-scale interaction, transport, and rheology parameters predict the target equipment-scale flow response with propagated uncertainty?",
        workflow="multiscale-coupling",
        system={
            "material": "user-specified chemistry and morphology",
            "equipment": "declared CFD domain",
        },
        conditions={"temperature_pressure_composition_path": "common overlap region declared"},
        observables=[
            "interaction_parameters",
            "transport_coefficients",
            "constitutive_parameters",
            "equipment_performance",
        ],
        scales=["electronic", "atomistic", "continuum", "equipment"],
        methods=[
            "DFT parameterization",
            "MD transport/rheology",
            "CFD equipment model",
            "uncertainty propagation",
        ],
        assumptions=[
            "handoff quantities have overlapping applicability",
            "units and reference states are transformed explicitly",
        ],
        boundary={
            "scale_interfaces": "source, receiver, units, conditions, and transformation declared for each edge"
        },
        initial={"upstream_evidence": "validated before each downstream handoff"},
        sources=[
            {
                "parameter": "all transferred quantities",
                "source": "native outputs plus validated transformation records",
            }
        ],
        convergence={
            "dft": "method convergence",
            "md": "sampling convergence",
            "cfd": "mesh/time-step/balance convergence",
        },
        validation={
            "checks": [
                "handoff schema",
                "unit and reference-state consistency",
                "intermediate experiment",
                "equipment benchmark",
            ]
        },
        uncertainty=[
            "electronic method",
            "force field",
            "sampling",
            "constitutive fit",
            "CFD discretization",
        ],
        resources={
            "task_graph": "staged with restartable artifacts",
            "hpc": "resource estimate per node",
        },
        artifacts=[
            "multiscale task graph",
            "handoff records",
            "uncertainty propagation and validation report",
        ],
        approvals=["each scale handoff", "final equipment-level acceptance"],
        acceptance={"all_handoffs_validated": True, "uncertainty_propagated": True},
    ),
    "failure-gate": contract(
        title="Failure classification, bounded recovery, and human-approval workflow",
        question="How should a failed scientific task be classified, recovered within bounded policy, or escalated without altering the scientific claim silently?",
        workflow="hpc-execution",
        system={
            "failed_task": "native command, environment, input, output, and scheduler evidence"
        },
        conditions={
            "failure_time_context": "platform, queue, resource, solver, and attempt recorded"
        },
        observables=["failure_class", "recoverability", "scientific_impact", "approval_decision"],
        scales=["execution", "workflow governance"],
        methods=[
            "deterministic failure classifier",
            "bounded recovery policy",
            "human approval gate",
        ],
        assumptions=["native evidence is retained", "unknown failures are not auto-retried"],
        boundary={
            "attempt_limit": "declared before recovery",
            "forbidden_changes": "scientifically material silent changes",
        },
        initial={"original_task": "immutable parameter and provenance snapshot"},
        sources=[
            {
                "parameter": "classification and recovery rules",
                "source": "versioned repository policy",
            }
        ],
        convergence={
            "not_applicable": "this workflow validates recovery governance rather than a numerical solution"
        },
        validation={
            "checks": [
                "classification evidence",
                "attempt count",
                "before/after parameter diff",
                "scientific impact statement",
            ]
        },
        uncertainty=["ambiguous error messages", "compound failures", "unknown model inadequacy"],
        resources={
            "retry_budget": "bounded",
            "human_response": "required for unknown or high-risk cases",
        },
        artifacts=["failure record", "recovery decision", "parameter diff", "approval record"],
        approvals=[
            "license and safety failures",
            "unknown or repeated failures",
            "scientifically material recovery",
        ],
        acceptance={"failure_classified": True, "recovery_bounded_and_recorded": True},
    ),
}


def render_readme(name: str, payload: dict[str, Any]) -> str:
    return f"""# {payload["model_object"]["description"]}

This is a preparation and validation example for `{payload["workflow"]}`. It does not claim that any external solver, license, database, cluster, or production calculation is available or has run.

## Use

```bash
python -m tsao_computation validate-contract examples/{name}/contract.json --strict
python -m tsao_computation probe
```

Replace every project-specific value with traceable data, complete the environment preflight, and retain native evidence. Input generation or normal program exit is not scientific acceptance.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[str] = []
    for name, payload in sorted(SCENARIOS.items()):
        directory = ROOT / "examples" / name
        contract_path = directory / "contract.json"
        readme_path = directory / "README.md"
        contract_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        readme_text = render_readme(name, payload)
        if args.check:
            if (
                not contract_path.is_file()
                or contract_path.read_text(encoding="utf-8") != contract_text
            ):
                changed.append(contract_path.relative_to(ROOT).as_posix())
            if not readme_path.is_file() or readme_path.read_text(encoding="utf-8") != readme_text:
                changed.append(readme_path.relative_to(ROOT).as_posix())
        else:
            directory.mkdir(parents=True, exist_ok=True)
            contract_path.write_text(contract_text, encoding="utf-8", newline="\n")
            readme_path.write_text(readme_text, encoding="utf-8", newline="\n")
    if changed:
        print(json.dumps({"out_of_date": changed}, indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
