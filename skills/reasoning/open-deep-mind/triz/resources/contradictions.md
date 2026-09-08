# Contradiction Modeling / TRIZ 矛盾建模

Modern TRIZ uses two main parametric contradiction models: **engineering/technical contradiction** and **physical contradiction**. They are models of selected key problems, not descriptions of every trade-off in a project.

## 1. Engineering contradiction (EC/TC)

An attempt to improve one system parameter through a particular action/state causes another justified parameter to worsen.

Use the form:

```text
IF    [action / parameter state],
THEN  [desired parameter / function improves],
BUT   [another parameter / function worsens].
```

Always formulate an inverted/alternative contradiction when useful:

```text
IF    [opposite action / state],
THEN  [second requirement improves],
BUT   [first requirement worsens].
```

### Quality test

- IF-line describes a controllable action/state, not a vague wish;
- THEN and BUT effects are causally/physically linked to IF;
- both outcomes matter to project goal/constraints;
- parameters are measurable or operationally defined;
- contradiction exists under stated operating conditions;
- there is no trivial way to satisfy both without invention.

### Matrix route

1. map THEN improvement to one or more justified typical parameters;
2. map BUT degradation to typical parameter(s);
3. preserve directionality: row = improve, column = worsen;
4. retrieve local cell using `lookup_matrix.py`;
5. translate suggested principles into concrete mechanisms;
6. force at least one non-matrix/rival route if all concepts cluster structurally.

An empty matrix cell is not “no solution”; use direct 40-principle search, separation, Su-Field, FOS/effects, trimming, or ARIZ.

## 2. Physical contradiction (PC)

A single parameter/property of one relevant object/element must satisfy two justified opposite requirements.

```text
Element X must have parameter/property A because R1,
and must have parameter/property not-A because R2.
```

The contradiction can often be derived from EC:

- the IF-line identifies the parameter/action around which PC is formed;
- THEN justifies one state;
- inverted BUT logic justifies the opposite state.

The conversion can also run from PC to two alternative ECs.

### Resolution routes

Primary route: `separation_principles.md`.

- time;
- space;
- condition/state;
- system level / part–whole.

Also consider FOS, scientific effects, clone-problem transfer, Su-Field standards, and ARIZ for difficult cases.

## 3. Contradiction versus compromise

A compromise picks an intermediate value:

```math
x_{compromise}\in(A,\neg A)
```

A TRIZ-style resolution changes the architecture/conditions so both requirements are fulfilled where/when they are actually needed:

```text
requirement 1 satisfied under domain Ω1
requirement 2 satisfied under domain Ω2
without unacceptable new harm
```

Compromise may still be rational in engineering. TRIZ simply searches for a stronger structural resolution before accepting it.

## 4. Secondary contradictions

Every concept can create new conflicts. Record them explicitly:

| Concept | Resolved contradiction | New engineering contradiction | New physical contradiction | Severity |
|---|---|---|---|---|

Do not conceal secondary contradictions behind a higher ideality score.

## 5. Output

```text
Key problem:
Evidence:
Base EC:
Inverted EC:
Parameter mappings:
Matrix cell and source status:
PC derived, if any:
Separation variables:
Secondary contradictions:
Best discriminating experiment/model:
```

See `39_parameters.md`, `40_principles.md`, `separation_principles.md`, and `sources.md`.
