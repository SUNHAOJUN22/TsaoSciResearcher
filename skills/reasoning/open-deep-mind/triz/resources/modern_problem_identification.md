# Modern TRIZ Problem Identification / 现代 TRIZ 问题识别

A complete TRIZ module should not begin every project with the 40 principles. Modern MATRIZ practice separates **problem identification**, **problem solving**, and **concept substantiation**.

## Goal

Convert the project goal and observable symptoms into a small set of **key problems** worth solving. The exact tool order is project-dependent.

## Toolbox

| Tool | Main question | Main output |
|---|---|---|
| Function-cost analysis | What does each component do, how well, and at what cost? | function model + function/cost disadvantages |
| Flow analysis | Where do substance, energy, or information flows degrade? | flow disadvantages |
| CECA | Why does the initial disadvantage occur? | branched cause-effect chains + key disadvantages |
| Trimming | Which component/operation can be eliminated and its useful functions reassigned? | trimming models + trimming problems |
| Feature transfer | Which competing/alternative system has a feature we need without our disadvantage? | transfer problems/concepts |
| S-curve analysis | Where is the system/MPV in its lifecycle? | maturity diagnosis + strategic direction |
| TESE analysis | Which evolution directions open new solution spaces? | evolution hypotheses |
| Innovative benchmarking | Which system should be improved and which systems provide useful comparison? | benchmark / alternative candidates |

## Recommended default sequence

```text
Project goal
→ Initial disadvantage
→ Function model
→ Optional cost model
→ Optional flow model
→ CECA
→ Select key disadvantages
→ choose one of:
   contradiction / Su-Field / function problem
   trimming problem
   feature-transfer problem
   ARIZ mini-problem
→ inventive synthesis
→ concept substantiation
```

This is a routing default, not a rigid mandatory chain.

## Key problem selection

A candidate deserves key-problem status when solving it is plausibly sufficient to move the project goal materially and when it is neither a mere symptom nor an irrelevant deep cause.

Use these tests:

1. **Goal leverage:** if removed, does the project metric improve materially?
2. **Causal position:** is it a root/intermediate disadvantage with a defensible chain to the initial disadvantage?
3. **Actionability:** can it be converted to a solvable TRIZ problem model?
4. **Dependency:** does eliminating one cause collapse an AND-branch or only one of several OR-branches?
5. **Evidence:** are the causal links measured/supported or merely plausible?
6. **Change envelope:** is the allowed degree of system change compatible with the proposed route?
7. **Risk:** could solving it create a worse secondary contradiction?

## Four key-problem models

Modern MATRIZ routing recognizes four major problem models:

```text
Engineering contradiction → contradiction matrix → inventive principle
Physical contradiction    → separation algorithm / FOS / scientific effects
Su-Field problem           → 76 Standard Inventive Solutions
Function problem           → Function-Oriented Search / scientific effects
```

Trimming and feature-transfer problems can themselves become key problems; difficult minimal-change problems may be escalated into ARIZ.

## Anti-patterns

- starting from the component the team already wants to redesign;
- assuming the initial symptom is the key problem;
- forcing every key problem into a contradiction;
- using a long “5 Whys” chain without AND/OR branching or evidence;
- choosing the deepest cause even if it is outside project control;
- treating cost, function, flow, and failure disadvantages as interchangeable;
- optimizing the current architecture before testing trimming or feature transfer.

## Handoff contract

```text
Project goal:
Initial disadvantage:
System / supersystem boundary:
Function disadvantages:
Cost disadvantages:
Flow disadvantages:
CECA root/intermediate disadvantages:
Selected key disadvantage(s):
Key problem type:
Why selected:
Evidence confidence:
Allowed degree of change:
TRIZ route:
```

## Source alignment

This router follows the current public MATRIZ problem-identification toolbox: function-cost analysis, flow analysis, CECA, trimming, feature transfer, S-curve analysis, TESE, and innovative benchmarking. See `sources.md`.
