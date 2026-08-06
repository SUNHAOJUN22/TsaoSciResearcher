<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher logo" width="118" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>Evidence-first scientific strategy, contract, handoff, and validation control layer</strong></p>
  <p>Question → model contract → evidence contract → guarded external execution → receipt → acceptance evidence</p>

[简体中文](README.zh-CN.md) · [Documentation](docs/index.md) · [Architecture](docs/ARCHITECTURE.md) · [Mathematical contracts](docs/MATHEMATICAL_CONTRACTS.md) · [Validation](docs/VALIDATION.md) · [Visual atlas](docs/VISUAL_ATLAS.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **Release 0.7.4** · Apache-2.0 · Python 3.10–3.13 · deterministic CLI and Python API

## 1. Acceptance-oriented overview

TsaoSciResearcher is a **scientific research control layer**, not a numerical solver. It routes research questions, retrieves validated capability contracts, generates first-principles strategy passports, preserves contradictory evidence, guards quantities and units, records applicability and identifiability boundaries, prepares checksum-bound external handoffs, verifies execution receipts, and exports deterministic reproducibility capsules.

The repository does **not** claim that DFT, quantum chemistry, molecular dynamics, FEM, CFD, process simulation, HPC execution, database retrieval, or laboratory work occurred unless externally produced, checksum-verifiable evidence is supplied.

The implemented inventory is machine checked:

| Delivery fact | Verified value |
|---|---:|
| Capability contracts | **341** |
| Preserved legacy/general contracts | **158** |
| Preserved workbook names | **322** |
| Domain computation/engineering contracts | **164** |
| Generic domain placeholders | **0** |
| Runtime additions | **19** |
| Primary workflows | **15** |
| JSON Schemas | **19** |
| Domain packs | **7** |
| AI-generated conceptual diagrams | **37** |

Evidence documents: [README audit](docs/README_AUDIT_REPORT.md), [capability matrix](docs/CAPABILITY_COVERAGE_MATRIX.md), [architecture mapping](docs/README_ARCHITECTURE_MAPPING.md), [validation evidence](docs/VALIDATION_EVIDENCE.json), [HTML test dashboard](docs/test-dashboard.html), and [SVG test dashboard](docs/test-dashboard.svg).

> Every diagram in this repository is an **AI-generated conceptual illustration for documentation**. A diagram is not an experimental observation, measured dataset, numerical solver result, or proof that an external computation ran.

## 2. What the repository implements

| Layer | Implemented responsibility | Explicit boundary |
|---|---|---|
| Router | deterministic bilingual task classification, positive/negative semantics, priority and clarification state | classification does not execute the selected method |
| Capability retrieval | validated v2 catalog search with bounded filters and defensive copies | catalog relevance is not scientific proof |
| Strategy adviser | model ladder, observables, conditions, assumptions, falsification, validation and uncertainty contracts | output is advisory-only |
| Scientific Passport | model, bridge, evidence, uncertainty, applicability, conflict and identifiability contracts | automatic approval is structurally disabled |
| Project state | canonical `.tsao-research/` state, hash-linked events and controlled transitions | a status word never substitutes for evidence |
| Handoff and receipt | checksum-bound input contracts and user-supplied external execution receipts | the repository does not launch the external engine |
| Reproducibility | deterministic capsule, safe archive checks, SBOM and release validation | reproducibility evidence does not establish physical truth |

```text
scientific question
    ↓
decision-critical observable, units and acceptance threshold
    ↓
state variables, governing principles, reservoirs and constraints
    ↓
minimum-sufficient falsifiable model
    ↓
applicability, evidence conflict, identifiability and scale-bridge gates
    ↓
qualified human review
    ↓
checksum-bound external handoff → receipt → independent acceptance
```

## 3. Architecture

```text
CLI / Python API
      │
      ├── router.py ───────────────> bounded primary workflow
      ├── capabilities.py ─────────> validated capability contracts
      ├── strategy.py ─────────────> Scientific Passport and integrity gates
      ├── mathematical_contracts.py> versioned equations and interpretation limits
      ├── state.py ─────────────────> hash-linked project state
      ├── handoff.py / receipts.py ─> external execution evidence boundary
      └── capsule.py ───────────────> deterministic reproducibility archive
```

![Research operating architecture](docs/assets/ai/research_os_architecture.svg)

![Progressive routing and loading](docs/assets/ai/progressive_routing_loading.svg)

![Computation handoff boundary](docs/assets/ai/computation_handoff_boundary.svg)

## 4. Machine-readable mathematical contracts

The `math` command exposes eight stable, bilingual contracts. They are **explanation and decision-support contracts**. They do not run a solver, fit parameters, propagate a numerical covariance matrix, or validate user-supplied evidence.

```bash
python -m tsao_researcher math
python -m tsao_researcher math --contract decision-readiness --language en
python -m tsao_researcher math --contract quantity-dimension --language zh-CN
```

Every response fixes the scientific boundary:

```json
{
  "schema_version": "1.0",
  "advisory_only": true,
  "solver_executed": false,
  "automatic_approval": false
}
```

### 4.1 Capability-ranking abstraction

\[
S(c\mid q,o,e)=w_qR(q,c)+w_oR(o,c)+w_eM(e,c)-w_xC(c)
\]

- \(c\): candidate capability
- \(q\): scientific question
- \(o\): decision-critical observable
- \(e\): declared evidence context
- \(C(c)\): conflict or exclusion penalty

This is a pedagogical abstraction of deterministic routing and bounded ranking. The runtime does not claim that the weights are fitted statistical parameters.

### 4.2 Quantity, unit, and dimension contract

\[
x=(v,u,d), \qquad d_{\mathrm{left}}=d_{\mathrm{right}}
\]

A claim must identify the value \(v\), unit \(u\), and physical dimension \(d\) whenever the decision depends on quantitative comparison. Missing units require review; incompatible dimensions under a shared comparison label are blocked.

### 4.3 Applicability and extrapolation risk

\[
r_{\mathrm{extra}}=\frac{d(x,\mathcal A)}{\max(s_{\mathcal A},\varepsilon)}
\]

Here \(x\) is the target condition, \(\mathcal A\) is the declared applicability domain, and \(s_{\mathcal A}\) is a characteristic domain scale. The runtime currently uses conservative lexical and structural extrapolation markers rather than pretending to compute this normalized distance from absent data.

### 4.4 Evidence triad and conflict ledger

\[
E=(E_{+},E_{-},E_{0}),\qquad
\kappa=\mathbf 1[E_{+}\neq\varnothing\land E_{-}\neq\varnothing]
\]

- \(E_+\): supporting evidence
- \(E_-\): challenging or refuting evidence
- \(E_0\): neutral or unresolved evidence

Negative and contradictory evidence remain visible. They are never silently averaged into a positive conclusion.

### 4.5 Mechanism and parameter identifiability

\[
D_{ij}(O,C)>\tau
\qquad\text{or}\qquad
\operatorname{rank}(J_{\theta})=p
\]

Competing mechanisms \(i\) and \(j\) require discriminating observables \(O\) under conditions \(C\). A unique parameter claim requires sufficient sensitivity rank. The repository records the requirement and conservative warnings; numerical Jacobian construction remains an external analysis task.

### 4.6 Decision-observable uncertainty budget

\[
\Sigma_y\approx
J\Sigma_{\theta}J^{\mathsf T}
+\Sigma_{\mathrm{num}}
+\Sigma_{\mathrm{sample}}
+\Sigma_{\mathrm{model}}
+\Sigma_{\mathrm{transfer}}
\]

Uncertainty must reach the observable used for acceptance or rejection. The contract separates parameter, numerical, sampling, model-form, and scale-transfer uncertainty so none can disappear behind one generic confidence word.

### 4.7 Multiscale bridge error budget

\[
U_{\mathrm{bridge}}^2=
U_{\mathrm{source}}^2+
U_{\mathrm{mapping}}^2+
U_{\mathrm{closure}}^2+
U_{\mathrm{target}}^2
\]

A microscopic result cannot jump directly to an industrial conclusion. Each scale bridge needs measurable variables, mapping assumptions, closure validation, and target-scale acceptance evidence.

### 4.8 Conservative decision-readiness aggregation

\[
G=\min\left(
 g_{\mathrm{quantity}},
 g_{\mathrm{applicability}},
 g_{\mathrm{evidence}},
 g_{\mathrm{identifiability}},
 g_{\mathrm{bridge}}
\right)
\]

The weakest mandatory contract controls readiness:

```text
BLOCK < REVIEW < PASS
```

A software `PASS` means that no declared software blocker remains. It is not scientific proof and does not bypass qualified human review.

![Mathematical contract registry](docs/assets/ai/mathematical_contract_registry.svg)

![Decision readiness lattice](docs/assets/ai/decision_readiness_lattice.svg)

![Uncertainty propagation budget](docs/assets/ai/uncertainty_propagation_budget.svg)

![Multiscale bridge error budget](docs/assets/ai/multiscale_bridge_error_budget.svg)

Detailed bilingual interpretation: [docs/MATHEMATICAL_CONTRACTS.md](docs/MATHEMATICAL_CONTRACTS.md).

## 5. Scientific model reconstruction strategy

The repository selects a method from the decision physics, not from a fashionable software name.

### 5.1 Start from governing structure

A generic state model is written as:

\[
\dot{x}=f(x,u,\theta)+\epsilon_{\mathrm{model}},
\qquad y=h(x,\theta)+\epsilon_{\mathrm{measurement}}
\]

The strategy must declare:

1. state variables \(x\), controls \(u\), and parameters \(\theta\);
2. observable \(y\) and acceptance threshold;
3. reservoirs, constraints, boundary and initial conditions;
4. the smallest model able to falsify the candidate mechanism;
5. numerical, experimental, and transfer validation requirements.

For a conserved extensive quantity \(\phi\), the control-volume structure is:

\[
\frac{\mathrm d}{\mathrm dt}\int_{\Omega}\rho\phi\,\mathrm dV
+\int_{\partial\Omega}\mathbf J_{\phi}\cdot\mathbf n\,\mathrm dA
=\int_{\Omega}s_{\phi}\,\mathrm dV
\]

This equation does not imply that a mesh, constitutive law, or solver run exists. It tells the strategy which conservation and closure declarations must be present before an external CFD, FEM, transport, or process handoff is acceptable.

### 5.2 Minimum-sufficient method ladder

| Problem class | Minimum-sufficient starting model | Escalation evidence |
|---|---|---|
| electronic structure, defects, interfaces | converged cluster or periodic DFT | functional sensitivity, finite-size and reference-state failures |
| reaction mechanism and selectivity | pathway/transition-state energetics and microkinetic skeleton | missing pathways, solvent/dynamics effects, transport coupling |
| conformation and free energy | ensemble-based MD/MC with convergence estimator | inadequate sampling, force-field failure, electronic reactivity |
| morphology and phase evolution | scaling/SCFT/CGMD/DPD/phase field | mapping failure, unresolved chemistry, process coupling |
| flow, heat and mass transfer | analytical/control-volume/1D reduced model | closure failure, geometry effects, instability, multiphysics coupling |
| mechanics and fracture | reduced mechanics or FEM | constitutive non-identifiability, localization, cohesive/phase-field need |
| reaction engineering | mass/energy balance plus kinetic/population model | residence-time heterogeneity, reactor CFD, plant-data calibration |
| mixed multiscale question | lowest-cost falsifiable reduced model | validated bridge variable and quantified transfer uncertainty |

## 6. Scientific Passport and acceptance strategy

Every strategy records:

| Contract | Required declarations | Typical blocker |
|---|---|---|
| Model Contract | variables, governing principles, assumptions, domain and failure conditions | no defined observable or domain |
| Quantity Contract | values, units, dimensions and comparison labels | missing unit or incompatible dimension |
| Applicability Contract | calibrated domain, transfer evidence and extrapolation markers | unsupported transfer outside domain |
| Evidence Contract | supporting, challenging and unresolved evidence IDs | contradiction hidden or evidence absent |
| Identifiability Contract | competing mechanisms and discriminating observables | equifinality or unsupported unique mechanism |
| Bridge Contract | source/target scales, bridge variables and acceptance tests | direct micro-to-industrial jump |
| Uncertainty Contract | parameter, numerical, sampling, model and transfer uncertainty | uncertainty not propagated to decision |

Recommended operating strategy:

```text
1. route before loading
2. define the decision observable and units
3. reconstruct governing structure and competing mechanisms
4. choose the minimum-sufficient falsifiable model
5. expose evidence conflict, applicability, identifiability and scale bridges
6. define validation and uncertainty acceptance thresholds
7. obtain qualified human approval
8. create checksum-bound external handoff
9. record receipt and output hashes
10. accept only after independent validation
```

![Scientific Passport matrix](docs/assets/ai/scientific_passport_matrix.svg)

![Evidence maturity ladder](docs/assets/ai/evidence_maturity_ladder.svg)

![Scientific integrity causality guard](docs/assets/ai/scientific_integrity_causality_guard.svg)

## 7. CLI usage

### Install

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
```

### Route a task

```bash
python -m tsao_researcher route \
  "Design a traceable multiscale study of trap-controlled charge transport"
```

### Search capability contracts

```bash
python -m tsao_researcher search \
  "polymer molecular dynamics" \
  --workflow computation-handoff \
  --limit 10
```

### Generate a strategy without executing a solver

```bash
python -m tsao_researcher strategy \
  "How do interfacial trap states control conductivity and breakdown?" \
  --observable "trap energy 1.0 eV" \
  --observable "conductivity S/m" \
  --condition "303 K" \
  --condition "20 kV/mm" \
  --evidence "independent experiment measurement" \
  --output strategy.json
```

### Inspect mathematical contracts

```bash
python -m tsao_researcher math
python -m tsao_researcher math --contract uncertainty-budget --language both
```

### Initialize and verify a project

```bash
python -m tsao_researcher init \
  --name "Mechanism study" \
  --question "Which mechanism is identifiable?" \
  --research-type mechanistic \
  --output study

python -m tsao_researcher verify study
```

### Record external execution evidence

```bash
python -m tsao_researcher receipt record study/.tsao-research \
  --handoff computation/job.json \
  --engine Gaussian \
  --engine-version 16 \
  --command g16 \
  --command job.com \
  --exit-code 0 \
  --output computation/result.out \
  --started-at 2026-08-06T00:00:00Z \
  --finished-at 2026-08-06T00:10:00Z

python -m tsao_researcher receipt verify study/.tsao-research
```

### Export a deterministic capsule

```bash
python -m tsao_researcher capsule export study/.tsao-research \
  --output study.zip \
  --mode full
python -m tsao_researcher capsule verify study.zip
```

## 8. Python API

```python
from tsao_researcher.mathematical_contracts import get_mathematical_contract
from tsao_researcher.strategy import advise_computation_strategy

contract = get_mathematical_contract("decision-readiness", "en")
assert contract["solver_executed"] is False
assert contract["automatic_approval"] is False

strategy = advise_computation_strategy(
    "Can one measurement distinguish two mechanisms?",
    ["rate constant 1/s", "selectivity %"],
    ["350 K", "1 bar"],
    ["must retain contradictory evidence"],
    ["independent experiment"],
)
assert strategy["status"] == "advisory-only"
```

## 9. Testing and delivery gates

Permanent CI runs on:

- Ubuntu / Python 3.10
- Ubuntu / Python 3.13
- Windows / Python 3.12
- macOS / Python 3.12

The full Linux qualification includes:

```text
complete pytest regression
line and branch coverage
reverse-order and seeded-random-order tests
Ruff format and lint
Mypy strict typing
Bandit source security
strict pip-audit
19-schema validation
README and generated-artifact consistency
SBOM and repository-tree checksum
MkDocs strict build
mutation smoke suite
performance smoke suite
deterministic source release
wheel and sdist isolated installation
```

Run locally:

```bash
python -m pip install -r requirements-ci.lock
python -m pip install -e . --no-deps
python -m pytest -q -p hypothesis.extra.pytestplugin
python -m pytest -q -p hypothesis.extra.pytestplugin -p pytest_cov \
  --cov=tsao_researcher --cov-branch
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python scripts/performance_smoke.py
python scripts/run_mutation_smoke.py
python scripts/build_readme_facts.py --check
python scripts/generate_checksums.py --check
mkdocs build --strict
```

## 10. Performance meaning and boundary

Performance measurements cover the Python control layer:

- task routing;
- capability catalog loading and search;
- strategy construction;
- schema and archive validation;
- deterministic packaging.

They do **not** represent DFT, MD, FEM, CFD, process-simulation, GPU, MPI, or laboratory speedups. External engines require their own fixed inputs, hardware/software environment, convergence tolerances, licenses, and qualified benchmarks.

## 11. Complete conceptual visual atlas

### Research control and architecture

<table>
<tr><td><img src="docs/assets/ai/research_os_architecture.svg" alt="Research OS architecture"/></td><td><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="Multi-agent orchestration"/></td></tr>
<tr><td><img src="docs/assets/ai/progressive_routing_loading.svg" alt="Progressive routing loading"/></td><td><img src="docs/assets/ai/project_state_machine.svg" alt="Project state machine"/></td></tr>
<tr><td><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="Project ledgers provenance"/></td><td><img src="docs/assets/ai/research_production_pipeline.svg" alt="Research production pipeline"/></td></tr>
</table>

### Capability, evidence, and requirements

<table>
<tr><td><img src="docs/assets/ai/capability_landscape.svg" alt="Capability landscape"/></td><td><img src="docs/assets/ai/capability_implementation_levels.svg" alt="Capability implementation levels"/></td></tr>
<tr><td><img src="docs/assets/ai/original_requirements_coverage.svg" alt="Original requirements coverage"/></td><td><img src="docs/assets/ai/evidence_claim_graph.svg" alt="Evidence claim graph"/></td></tr>
<tr><td><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="Evidence citation integrity loop"/></td><td><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="Reproducibility quality gates"/></td></tr>
</table>

### Strategy, mathematics, and multiscale reasoning

<table>
<tr><td><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="First principles strategy ladder"/></td><td><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="Scientific method decision tree"/></td></tr>
<tr><td><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="Multiscale science pipeline"/></td><td><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="Multiscale case study"/></td></tr>
<tr><td><img src="docs/assets/ai/mathematical_contract_registry.svg" alt="Mathematical contract registry"/></td><td><img src="docs/assets/ai/decision_readiness_lattice.svg" alt="Decision readiness lattice"/></td></tr>
<tr><td><img src="docs/assets/ai/uncertainty_propagation_budget.svg" alt="Uncertainty propagation budget"/></td><td><img src="docs/assets/ai/multiscale_bridge_error_budget.svg" alt="Multiscale bridge error budget"/></td></tr>
</table>

### Scientific integrity and quantitative gates

<table>
<tr><td><img src="docs/assets/ai/scientific_passport_matrix.svg" alt="Scientific Passport matrix"/></td><td><img src="docs/assets/ai/evidence_maturity_ladder.svg" alt="Evidence maturity ladder"/></td></tr>
<tr><td><img src="docs/assets/ai/decision_readiness_gate.svg" alt="Decision readiness gate"/></td><td><img src="docs/assets/ai/active_evidence_learning_loop.svg" alt="Active evidence learning loop"/></td></tr>
<tr><td><img src="docs/assets/ai/quantity_dimension_contract.svg" alt="Quantity dimension contract"/></td><td><img src="docs/assets/ai/applicability_extrapolation_guard.svg" alt="Applicability extrapolation guard"/></td></tr>
<tr><td><img src="docs/assets/ai/evidence_conflict_resolution.svg" alt="Evidence conflict resolution"/></td><td><img src="docs/assets/ai/mechanism_identifiability_gate.svg" alt="Mechanism identifiability gate"/></td></tr>
<tr><td><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="Uncertainty quantification validation"/></td><td><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="Scientific integrity causality guard"/></td></tr>
</table>

### External execution, laboratory, writing, and release

<table>
<tr><td><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="Computation handoff boundary"/></td><td><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="Human approval boundary"/></td></tr>
<tr><td><img src="docs/assets/ai/laboratory_data_quality.svg" alt="Laboratory data quality"/></td><td><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="Scientific writing evidence chain"/></td></tr>
<tr><td><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="Scientific figure edit guard"/></td><td><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="Installation compatibility matrix"/></td></tr>
<tr><td><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="Supply chain release attestation"/></td><td></td></tr>
</table>

> These are AI-generated conceptual illustrations for repository documentation only. They do not represent experimental data, measured results, solver contours, trajectories, or completed external execution.

## 12. Repository layout

```text
.
├── tsao_researcher/
│   ├── router.py
│   ├── capabilities.py
│   ├── strategy.py
│   ├── mathematical_contracts.py
│   ├── state.py
│   ├── handoff.py
│   ├── receipts.py
│   └── capsule.py
├── scripts/
├── tests/
├── schemas/
├── workflows/
├── domain-packs/
├── docs/
├── examples/
├── README.md
├── README.zh-CN.md
├── VERSION
└── SHA256SUMS
```

## 13. Scientific and delivery boundary

A software gate can establish deterministic behavior, schema consistency, traceability, security posture, packaging reproducibility, and the absence of declared blockers. It cannot establish that a physical mechanism is true.

Final scientific acceptance still requires, as appropriate:

- qualified domain review;
- fixed external inputs and engine versions;
- convergence and sensitivity evidence;
- calibrated measurements and uncertainty;
- independent replication or validation;
- checksum-bound receipts and outputs.

**TsaoSciResearcher controls the scientific workflow. It does not impersonate the science that must still be executed and validated.**
