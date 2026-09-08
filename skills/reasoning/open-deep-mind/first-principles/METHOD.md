# First Principles Engine / 第一性原理思考

## Purpose

First Principles Thinking decomposes a problem until the remaining starting points are explicit and justified for the current domain, scale, purpose, and theory level, then reconstructs candidate explanations or solutions from those starting points.

It is not:

- ignoring prior knowledge;
- assuming every convention is false;
- claiming zero assumptions;
- equating “physics-based” with exact;
- using decomposition without reconstruction;
- using analogy or authority as proof.

The method is:

\[
\text{decompose}
\rightarrow
\text{classify}
\rightarrow
\text{verify}
\rightarrow
\text{model}
\rightarrow
\text{reconstruct}
\rightarrow
\text{derive/test}
\rightarrow
\text{decide/update}
\]

---

## 1. Relative firstness

Every claimed principle must state:

```text
Domain:
Scale:
Purpose:
Theory level:
Conditions:
Date/version:
```

Examples:

- mass conservation may be foundational for a process model;
- quantum mechanics may be foundational for an electronic-structure model;
- a constitutional right may be a hard constraint in a policy analysis;
- a user's preference is a value input, not a law;
- a fitted constitutive equation may close a continuum model but is not a fundamental law.

A principle may be first **within a model** while still depending on deeper theories.

---

## 2. Proposition ledger

Classify before reasoning.

| Code | Type | Acceptance question |
|---|---|---|
| `D` | Definition | Is the meaning explicit and non-circular? |
| `O` | Observation | Is it measured or sourced under stated conditions? |
| `L` | Law / invariant | Is it independently supported in this domain? |
| `C` | Constraint | Is it truly non-negotiable, and who can change it? |
| `A` | Assumption | Is it necessary, testable, and sensitivity-audited? |
| `E` | Empirical closure / estimate | What data, fit, proxy, heuristic, or learned model produced it? |
| `V` | Value | Whose objective, duty, or risk tolerance is it? |
| `U` | Unknown | Could resolving it change the decision? |

Add:

- status: verified / supported / plausible / contested / unknown;
- scope;
- source;
- confidence;
- dependencies;
- falsifier or revision condition;
- owner;
- review date.

Use [`../assets/claim-ledger-template.md`](../assets/claim-ledger-template.md) and [`../assets/claim-ledger.schema.json`](../assets/claim-ledger.schema.json).

---

## 3. The P9 protocol

### P1 — Delete, modify, or justify the requirement

Test the requirement before optimizing it.

1. Remove it mentally.
2. Observe which outcome, duty, or constraint fails.
3. Verify the source of the requirement.
4. Delete, modify, retain, or mark it for verification.
5. Record who has authority to change it.

Do not delete safety margins, legal obligations, ethical protections, data-integrity controls, or physical constraints unless their status is verified and a justified replacement exists.

**Output:** requirement ledger with `delete / modify / retain / verify`.

---

### P2 — Define the real outcome and boundary

Replace solution-shaped statements with outcomes.

Bad:

> We need a microservice, an AI model, a new reactor internals design, or a new department.

Better:

> The system must achieve a specified function under explicit latency, reliability, safety, cost, maintenance, and validity conditions.

Specify:

- target outcome;
- measurable success and failure;
- system boundary;
- spatial/organizational scale;
- time horizon;
- stakeholders;
- reversible versus irreversible choices;
- baseline and do-nothing option.

**Red blocker:** a preferred technology is treated as the outcome itself.

---

### P3 — Expose assumptions and proposition types

Create the full ledger. Challenge:

- technical assumptions;
- historical artifacts;
- resource assumptions;
- market or behavioral assumptions;
- measurement assumptions;
- legal assumptions;
- ethical assumptions;
- stationarity assumptions;
- scale and boundary assumptions;
- empirical closures.

For each assumption:

```text
Why is it needed?
What evidence supports it?
What happens if it is false?
Can it be tested cheaply?
Can the design avoid depending on it?
```

Prioritize assumptions by a risk score such as:

\[
R_i = P(A_i\text{ false})\, I_i\, D_i
\]

where \(I_i\) is impact and \(D_i\) is difficulty of detecting failure. Use qualitative bands when numerical probabilities are unjustified.

---

### P4 — Decompose to irreducibles

Use a dependency graph rather than endless “why” questions.

A node may stop decomposing only when it is one of:

1. an explicit definition;
2. a direct observation with uncertainty;
3. a domain law or invariant;
4. a verified hard constraint;
5. an explicit value or duty;
6. an unknown that cannot be resolved within the decision window.

Apply only the decompositions relevant to the task:

- functional;
- causal;
- material/component;
- temporal;
- cost;
- information-flow;
- stakeholder;
- scale/hierarchy.

Check independence: two “fundamentals” that derive from the same hidden assumption are not independent.

**Output:** dependency graph plus explicit stopping reasons.

---

### P5 — Qualify foundations

A candidate foundation must pass:

| Test | Question |
|---|---|
| Type | Is it D, O, L, C, V, or unresolved U? |
| Scope | Where and when does it hold? |
| Independence | Is it merely inherited from another claim? |
| Evidence | Is support appropriate to the claim? |
| Counterexample | Is there a known case that breaks it? |
| Sensitivity | Would changing it alter the result? |
| Authority | If a constraint, who can waive or revise it? |
| Value transparency | If normative, whose value is it? |

Classify:

- **hard foundation** — violating it makes the solution incoherent or infeasible;
- **working foundation** — justified enough for current action, but revisable;
- **design preference** — useful, not compulsory;
- **unknown** — must be tested, bounded, or made irrelevant.

A Foundation Charter from First Philosophy may supply these items, but it does not eliminate the need to verify task-specific facts.

---

### P6 — Build the model

Choose a model class that matches the question.

#### Constraint model

\[
\mathcal X_f=\{x\mid h(x)=0,\ g(x)\le 0\}
\]

Use for feasibility and design-space pruning.

#### Causal model

\[
X_i=f_i(\operatorname{Pa}_i,U_i)
\]

Use for interventions and counterfactuals.

#### Dynamic model

\[
\dot{\mathbf x}=\mathbf f(\mathbf x,\mathbf u,\boldsymbol\theta,t)
\]

Use for evolution, feedback, delay, and control.

#### Conservation model

\[
\frac{\partial q}{\partial t}+\nabla\cdot \mathbf J_q=s_q
\]

Use for mass, energy, momentum, charge, probability, or a justified analogue.

#### Optimization model

\[
x^\star=\arg\min_{x\in\mathcal X_f}J(x;V)
\]

Make value dependence \(V\) explicit.

#### Bayesian model

\[
p(\theta\mid y)\propto p(y\mid\theta)p(\theta)
\]

Use when evidence updating and uncertainty are central.

#### Argument model

```text
Premises + inference rule + defeaters -> conclusion
```

Use for conceptual, legal, ethical, strategic, or mixed claims.

Every model must state:

```text
purpose
states / controls / parameters
relations or governing equations
constraints
initial and boundary conditions where relevant
assumptions and empirical closures
observation model
error/discrepancy model
validity domain
falsifiers
```

Machine-readable model contract: [`model-contract.schema.json`](model-contract.schema.json).

---

### P7 — Reconstruct alternatives

Build upward from accepted foundations only.

Start with the **minimum sufficient system**:

\[
S_0=\min\{S:S\text{ satisfies all hard foundations}\}
\]

Add a component only if it earns its complexity:

\[
\Delta U_i>\Delta C_{\text{complexity},i}+\Delta R_{\text{failure},i}
\]

Generate structurally distinct options when practical:

1. **minimal** — fewest components or commitments;
2. **balanced** — best expected trade-off;
3. **frontier** — higher upside with explicitly higher uncertainty;
4. **do nothing / preserve option** — when delay or learning has value.

Morphological construction may be used:

| Function/parameter | Option A | Option B | Option C |
|---|---|---|---|

Reject hard-constraint violations before scoring.

---

### P8 — Derive, trace, falsify, and stress-test

This stage intentionally combines derivation and adversarial testing so the P9 protocol remains exactly nine stages.

#### P8A — Derive and trace

For every material conclusion:

```text
Foundation IDs
-> inference/model
-> intermediate result
-> conclusion
-> decision implication
```

Quantitative checks:

- units and dimensions;
- orders of magnitude;
- limiting cases;
- conservation residuals;
- parameter provenance;
- numerical convergence;
- uncertainty propagation;
- sensitivity;
- identifiability;
- domain shift;
- model discrepancy.

Qualitative checks:

- no equivocation;
- no missing premise;
- causal role stated;
- alternative explanation considered;
- conclusion strength does not exceed evidence.

#### P8B — Falsify and stress-test

Attack the leading model with the strongest relevant tests:

- boundary cases;
- inversion;
- adversarial examples;
- null model;
- counterfactual intervention;
- pre-mortem;
- FMEA or fault-tree logic;
- out-of-distribution test;
- alternative objective function;
- stakeholder reversal;
- model-class comparison.

For each major conclusion record:

```text
Falsifier:
Strongest rival:
Most likely failure mode:
Early warning signal:
Fallback:
Review trigger:
```

Do not call a model validated merely because it reproduces data used to construct or calibrate it.

---

### P9 — Decide, act, monitor, and update

Choose the next action by balancing:

- expected benefit;
- downside and irreversibility;
- information value;
- cost of delay;
- robustness;
- legal, ethical, and safety constraints.

Value of information can be represented as:

\[
\operatorname{VOI}
=
\mathbb E[\max_a U(a,\theta)\mid\text{new information}]
-
\max_a\mathbb E[U(a,\theta)]
\]

Select the smallest experiment or action that most reduces decision-relevant uncertainty.

Record:

- decision;
- rationale;
- foundation trace;
- assumptions and closures;
- rejected options;
- monitoring variables;
- next discriminating action;
- review trigger;
- reversal condition.

Machine-readable decision contract: [`decision-record.schema.json`](decision-record.schema.json).

---

## 4. Scale bridges

A cross-scale chain must never be written as if each arrow were automatic.

\[
\text{lower-scale state}
\xrightarrow[\text{uncertainty}]{\text{coarse-graining / closure}}
\text{effective variables}
\xrightarrow[\text{validation}]{\text{model}}
\text{higher-scale behavior}
\]

For every bridge, state:

1. mapping variables;
2. closure assumption;
3. lost information;
4. calibration source;
5. uncertainty propagation;
6. validation domain;
7. failure conditions.

Examples:

- electronic structure → force field;
- force field → molecular ensemble;
- molecular ensemble → constitutive relation;
- constitutive relation → component performance;
- component performance → process or organizational outcome.

---

## 5. First-principles strictness ladder

| Level | Name | Minimum requirement |
|---|---|---|
| F0 | Rhetorical | “Think differently” with no auditable foundations |
| F1 | Fact–constraint | explicit facts, costs, resources, and hard constraints |
| F2 | Mechanism–causal | causal graph or mechanism chain |
| F3 | Governing-equation | conservation/dynamics plus boundary and closure |
| F4 | Formal/from-scratch | formal proof, ab initio, or foundational computation with explicit approximations |
| F5 | Meta-foundational | examination of why the starting principles qualify as foundations |

Use the level appropriate to the task. Do not claim F4 rigor for an F1 decomposition.

---

## 6. Recursion and method rotation

Each revision pass must target a specific weakness.

```text
Pass 1: clarify foundations and build baseline
Pass 2: attack highest-risk assumption
Pass 3: construct strongest rival model
Pass 4: change method class or scale
Pass 5: pre-mortem and decision calibration
```

If score improvement is less than two points twice:

- change the framing;
- change the model class;
- seek discriminating evidence;
- or stop and report underdetermination.

Repeating the same argument with more words is not refinement.

---

## 7. Output format

```markdown
# First Principles Analysis: [question]

## 1. Requirement verdict
| Requirement | Source | Delete/modify/retain/verify | Reason |

## 2. Outcome and boundary
- Outcome:
- Success:
- Failure:
- Boundary:
- Scale/time:
- Baseline:

## 3. Proposition ledger
| ID | Type | Claim | Status | Scope | Source | Falsifier |

## 4. Decomposition
[dependency graph or hierarchy]

## 5. Accepted foundations
- Hard:
- Working:
- Values:
- Unknowns:

## 6. Model contract
- Model class:
- Variables:
- Relations/equations:
- Parameters/provenance:
- IC/BC/closure:
- Observation/error model:
- Validity range:

## 7. Alternatives
| Option | Foundation trace | Benefits | Costs | Risks |

## 8. Derivation and stress test
- Trace:
- Strongest rival:
- Failure modes:
- Sensitivity:
- Falsifier:

## 9. Decision record
- Decision:
- Why:
- Uncertainty:
- Next discriminating action:
- Review trigger:
```

---

## 8. Common failure modes

| Failure | Symptom | Repair |
|---|---|---|
| Analogy trap | “Company X does this” is treated as proof | compare underlying constraints |
| Decomposition without synthesis | long list of parts, no solution | reconstruct minimum sufficient system |
| Assumption laundering | fitted relation presented as law | classify as `A` or `E` |
| Deletion absolutism | safeguards removed for elegance | verify duty, risk, and authority |
| Physics theater | equations added without variables, units, or data | define complete model contract |
| Precision theater | exact number from uncertain inputs | propagate ranges |
| Correlation mechanism | predictor declared a cause | add causal identification or mechanism |
| Scale jump | micro result directly claimed as macro performance | add bridge and validation |
| Proxy optimization | metric improves while real goal worsens | audit objective and Goodhart risk |
| Reinvent-everything trap | proven components rejected for ideological purity | reuse when constraints match |
| Confirmation loop | only the favored model is elaborated | steelman rival and define falsifier |
| Value hiding | “optimal” without stating for whom | expose objective and distribution |

For the complete diagnostic catalog, load [`../references/failure-modes.md`](../references/failure-modes.md).

---

## 9. Completion checklist

- [ ] P1 requirement test is safe and verified.
- [ ] Outcome is not solution-shaped.
- [ ] Boundary, scale, and time are explicit.
- [ ] Proposition types are correctly classified.
- [ ] Candidate foundations passed acceptance tests.
- [ ] Assumptions and empirical closures are visible.
- [ ] Model class matches the decision.
- [ ] Every major conclusion has a trace.
- [ ] At least one strong rival was tested.
- [ ] Falsifier and early warning are stated.
- [ ] Uncertainty and value commitments are explicit.
- [ ] Recommendation is actionable and reversible where possible.
- [ ] Quality gate has no red blocker.
