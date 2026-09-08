# Trimming / 裁剪

Trimming improves an engineering system by eliminating a component/operation or unloading part of its useful functions, then redistributing the required functions to remaining system or supersystem resources.

> Trimming is not “delete components aggressively.” A component can be removed only when its necessary useful functions are eliminated, transferred, or no longer required without violating hard constraints.

## Inputs

- validated function model;
- function ranks/performance;
- component costs where relevant;
- key disadvantages;
- safety, legal, reliability, maintainability and lifecycle constraints.

## Two modes

### Complete trimming

Remove the component/operation and redistribute all required useful functions.

### Partial trimming

Retain the component but transfer some useful functions elsewhere so it can become smaller, cheaper, lighter, simpler, cooler, less stressed, etc.

## Generic redistribution targets

For every useful function of the candidate component, test whether it can be:

1. eliminated because the need disappears after another change;
2. performed by the function object/product itself;
3. performed by another system component;
4. performed by a supersystem/environment component;
5. performed by a field, material property, geometry, interface, software/control, or existing resource;
6. combined with another function in a multifunctional component.

The exact classical trimming rules differ for devices and processes; use the current MATRIZ references when strict rule numbering is needed.

## Procedure

1. Select component/operation to trim based on function/cost disadvantage or key-disadvantage link.
2. List every useful function it performs.
3. For each function, select a redistribution/elimination rule.
4. Build a candidate trimming model.
5. Identify **trimming problems** created by the new model.
6. Solve those problems through contradiction, Su-Field, FOS/effects, feature transfer, or ARIZ.
7. Repeat for other components and compare alternative trimming models.
8. Validate against hard constraints and system-level risks.

## Trimming model

| Removed/unloaded component | Useful function | New carrier or eliminated need | New problem | Evidence/constraint |
|---|---|---|---|---|

A trimming model is itself a new function model and must be audited as such.

## Evaluation

Compare baseline versus trimmed concept:

```math
\Delta V \sim \Delta(\text{functionality})-\Delta(\text{cost+complexity+risk})
```

Also inspect:

- fault tolerance and redundancy;
- failure containment;
- maintainability/inspectability;
- manufacturing/process complexity;
- coupling to supersystem;
- energy/material/information flows;
- new single points of failure;
- regulatory/safety requirements.

## Anti-patterns

- deleting a safeguard because it has no “productive” function;
- ignoring latent/emergency functions;
- moving complexity to software/supersystem and pretending it disappeared;
- trimming a component before function modeling;
- removing redundancy without reliability analysis;
- using cost alone as the trimming criterion.

## Output

```text
Candidate component:
Reason for trimming:
Useful functions:
Complete or partial trimming:
Redistribution plan:
Trimming model:
New trimming problems:
New contradictions:
Value/ideality impact:
Hard blockers:
Validation plan:
```

See `sources.md` for public MATRIZ trimming/trimming-model/partial-trimming references.
