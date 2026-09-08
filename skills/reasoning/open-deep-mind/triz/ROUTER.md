# TRIZ Engineering Router / TRIZ 工程发明路由

> **Explicit opt-in only.** This module is separate from First Philosophy and First Principles. It is never part of the default OpenDeepMind route.

Complete subsystem map: [`README.md`](README.md)

## Activation gate

Load TRIZ only when the user explicitly requests TRIZ/ARIZ, contradiction-matrix analysis, inventive principles, Su-Field analysis, IFR, Standard Inventive Solutions, engineering-system evolution, or explicitly accepts a suggested TRIZ route.

Do **not** activate merely because:

- a problem is difficult;
- the word “contradiction” appears;
- an optimization has trade-offs;
- the user asks for creativity;
- a business, organization, UX, policy, ethics, or pure-software problem can be forced into a physical analogy.

For non-engineering use explicitly requested by the user, label the result:

```text
TRIZ status: analogical transfer, not canonical engineering TRIZ
```

## Relationship to the core

```text
Default:
First Philosophy -> First Principles -> competing models -> quality gate

Explicit TRIZ:
First Philosophy / First Principles qualification
-> TRIZ inventive synthesis
-> First Principles validation
-> quality gate
```

TRIZ generates candidate concepts. It does not validate physics, safety, manufacturability, legality, lifecycle performance, or causal claims.

## T10 workflow

Exactly ten stages are used:

### T1 — Confirm explicit activation and engineering scope

Record the trigger, canonical-vs-analogical status, engineering system, primary function, decision/deliverable, and non-negotiable safety/regulatory constraints.

### T2 — Identify the key problem

Load the smallest necessary subset of:

- `resources/modern_problem_identification.md`
- `resources/function_analysis.md`
- `resources/flow_analysis.md`
- `resources/cause_effect_chain.md`
- `resources/trimming.md`
- `resources/feature_transfer.md`
- `resources/innovative_benchmarking.md`

Do not confuse a symptom with the key engineering problem.

### T3 — Build resource, ideality, and IFR model

Load `resources/ideality_ifr_resources.md`. Inventory substances, fields, space, time, information, functions, harmful effects, and supersystem resources. State baseline ideality qualitatively or quantitatively only when quantities are commensurable.

### T4 — Formulate the problem model

Choose one or more justified models:

- engineering/technical contradiction;
- physical contradiction;
- Su-Field problem;
- generalized function/effect request;
- ARIZ mini-problem;
- evolution/roadmap question.

Use `resources/contradictions.md` where contradiction modeling is relevant.

### T5 — Select the solving route

| Problem model | Load |
|---|---|
| Engineering contradiction | `39_parameters.md` + matrix + `40_principles.md` |
| Physical contradiction | `separation_principles.md` |
| Su-Field problem | `substance_field_modeling.md` + `76_standard_solutions.md` |
| Hard minimal-change problem | `ariz_85c.md` |
| Function/effect request | `effects_and_fos.md` + `clone_problems.md` as needed |
| Technology roadmap | `s_curve_and_tese.md` + `evolution_trends.md` |
| Framing inertia | `psychological_inertia_tools.md` |

Do not force a matrix lookup when the parameter mapping is weak.

### T6 — Generate structurally distinct concept families

Where practical include:

- a resource-reuse / low-change concept;
- a separation or interaction-change concept;
- a field/mechanism-change concept;
- a trimming/supersystem concept;
- optionally a high-risk frontier concept.

Each concept must name its route, mechanism, resource, contradiction/problem resolved, and new risk.

### T7 — Translate abstractions into engineering mechanisms

Never stop at “use segmentation,” “add feedback,” or “make it dynamic.” Translate:

```text
TRIZ abstraction
-> geometry / material / field / timing / control change
-> interaction or mechanism change
-> predicted useful and harmful effects
```

### T8 — Apply hard engineering gates

Reject concepts that fail verified hard constraints such as:

- basic physical feasibility;
- material compatibility;
- safety;
- regulatory limits;
- manufacturability;
- operating envelope;
- maintainability/lifecycle;
- scale consistency.

A numerical ideality score never overrides a hard blocker.

### T9 — Define discriminating validation

For each leading concept specify the smallest useful next check:

- governing-equation or dimensional check;
- simulation;
- material compatibility test;
- benchtop experiment;
- prototype;
- accelerated aging;
- FMEA/hazard analysis;
- manufacturability/cost estimate;
- patent or prior-art search.

State what result would reject or materially weaken the concept.

### T10 — Return to OpenDeepMind

Return shortlisted concepts to the canonical First Principles module for model completeness, evidence, uncertainty, competing-model, falsification, and decision-quality checks.

**Return to OpenDeepMind** is mandatory. A matrix cell, inventive principle, Standard Inventive Solution, ARIZ path, or evolution trend is a search direction—not proof.

## Progressive-loading rule

Load only the resource files reached by the selected route. The full matrix, 76 SIS, ARIZ, effects, and evolution files must not be loaded together unless the task genuinely requires them.

## Deterministic tools

```bash
python open-deep-mind/triz/scripts/lookup_matrix.py --improve 10 --worsen 17
python open-deep-mind/triz/scripts/lookup_standard_solution.py 1.2.1
python open-deep-mind/triz/scripts/validate_triz_module.py
```

## Output

Use [`resources/output_template.md`](resources/output_template.md).

Every output must preserve source type:

```text
matrix-derived
inventive-principle direct search
separation-derived
standard-solution-derived
ARIZ-derived
FOS/effects-derived
evolution-derived
agent inference
current engineering evidence
```

Sources and provenance: [`resources/sources.md`](resources/sources.md).
