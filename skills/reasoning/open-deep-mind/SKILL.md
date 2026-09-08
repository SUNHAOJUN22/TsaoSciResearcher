---
name: open-deep-mind
description: >-
  A domain-general reasoning skill with isolated First Philosophy and First Principles
  core modules plus an explicit-only TRIZ engineering module. Use First Philosophy
  for framing, semantics, ontology, evidence, causality, boundaries, values, and
  foundational disputes; use First Principles for decomposition, mechanism/model
  construction, from-scratch design, falsification, and decisions. Load TRIZ only
  when the user explicitly requests or accepts TRIZ/ARIZ, contradiction-matrix,
  inventive-principle, Su-Field, IFR, Standard Inventive Solutions, or engineering-
  system-evolution analysis.
license: Apache-2.0 AND CC-BY-4.0 with documented third-party exceptions; see ../LICENSE.md
compatibility: Agent Skills-compatible runtimes. Core routing and validation require no third-party Python packages. Current, disputed, high-stakes, or source-sensitive facts should be externally verified.
metadata:
  author: SUNHAOJUN22
  version: "1.2.0"
  repository: SUNHAOJUN22/OpenDeepMind_skill
  languages: English, Chinese
---

# OpenDeepMind Router

OpenDeepMind is **one Agent Skill with three isolated method modules**:

| Module | Role | Canonical entry | Activation |
|---|---|---|---|
| **Φ First Philosophy / 第一哲学** | qualify what may count as a foundation | [first-philosophy/METHOD.md](first-philosophy/METHOD.md) | core or explicit |
| **P First Principles / 第一性原理** | decompose, model, reconstruct, test, decide | [first-principles/METHOD.md](first-principles/METHOD.md) | core or explicit |
| **T TRIZ Engineering / TRIZ 工程发明** | systematic engineering invention | [triz/ROUTER.md](triz/ROUTER.md) | **explicit-only** |

Machine-readable registry: [MODULES.json](MODULES.json)  
Architecture contract: [ARCHITECTURE.md](ARCHITECTURE.md)

Default sequence:

\[
\text{frame}
\rightarrow
\Phi\text{ foundation qualification}
\rightarrow
P\text{ reconstruction}
\rightarrow
\text{rival / falsification}
\rightarrow
\text{quality gate}
\rightarrow
\text{decision / revision}
\]

Explicit TRIZ sequence:

\[
\Phi/P\text{ qualification}
\rightarrow
T\text{ inventive synthesis}
\rightarrow
P\text{ validation}
\rightarrow
\text{quality gate}
\]

---

## 1. Non-negotiable invariants

1. **Module isolation.** First Philosophy, First Principles, and TRIZ have separate canonical method bodies and validators.
2. **Foundation before construction when framing is material.** Do not optimize an incoherent frame.
3. **Relative firstness.** “First” is relative to a stated domain, scale, purpose, theory level, and conditions unless a stronger claim is justified.
4. **Typed claims.** Keep `D/O/L/C/A/E/V/U` distinct.
5. **No fabricated certainty.** Label inference, model dependence, uncertainty, disputed evidence, and values.
6. **No hidden value function.** Facts do not by themselves determine what ought to be optimized.
7. **No scale teleportation.** Cross-scale claims require an explicit bridge, information-loss statement, uncertainty, and validation.
8. **No explanation by vocabulary.** A label or named framework is not a mechanism.
9. **No single-solution theater.** Keep a serious rival, null model, or structurally different option.
10. **No untestable closure.** State what evidence, intervention, proof, or failure would change the conclusion.
11. **TRIZ is explicit-only.** Never silently load TRIZ because a problem is hard, creative, or contains a trade-off.
12. **TRIZ is not validation.** TRIZ concepts return to First Principles for physics/evidence/safety/feasibility checks.
13. **Language alignment.** Answer in the user's language unless another language is requested.

---

## 2. Route selection

Choose the lightest route that preserves rigor.

| Signature | Route | Load |
|---|---|---|
| meaning, ontology, evidence standard, ethics, category dispute | `Φ` | [first-philosophy/METHOD.md](first-philosophy/METHOD.md) |
| design, mechanism, diagnosis, architecture, cost, optimization | `P` | [first-principles/METHOD.md](first-principles/METHOD.md) |
| novel, ambiguous, cross-domain, high-impact, high-uncertainty | `Φ→P` | both core modules |
| P reveals unstable definition/ontology/value/boundary | `P→Φ repair` | return to First Philosophy |
| explicit TRIZ/ARIZ/matrix/40 principles/Su-Field/IFR/SIS/evolution | `T` | [triz/ROUTER.md](triz/ROUTER.md) |
| reversible low-stakes task | Rapid | use minimal relevant core route |
| research, safety, policy, expensive/irreversible decision | Deep | core route + full shared quality/evidence checks |

### TRIZ activation gate

A candidate engineering contradiction is permission to **suggest** TRIZ once; it is not permission to execute it.

Load TRIZ only when:

- the user explicitly requests a TRIZ-family method; or
- after a suggestion, the user explicitly accepts the TRIZ route.

For business, organization, UX, policy, ethics, and pure software problems, canonical TRIZ is out of scope. If the user explicitly asks for analogical use, label it:

```text
TRIZ status: analogical transfer, not canonical engineering TRIZ
```

---

## 3. Common intake contract

Normalize the task into the smallest sufficient record:

```text
Question:
Decision or deliverable:
Why it matters:
System boundary:
Scale(s):
Time horizon:
Stakeholders:
Known evidence:
Constraints:
Values/objectives:
Unknowns:
Required confidence:
Explicit optional method requested:
```

Do not ask for information that can be responsibly inferred or retrieved. Ask only when a missing item materially changes route, evidence standard, safety, or decision.

---

## 4. Core route

### Route Φ — First Philosophy

Load [first-philosophy/METHOD.md](first-philosophy/METHOD.md).

Required handoff artifact: **Foundation Charter** containing at least:

```text
neutral + rival frames
definitions
ontology
epistemic status
logic / causality / explanation commitments
boundary / scale / time
values / duties / stakeholders
accepted / conditional / rejected foundations
blocking unknowns
```

Machine-readable contract lives inside `first-philosophy/`.

### Route P — First Principles

Load [first-principles/METHOD.md](first-principles/METHOD.md).

The normalized P9 protocol is **P1..P9**, not P0..P9. Required outputs include:

```text
requirement verdict
proposition ledger
dependency decomposition
accepted foundations
model contract
structurally distinct alternatives
derivation trace
rival / falsifiers / stress tests
decision record
```

Machine-readable model/decision contracts live inside `first-principles/`.

### Route T — TRIZ Engineering

Only after explicit activation, load [triz/ROUTER.md](triz/ROUTER.md).

TRIZ uses a true **T1..T10** protocol and progressive-loads only the relevant resources. Its output is a set of inventive concepts/hypotheses, not validated conclusions.

Return every leading TRIZ concept to First Principles for model completeness, physical feasibility, data/evidence, uncertainty, safety, manufacturability, competing-model, and falsification checks.

---

## 5. Shared proposition ledger

All modules may exchange load-bearing claims using:

| Code | Type | Meaning |
|---|---|---|
| `D` | Definition | lexical, stipulated, operational, or theoretical meaning |
| `O` | Observation | measured, recorded, witnessed, or directly sourced fact |
| `L` | Law / invariant | independently supported rule within a stated domain |
| `C` | Constraint | physical, logical, legal, ethical, safety, or resource boundary |
| `A` | Assumption | adopted premise not established as fact |
| `E` | Empirical closure / estimate | fit, constitutive relation, heuristic, proxy, learned approximation |
| `V` | Value | objective, duty, preference, utility, risk tolerance |
| `U` | Unknown | material unresolved question |

Canonical schema: [assets/claim-ledger.schema.json](assets/claim-ledger.schema.json)

Never let one type borrow the authority of another.

---

## 6. Evidence discipline

For externally checkable claims:

1. prefer primary sources, official documentation, original datasets, standards, or peer-reviewed research;
2. separate observation from interpretation and model output;
3. record date/version/jurisdiction/measurement conditions where material;
4. verify current or high-stakes facts;
5. do not turn absence of evidence into evidence of absence;
6. do not elevate model fit, analogy, patent pattern, matrix cell, or named method into causal evidence;
7. expose inaccessible or insufficient evidence.

Evidence labels:

- **Verified** — suitable direct/reproducible support;
- **Supported** — multiple relevant lines, not decisive;
- **Plausible** — coherent but underdetermined;
- **Contested** — credible conflicting evidence/models;
- **Unknown** — not responsibly resolved.

---

## 7. Quantitative model contract

For quantitative work, expose the relevant subset of:

\[
\mathcal M=
\{\mathbf x,\mathbf u,\boldsymbol\theta,
\mathbf F,\mathbf h,\mathbf g,
\mathrm{IC},\mathrm{BC},\mathcal O,\mathcal E\}
\]

with:

- states and controls;
- parameters and provenance;
- governing relations/equations;
- equality/inequality constraints;
- initial/boundary conditions where applicable;
- assumptions and empirical closures;
- observation model;
- error/model-discrepancy model;
- validity domain.

Required checks as applicable:

- units/dimensions;
- limiting cases;
- conservation/invariance;
- identifiability;
- convergence/numerical error;
- sensitivity/UQ;
- model discrepancy;
- domain shift;
- scale bridges.

“Computed from first principles” never means “free of approximation.”

---

## 8. Counter-model and falsification

Before a substantive recommendation, construct at least one decision-relevant alternative:

- rival ontology or frame;
- rival causal/mechanism model;
- alternative objective function;
- minimum sufficient design;
- null model;
- do-nothing baseline;
- boundary/inversion case.

Steelman it. Do not manufacture a weak opponent.

Every major conclusion should expose:

```text
Falsifier:
Strongest rival:
Most likely failure mode:
Early warning:
Fallback:
Review trigger:
```

---

## 9. Shared quality gate

Load [references/quality-gates.md](references/quality-gates.md).

Red blockers dominate any score. A response cannot be labeled validated/final/complete while a relevant blocker remains.

Shared checks include:

- semantic/category consistency;
- evidence-to-claim fit;
- assumptions/closures visible;
- causal/mechanism adequacy;
- units, parameters, boundary/closure and convergence where mathematical;
- scale bridges;
- serious alternatives;
- falsifier and uncertainty;
- values/stakeholders;
- safety/legal/ethical constraints;
- actionability and traceability.

---

## 10. Depth levels

### Rapid

For low-stakes/reversible decisions, keep only:

- actual outcome;
- one requirement challenge;
- key foundations/assumptions;
- two options;
- recommendation;
- falsifier/review trigger.

TRIZ remains excluded unless explicitly activated.

### Standard

Require:

- appropriate foundation qualification;
- proposition ledger;
- one serious rival;
- quality gate;
- structured recommendation.

### Deep

Add as relevant:

- source verification;
- multiple competing models;
- sensitivity/identifiability/UQ;
- scale-bridge audit;
- stakeholder/ethical review;
- pre-mortem;
- reproducibility record;
- explicit unresolved research questions.

---

## 11. Stop conditions

Stop when one of these holds:

1. required quality threshold passes with no red blocker;
2. evidence cannot distinguish leading models and the next discriminating test is identified;
3. value of more analysis is lower than cost of delay;
4. the problem dissolves after a requirement/category/frame correction;
5. repeated revisions plateau and the reason is reported;
6. in explicit TRIZ mode, no concept survives hard physics/safety/feasibility gates—report the unresolved contradiction rather than invent certainty.

---

## 12. Output behavior

Prefer:

- explicit tables over vague prose;
- mechanism chains over labels;
- ranges over false precision;
- traceability over decorative complexity;
- one clear recommendation over an undifferentiated menu;
- explicit uncertainty over rhetorical confidence.

Do not expose private chain-of-thought. Provide a concise reasoning audit: premises, evidence, assumptions, model/inference structure, checks, and conclusion.

Every substantive output ends with the relevant subset of:

```text
Decision / conclusion:
Why:
Trace to foundations:
Key assumptions / closures:
Uncertainty / validity domain:
What would change the conclusion:
Next discriminating action:
Review trigger:
```

Templates: [assets/output-templates.md](assets/output-templates.md)

---

## 13. Boundaries

This skill may structure medical, legal, financial, safety, or policy reasoning, but it does not replace qualified professional judgment, jurisdiction-specific verification, empirical testing, or certification.

It will not:

- declare metaphysical certainty where only a working foundation exists;
- fabricate sources, experiments, measurements, patents, or consensus;
- remove safeguards without verification;
- turn ethical disagreement into a mere optimization error;
- use first-principles language to justify a predetermined result;
- silently force TRIZ onto a task;
- treat a TRIZ pattern as performance evidence.

---

## 14. Supporting resources

### Canonical modules

- [first-philosophy/README.md](first-philosophy/README.md)
- [first-philosophy/METHOD.md](first-philosophy/METHOD.md)
- [first-principles/README.md](first-principles/README.md)
- [first-principles/METHOD.md](first-principles/METHOD.md)
- [triz/README.md](triz/README.md)
- [triz/ROUTER.md](triz/ROUTER.md)

### Shared infrastructure

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MODULES.json](MODULES.json)
- [references/method-atlas.md](references/method-atlas.md)
- [references/domain-routing.md](references/domain-routing.md)
- [references/quality-gates.md](references/quality-gates.md)
- [references/failure-modes.md](references/failure-modes.md)
- [references/intellectual-lineage.md](references/intellectual-lineage.md)
- [references/glossary.md](references/glossary.md)
- [references/worked-examples.md](references/worked-examples.md)
- [assets/output-templates.md](assets/output-templates.md)
- [assets/claim-ledger-template.md](assets/claim-ledger-template.md)

Compatibility aliases `FIRST_PHILOSOPHY.md`, `FIRST_PRINCIPLES.md`, and `TRIZ_ENGINEERING.md` are retained only for old links; new maintenance must target canonical module paths.
