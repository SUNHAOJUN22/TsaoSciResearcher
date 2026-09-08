# Psychological-Inertia Tools / 克服心理惯性工具

TRIZ does not only provide contradiction and knowledge-base tools. Classical TRIZ and ARIZ also use deliberate **thinking operators** to escape optimization inertia, fixed scale assumptions, component fixation, and visually obvious but structurally weak problem frames.

These operators generate **reframings and hypotheses**. They do not validate engineering concepts.

---

## 1. Multi-Screen / Nine Windows / System Operator

Detailed file: [`multiscreen_operator.md`](multiscreen_operator.md).

Core 3×3 view:

|  | Past | Present | Future |
|---|---|---|---|
| Supersystem | previous environment | current supersystem | possible future supersystem |
| System | predecessor | current system | next-generation system |
| Subsystem | previous mechanism/material | current mechanism/material | possible lower-level transition |

Use it to find:

- supersystem resources;
- historical constraints that no longer apply;
- micro-level mechanisms;
- potential trimming/integration;
- new system boundaries;
- alternative future curves.

Do not treat the future cells as predictions without evidence.

---

## 2. STC / Size–Time–Cost Operator

The STC operator deliberately drives three dimensions to unrealistic extremes to expose hidden assumptions and alternative mechanisms.

For each dimension ask both extremes.

### Size

```text
What if the system/component were extremely small, approaching micro/nano scale?
What if it were extremely large, approaching the supersystem/environment scale?
```

Explore:

- surface/volume scaling;
- local versus distributed functions;
- field dominance;
- discrete versus continuum behavior;
- interfaces and gradients;
- modularity/poly-systems.

### Time

```text
What if the required event occurred almost instantaneously?
What if it took an extremely long time?
```

Explore:

- impulses/pulses;
- transient versus steady-state behavior;
- pre-action/post-action;
- aging/creep/diffusion;
- idle-time resources;
- sequencing and time separation.

### Cost

```text
What if cost were effectively unlimited?
What if the solution had to cost almost nothing?
```

Explore:

- what the technically ideal mechanism would be without budget restriction;
- which expensive functions/components are merely implementation choices;
- which existing/free resources could replace added components;
- what minimum sufficient architecture remains at near-zero cost.

### STC result format

| Dimension | Extreme | Assumption exposed | New mechanism/resource | Reality translation |
|---|---|---|---|---|

The final concept must return from the extreme thought experiment to real constraints.

---

## 3. Smart Little People (SLP) / 小人模型

SLP replaces a difficult-to-imagine field, continuous medium, interface, or microstructure with a population of imaginary small agents that can move, group, separate, change state, carry loads, block/permit flows, or coordinate locally.

Use it when:

- the conflict occurs in a continuous material/field/interface;
- macro-level language hides the required local state distribution;
- a physical contradiction may be resolved by microstructure, spatial distribution, or local coordination;
- ARIZ has localized an operating zone but the physical transformation remains hard to visualize.

### Procedure

1. Draw/describe the operating zone.
2. Replace relevant material/field behavior with many identical small agents.
3. State what the agents currently do under the harmful condition.
4. State what they must do to satisfy the useful requirement.
5. Allow different agents to occupy different states/locations/times if needed.
6. Look for the minimum rule change that creates the desired collective behavior.
7. Translate that rule back into a real physical mechanism:
   - particles;
   - pores/cells;
   - domains/phases;
   - fibers/layers;
   - droplets/bubbles;
   - field-responsive inclusions;
   - local states/gradients;
   - interfaces/defects;
   - distributed control elements.
8. Validate the translation with actual physics.

### Example abstraction

Instead of:

```text
“The surface must be both permeable and impermeable.”
```

SLP may suggest:

```text
some local elements open only under condition C,
others remain closed,
and collective connectivity changes sharply at a threshold.
```

Engineering translations might include valves, phase-changing pores, stimuli-responsive membranes, percolation networks, or distributed shutters—only if the governing mechanism supports them.

---

## 4. Intensification of contradiction

ARIZ deliberately pushes a selected IF-parameter to an extreme to defeat ordinary optimization thinking.

Examples:

```text
“lighter” → zero mass / component disappears
“smaller” → zero size
“faster”  → instantaneous
“less contact” → no contact
“lower cost” → no dedicated component/resource
```

Then reformulate THEN/BUT effects and ask what resource/mechanism could make the extreme state workable.

This is a conceptual operator, not a literal requirement.

---

## 5. Inversion and harmful-resource conversion

Useful supplementary prompts:

- instead of preventing the harmful effect, can it be used?
- instead of moving the tool, move the product/environment;
- instead of adding a component, remove one;
- instead of strengthening the desired action, weaken the reason it is needed;
- instead of suppressing a flow, redirect/recycle it;
- instead of measuring directly, make the system self-regulating or measure a derivative/proxy.

Keep only concepts that preserve the actual main function and constraints.

---

## 6. Integration with the OpenDeepMind claim ledger

Every insight from these operators begins as:

```text
A — assumption challenged
U — speculative mechanism / unknown
```

It becomes a supported engineering claim only after physical/evidence validation.

Do not let an imaginative reframe enter the proposition ledger as `O` (observation) or `L` (law).

---

## 7. Provenance

- MATRIZ ARIZ documentation emphasizes overcoming psychological inertia and intensifying contradictions/resources.
- Altshuller Institute materials and TRIZ literature describe Nine Windows/System Operator and Smart Little People as tools for escaping psychological inertia.
- Size–Time–Cost is a classical TRIZ creativity/psychological-inertia operator used to drive problem parameters to extremes.

See [`sources.md`](sources.md) for links and provenance notes.
