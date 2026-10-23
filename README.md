<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher logo" width="118" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>Evidence-first scientific strategy, mathematical contracts, guarded handoff, and validation control layer</strong></p>
  <p>Question → observables → model contract → evidence contract → guarded external execution → receipt → acceptance evidence</p>

[简体中文](README.zh-CN.md) · [Documentation](docs/index.md) · [Architecture](docs/ARCHITECTURE.md) · [Mathematical contracts](docs/MATHEMATICAL_CONTRACTS.md) · [Validation](docs/VALIDATION.md) · [Visual atlas](docs/VISUAL_ATLAS.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

## Project vision: questions, contracts and verifiable evidence

![Project vision: questions, contracts and verifiable evidence](docs/assets/vision-en.png)

> AI-generated conceptual illustration. The evidence triad E=(E+, E−, E0), weakest-gate G=min(g_i), and H=SHA256(bytes) summarize implemented contracts. The image is a vision and navigation aid, not computed research data or automatic scientific approval.



> **Release 0.7.4 · acceptance-hardened main** · Apache-2.0 · Python 3.10–3.13 · deterministic CLI and Python API

## 1. What this repository is

TsaoSciResearcher is a **scientific research control layer**. It helps turn an under-specified research question into a traceable, falsifiable and reviewable research strategy. The runtime performs deterministic routing, capability retrieval, scientific-quality checks, strategy construction, project-state management, checksum-bound external handoff, execution-receipt verification and reproducibility packaging.

It is **not** a DFT, quantum-chemistry, molecular-dynamics, CFD, FEM, process-simulation, HPC or laboratory solver. A strategy, equation, handoff file, PASS label or AI diagram never proves that a physical calculation or experiment occurred.

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
| JSON Schemas | **20** |
| Domain packs | **7** |
| Registered historical conceptual atlas assets | **38** |
| New localized vision images | **2** |

Acceptance evidence: [README audit](docs/README_AUDIT_REPORT.md), [capability matrix](docs/CAPABILITY_COVERAGE_MATRIX.md), [architecture mapping](docs/README_ARCHITECTURE_MAPPING.md), [mathematical contracts](docs/MATHEMATICAL_CONTRACTS.md), [mathematical registry schema](schemas/v2/mathematical-contract-registry.schema.json), [validation evidence](docs/VALIDATION_EVIDENCE.json), [HTML dashboard](docs/test-dashboard.html), and [SVG dashboard](docs/test-dashboard.svg).

> The localized vision is an **AI-generated conceptual illustration**. The 38 registered atlas assets are historical conceptual documentation; generated test dashboards summarize software evidence. Their roles are separate, and none is a substitute for measured scientific data.

## 2. Architecture and responsibility boundary

```mermaid
flowchart TD
    A["CLI / Python API"]
    B["Routing and strategy"]
    C["State and approval ledger"]
    D["Handoff and receipt"]
    E["Evidence and capsule"]
    A --> B
    A --> C
    C --> D
    D --> E
```

![Research operating architecture](docs/assets/ai/research_os_architecture.svg)

![Progressive routing and loading](docs/assets/ai/progressive_routing_loading.svg)

![Computation handoff boundary](docs/assets/ai/computation_handoff_boundary.svg)

A typical research flow is:

```text
scientific question
    ↓
decision-critical observable + unit + acceptance threshold
    ↓
state variables + governing principles + constraints
    ↓
minimum-sufficient falsifiable model
    ↓
evidence / applicability / identifiability / bridge gates
    ↓
qualified human review
    ↓
checksum-bound external handoff
    ↓
execution receipt + independently reviewable evidence
```

## Runtime guarantees and practical workflow

The runtime separates a useful research plan, a supplied execution record, verified local bytes, and independent scientific acceptance. These are distinct states in the code. `state.verify()` now invokes the real receipt verifier; `quality` requires a real `project_root` before it can report verified bidirectional local traceability.

| Entry point | What is checked | What the result establishes |
|---|---|---|
| `create_handoff()` | project, methods, scale, finite input inventory, file sizes and SHA-256 | a prepared external job contract |
| `record_receipt()` | ready registered handoff, current input bytes, argv, engine fields, timestamps, exit status, output files | a supplied execution declaration bound to retained input snapshots |
| `verify()` / `verify_receipts()` | legal event history, current output bytes, retained input snapshots, registry membership and approval bindings | local state and artifact integrity |
| `quality` / `check_evidence_traceability()` | registered claim text, reciprocal evidence links, local source locators and checksums, every referenced receipt's actual output binding | `LOCAL_ARTIFACT_LINKS_VERIFIED` when all checks succeed |
| `transition(..., "accepted")` | a fresh approval reference bound to this project's exact transition event | `DECLARED_NOT_IDENTITY_VERIFIED`; no authentication of an external person's identity |
| `capsule export --mode full` | complete deterministic inventory, file hashes, state and receipt verification | a portable integrity archive including retained input bytes |

### Install and upgrade

Python **3.10 or newer** is required by this repository; the permanent matrix exercises Linux 3.10/3.12/3.13 and Windows 3.12. Use an isolated environment outside the checkout so tooling and release inventories cannot contaminate one another:

```bash
python -m venv ../tsao-researcher-env
# POSIX shell; on Windows activate ../tsao-researcher-env/Scripts/Activate.ps1
. ../tsao-researcher-env/bin/activate
python -m pip install -r requirements-ci.lock
python -m pip install -e . --no-deps
python -m pip check
python -m tsao_researcher --version
```

The CI lock explicitly pins `certifi==2026.10.19` and `pip==26.2.0`; the resolved environment is audited again during CI. Researcher has no MCP runtime dependency. Legacy receipts without retained `input_snapshots`, or approvals without event/scope bindings, intentionally fail the stronger verifier. Preserve the old archive, reconstruct new declarations only from available original bytes and real review references, and keep the historical record; filling missing fields is not evidence that an old execution happened. An omitted engine version remains explicit `null`, never an invented version.

### Executable setup and handoff

This creates a **demonstration input and prepared handoff**, not a solver result:

```bash
python -m tsao_researcher init --name demo \
  --question "Which calculation would distinguish the candidate mechanisms?" \
  --output ./research-demo
python - <<'PY'
from pathlib import Path
from tsao_researcher.handoff import create_handoff
root = Path("research-demo/.tsao-research")
(root / "data/input.dat").write_text("demonstration input only\n", encoding="utf-8")
create_handoff(root, "computation/job.json",
    "Which calculation would distinguish the candidate mechanisms?",
    "energy difference", "quantum", ["DFT"], ["data/input.dat"],
    scale="electronic", evaluation_metrics=["energy difference in eV"],
    expected_outputs=["converged energy and method provenance"])
PY
python -m tsao_researcher verify ./research-demo
```

Run the chosen external engine separately, retain its real input/output/logs, and record the actual argv, software version, environment and times. The `receipt record` example in section 8 assumes those files already exist. `--command` is repeatable and represents an argument vector; it does not execute a shell command. Recheck `receipt verify` and `verify` before advancing state or exporting an archive.

### Input snapshots and byte integrity

For each handoff input $i$, the implementation verifies the pair

$$
I_i=\left(\operatorname{size}(B_i),\operatorname{SHA256}(B_i)\right),
\qquad S_i=\texttt{artifacts/input-snapshots/}\operatorname{SHA256}(B_i).
$$

`input_snapshots.py` compares the live input to the handoff manifest **before** creating the receipt, streams the copy, verifies the copied size/hash, rejects symbolic-link components, and refuses to replace an altered existing snapshot. Later receipt verification uses the retained snapshot. Editing a working input later does not rewrite the historical input associated with a prior receipt. Missing or altered snapshots fail verification. Successful receipts need nonempty checksum-verified outputs; failed executions remain explicitly failed and may have no output.

For output $j$, acceptance of the local byte binding requires

$$
\operatorname{size}(B_j)=s_j\ \land\
\operatorname{SHA256}(B_j)=h_j.
$$

A digest proves consistency of bytes against the recorded manifest. It cannot prove that an external engine produced them or that the reported physics is correct. Metadata capsules exclude raw `data`, `figures` and `artifacts`; full capsules include retained input snapshots. Choose the mode according to the evidence transfer required.

### Event chain, legal transitions and declared approvals

Each event includes its predecessor hash in the canonical body:

$$
h_i=\operatorname{SHA256}\!\left(\operatorname{canonicalJSON}(e_i\setminus\{\texttt{event\_hash}\})\right),
\qquad e_i[\texttt{previous\_event\_hash}]=h_{i-1}.
$$

Verification additionally requires an initialized `proposed` state, legal transition edges, matching previous/next state, chronological timezone-aware timestamps, matching project identity, and the final project head. Rehashing an illegal transition does not make it valid. The normal path is `proposed → planned → running → completed → checked → validated → accepted`; the implemented rejection/supersession edges remain available.

An approval ledger record binds project, scope, target state, transition event hash, timestamp and reference. Duplicate/orphan references, foreign records, revoked approvals, and non-boolean revocation flags are rejected. `accepted` requires fresh references for that transition. The local record is explicitly `DECLARED_NOT_IDENTITY_VERIFIED`; cryptographic identity verification and scientific sign-off remain outside this declaration API. The v16/v17 replay helpers similarly return `ACCEPTANCE_DECLARED_UNVERIFIED` or `SIGNED_RECEIPT_DECLARED_UNVERIFIED` when given positive boolean declarations.

### Real evidence resolution

Set `spec.project_root` in a `kind: "evidence-traceability"` quality request. The submitted claim text and evidence IDs must match `claims.jsonl`; each supporting evidence row in `evidence.jsonl` must link back to the claim. Local source kinds, locator, checksum and current bytes are resolved. An `execution-receipt` evidence role must point to an actual output of a referenced successful receipt, and **every** referenced receipt must bind supplied execution evidence:

$$
C\leftrightarrow E_i,\qquad
\forall R_k\in R,\ \exists E_i:\
\operatorname{path}(E_i)\in\operatorname{outputs}(R_k)
\land h(E_i)=h_{R_k}.
$$

Without `project_root`, the result is `WARN / UNVERIFIED_DECLARATION`, even if flags claim that sources or receipts were verified. Missing or inconsistent actual records produce `BLOCK`. Background, null, refuting or planned-handoff records cannot certify positive support. Web/paper declarations are not silently treated as checked local files. `LOCAL_ARTIFACT_LINKS_VERIFIED` means local identity and integrity; it is not automatic verification of the scientific assertion.

### Quantities, uncertainty and causal language

`compare_quantities()` supports the implemented pressure units `Pa`, `kPa`, `MPa`, `bar`, and temperature `K`. It checks dimensions and finite numeric values both before and after scale conversion:

$$
v_{\mathrm{SI}}=s_u v_u,\qquad
\operatorname{finite}(v_u)\land\operatorname{finite}(v_{\mathrm{SI}}).
$$

Booleans, numeric strings, integers outside the finite numeric range and conversion overflow are rejected. All implemented unit factors are integers, so integer inputs retain their exact distinctions during scaling and comparison: `2**53 Pa` is smaller than `(2**53 + 1) Pa`. Float inputs retain ordinary binary floating-point rounding; equality does not imply an uncertainty tolerance.

Public JSON/JSONL readers, quality requests, handoff/receipt verification, project registries and capsule manifests reject duplicate keys, non-finite numbers and nonzero decimal tokens that would silently become zero. YAML project metadata and compatibility validators apply the same numeric and explicit-key checks, while preserving ordinary YAML merge overrides:

$$
x\ne0\ \land\ \operatorname{fl}(x)=0
\quad\Longrightarrow\quad\text{reject the input}.
$$

True signed zero and representable subnormals such as `5e-324` remain valid. Choose appropriate units before serializing an out-of-range measurement, or retain it as explicitly documented textual source evidence; never replace it with a zero-valued measurement. A value already rounded to zero by the caller cannot reveal its original decimal token.

The mathematical registry's more general uncertainty and scale equations in section 3 are advisory contracts; the runtime does not execute Jacobian estimation, Bayesian inference, CFD or DFT from those formulas. Use covariance terms when errors are correlated, and justify local linearization before applying first-order propagation.

The deterministic causal guard scopes negation to the affected marker. “Cannot establish causality” cannot hide a separate affirmative “C causes D” assertion in the same text. Simplified/traditional Chinese markers, including `使得`, `导致/導致`, `驱动/驅動` and `决定/決定`, are handled. It still needs the declared design, comparison, temporal order and confounder controls; this guard is not a general natural-language proof engine.

## 3. Schema-backed mathematical contracts

The `math` command exposes eight stable bilingual contracts. The payload is now validated against a packaged Draft 2020-12 Schema before it is returned.

```bash
python -m tsao_researcher math
python -m tsao_researcher math --schema
python -m tsao_researcher math --contract decision-readiness --language en
python -m tsao_researcher math --contract quantity-dimension --language zh-CN
python -m tsao_researcher math --contract uncertainty-budget --output contract.json
python scripts/validate_mathematical_contracts.py --check
```

Every contract response fixes the truth boundary:

```json
{
  "schema_version": "1.0",
  "schema_id": "https://sunhaojun22.github.io/TsaoSciResearcher/schemas/v2/mathematical-contract-registry.schema.json",
  "advisory_only": true,
  "solver_executed": false,
  "automatic_approval": false
}
```

The canonical Schema is [`schemas/v2/mathematical-contract-registry.schema.json`](schemas/v2/mathematical-contract-registry.schema.json). A byte-identical package mirror is shipped under `tsao_researcher/data/schemas/` so installed CLI consumers can validate the same contract offline.

![Mathematical contract schema pipeline](docs/assets/ai/mathematical_contract_schema_pipeline.svg)

### 3.1 Capability-ranking abstraction

$$
S(c\mid q,o,e)=w_qR(q,c)+w_oR(o,c)+w_eM(e,c)-w_xC(c)
$$

- $c$: candidate capability
- $q$: scientific question
- $o$: decision-critical observable
- $e$: declared evidence context
- $C(c)$: conflict or exclusion penalty

Use this as a decomposition of deterministic routing logic, not as a fitted statistical model. A method should be relevant to the question, able to produce the requested observable, compatible with the evidence, and not excluded by negative semantics.

### 3.2 Quantity, unit and dimension contract

$$
x=(v,u,d),\qquad d_{\mathrm{left}}=d_{\mathrm{right}}
$$

A quantitative comparison should identify value $v$, unit $u$ and physical dimension $d$. Missing units require review. Incompatible dimensions block the comparison.

### 3.3 Applicability and extrapolation

$$
r_{\mathrm{extra}}=
\frac{d(x,\mathcal A)}{\max(s_{\mathcal A},\varepsilon)}
$$

Here $x$ is the target condition, $\mathcal A$ is the declared applicability domain and $s_{\mathcal A}$ is a characteristic domain scale. The farther the transfer, the stronger the evidence and uncertainty inflation must become. The runtime does not fabricate a numerical distance when data are absent.

### 3.4 Evidence triad and conflict ledger

$$
E=(E_+,E_-,E_0),\qquad
\kappa=\mathbf 1[E_+\neq\varnothing\land E_-\neq\varnothing]
$$

Supporting, challenging and unresolved evidence stay separate. Contradictory evidence is preserved rather than silently averaged into a positive conclusion.

### 3.5 Mechanism and parameter identifiability

$$
D_{ij}(O,C)>\tau
\qquad\text{or}\qquad
\operatorname{rank}(J_\theta)=p
$$

Mechanism selection requires discriminating observables. Unique parameter claims require sufficient sensitivity rank. Numerical Jacobian construction remains an external analysis task.

### 3.6 Decision-observable uncertainty budget

$$
\Sigma_y\approx
J\Sigma_\theta J^{\mathsf T}
+\Sigma_{\mathrm{num}}
+\Sigma_{\mathrm{sample}}
+\Sigma_{\mathrm{model}}
+\Sigma_{\mathrm{transfer}}
$$

Uncertainty must reach the actual acceptance observable. Parameter, numerical, sampling, model-form and scale-transfer uncertainty must remain traceable instead of being collapsed into an undocumented confidence score.

### 3.7 Multiscale bridge error budget

$$
U_{\mathrm{bridge}}^2=
U_{\mathrm{source}}^2+
U_{\mathrm{mapping}}^2+
U_{\mathrm{closure}}^2+
U_{\mathrm{target}}^2
$$

This quadrature requires mutually uncorrelated standard-uncertainty contributions expressed in the same output units. Correlated contributions require their cross-covariance terms; first-order propagation is only a local linear approximation. A microscopic result cannot jump directly to an engineering conclusion. Each bridge needs measurable bridge variables, mapping assumptions, closure validation and target-scale acceptance evidence.

### 3.8 Conservative decision readiness

$$
G=\min\left(
 g_{\mathrm{quantity}},
 g_{\mathrm{applicability}},
 g_{\mathrm{evidence}},
 g_{\mathrm{identifiability}},
 g_{\mathrm{bridge}}
\right)
$$

The weakest mandatory gate controls readiness:

```text
BLOCK < REVIEW < PASS
```

A software `PASS` means that no declared software blocker remains. It is not physical proof and cannot bypass qualified human review.

![Mathematical contract registry](docs/assets/ai/mathematical_contract_registry.svg)
![Decision readiness lattice](docs/assets/ai/decision_readiness_lattice.svg)
![Uncertainty propagation budget](docs/assets/ai/uncertainty_propagation_budget.svg)
![Multiscale bridge error budget](docs/assets/ai/multiscale_bridge_error_budget.svg)

Detailed bilingual interpretation: [docs/MATHEMATICAL_CONTRACTS.md](docs/MATHEMATICAL_CONTRACTS.md).

## 4. Scientific model-reconstruction strategy

TsaoSciResearcher selects methods from the decision physics rather than from a fashionable solver name.

A generic state model is:

$$
\dot{x}=f(x,u,\theta)+\epsilon_{\mathrm{model}},
\qquad
y=h(x,\theta)+\epsilon_{\mathrm{measurement}}
$$

A strategy should declare:

1. state variables $x$, controls $u$, and parameters $\theta$;
2. decision observable $y$ and acceptance threshold;
3. conserved quantities, reservoirs, boundary and initial conditions;
4. the minimum model able to falsify the candidate mechanism;
5. validation, uncertainty and escalation rules.

For a mass-specific quantity $\phi$ in a fixed control volume, with density $\rho$, total outward flux $\mathbf J_\phi$ (advective plus diffusive), and volumetric source $s_\phi$:

$$
\frac{\mathrm d}{\mathrm dt}\int_{\Omega}\rho\phi\,\mathrm dV
+\int_{\partial\Omega}\mathbf J_\phi\cdot\mathbf n\,\mathrm dA
=\int_{\Omega}s_\phi\,\mathrm dV
$$

This equation does not imply that a mesh, constitutive model or solver run exists. It defines what must be declared before a CFD, FEM, transport or process handoff can be considered scientifically interpretable.

### Minimum-sufficient method ladder

| Problem class | Start with | Escalate when |
|---|---|---|
| electronic structure / defects / interfaces | converged cluster or periodic DFT strategy | functional, finite-size or reference-state sensitivity matters |
| reaction mechanism / selectivity | pathway energetics + microkinetic skeleton | pathways, solvent/dynamics or transport remain unresolved |
| conformation / free energy | ensemble MD/MC strategy + convergence estimator | sampling or force-field evidence is inadequate |
| morphology / phase evolution | scaling / SCFT / CGMD / DPD / phase-field strategy | mapping or closure fails |
| flow / heat / mass transfer | analytical / control-volume / reduced model | geometry, instability or closure requires CFD/multiphysics |
| mechanics / fracture | reduced mechanics or FEM strategy | constitutive non-identifiability or localization dominates |
| reaction engineering | mass/energy balances + kinetics/population model | RTD, mixing or plant-data coupling is decisive |
| mixed multiscale problem | lowest-cost falsifiable model | a validated bridge variable justifies escalation |

![First-principles strategy ladder](docs/assets/ai/first_principles_strategy_ladder.svg)
![Scientific method decision tree](docs/assets/ai/scientific_problem_method_decision_tree.svg)
![Multiscale science pipeline](docs/assets/ai/multiscale_science_pipeline.svg)

## 5. Scientific Passport and integrity gates

A generated strategy carries structured declarations for model assumptions, evidence maturity, uncertainty, applicability and cross-scale transfer.

Useful abstractions include:

$$
\mathcal P=
\{M,E,U,A,I,B,V,F\}
$$

where $M$ is the model contract, $E$ evidence, $U$ uncertainty, $A$ applicability, $I$ identifiability, $B$ bridge contract, $V$ validation and $F$ falsification.

The strategy remains advisory even when every software gate is green.

![Scientific Passport matrix](docs/assets/ai/scientific_passport_matrix.svg)
![Evidence maturity ladder](docs/assets/ai/evidence_maturity_ladder.svg)
![Decision readiness gate](docs/assets/ai/decision_readiness_gate.svg)
![Active evidence loop](docs/assets/ai/active_evidence_learning_loop.svg)
![Quantity and dimension contract](docs/assets/ai/quantity_dimension_contract.svg)
![Applicability extrapolation guard](docs/assets/ai/applicability_extrapolation_guard.svg)
![Evidence conflict resolution](docs/assets/ai/evidence_conflict_resolution.svg)
![Mechanism identifiability gate](docs/assets/ai/mechanism_identifiability_gate.svg)
![Uncertainty validation](docs/assets/ai/uncertainty_quantification_validation.svg)
![Scientific integrity causality guard](docs/assets/ai/scientific_integrity_causality_guard.svg)

## 6. Acceptance strategy and evidence scope

The repository supports three validation scopes:

- `preflight`: current checkout checks only; CI-only gates remain explicit `NOT_RUN`/`PARTIAL`.
- `current-tree`: a fresh externally attested end-to-end CI run bound to the tested commit.
- `composite`: a pinned exact-tree full-repository baseline plus a SHA-256-bound focused current-change regression.

The checked-in record now uses **preflight** evidence: it binds the current source digest but leaves full CI qualification **PARTIAL** until an external run produces its attestation. The historical composite baseline and focused Schema/CLI records remain references, not proof of the changed tree.

```text
validation_scope = preflight
status = PARTIAL
current_end_to_end_ci = NOT_RUN until externally attested
```

`SHA256SUMS` records a recomputed complete-checkout digest in preflight mode. Composite mode instead explicitly defers a new whole-tree digest. Neither scope permits copying an old PASS onto changed code.

See [validation evidence](docs/VALIDATION_EVIDENCE.json), [baseline record](docs/VALIDATION_BASELINE.json), and [focused regression](docs/CURRENT_CHANGE_REGRESSION.json).

![Reproducibility quality gates](docs/assets/ai/reproducibility_quality_gates.svg)
![Compatibility matrix](docs/assets/ai/installation_compatibility_matrix.svg)
![Supply-chain attestation](docs/assets/ai/supply_chain_release_attestation.svg)

## 7. Core CLI

```bash
python -m pip install -r requirements-ci.lock
python -m pip install -e . --no-deps
python -m pip check

python -m tsao_researcher --version
python -m tsao_researcher route "run an actual DFT calculation"
python -m tsao_researcher search "molecular dynamics" --limit 3
python -m tsao_researcher quality examples/scientific-quality-check.json
python -m tsao_researcher strategy \
  "Can two mechanisms be discriminated?" \
  --observable "rate constant 1/s" \
  --condition "350 K" \
  --evidence "independent measurement"
python -m tsao_researcher math --schema
python -m tsao_researcher math --contract decision-readiness --output contract.json
python scripts/validate_mathematical_contracts.py --check
```

## 8. External execution boundary

TsaoSciResearcher prepares and verifies evidence around execution; it does not impersonate the engine.

```text
validated strategy
    ↓
checksum-bound handoff
    ↓
external engine / instrument / laboratory
    ↓
user-supplied receipt + output hashes
    ↓
receipt verification
    ↓
qualified scientific acceptance
```

![Project state machine](docs/assets/ai/project_state_machine.svg)
![Project ledgers and provenance](docs/assets/ai/project_ledgers_provenance.svg)
![Evidence claim graph](docs/assets/ai/evidence_claim_graph.svg)
![Evidence citation integrity](docs/assets/ai/evidence_citation_integrity_loop.svg)
![Human approval boundary](docs/assets/ai/human_approval_acceptance_boundary.svg)

Example receipt workflow:

```bash
python -m tsao_researcher receipt record . \
  --handoff computation/job.json \
  --engine external-engine \
  --engine-version 1.0 \
  --command engine \
  --command run \
  --exit-code 0 \
  --output computation/result.dat \
  --started-at 2026-08-07T01:00:00Z \
  --finished-at 2026-08-07T01:10:00Z

python -m tsao_researcher receipt verify .
```

## 9. Reproducibility

```bash
python -m tsao_researcher capsule export . --mode metadata --output project-metadata.zip
python -m tsao_researcher capsule export . --mode full --output project-full.zip
python -m tsao_researcher capsule verify project-full.zip
```

A reproducibility capsule preserves software state and evidence relationships. It does not establish physical truth by itself.

## 10. Quality and testing

The permanent quality stack includes:

- Linux Python 3.10/3.12/3.13 and Windows Python 3.12 compatibility;
- complete regression and line/branch coverage;
- reverse and seeded-random test ordering;
- Ruff format/lint and strict Mypy;
- Bandit and dependency vulnerability audit;
- mutation testing and bounded performance smoke tests;
- Schema validation, deterministic SBOM and documentation build;
- byte-identical source releases and isolated wheel/sdist installation.

Historical baselines remain explicitly tied to their original source. Current test counts, coverage, mutation results and security outcomes must come from the actual current-SHA CI artifacts. The release floors require **95% statement-line coverage, 90% branch coverage, 95% combined coverage, and 24 killed critical mutants**. All three coverage measures are computed from their own integer counts:

$$
\begin{aligned}
C_\ell&=100\frac{n_\ell}{N_\ell}\qquad(N_\ell>0),\\
C_b&=\begin{cases}100\frac{n_b}{N_b},&N_b>0\\100,&N_b=0\end{cases},\\
C_{\mathrm{combined}}&=100\frac{n_\ell+n_b}{N_\ell+N_b}.
\end{aligned}
$$

Here $n_\ell,N_\ell$ are covered and total executable statement lines; $n_b,N_b$ are covered and total branches. The existing `line_percent` field now records the actual statement-line ratio; `combined_percent` explicitly records the separate combined measure. For example, 94/100 statement lines and 100/100 branches yield 97% combined coverage but still **fail** the statement-line floor. Historical entries are preserved; new quality histories retain the explicit combined field when supplied. Publication attestations bind the complete quality and history artifact bytes.

## 11. Complete conceptual atlas

The following paths are machine-checked by `scripts/build_readme_facts.py`; every SVG contains `<title>` and `<desc>` accessibility metadata.

<details>
<summary>Show all 38 repository-local conceptual figures</summary>

![Research OS](docs/assets/ai/research_os_architecture.svg)
![Multi-agent orchestration](docs/assets/ai/multi_agent_orchestration.svg)
![Evidence claim graph](docs/assets/ai/evidence_claim_graph.svg)
![Multiscale science pipeline](docs/assets/ai/multiscale_science_pipeline.svg)
![Reproducibility quality gates](docs/assets/ai/reproducibility_quality_gates.svg)
![Computation handoff](docs/assets/ai/computation_handoff_boundary.svg)
![Project state machine](docs/assets/ai/project_state_machine.svg)
![Capability landscape](docs/assets/ai/capability_landscape.svg)
![Requirements coverage](docs/assets/ai/original_requirements_coverage.svg)
![Capability implementation levels](docs/assets/ai/capability_implementation_levels.svg)
![Progressive routing](docs/assets/ai/progressive_routing_loading.svg)
![Project ledgers](docs/assets/ai/project_ledgers_provenance.svg)
![Evidence citation loop](docs/assets/ai/evidence_citation_integrity_loop.svg)
![Research production pipeline](docs/assets/ai/research_production_pipeline.svg)
![Installation compatibility](docs/assets/ai/installation_compatibility_matrix.svg)
![Supply-chain attestation](docs/assets/ai/supply_chain_release_attestation.svg)
![First-principles strategy](docs/assets/ai/first_principles_strategy_ladder.svg)
![Method decision tree](docs/assets/ai/scientific_problem_method_decision_tree.svg)
![Uncertainty validation](docs/assets/ai/uncertainty_quantification_validation.svg)
![Causality guard](docs/assets/ai/scientific_integrity_causality_guard.svg)
![Laboratory data quality](docs/assets/ai/laboratory_data_quality.svg)
![Writing evidence chain](docs/assets/ai/scientific_writing_evidence_chain.svg)
![Scientific figure edit guard](docs/assets/ai/scientific_figure_edit_guard.svg)
![Human approval boundary](docs/assets/ai/human_approval_acceptance_boundary.svg)
![Multiscale case study](docs/assets/ai/polymer_multiscale_case_study.svg)
![Scientific Passport matrix](docs/assets/ai/scientific_passport_matrix.svg)
![Evidence maturity ladder](docs/assets/ai/evidence_maturity_ladder.svg)
![Decision readiness gate](docs/assets/ai/decision_readiness_gate.svg)
![Active evidence loop](docs/assets/ai/active_evidence_learning_loop.svg)
![Quantity dimension contract](docs/assets/ai/quantity_dimension_contract.svg)
![Applicability guard](docs/assets/ai/applicability_extrapolation_guard.svg)
![Evidence conflict](docs/assets/ai/evidence_conflict_resolution.svg)
![Mechanism identifiability](docs/assets/ai/mechanism_identifiability_gate.svg)
![Mathematical contract registry](docs/assets/ai/mathematical_contract_registry.svg)
![Decision readiness lattice](docs/assets/ai/decision_readiness_lattice.svg)
![Uncertainty propagation budget](docs/assets/ai/uncertainty_propagation_budget.svg)
![Multiscale bridge error budget](docs/assets/ai/multiscale_bridge_error_budget.svg)
![Mathematical contract schema pipeline](docs/assets/ai/mathematical_contract_schema_pipeline.svg)

</details>

## 12. Repository layout

```text
.
├── tsao_researcher/          # deterministic runtime
├── schemas/                  # contract and evidence Schemas
├── capabilities/             # validated capability catalog
├── workflows/                # research workflow contracts
├── domain-packs/             # domain-specific capability packs
├── scripts/                  # validation, packaging and evidence tooling
├── tests/                    # regression and contract tests
├── examples/                 # canonical machine-readable examples
├── docs/                     # architecture, evidence, reports and visual atlas
├── README.md
├── README.zh-CN.md
├── VERSION
└── SHA256SUMS
```

## 13. Scientific and engineering disclaimer

Passing software checks means that the declared software contracts are internally consistent at the stated evidence scope. It does **not** certify a scientific hypothesis, external solver result, instrument measurement, medical conclusion, legal conclusion or safety decision.

External computations and experiments must be independently executed, recorded and reviewed. TsaoSciResearcher keeps the boundary explicit rather than fabricating a run.

## 14. License

Apache-2.0.


## Seven-repository source-pinned acceptance

The [complete parallel repair prompt](docs/SEVEN_REPOSITORY_ACCEPTANCE_PROMPT.md) assigns **one repository to each child agent**, with three child slots rotated across seven repositories. The [workflow](.github/workflows/six-repository-acceptance.yml) retains its historical filename but is displayed as **Seven repository acceptance**. It tests all seven repositories with a matrix limit of seven, after their real baseline gates. The [plan](.github/acceptance/repositories.json) pins six external main SHAs and resolves Researcher's `SELF` to the workflow revision.

Phase two depends on all phase-one jobs. Every repository requires two independent v2 segments, each with at least 10,800 seconds of successful, nonempty test-process wall time:

$$
t_{r,p}=\sum_{k\in\mathcal S_{r,p}}\frac{m_{k,\mathrm{end}}-m_{k,\mathrm{start}}}{10^9}
\ge 10{,}800\ \mathrm{s},\qquad
T_r=t_{r,1}+t_{r,2}\ge 21{,}600\ \mathrm{s}.
$$

Here $m$ is a monotonic nanosecond clock. Each command is subject to a 1,800-second timeout; the independent verifier rejects recorded intervals above 1,801 seconds. UTC and monotonic elapsed intervals must agree within one second. Only completed canonical command cycles count. Installation, queueing, sleeps, failed tests and missing witnesses cannot contribute accepted time.

[The executor](.github/acceptance/regression_segment.py) checks the exact clean checkout, dependency fingerprint and sole remote `main` at the start, at the end and periodically. [The verifier](.github/acceptance/verify_segments.py) requires **14 receipts** with globally unique segment/iteration IDs, exact run and attempt identities, source and orchestration SHAs, tree hashes, absolute source/output paths, argv and interpreter identities, original logs/JUnit/event hashes, nonoverlapping phase intervals, and phase-two binding to the phase-one receipt hash. Changing the source invalidates qualification for the old source; it never transfers elapsed time to a different commit.

### Pytest subtests and original reports

Pytest's [documented JUnit implementation](https://docs.pytest.org/en/stable/_modules/_pytest/junitxml.html) can count successful subtests without separate `<testcase>` elements; multiple skipped subtests may share a parent element. See the [upstream issue](https://github.com/pytest-dev/pytest-subtests/issues/83). The controller keeps the raw XML and records collection/setup/call/teardown/subtest events using only public hooks in [the observer](.github/acceptance/tsao_acceptance_pytest_events.py). It does not alter test selection, outcomes or XML totals.

For a failure-free pytest session, the verifier reconciles:

$$
N_{\mathrm{JUnit}}=N_{\mathrm{ordinary\ call\ pass}}+N_{\mathrm{subtest\ pass}}+N_{\mathrm{all\ skip\ events}},
\qquad
N_{\mathrm{leaves}}=N_{\mathrm{ordinary\ cases}}+N_{\mathrm{collection\ skips}}.
$$

Ordinary tests, passed subtests, skipped subtests and collection skips are recorded separately. Any collection/setup/call/teardown/subtest failure or error, nonzero process exit, incomplete lifecycle or XML/event mismatch fails closed. Every Python command explicitly loads the observer from the control checkout; the observed interpreter must match the command (or the recorded `uv` target interpreter for Aspen). Vitest keeps strict summary-to-leaf reconciliation. No event witness means no Python segment qualification.

```bash
python -m unittest discover -s .github/acceptance -p test_regression_segment.py -v
```

These controller tests include real subprocess pass/failure/subtest fixtures and synthetic fourteen-receipt tamper tests. Fixture timestamps are **not six-hour evidence**. A short executor run is `SMOKE_ONLY`; v1 receipts and incomplete evidence cannot yield `SEGMENTED_REGRESSION_COMPLETE`. The actual Actions result and preserved raw artifacts are the status record. This is segmented Linux software regression; cross-platform release gates, uninterrupted service availability and external scientific acceptance retain their separate meanings.
