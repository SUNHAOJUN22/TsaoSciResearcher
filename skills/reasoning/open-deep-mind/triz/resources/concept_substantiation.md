# Concept Substantiation / 概念论证与工程验证

TRIZ concept generation ends where engineering substantiation begins. Modern MATRIZ explicitly separates the stage in which proposed solutions are evaluated against technical, production, time-to-market, investment, and cost requirements. OpenDeepMind extends that stage with its First-Principles and evidence gates.

## Hard gate before scoring

Reject or block concepts that violate any verified:

- physical law / governing constraint;
- safety requirement;
- legal/regulatory requirement;
- material compatibility limit;
- manufacturing/process envelope;
- operating-temperature/pressure/field envelope;
- reliability/lifecycle requirement;
- required maintainability/inspectability;
- ethical/environmental constraint;
- dimensional or unit consistency.

A TRIZ ideality score never overrides a hard blocker.

## Model contract

For each concept document:

```text
Function delivered:
TRIZ origin:
Physical mechanism:
State variables:
Inputs / controls:
Parameters and provenance:
Boundary / initial conditions:
Constitutive / closure assumptions:
Operating range:
Failure modes:
Evidence status:
```

## Concept scorecard

Score only after hard-gate survival.

| Dimension | Typical questions |
|---|---|
| Contradiction resolution | Is the contradiction actually removed rather than averaged? |
| Ideality delta | More useful function for less harm/cost/complexity? |
| Physical feasibility | Governing physics/mechanism plausible under real conditions? |
| Resource use | Does it exploit available resources or add costly new ones? |
| Controllability | Can the effect be initiated, stopped, measured, and stabilized? |
| Manufacturability | Can it be produced with realistic process capability/tolerance? |
| Reliability | Degradation, fatigue, fouling, drift, wear, aging, failure containment? |
| Integration | Interfaces, controls, utilities, supersystem coupling? |
| Safety / regulation | Hazards, certification, fail-safe/fail-operational needs? |
| Lifecycle | maintainability, repair, recycling, environmental burden? |
| Economics | capex, opex, BOM, yield, downtime, learning curve? |
| Novelty / IP | is it already known, protected, or free to operate? |
| Evidence / uncertainty | what is measured, simulated, assumed, unknown? |

Weights are project-specific and must be explicit.

## Validation ladder

Use the cheapest test capable of discriminating between concepts or falsifying the key mechanism:

```text
0. dimensional / order-of-magnitude check
1. analytical model / simple calculation
2. literature / prior-art / effects evidence
3. numerical simulation
4. material/component bench test
5. subsystem prototype
6. integrated prototype
7. representative environment test
8. reliability / accelerated-aging / safety qualification
9. pilot / production validation
```

Do not climb the ladder automatically; design tests for **value of information**.

## Falsification contract

For every leading concept:

```text
Critical mechanism claim:
Observation that supports it:
Observation that would reject/weaken it:
Most sensitive unknown:
Early warning signal:
Fallback / rival concept:
Review trigger:
```

## Patent and novelty discipline

TRIZ helps generate technically inventive concepts; it does not establish patent novelty, inventive step/non-obviousness, freedom to operate, or ownership.

For potentially commercial concepts:

- perform current prior-art search;
- separate the TRIZ principle from the concrete patentable embodiment;
- record dates and jurisdictions;
- involve qualified IP counsel when decisions depend on legal conclusions.

## From TRIZ back to OpenDeepMind

Final handoff:

```text
Concept(s) surviving TRIZ:
Foundation/claim IDs relied upon:
Mechanism model:
Physical validation status:
Remaining assumptions and unknowns:
Secondary contradictions:
Rival concept / null model:
Quality-gate blockers:
Next discriminating action:
```

A concept is “TRIZ-derived” until these checks support a stronger label. Do not call it validated, optimized, or production-ready based only on method provenance.

See `sources.md` for the public MATRIZ concept-substantiation stage and the main OpenDeepMind quality gates for the extended audit.
