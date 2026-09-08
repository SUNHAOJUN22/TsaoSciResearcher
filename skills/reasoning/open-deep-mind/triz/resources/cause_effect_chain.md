# Cause–Effect Chain Analysis (CECA) / 因果链分析

CECA links the **initial disadvantage** implied by the project goal to deeper disadvantages and selects the **key disadvantages** that should become TRIZ key problems.

## Starting point

Form the initial disadvantage by inverting the project goal.

```text
Goal: reduce contamination
Initial disadvantage: product contamination is too high
```

If the project has several independent goals, build separate initial disadvantages and connect their chains where evidence supports interaction.

## Input evidence

CECA should consume:

- function disadvantages from function analysis;
- cost disadvantages where relevant;
- flow disadvantages if flow analysis was performed;
- measured failure mechanisms and operating records;
- only then additional hypothesized disadvantages, explicitly marked as hypotheses.

## Chain grammar

A CECA chain contains **disadvantages only**.

```text
Initial disadvantage
↓ because
Intermediate disadvantage
├─ AND ─ cause A
│       cause B
└─ OR  ─ cause C
        cause D
```

### AND

Use AND when at least two causes must occur jointly for the parent disadvantage. Eliminating one may collapse that branch even if the other cause remains.

### OR

Use OR when any one of several independent causes can produce the parent disadvantage. Eliminating one leaves the others active.

## Procedure

1. State the initial disadvantage.
2. Ask “why does this disadvantage occur?”
3. Add direct causes only; do not jump over mechanism levels without explanation.
4. Use function/flow disadvantages whenever they match the chain.
5. Complete one branch deeply before proliferating branches.
6. Aim for at least several levels where useful; “five whys” is a heuristic, not a stopping law.
7. Mark every causal edge as `verified`, `supported`, `hypothesized`, or `unknown`.
8. Search for vicious circles/feedback loops.
9. Identify candidate key disadvantages near roots or at strategically useful intermediate nodes.
10. Select key disadvantages based on leverage, evidence, project control, and solvability.

## Evidence-aware edge format

| Parent disadvantage | Cause | Logic | Evidence | Confidence | Test |
|---|---|---|---|---|---|

Do not let CECA turn into storytelling. A plausible causal edge is still an assumption until supported.

## Key disadvantage selection

Prefer disadvantages that:

- causally control a large part of the chain;
- are linked to the project goal;
- can be transformed into an engineering/physical contradiction, Su-Field, function problem, trimming problem, feature-transfer problem, or ARIZ mini-problem;
- are within the allowed change envelope;
- do not merely restate the original symptom;
- have a realistic validation path.

A parameter-shaped disadvantage is often suitable for contradiction modeling, but not every key disadvantage must be a contradiction.

## Vicious circles

Represent feedback explicitly:

```text
D1 → D2 → D3 → D1
```

Breaking the highest-leverage edge may outperform solving the deepest local cause.

## Anti-patterns

- mixing positive effects into the chain;
- treating correlation or temporal order as causality;
- using only one linear chain where multiple causes exist;
- choosing the deepest node automatically;
- repeating the same disadvantage with different wording;
- hiding uncertainty in causal links;
- failing to distinguish AND from OR;
- choosing a cause outside project control while ignoring a tractable intermediate cause.

## Output

```text
Project goal:
Initial disadvantage:
CECA graph:
AND/OR logic:
Evidence status per edge:
Vicious circles:
Candidate key disadvantages:
Selected key disadvantage(s):
Rationale:
Key problem model(s):
Discriminating evidence still needed:
```

See `sources.md` for the public MATRIZ CECA procedure and terminology.
