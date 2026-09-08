# ARIZ-85C / 发明问题解决算法

ARIZ is the deep TRIZ route for a difficult key problem when quick contradiction/separation/standard-solution routes do not yield a satisfactory non-compromise concept. The public MATRIZ knowledge base presents ARIZ-85C as **9 parts organized in 3 blocks**.

> This file is an operational map, not a verbatim reproduction of ARIZ. For formal training or publication-critical use, consult the MATRIZ ARIZ-85C template/original source listed in `sources.md`.

## Three-block architecture

```text
Block 1 — Restructure the original problem
  Part 1: Analyze the system
  Part 2: Analyze the problem model
  Part 3: Define IFR and formulate physical contradiction

Block 2 — Remove the physical contradiction
  Part 4: Resolve the physical contradiction
  Part 5: Apply knowledge base / effects / standards / matrix
  Part 6: Change the mini-problem

Block 3 — Analyze and generalize the solution
  Part 7: Review the solution and contradiction removal
  Part 8: Develop maximum use of the solution
  Part 9: Review the solution process itself
```

---

# Part 1 — Analyze the system and restructure the problem

Produce these artifacts in order:

1. **Main function** and relevant system/supersystem components.
2. **Mini-problem**: preserve or simplify the system while obtaining the required result with minimal change.
3. **Base engineering contradiction** and **inverted contradiction**.
4. **Conflicting pair**: product/object acted upon and tool/object directly interacting with it.
5. Two states of the tool/product that create the opposing outcomes.
6. Select the base contradiction according to the main useful function and project goal.
7. **Intensify the conflict**: push the action/property in the IF-line toward an extreme to break optimization inertia.
8. Form the ARIZ problem model including conflicting pair, intensified contradiction, and an unknown **X-factor** that must provide the required effect without unacceptable harm.
9. Optionally test applicable Standard Inventive Solutions at the end of Part 1.

Output:

```text
System / supersystem:
Main function:
Mini-problem:
EC-1:
EC-2 inverted:
Product:
Tool:
Selected/intensified contradiction:
X-factor requirement:
```

---

# Part 2 — Analyze the problem model and resources

Localize the conflict.

- **Operating zone (OZ):** the spatial region where the contradictory interaction occurs.
- **Operating time (OT):** the time intervals associated with the opposing requirements; distinguish before/during/after or OT-1/OT-2 as appropriate.
- **Substance–field resources (SFR):** substances, fields, space, time, information, byproducts, voids, environment, supersystem resources, and latent properties available in/near OZ and OT.

Resource ledger:

| Resource | Where/when available | Useful property | Harm/risk | Controllability | Cost to mobilize |
|---|---|---|---|---|---|

Prefer resources already present before adding new components.

---

# Part 3 — Ideal Final Result and physical contradiction

Create an increasingly sharp target:

### IFR-1

```text
The X-element itself removes/prevents [harm]
while preserving [useful effect]
in OZ during OT,
using available resources and minimal system change.
```

### Macro physical contradiction

```text
Element/zone X must have property A because [requirement 1],
and property not-A because [requirement 2].
```

### Micro physical contradiction

Re-express the contradiction at the level of particles, structure, phase, field, interface, distribution, or microstate when this creates a new resolution path.

### IFR-2 / resource embodiment

State which available resource could ideally provide the contradictory function without a dedicated new subsystem.

---

# Part 4 — Resolve the physical contradiction

Use the smallest adequate resolution mechanism:

1. separation in space;
2. separation in time;
3. separation by condition/state;
4. separation between part/whole/system levels;
5. phase-state or structural transition;
6. resource mobilization;
7. void/absence as a resource;
8. field-controlled/smart material;
9. micro-level transition.

For each concept, show explicitly where `A` and `not-A` coexist without averaging into a compromise.

---

# Part 5 — Apply the TRIZ knowledge base

If direct separation is insufficient, route through the appropriate knowledge base:

- **76 Standard Inventive Solutions** for Su-Field problem models;
- **scientific effects** for a required function/effect;
- **40 Inventive Principles** and contradiction matrix as supporting search directions;
- **Function-Oriented Search** when an analogous function is likely solved elsewhere;
- validated domain physics/chemistry/biology knowledge.

Do not select a scientific effect only because its name resembles the target function. Match operating conditions, scale, materials, controllability, and failure modes.

---

# Part 6 — Change the mini-problem when stuck

If no strong solution exists:

- reconsider the chosen base versus inverted contradiction;
- reselect the conflicting pair;
- widen the system boundary;
- narrow to a smaller operational zone;
- split the problem into independent mini-problems;
- combine related mini-problems when their interaction is the real bottleneck;
- invert the objective (use the harmful factor rather than merely suppress it);
- change the system level or mechanism class.

A failed concept is evidence about the problem model, not only about the concept.

---

# Part 7 — Review the solution and contradiction removal

For each leading concept:

1. confirm the physical contradiction is **resolved**, not averaged;
2. compare the concept with IFR/ideality;
3. identify secondary contradictions;
4. identify side effects and new harmful functions;
5. test physical feasibility and dimensional consistency;
6. define falsifying evidence or a rejecting experiment;
7. compare against at least one rival embodiment.

---

# Part 8 — Develop maximum use of the solution

Ask how the concept propagates through system and supersystem:

- can the same mechanism replace other components/functions?
- can new useful functions be obtained with no or little extra cost?
- can the concept be generalized to adjacent operating modes/products?
- can a new bi/poly-system, supersystem role, or platform emerge?
- can the new system subsequently be trimmed/convolved?

Also identify new problems introduced; queue them as separate TRIZ/OpenDeepMind problems rather than hiding them.

---

# Part 9 — Review the solution process

Conduct a process post-mortem:

```text
Original frame:
Where the real contradiction emerged:
Which resource was decisive:
Which step changed the solution space:
Methods attempted but rejected:
What evidence discriminated concepts:
What should be added to the knowledge base:
What would make a future run faster or more reliable:
```

This is how the skill becomes a learning system rather than a one-shot prompt.

---

# Invocation rules

Use ARIZ when:

- the user explicitly requests `ARIZ` / deep TRIZ;
- quick matrix/principle/separation/Su-Field routes repeatedly yield compromises;
- the problem remains fuzzy after basic contradiction formulation;
- a minimal-change mini-problem and precise physical contradiction are needed.

Do not invoke ARIZ merely because the problem is long or difficult. If evidence about the system is missing, collect/verify it first.

# Provenance

This operational version is newly structured for OpenDeepMind from the classical ARIZ-85C lineage, the MIT-licensed `Antropocosmist/triz-engineering-solver/resources/ariz_85c.md`, and the public MATRIZ ARIZ documentation. See `sources.md`.
