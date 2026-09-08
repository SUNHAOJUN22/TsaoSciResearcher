# Worked Example — EV Battery Pack: Energy Density vs Thermal Safety

> Demonstration only. Cell chemistry, certification, propagation criteria, materials, thresholds, and test methods must be verified for the actual product and jurisdiction.

## 0. Scope

- System: rechargeable battery pack/module.
- Main function: store and deliver electrical energy safely over the required lifecycle.
- Initial disadvantage: tighter packing can improve volumetric energy density while reducing thermal-management space and increasing coupling between cells during faults.
- Resources: cell casing, inter-cell space, cold plate/coolant, BMS sensing/control, vent paths, module structure, phase/thermal properties.

## 1. Physical contradiction candidate

One possible formulation:

```text
The inter-cell region should conduct heat effectively during normal operation
because cells must reject routine heat,
AND it should impede harmful heat/flame/mass transfer during an abnormal event
because propagation must be limited.
```

This may be separable by **condition**, **space**, **system level**, or a combination.

## 2. IFR

```text
The pack remains densely integrated and rejects normal heat efficiently,
while the same local resources isolate abnormal heat/mass transfer when a fault occurs,
without adding an excessive active subsystem.
```

## 3. Concept families

### A. Condition-switching thermal interface

- TRIZ: separation by condition, parameter changes, phase transitions.
- Mechanism: thermal/interface properties change at a temperature/state threshold.
- Resource: inter-cell material/space.
- Unknowns: transition temperature, thermal conductivity in each state, cycle stability, flammability, aging.

### B. Spatial separation of normal and fault heat paths

- TRIZ: local quality, another dimension, segmentation.
- Mechanism: routine heat follows an engineered path to a cold plate while fault propagation path is interrupted by geometry/barriers/vent routing.
- Resource: cell casing, bottom/top interfaces, module structure.
- Unknowns: contact resistance, structural integrity, propagation pathways.

### C. Dedicated vent-flow supersystem path

- TRIZ: taking out, flow analysis, transition to supersystem.
- Mechanism: route vented gases/particles away from neighboring cells into a controlled channel/sink.
- Resource: pack enclosure / available voids / existing exhaust path.
- New contradiction: added volume/mass/pressure-drop/sealing complexity.

### D. Adaptive control / early isolation

- TRIZ: feedback, dynamization, decreasing human involvement where justified.
- Mechanism: detect anomalous state early and change electrical/thermal configuration before propagation.
- Resource: BMS sensors, contactors, thermal control.
- New contradiction: detection reliability versus false trips/complexity.

## 4. Engineering contradiction route

Candidate typical-parameter mappings should be tested rather than asserted automatically, e.g. volume/area/quantity versus reliability/temperature/complexity. Use the local matrix lookup and compare multiple justified mappings.

## 5. Su-Field route

A harmful thermal interaction can be modeled as:

```text
faulting cell (S2) --thermal/radiative/chemical field F_harm--> neighboring cell (S1)
```

Potential SIS classes:

- Class 1.2: destroy/neutralize harmful coupling;
- Class 2: improve controllability/structure of fields/substances;
- Class 5: introduce barriers, fields, phase transitions, or resources economically.

## 6. Substantiation

Required checks may include:

- normal-operation temperature uniformity;
- fault heat-release and propagation model;
- vent/pressure path;
- electrical isolation;
- materials compatibility/flammability;
- aging/cycling effects;
- structural crash/load interactions;
- BMS detection/diagnostic performance;
- representative propagation/safety testing.

## 7. Status rule

Do not label any of these concepts “safe” or “validated” until the actual cell/module data and required safety tests support that conclusion.
