# Scientific Effects and Function-Oriented Search (FOS)
# 科学效应库与功能导向搜索

Use these routes when the key problem is modeled as a **function** or when a physical contradiction needs a mechanism that the standard TRIZ transformations do not directly supply.

## Function model for search

Convert the desired action to a generalized function:

```text
[verb / physical action] + [generalized object] + [required conditions/performance]
```

Remove industry-specific nouns unless they are physically essential.

Bad:

```text
clean refinery heat-exchanger tube
```

Better:

```text
remove adherent solid/viscous deposit from a heat-transfer surface
without stopping flow and without contaminating the product
```

## FOS route

FOS searches for existing technologies worldwide that perform the same generalized function, especially in **leading areas** where that function is more demanding or important.

Procedure:

1. formulate generalized function;
2. identify demanding/leading areas;
3. search patents, standards, papers, products, biology/nature, and adjacent industries;
4. extract the underlying working principle, not the product name;
5. compare operating conditions;
6. adapt the mechanism to available resources;
7. formulate transfer contradictions/incompatibilities;
8. validate feasibility and novelty.

Search record:

| Source domain | Technology | Generalized function | Working principle | Conditions | Transfer mismatch | Evidence |
|---|---|---|---|---|---|---|

## Scientific-effects route

The scientific-effects database concept organizes physical, chemical, biological, geometric, and related phenomena by **function and resource**, rather than by discipline alone.

For a desired function, build an effects query:

```text
Required function:
Input resource available:
Desired output/effect:
Operating medium:
Length/time/energy scale:
Temperature/pressure/electrical/chemical range:
Forbidden materials/fields:
Control requirement:
Reversibility:
Safety constraints:
```

Then identify candidate effects such as:

- mechanical/wave/resonance;
- acoustic/ultrasonic;
- thermal/phase-transition;
- chemical/electrochemical;
- electrical/electrostatic;
- magnetic/electromagnetic;
- optical/photonics;
- capillary/interfacial;
- rheological/field-responsive;
- biological/biomimetic when technically justified.

OpenDeepMind does **not** ship a fabricated universal effects database. For real analyses, retrieve current technical sources and record provenance.

## Effect-to-concept translation

```text
Scientific effect
→ governing relation / activation conditions
→ available system resource
→ embodiment
→ useful effect
→ side effect / new contradiction
→ control method
→ validation experiment
```

Example structure:

```math
\text{effect feasibility}
= f(\text{material},\text{field},\text{scale},\text{boundary conditions},\text{control})
```

## Selection matrix

Score qualitatively or quantitatively on:

- function match;
- compatibility with operating conditions;
- resource availability;
- controllability;
- maturity/TRL where relevant;
- integration burden;
- new harmful effects;
- manufacturability;
- safety/regulatory impact;
- novelty/IP risk.

Do not rank effects by novelty alone.

## When to combine FOS with Feature Transfer

Use FOS when searching broadly by function. Use feature transfer when a concrete alternative system has been selected and a specific feature/advantage must be transferred into the base system.

## Output

```text
Generalized function:
Leading areas searched:
Candidate technologies/effects:
Source evidence:
Operating-condition match:
Mechanism:
Transfer/adaptation problem:
TRIZ principles/contradictions created:
Recommended embodiment(s):
Validation:
Novelty/patent search needed:
```

See `sources.md` for public MATRIZ FOS and scientific-effects definitions.
