# Method Atlas

This atlas routes methods by the **kind of uncertainty** in the problem. Use methods as instruments, not as authorities.

> **TRIZ routing override:** TRIZ is an optional specialist module. Do not load or apply it from the default method bundle or routing table. Use [../TRIZ_ENGINEERING.md](../TRIZ_ENGINEERING.md) only when the user explicitly requests or accepts the TRIZ route.

---

## 1. Selection rule

Choose one method from each layer that is materially relevant:

1. **Foundation** — clarify meaning, ontology, evidence, or value.
2. **Structure** — decompose dependencies, causes, functions, or constraints.
3. **Construction** — generate models or solutions.
4. **Adversarial** — attack assumptions and failure modes.
5. **Calibration** — compare against evidence and decision thresholds.

Default bundle:

\[
\text{Conceptual analysis}
+
\text{causal/mechanism map}
+
\text{morphological synthesis}
+
\text{inversion}
+
\text{evidence audit}
\]

TRIZ is deliberately absent from this default bundle.

Do not use more methods merely to make the process look sophisticated.

---

## 2. Routing matrix

| Problem signature | Foundation method | Structure method | Construction method | Adversarial method | Calibration |
|---|---|---|---|---|---|
| Key term is disputed | conceptual analysis | category map | operational definition | counterexample | inter-rater/source check |
| Requirement may be inherited | methodic doubt | requirement tree | minimum sufficient system | deletion/inversion | failure and duty audit |
| Mechanism is uncertain | four-cause/explanation audit | causal graph | competing mechanism models | null model | intervention/discriminating test |
| Complex system with feedback | boundary audit | stock-flow/feedback loops | scenario architecture | perturbation | sensitivity and stability |
| Engineering architecture | ontology of components/processes | functional decomposition | morphological matrix | pre-mortem/FMEA | constraints and tests |
| Scientific model | epistemic audit | equations + scale bridges | rival model classes | boundary/null tests | prediction and UQ |
| Strategy/business | value and stakeholder audit | value chain/constraint map | portfolio options | competitor/inversion | scenarios and real options |
| Policy/ethics | ethical-first audit | stakeholder and institutional map | policy alternatives | role reversal/red team | rights, distribution, evidence |
| Personal decision | value clarification | option dependency map | reversible experiments | regret/pre-mortem | review date and signals |
| Creative/product innovation | semantic reframing | job/tension decomposition | morphology/bisociation; TRIZ only by explicit request | worst idea/inversion | usefulness, novelty, feasibility |
| Explicit engineering TRIZ request | foundation and engineering-scope audit | function/CECA/contradiction model | load `TRIZ_ENGINEERING.md` | inverted contradiction/pre-mortem | physics, feasibility, experiment, quality gate |

---

## 3. Foundation method cards

### 3.1 Socratic elenchus

**Use when:** a claim sounds obvious but its meaning or support is unclear.

**Procedure**

1. Ask for the claim in one sentence.
2. Define each load-bearing term.
3. Elicit the general rule behind the claim.
4. Search for a counterexample or conflicting commitment.
5. Revise the claim to preserve what survives.

**Output:** revised claim, rejected ambiguity, counterexample.

**Failure risk:** interrogation without constructive reformulation.

---

### 3.2 Conceptual analysis

**Use when:** category boundaries or necessary/sufficient conditions matter.

**Procedure**

1. collect central and boundary cases;
2. propose necessary and sufficient conditions;
3. test counterexamples;
4. distinguish lexical, operational, and theoretical meanings;
5. select a task-appropriate working definition.

**Failure risk:** assuming ordinary language alone settles empirical ontology.

---

### 3.3 Aristotelian explanatory analysis

**Use when:** “what is it?” and “why does it occur?” are mixed.

Map:

- material/implementation;
- form/organization;
- efficient/generative process;
- function/purpose.

Add enabling, triggering, maintaining, and preventing conditions.

**Failure risk:** treating purpose as an efficient cause, or importing design language into natural systems without justification.

---

### 3.4 Methodic doubt

**Use when:** authority, legacy, or convention is doing the work of evidence.

**Procedure**

1. list inherited beliefs;
2. identify conceivable error modes;
3. classify what survives the required confidence standard;
4. rebuild in explicit steps.

**Failure risk:** using radical doubt where ordinary calibrated evidence is sufficient.

---

### 3.5 Conditions-of-possibility analysis

**Use when:** asking what must be true for a capability, measurement, experience, or institution to exist.

**Procedure**

1. specify the phenomenon;
2. list candidate necessary conditions;
3. seek alternative enabling sets;
4. distinguish constitutive from contingent conditions;
5. keep only robust necessities.

**Failure risk:** confusing a familiar implementation with a necessary condition.

---

### 3.6 Phenomenological description

**Use when:** lived experience, perception, human–computer interaction, or observer framing matters.

**Procedure**

1. bracket premature explanation;
2. describe the structure of appearance;
3. identify attention, embodiment, temporality, and context;
4. distinguish first-person and third-person claims;
5. reconnect to empirical inquiry.

**Failure risk:** treating description as sufficient causal explanation.

---

### 3.7 Hermeneutic loop

**Use when:** texts, institutions, historical choices, or culturally embedded evidence require interpretation.

Iterate:

\[
\text{part} \leftrightarrow \text{whole}
\]

while making prior assumptions and alternative readings explicit.

**Failure risk:** unfalsifiable interpretation with no evidence constraints.

---

### 3.8 Ethical-first analysis

**Use when:** rights, responsibility, asymmetrical power, or irreversible harm may dominate utility.

**Procedure**

1. identify affected parties;
2. list duties and protections;
3. map benefits, harms, and distribution;
4. test consent and role reversal;
5. separate non-tradeable constraints from preferences.

**Failure risk:** moralizing without facts, or optimizing away rights.

---

## 4. Structural method cards

### 4.1 Five Whys with branching

Do not force a single chain. Use a directed graph:

```text
Observed outcome
├── mechanism A
│   ├── condition A1
│   └── condition A2
└── mechanism B
    ├── condition B1
    └── condition B2
```

Stop only at a justified foundation or decision-relevant unknown.

**Failure risk:** choosing the first plausible chain and calling it root cause.

---

### 4.2 Functional decomposition

Represent:

\[
\text{system goal}
\rightarrow
\text{functions}
\rightarrow
\text{subfunctions}
\rightarrow
\text{means}
\]

Separate **what must be achieved** from **how it is currently implemented**.

**Best for:** engineering, organizations, services, software.

---

### 4.3 Causal graph

Nodes are variables; arrows encode direct causal assumptions.

Ask:

- confounders?
- colliders?
- mediators?
- selection bias?
- intervention available?
- temporal order?
- transportability?

**Failure risk:** drawing arrows without identification or evidence.

---

### 4.4 Mechanism map

Require:

\[
\text{entities}
+
\text{activities}
+
\text{organization}
+
\text{conditions}
\rightarrow
\text{phenomenon}
\]

**Best for:** biology, chemistry, materials, failure analysis, social mechanisms.

---

### 4.5 Constraint map

Classify:

- physical;
- logical;
- legal;
- ethical;
- resource;
- time;
- compatibility;
- organizational;
- preference.

Mark each as hard, soft, assumed, or negotiable.

**Failure risk:** treating every stakeholder preference as a hard constraint.

---

### 4.6 Systems and feedback analysis

Identify:

- stocks;
- flows;
- reinforcing loops;
- balancing loops;
- delays;
- thresholds;
- bottlenecks;
- adaptation;
- unintended consequences.

**Failure risk:** decorative loop diagrams with no variables or signs.

---

### 4.7 Scale and hierarchy map

For every level:

```text
state variables
interaction rules
emergent observables
bridge to next level
information lost
validation
```

**Failure risk:** reductionism or scale teleportation.

---

## 5. Construction method cards

### 5.1 Minimum sufficient system

Start with nothing. Add only components required by accepted foundations.

For component \(i\):

\[
\text{net justification}_i
=
\text{benefit}_i
-
\text{complexity}_i
-
\text{risk}_i
\]

Delete or defer components with no positive decision-relevant contribution.

---

### 5.2 Morphological analysis

1. list independent functions or parameters;
2. list alternatives for each;
3. combine compatible cells;
4. prune hard-constraint violations;
5. rank by objectives and robustness.

**Failure risk:** combinatorial volume without meaningful distinctions.

---

### 5.3 TRIZ contradiction analysis — opt-in only

**Activation:** use only when the user explicitly asks for or accepts TRIZ. Load the complete protocol in [../TRIZ_ENGINEERING.md](../TRIZ_ENGINEERING.md).

Formulate:

> Improving \(A\) worsens \(B\) under a specified engineering action and verified conditions.

Then route through the appropriate TRIZ model:

- technical contradiction → typical parameters, matrix, and inventive principles;
- physical contradiction → separation in time, space, condition, or system level;
- defective interaction → Su-Field and standard-solution classes;
- stubborn mini-problem → ARIZ-85C;
- explicit roadmap → S-curve and engineering-system evolution.

TRIZ concepts must return to First Principles for physical, mathematical, safety, feasibility, and evidence validation.

**Failure risks:** applying generic principles without a real contradiction; treating a matrix cell as proof; using TRIZ automatically on business, UX, policy, or pure software tasks; naming a principle without a concrete mechanism.

---

### 5.4 Inversion

Ask:

- How would we guarantee failure?
- What if the assumed direction is reversed?
- What if the scarce resource becomes abundant?
- What if the objective is a constraint and the constraint an objective?
- What if we preserve options instead of optimizing now?

Invert back into actionable safeguards or alternatives.

---

### 5.5 Bisociation / cross-domain transfer

Connect two domains only after comparing their structures:

| Source domain | Target domain | Structural match | Structural mismatch |
|---|---|---|---|

Transfer relations, not surface imagery.

**Failure risk:** analogy replacing proof.

---

### 5.6 Constraint relaxation ladder

For each constraint:

1. immutable;
2. externally fixed but revisable;
3. internally imposed;
4. historical artifact;
5. preference.

Generate solutions at each relaxation level and record the authority/cost required to move levels.

---

### 5.7 Real-options design

When uncertainty is high and decisions are partly reversible:

- stage commitment;
- buy information;
- preserve exit;
- use modularity;
- set review triggers;
- cap downside.

**Failure risk:** delaying indefinitely without a learning plan.

---

## 6. Adversarial method cards

### 6.1 Steelman

Construct the strongest version of the rival claim using its best evidence and assumptions.

The rival must be capable of changing the decision.

### 6.2 Null model

Ask what would be observed without the proposed mechanism or intervention.

### 6.3 Pre-mortem

Assume the recommendation failed. Identify:

- failure event;
- causal path;
- earliest signal;
- preventability;
- contingency.

### 6.4 Boundary and limit tests

Evaluate zero, infinity, extreme load, no-data, adversarial actor, regime change, and long-horizon behavior as applicable.

### 6.5 Role reversal

Swap decision-maker and affected party; current and future generation; majority and minority; provider and user.

### 6.6 Red team

Assign a critic to attack:

- definitions;
- source quality;
- causal identification;
- hidden assumptions;
- scale bridges;
- objective function;
- operational feasibility.

The red team must cite the exact claim it is attacking.

---

## 7. Calibration methods

### 7.1 Falsification test

State an observation or proof outcome that would lower confidence or reject the model.

A statement compatible with every possible result carries little discriminating content.

### 7.2 Bayesian update

Record prior, likelihood, posterior, and sensitivity to the prior.

Do not use numerical probabilities when they are merely decorative.

### 7.3 Sensitivity analysis

Local:

\[
S_i^{\text{local}}
=
\frac{\partial y}{\partial \theta_i}
\]

Global:

\[
S_i =
\frac{\operatorname{Var}_{\theta_i}
[\mathbb E(Y\mid\theta_i)]}
{\operatorname{Var}(Y)}
\]

Use qualitative sensitivity when quantitative models are unavailable.

### 7.4 Triangulation

Combine independent:

- methods;
- datasets;
- observers;
- scales;
- theories.

Repeated claims from a common upstream source are not independent evidence.

### 7.5 Backtesting and prospective testing

Separate:

- training/calibration;
- retrospective test;
- prospective test;
- domain-shift test.

### 7.6 Decision calibration

Compare:

- cost of false positive;
- cost of false negative;
- reversibility;
- value of information;
- cost of delay.

---

## 8. Method rotation rules

When analysis plateaus:

| Pass | Change |
|---|---|
| 1 | baseline bundle |
| 2 | replace the highest-risk assumption or definition |
| 3 | replace the causal/model class |
| 4 | shift scale, stakeholder, or time horizon |
| 5 | run pre-mortem and real-options analysis |

Hard rules:

- do not use the same adversarial method twice in succession;
- do not add methods without identifying the weakness they address;
- if the rival model remains observationally equivalent, seek a discriminating test;
- if the frame itself is unstable, return to First Philosophy rather than iterating inside the same frame;
- do not introduce TRIZ during method rotation unless its explicit activation contract is satisfied.

---

## 9. Compatibility cautions

| Combination | Risk | Mitigation |
|---|---|---|
| Five Whys + single causal chain | false root cause | branch causes and test them |
| TRIZ + unverified constraints | solving an invented contradiction | verify constraint ledger and explicit activation first |
| TRIZ principle + no mechanism | vocabulary presented as solution | translate principle into physical change and test |
| Morphology + many soft criteria | arbitrary ranking | separate hard pruning from value scoring |
| Bayesian numbers + weak elicitation | precision theater | report ranges and sensitivity |
| Analogy + bisociation | surface transfer | require structural correspondence |
| Phenomenology + causal claim | level confusion | separate description and mechanism |
| Formal proof + empirical premise | reality overclaim | verify premise outside the formal system |
| DFT/physics model + macro claim | scale jump | explicit bridge and validation |
