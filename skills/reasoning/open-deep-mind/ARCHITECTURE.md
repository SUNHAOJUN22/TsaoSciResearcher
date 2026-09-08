# OpenDeepMind Architecture / 模块架构

## 1. Architectural rule

OpenDeepMind is one Agent Skill with **three isolated reasoning modules**, shared infrastructure, and a separate behavioral-evaluation plane:

```text
                 ┌──────────────────────────────┐
                 │        SKILL.md Router       │
                 └──────────────┬───────────────┘
                                │
                 ┌──────────────┼───────────────┐
                 │              │               │ explicit only
                 v              v               v
       ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
       │ First Philosophy│ │ First Principles│ │      TRIZ      │
       │       Φ          │ │       P         │ │       T        │
       └────────┬─────────┘ └───────┬────────┘ └────────┬───────┘
                │ Foundation Charter │                  │ concepts
                └───────────────────>│<─────────────────┘
                                    │ validation
                                    v
                           shared quality gate

     ┌─────────────────────────────────────────────────────┐
     │ evals/ behavioral observation plane                 │
     │ cases · baselines · graders · metrics · aggregation │
     └─────────────────────────────────────────────────────┘
             observes outputs; never participates in routing
```

The modules share common schemas, evidence discipline, quality gates, and output infrastructure, but **do not share method bodies**.

The `evals/` layer is intentionally one-way: it observes and scores module behavior. It is **not a fourth reasoning module**, is not listed in `MODULES.json`, and must never be loaded to solve a user task.

## 2. Canonical module locations

| Module | Canonical entry | Activation | Responsibility |
|---|---|---|---|
| First Philosophy | `first-philosophy/METHOD.md` | core or explicit | qualify definitions, ontology, evidence, logic, causality, boundaries, values, praxis |
| First Principles | `first-principles/METHOD.md` | core or explicit | decompose, classify, model, reconstruct, derive, falsify, decide |
| TRIZ | `triz/ROUTER.md` | explicit only | engineering invention, contradiction resolution, ARIZ, Su-Field, TESE, FOS |

Root files `FIRST_PHILOSOPHY.md`, `FIRST_PRINCIPLES.md`, and `TRIZ_ENGINEERING.md` are compatibility aliases only. New code and documentation must target the canonical module paths.

The evaluation package is separately located at `evals/` and has no activation entry in the Skill router.

## 3. Dependency direction

The runtime dependency graph is intentionally asymmetric:

```text
First Philosophy ──Foundation Charter──> First Principles
First Principles ──repair request──────> First Philosophy
First Principles ──explicit opt-in─────> TRIZ
TRIZ ──concept candidates──────────────> First Principles validation
```

The evaluation dependency is outside runtime:

```text
Φ/P/TRIZ outputs ──recorded runs──> evals grading / benchmark aggregation
```

There is no reverse edge:

```text
evals ─X─> runtime reasoning
```

A handoff is not an import. Each module must remain usable and auditable without copying another module's method text.

### Forbidden coupling

- First Philosophy must not load or invoke TRIZ.
- First Principles must not auto-load TRIZ.
- TRIZ must not replace First-Principles physical/evidence validation.
- Shared domain routing must not make TRIZ a default creative method.
- `evals/` must not be registered as a reasoning module or loaded as runtime methodology.
- Holdout benchmark cases must not be converted into case-specific Skill rules.
- A module may read shared `references/` or `assets/`, but module-specific rules belong inside that module.

## 4. Shared contracts

### Proposition ledger

All modules may exchange typed claims using:

```text
D Definition
O Observation
L Law / invariant
C Constraint
A Assumption
E Empirical closure / estimate
V Value
U Unknown
```

Canonical machine-readable schema:

`assets/claim-ledger.schema.json`

### Φ → P contract

First Philosophy outputs a **Foundation Charter**. The machine-readable example/schema live inside `first-philosophy/`.

### P output contract

First Principles outputs a model contract, alternatives, falsifiers, and a decision record. Machine-readable schemas live inside `first-principles/`.

### P → T activation contract

TRIZ activation requires explicit user request or explicit user acceptance after a suggestion. Merely detecting a trade-off or contradiction is insufficient.

### T → P return contract

TRIZ returns candidate concepts with mechanism, resource, contradiction resolved, secondary contradiction, ideality direction, and validation requirement. It does not return a validated engineering conclusion.

### Runtime → evaluation contract

A benchmark run records at least:

```text
case ID
configuration
repetition
model / version
selected route
loaded modules
response artifact
tokens
duration
repository commit
```

Grading is a separate artifact containing assertion evidence, red blockers, route/leakage/TRIZ-activation status, semantic score where used, and case verdict.

## 5. Protocol numbering invariants

- First Philosophy is **Φ8**: `Φ0` through `Φ7` = 8 stages.
- First Principles is **P9**: `P1` through `P9` = 9 stages. Stage `P8` contains both derivation/trace and falsification/stress testing.
- TRIZ is **T10**: `T1` through `T10` = 10 stages.

Validators must fail when these invariants are violated.

## 6. Progressive disclosure

The root `SKILL.md` is the only default activation file. It should stay below the Agent Skills progressive-disclosure target and link directly to the three module entries plus shared references. Detailed knowledge remains in module resources and is loaded only when the selected route needs it.

`evals/` is intentionally excluded from runtime progressive disclosure. Benchmark prompts, expected behavior and grader assertions are measurement artifacts, not instructions for answering live user requests.

## 7. Behavioral evaluation plane

Canonical evaluation entrypoint: `../BENCHMARK.md` and `evals/README.md`.

Initial benchmark v1.0.0:

```text
60 authored cases
├── 12 routing / activation
├── 10 First Philosophy
├── 12 First Principles
├──  8 Dual Engine
├── 10 explicit TRIZ
└──  8 TRIZ near-miss / anti-trigger

36 train / 12 validation / 12 holdout
3 repetitions by default
```

Four configurations are defined in `evals/benchmark-config.json`:

```text
no_skill
first_principles_baseline
opendeepmind_full
opendeepmind_no_triz_ablation   [triz-positive only]
```

`opendeepmind_full` is production behavior: normal Φ/P routing with TRIZ explicit-only. The no-TRIZ ablation intentionally disables T and forces P on the same explicit-TRIZ cases; it is not production behavior and its routing accuracy is not scored.

Declared paired comparisons:

```text
opendeepmind_full vs no_skill
opendeepmind_full vs first_principles_baseline
opendeepmind_full vs opendeepmind_no_triz_ablation [triz-positive]
```

The third comparison estimates the marginal contribution of the TRIZ module on tasks that explicitly request it.

Evaluation metrics include case/assertion pass rate, routing accuracy, red-blocker rate, TRIZ false-activation, module leakage, semantic quality, rival/falsifier coverage, tokens, time, and common-case paired deltas.

The workspace manifest enumerates every expected run slot. For the validation split the current design yields 114 expected slots: 108 from the three full-scope configurations plus 6 no-TRIZ ablation slots on the two validation TRIZ-positive cases. Missing run/grading artifacts therefore remain visible and block publication readiness.

**Authored cases are not performance results.** No behavioral score may be published until real model runs, raw outputs, grading artifacts, model/settings metadata and aggregate results exist.

## 8. Validation layers

```text
repository validator
├── root structure / version / links / frontmatter
├── First Philosophy module validator
├── First Principles module validator
├── TRIZ module validator
├── behavioral-eval definition validator
├── claim-ledger validator
├── deterministic matrix/SIS lookups
└── regression tests / Python compilation
```

The CI workflow runs the owned structural layers. Model-execution benchmarks remain a separate experiment because they require a chosen model/provider/runtime and comparable run settings.

## 9. Completeness definition

A reasoning module is considered structurally complete when it has:

1. a canonical entry;
2. a machine-readable manifest;
3. explicit activation rules;
4. input/output contracts;
5. stopping/repair conditions;
6. examples or fixtures;
7. a validator;
8. documented dependencies and prohibited dependencies;
9. provenance/license information where third-party material is used;
10. CI coverage.

The evaluation layer is considered structurally complete when it has:

1. realistic authored cases;
2. explicit train/validation/holdout discipline;
3. comparable baseline and ablation configurations;
4. run/grading/aggregate contracts;
5. deterministic definition validation;
6. semantic grading anchors;
7. anti-gaming/holdout rules;
8. reproducibility metadata requirements;
9. manifest-complete aggregation tooling;
10. a publication rule that forbids synthetic scores.

This is a repository completeness criterion, not a claim that any methodology is philosophically/scientifically exhaustive or empirically superior before the behavioral runs are executed.
