# Flow Analysis / 流分析

Flow analysis identifies disadvantages in the movement of **substance, energy/fields, and information** through an engineering system. Use it when the initial problem involves transport, conversion, distribution, bottlenecks, waste, accumulation, leakage, delay, or poorly utilized resources.

## Flow model

For each material flow:

```text
source → channel/component → transformation → sink/use
```

Record:

| Flow ID | Type | Source | Channel | Transformations | Destination | Useful/harmful/neutral | Key parameters |
|---|---|---|---|---|---|---|---|

Types:

- substance/material;
- energy/field;
- information/signal.

## Main disadvantage families

### 1. Conductivity disadvantages

Examples:

- bottleneck / local high resistance;
- stagnant zone;
- poor transferability;
- unnecessarily long path;
- high channel resistance;
- low flow density;
- excessive number of transformations.

### 2. Utilization disadvantages

Examples:

- gray zone / state difficult to predict or control;
- channel damages flow;
- flow damages channel;
- useful flow reaches destination but is poorly used;
- recoverable residual/waste flow is discarded.

### 3. Harmful or accidental flows

Examples:

- leaked heat, vibration, noise, current, chemicals, contamination, stress, radiation, information;
- reverse flow/backflow;
- parasitic coupling/crosstalk;
- harmful flow reaching a vulnerable component.

### 4. Flow partition / distribution disadvantages

Examples:

- uneven division;
- under-supplied branch;
- over-supplied branch;
- poor mixing or segregation;
- maldistribution across parallel channels;
- unstable switching between routes.

## Procedure

1. Define the function that each flow enables.
2. Trace the flow from source to sink, including transformations and storage/accumulation.
3. Mark useful, harmful, neutral, and wasted portions.
4. Quantify where possible: rate, density, pressure/voltage/temperature gradient, latency, loss, transformation efficiency, residence time, entropy/quality degradation.
5. Identify disadvantage locations.
6. Connect flow disadvantages to function disadvantages and CECA.
7. For redesign, use TESE flow-enhancement mechanisms only after the baseline flow model is explicit.

## Design directions after diagnosis

For useful flows consider:

- remove transformations;
- shorten path;
- reduce bottlenecks/stagnation;
- improve channel conductivity/density;
- recirculate or redistribute;
- combine compatible flows;
- use a flow to carry another flow;
- move the flow into a better supersystem channel.

For harmful flows consider:

- decrease channel conductivity;
- add transformation/barrier/sink;
- redirect/bypass;
- anti-flow/counter-field;
- modify the vulnerable object;
- recover/recycle the harmful/waste flow;
- convert harm into useful function.

These are search directions, not automatic solutions.

## Output

```text
Flow inventory:
Flow diagrams:
Measured/estimated parameters:
Flow disadvantages:
Key flow disadvantage candidates:
CECA links:
Relevant resources:
Potential flow-enhancement directions:
Required measurements:
```

See `sources.md` for current MATRIZ definitions and flow-disadvantage taxonomy.
