# Ideality, IFR and Resource Analysis / 理想度、IFR 与资源分析

TRIZ directs invention toward more useful function with fewer payment factors and toward solving a **specific problem** with minimal system change.

## 1. Ideality

A common conceptual form is:

```math
I = \frac{\sum B}{\sum P}
```

where `B` represents useful benefits/functions and `P` represents payment factors such as:

- direct cost;
- harmful functions;
- complexity;
- material/energy use;
- occupied space/mass;
- maintenance and downtime;
- environmental burden;
- safety/reliability risk;
- lifecycle burden.

MATRIZ explicitly cautions that there is no universally established numerical calculation system for ideality. Therefore OpenDeepMind prefers **relative ideality** and transparent criteria:

```math
\Delta I = I_{concept} - I_{baseline}
```

If terms are not commensurable, use a qualitative comparison rather than fabricated precision.

## 2. Ideal system versus IFR

### Ideal system

Limiting concept: function remains while components/payment factors tend toward zero.

```text
The system tends not to exist, but its main function is still performed.
```

This is a direction-of-evolution concept.

### Ideal Final Result (IFR)

ARIZ problem-solving target for a **specific problem**:

```text
The problem is fully eliminated with minimal changes to the existing system,
without deterioration of relevant system parameters.
```

The real system still exists, has cost, occupies space, and requires maintenance.

Do not confuse ideal system and IFR.

## 3. IFR construction

Start with a concrete problem model, operational zone/time, and resources:

```text
The available X-resource itself performs [required function]
in [operating zone] during [operating time],
while preserving [useful effect] and eliminating [harmful effect],
with minimal new substance/field/component and no unacceptable secondary harm.
```

IFR is a search target, not a claim that such a solution exists.

## 4. Resource taxonomy

Inventory resources at system, subsystem, environment, and supersystem levels.

| Class | Examples |
|---|---|
| Substance | existing components, coatings, particles, waste, byproducts, impurities |
| Field | mechanical, acoustic, thermal, chemical, electrical, magnetic/EM |
| Space | cavities, free surfaces, interfaces, gradients, unused dimensions |
| Time | pauses, startup, shutdown, transient states, pre/post-process intervals |
| Information | sensor signals, noise patterns, state history, correlations |
| Functional | duplicated/idle functions, self-service, feedback opportunities |
| Supersystem | environment, neighboring equipment, infrastructure, user/process resources |
| Harmful resources | heat, vibration, pressure, friction, contamination, waste flows that may be redirected |
| Void/absence | vacuum, cavities, bubbles, gaps, removal of a substance/component |

## 5. Resource-quality test

For each resource record:

```text
availability:
location/time:
quantity/intensity:
variability:
controllability:
compatibility:
safety:
cost to mobilize:
new harm created:
```

“Free resource” means already present, not necessarily zero-risk or zero-cost to exploit.

## 6. Ideality comparison table

| Concept | Useful effects gained | Harm reduced | Added cost/complexity | New risks | Resource reuse | Relative ideality |
|---|---|---|---|---|---|---|

Do not reject a concept solely because it adds a component if the net system-level value/ideality improves materially.

## 7. Resource-first concept generation

Before adding new technology ask:

1. Can a current system component perform the function?
2. Can the object/product itself perform it?
3. Can the environment/supersystem perform it?
4. Can a harmful/waste effect be converted?
5. Can timing/space/structure make the function unnecessary?
6. Can a temporary substance/field disappear after its task?
7. Can a phase transition or threshold effect self-regulate the action?

## Output

```text
Baseline ideality/payment factors:
IFR:
OZ / OT:
Resource inventory:
Resources rejected and why:
Concept relative-ideality comparison:
Secondary contradictions:
Validation required:
```

See `sources.md` for current MATRIZ definitions of ideality, ideal system, IFR and ARIZ resource use.
