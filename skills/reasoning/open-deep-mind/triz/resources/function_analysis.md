# Function Analysis / 功能分析

Function analysis converts an engineering system from a component description into a network of **functions, performance levels, disadvantages, and costs**. It is the foundation for CECA, trimming, feature transfer, and many problem-solving routes.

## Function grammar

Use a concrete affirmative relation:

```text
Function carrier → action → function object
```

or, when needed:

```text
Component A changes / maintains parameter X of Component B
```

Avoid vague verbs such as “provide”, “protect”, “optimize”, “support”, or “improve” unless translated into a measurable change/maintenance of an object's parameter.

A function carrier does not act on itself; split the object if needed.

## Component model

Include:

- system components;
- target component/object of the main function;
- materially relevant supersystem components;
- environment when it participates in functions/flows;
- human operator only when a human truly performs/receives engineering functions.

## Function categories

At minimum distinguish:

- **useful function** — changes/maintains the object in a required direction;
- **harmful function** — changes/maintains it in an unacceptable direction;
- **measurement function** — reveals information about a component/state.

For device/process analysis, useful functions may additionally be ranked by main/basic, additional/auxiliary or productive/providing/supporting/corrective roles as appropriate to the selected MATRIZ convention.

## Performance level

For each useful function mark:

- sufficient/normal;
- insufficient;
- excessive.

Function disadvantages therefore include:

```text
harmful function
useful but insufficient function
useful but excessive function
```

These are direct inputs to CECA.

## Function model table

| ID | Carrier | Action | Object | Category | Performance | Evidence | Cost share | Disadvantage |
|---|---|---|---|---|---|---|---:|---|

For a device, also construct an interaction matrix if needed before finalizing functions.

## Cost analysis

When project goals involve cost/value, record absolute and relative component costs. A high relative cost with low functional contribution is a candidate cost disadvantage/trimming target, but cost alone never authorizes removal.

A simple internal diagnostic may be:

```math
\text{value index}_i \propto \frac{\text{normalized functional contribution}_i}{\text{relative cost}_i}
```

Do not invent precise scores without a defined scoring scheme.

## Procedure

1. Define system boundary and main function.
2. Build component model including relevant supersystem elements.
3. Identify physical interactions.
4. Convert interactions into correctly worded functions.
5. Classify useful/harmful/measurement and performance level.
6. Add cost data if relevant.
7. Extract function/cost disadvantages.
8. Pass disadvantages to CECA; pass function model to trimming and feature transfer.

## Quality checks

- main function acts on the correct target component;
- all functions have carrier, action, object;
- wording is physical/operational rather than intention-based;
- harmful effects are represented as harmful functions, not adjectives;
- sufficient/insufficient/excessive judgments have evidence or explicit assumptions;
- supersystem resources are not omitted merely because they are outside the product bill of materials;
- costs are not confused with harmful functions.

## Output

```text
System:
Main function:
Target component:
Component model:
Function model:
Function disadvantages:
Cost disadvantages:
Candidate components for CECA/trimming/feature transfer:
Unknowns / missing measurements:
```

See `sources.md` for the public MATRIZ function-analysis/function-model definitions used in this module.
