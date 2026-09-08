# Substance–Field Modeling (Su-Field) / 物场建模

Su-Field modeling expresses a selected engineering problem as interactions among material objects (“substances”) and fields. In current MATRIZ practice it is used as a problem model; the 76 Standard Inventive Solutions process that model into solution models.

## Minimal model

A minimally functioning Su-Field contains:

```text
S1 ← F — S2
```

- `S1`: product / object receiving the action;
- `S2`: tool / object causing the action;
- `F`: physical interaction field.

MATRIZ commonly groups fields using **MATChEM**:

```text
Mechanical
Acoustic
Thermal
Chemical
Electrical
Magnetic / Electromagnetic
```

The field must correspond to a real interaction mechanism, not a metaphor such as “trust field” or “motivation field”.

## Problem models

### Incomplete Su-Field

One of the required substances/fields is missing.

```text
S1       (no effective S2/F)
```

Typical route: Class 1.1 standards — synthesize a workable interaction using the smallest available resource.

### Insufficient Su-Field

All three elements exist but useful action is too weak, unstable, unselective, or poorly controllable.

```text
S2 --F_weak--> S1
```

Typical route: Class 2 — complexification, segmentation, dynamization, field/substance structuring, rhythm coordination, Fe/E-field routes.

### Harmful / excessive Su-Field

The interaction produces unacceptable harm or useful action plus harmful excess.

```text
S2 ~~F_harm~~> S1
```

Typical route: Class 1.2 and related standards — third substance, modified existing substance, sacrificial sink, counter-field, switching off coupling.

### Measurement Su-Field

Measurement/detection can be modeled with an input field, sensing substance, and output field/signal.

Typical route: Class 4 standards.

## Modern relationship to CECA

Classical TRIZ used substance-field analysis itself to discover the relevant substances/fields. Modern MATRIZ notes that CECA now often identifies key disadvantages and the associated components/interactions first; Su-Field modeling then abstracts the selected problem.

Therefore:

```text
Function/flow analysis → CECA → key disadvantage → Su-Field model → 76 SIS
```

is usually stronger than forcing a Su-Field from the initial symptom.

## Modeling procedure

1. Select a key problem and operational zone.
2. Identify the object/product receiving the problematic action (`S1`).
3. Identify the tool/source (`S2`).
4. Identify the physical field/interactions (`F`).
5. Mark action as useful, insufficient, excessive, harmful, missing, or measurement-related.
6. Include relevant additives/environment only when they participate physically.
7. Choose the closest SIS class/standard.
8. Translate standard solution into a concrete physical embodiment.
9. Return concept to First Principles for physical validation.

## Complex models

- **Complex Su-Field:** add a responsive third substance/additive to `S1` or `S2`.
- **Chain Su-Field:** one substance participates in two linked Su-Fields.
- **Double Su-Field:** two different fields provide interactions between the same substances.
- **Fe-Field:** magnetic/ferromagnetic field-responsive form of Su-Field.
- **E-Field:** current/electrical-interaction analogue in the classical standards.

## Resource questions

Before adding a new `S3` or `F2`, ask:

- can `S1` or `S2` be modified to perform the role?
- can a void/bubble/foam/interface act as `S3`?
- is the needed substance/field already in the environment/supersystem?
- can a harmful/waste field be redirected into the useful role?
- can timing/geometry/segmentation eliminate the need for a new element?

## Output

```text
Key problem:
Operating zone/time:
S1:
S2:
F:
Su-Field type:
Useful/harmful interactions:
Resource inventory:
Selected SIS number/class:
Generic transformation:
Concrete embodiment:
Secondary contradiction:
Validation:
```

See `76_standard_solutions.md` and `sources.md`.
