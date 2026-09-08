# Worked Example — Heat Exchanger Fouling

> Demonstration for process engineering. Fouling mechanisms differ by service; use actual fluid chemistry, hydraulics, heat flux, metallurgy, process constraints, and operating history.

## 0. Scope

- System: shell-and-tube or analogous heat exchanger.
- Main function: transfer thermal energy between process streams while maintaining separation/required flow conditions.
- Initial disadvantage: deposit formation degrades heat transfer and/or raises pressure drop, causing energy/throughput/maintenance penalties.
- Resources: process flow, temperature/pressure gradients, tube/shell surfaces, utilities, shutdown cycles, vibration/acoustic/field possibilities, downstream separation.

## 1. Function and flow analysis

Useful functions:

```text
hot stream → transfers heat → wall
wall → transfers heat → cold stream
```

Potential harmful functions/flows:

```text
foulant species/particles → adhere/react/deposit → surface
surface roughness/deposit → increases resistance → flow
fouling layer → insulates → heat transfer
```

Flow analysis should identify the actual deposition zones, boundary-layer conditions, stagnant areas, transformation steps, and whether the mechanism is precipitation, particulate deposition, reaction/coking, corrosion product, biological growth, or another process.

## 2. Key problem candidates

A CECA may produce different roots, for example:

- wall conditions favor adhesion/reaction;
- boundary-layer mass/heat transfer creates local supersaturation;
- shear is insufficient in the operational zone;
- upstream contamination reaches the surface;
- cleaning action is intermittent/expensive;
- the mitigation method itself imposes pressure-drop/energy penalties.

Select the key problem only after evidence links it to the initial disadvantage.

## 3. Engineering contradiction example

A common generic contradiction is:

```text
IF flow disturbance/turbulence or cleaning action is increased,
THEN deposition tendency decreases,
BUT pressure drop, energy use, erosion, vibration, or complexity may increase.
```

Map to 39 parameters only after selecting the exact physical variables. Use `lookup_matrix.py` for the selected pair.

## 4. Physical contradiction example

For some services:

```text
The wall/interface must interact strongly with the process fluid
because heat transfer requires contact,
AND must interact weakly/non-adhesively with foulant species
because deposition must be suppressed.
```

Potential separation: local quality, condition-dependent surfaces, phase/interface effects, temporal cleaning cycles.

## 5. Su-Field model

Example harmful model:

```text
foulant/process species (S2) --chemical/thermal/mechanical F_harm--> wall/deposit surface (S1)
```

Routes to investigate:

- 1.2.1/1.2.2: interpose or derive a protective/intermediate state;
- 1.2.4: counteracting field/action;
- 2.2: dynamize/structure field or surface;
- Class 5: use existing fields, temporary substances, phase transitions, or environmental resources.

## 6. Concept families

### A. Conditioned / low-adhesion surface

- TRIZ: local quality, parameter changes, SIS 1.2.2.
- Mechanism: alter wall/interface chemistry/topography so adhesion/reaction is reduced while thermal resistance remains acceptable.
- Secondary contradiction: coating/texture durability and added thermal resistance.

### B. Periodic/pulsed hydrodynamic action

- TRIZ: periodic action, field dynamization, rhythm coordination.
- Mechanism: create transient shear/flow structures only when needed rather than imposing permanent high pressure drop.
- Resource: existing process flow/control/valves/pumps if compatible.
- Secondary contradiction: process disturbance/control burden/fatigue.

### C. Acoustic/vibration cleaning

- TRIZ: mechanical vibration, field structuring, counter-field.
- Mechanism: disrupt incipient deposit attachment or fracture weak deposits.
- Secondary contradiction: fatigue, resonance, coupling efficiency, power, local effectiveness.

### D. Multiphase/interface disruption

- TRIZ: segmentation, phase transitions/two-phase state, Su-Field third substance.
- Mechanism: use controlled bubbles/droplets/phase behavior to disturb boundary layer or interpose a low-adhesion interface.
- Secondary contradiction: downstream separation, cavitation/erosion, process contamination, pressure behavior.

### E. Upstream extraction / foulant removal

- TRIZ: taking out, flow analysis, FOS/effects.
- Mechanism: remove or transform deposition precursor before the heat-transfer zone.
- Secondary contradiction: separator/regeneration burden, product loss.

### F. Self-monitoring / predictive intervention

- TRIZ: feedback, measurement standards, decreasing human involvement when justified.
- Mechanism: infer fouling state from heat-transfer/pressure/thermal signatures and trigger cleaning or operating change before severe degradation.
- Secondary contradiction: sensor/model uncertainty and false interventions.

## 7. Substantiation

For shortlisted concepts evaluate:

- overall heat-transfer coefficient and fouling resistance over time;
- pressure drop and pump energy;
- deposition/cleaning kinetics;
- wall temperature and reaction risk;
- erosion/corrosion/fatigue;
- contaminant/product compatibility;
- operability and control transients;
- turnaround/maintenance burden;
- CAPEX/OPEX and lifecycle;
- representative pilot or side-stream test.

## 8. Lesson

The strongest TRIZ move is often not “apply Principle #X”; it is finding the **right key disadvantage and physical interaction** before selecting a solution model.
