# Separation Principles for Physical Contradictions / 物理矛盾分离原则

A physical contradiction exists when one element or one system parameter must satisfy two justified opposite requirements. Unlike an engineering contradiction, it is normally resolved by separating the opposing states along an independent axis rather than by compromise.

| Axis | Core question | Typical implementation families | Linked principles |
|---|---|---|---|
| **Space / 空间** | Can `A` exist in one region and `¬A` in another? | layers, gradients, segmented zones, local quality, interfaces | #1, #3, #4, #7, #17, #30 |
| **Time / 时间** | Can `A` exist during one interval and `¬A` during another? | pulsing, sequencing, deployment/retraction, pre-action, duty cycling | #9, #10, #15, #18, #19, #20, #21, #34 |
| **Condition / 条件** | Can the state switch with load, temperature, field, concentration, phase, frequency, or interaction? | smart materials, feedback, phase transitions, threshold devices | #28, #31, #32, #35, #36, #37, #38, #39 |
| **System level / 系统层级** | Can parts carry one property while the whole/supersystem carries the opposite? | composites, nested systems, poly-systems, distributed functions | #1, #5, #6, #25, #33, #40 |

## Decision procedure

For `Element X must be P and not-P`:

1. Verify that both requirements are real, measurable, and refer to the same parameter of the same relevant element.
2. Test space: identify regions where only one requirement is active.
3. Test time: identify operating phases, transitions, or duty cycles.
4. Test condition: identify a state variable that can switch the property.
5. Test system level: distribute the opposing requirements across part/whole/supersystem.
6. If none works, return to problem formulation; the contradiction may be misframed.

## Output contract

```text
Element:
Contradictory parameter:
State A and justification:
State not-A and justification:
Chosen separation axis:
Separation variable:
Transition/control mechanism:
Failure mode:
New contradiction introduced:
Validation test:
```

## Example

Landing gear must be present for takeoff/landing and absent during cruise. The requirement is separated in **time**: extend it only during the relevant operating phases.

## Caution

Separation is not successful merely because two regions/times are named. The transition mechanism, control authority, response time, durability, and secondary effects must be engineering-feasible.

## Provenance

Adapted from the MIT-licensed `Antropocosmist/triz-engineering-solver/resources/separation_principles.md` and cross-checked against public Altshuller Institute descriptions of physical contradictions and separation.
