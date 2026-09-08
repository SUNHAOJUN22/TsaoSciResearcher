# Trends of Engineering System Evolution (TESE) / 工程系统进化趋势

Use TESE primarily for **roadmapping, next-generation architecture, bottleneck identification, and design-space expansion**, not as proof that a specific future will occur. OpenDeepMind treats evolution trends as structured hypothesis generators whose predictions require evidence, competing paths, and falsifiers.

## Modern MATRIZ hierarchy

```text
Trend of S-curve evolution
└── Trend of increasing value
    ├── Transition to the supersystem
    ├── Increasing degree of trimming
    ├── Increasing completeness of system components
    │   └── Decreasing human involvement
    ├── Flow enhancement
    └── Increasing coordination
        ├── Increasing controllability
        │   └── Increasing dynamization
        └── Uneven development of system components
```

The exact hierarchy continues to evolve in modern TRIZ practice; use the current MATRIZ Knowledge Base for project-critical taxonomy.

---

## 1. S-curve evolution

For a selected **main parameter of value (MPV)**, model performance/value against time:

```text
Stage 1 — emergence / prototype
Transition — first serious market/operational competition
Stage 2 — rapid growth
Stage 3 — maturity / limits
Stage 4 — decline, specialization, supersystem absorption, or replacement
```

Do not place a system on an S-curve using intuition alone. Examine:

- MPV history and rate of improvement;
- technical limits and resource consumption;
- patent/research activity where available;
- market adoption, competition, production scale, cost trends;
- emergence of alternative principles of operation;
- investment needed for incremental improvement versus a new curve.

A system may occupy different stages for different MPVs.

---

## 2. Increasing value

Value is treated comparatively: useful functionality and customer/system benefit increase relative to payment factors such as cost, complexity, mass, energy, maintenance, environmental burden, risk, and space.

```math
V \sim \frac{\text{useful functionality / value}}{\text{payment factors}}
```

Use this as a design direction, not a universal scalar unless the quantities are operationalized.

---

## 3. Transition to the supersystem

As local improvement saturates, integrate with other systems/supersystem resources.

Four useful mechanisms:

1. **Increasing difference in parameters** among systems that perform the same/similar main function.
2. **Increasing difference in main functions** of integrated systems: allied → heterogeneous → inverse/complementary systems.
3. **Deeper integration**: unlinked → partially trimmed → deeply integrated / difficult to separate.
4. **Increasing number of integrated systems**: mono → bi → poly-system.

Every proposed integration should answer:

```text
New resource gained:
Component/function made redundant:
Integration burden:
New coupling/failure mode:
Potential later trimming/convolution:
```

---

## 4. Increasing degree of trimming

Systems tend to eliminate components or operations while preserving or improving functions by redistributing them to:

- remaining system components;
- the product/object itself;
- supersystem components;
- fields, materials, geometry, information, or environment.

This trend motivates `trimming.md`, but removal is not inherently progress. Preserve safety, redundancy, maintainability, legal duties, and robustness.

---

## 5. Increasing completeness of system components

Engineering systems evolve toward acquisition/integration of the function blocks required to operate effectively, commonly including:

- operating agent / working element;
- transmission;
- energy source;
- control system.

A subsystem may initially outsource these functions to humans or the supersystem and later internalize them.

### Decreasing human involvement

A common development path is progressive transfer from humans to the engineering system, especially:

1. transmission/actuation functions;
2. energy-supply functions;
3. control functions;
4. decision-making functions.

Do not equate less human involvement with better design when human judgment is a required safety, ethical, legal, or resilience mechanism.

---

## 6. Flow enhancement

Flows include substance, energy/field, and information.

### Useful-flow directions

Improve conductivity/utilization by considering:

- fewer transformations;
- more efficient flow type;
- shorter path;
- removal of bottlenecks, stagnant or gray zones;
- bypasses;
- increased channel conductivity or flow density;
- recirculation;
- modulation/resonance/pulsing;
- combining useful flows;
- using one flow to support another;
- moving flow through a supersystem channel.

### Harmful/accidental-flow directions

Reduce transmission or impact by considering:

- lower-conductivity path;
- longer/segmented path or bottleneck where safe;
- anti-flow/counter-flow;
- redistribution/bypass;
- modifying the vulnerable object/channel;
- preset neutralizing substance/energy/information;
- transfer to supersystem;
- recovery/recycling of waste flows.

See `flow_analysis.md` before applying the trend.

---

## 7. Increasing coordination

System components and supersystem interfaces tend toward more effective coordination.

### Coordination of shape

Use identical, self-compatible/nestable, compatible-with-supersystem, or specially adapted shapes depending on function.

### Coordination of rhythms

- identical/synchronized rhythms;
- complementary rhythms filling one another's idle periods;
- special matching/detuning, including resonance/anti-resonance.

### Coordination of materials

Explore identical, similar, inert, shifted-parameter, and opposite/complementary material combinations.

### Coordination of action/contact dimensionality

Transition between point (0D), line (1D), surface (2D), and volume (3D) interaction. Direction depends on whether the interaction is useful/harmful and which resources exist.

---

## 8. Increasing controllability

A developing system generally gains more independent ways to influence relevant parameters, states, locations, timing, and feedback.

Questions:

- which state cannot currently be sensed?
- which parameter can be sensed but not controlled?
- is control open-loop or feedback-based?
- can action be localized in space/time/condition?
- can the system become adaptive without excessive complexity?

### Increasing dynamization

Dynamization supports controllability.

**Substance/structure line:** monolith → zones → joints → multi-joint → flexible → dispersed/powder → liquid/gas → field-mediated, where physically appropriate.

**Field line:** constant → spatial gradient → time-varying → pulsed → resonant → structured/interference-based/adaptive.

**Function line:** single-function → multifunctional/adaptive function sets.

Not every system must traverse every stage.

---

## 9. Uneven development of components

Subcomponents evolve at different rates; the slowest/development-limiting element becomes a new bottleneck.

Procedure:

1. identify main function and MPVs;
2. list subsystems/functions;
3. estimate maturity/limit for each;
4. identify mismatch that restricts system value;
5. formulate the limiting subsystem as a key disadvantage/problem;
6. solve locally or shift system architecture/supersystem relation.

Do not assume the oldest component is the bottleneck; verify performance and causal dependence.

---

# Roadmapping protocol

```text
1. Define system, supersystem, main function, and MPVs.
2. Determine evidence for current S-curve stage for each major MPV.
3. Apply all materially relevant TESE branches.
4. Generate at least three evolution hypotheses.
5. Identify required enabling resources/technologies.
6. Identify competing evolution paths and replacement technologies.
7. Specify leading indicators and falsifiers.
8. Convert the strongest hypotheses into staged R&D/engineering options.
```

Output:

| Horizon | Trend | Predicted transition | Resource/enabler | Competing path | Leading signal | Falsifier |
|---|---|---|---|---|---|---|

# Classical eight-trend crosswalk

Older summaries often present eight broad recurring directions: increasing ideality, uneven subsystem development, supersystem transition, micro-level transition, increasing dynamism, complexity then convolution, matching/mismatching, and reduced human involvement. OpenDeepMind retains these as historical shorthand but routes new analyses through the more explicit modern MATRIZ hierarchy above.

# Provenance

Built from the classical TRIZ evolution tradition, the MIT-licensed `Antropocosmist/triz-engineering-solver/resources/evolution_trends.md`, and the current public MATRIZ TESE/S-curve knowledge-base articles. See `sources.md`.
