# Innovative Benchmarking / 创新标杆分析

Innovative benchmarking supports problem identification by comparing engineering systems on functions, MPVs, disadvantages, costs/resources, and maturity. In current MATRIZ terminology it helps identify the best system for improvement and candidate systems for feature transfer.

## Scope

Use for:

- deciding which product/system variant should be the base system;
- finding alternative/competing systems for feature transfer;
- identifying where a competitor's advantage actually comes from;
- innovation strategy and S-curve comparison.

Do not use benchmark popularity as proof that a technology is better.

## Procedure

1. Define the main function and target component.
2. Define comparable MPVs and hard constraints.
3. Select systems that genuinely perform the same/similar main function.
4. Normalize operating conditions before comparison.
5. Compare function performance, cost/payment factors, resource use, failure modes, and maturity.
6. Identify complementary advantages/disadvantages.
7. Select:
   - base system for improvement;
   - alternative system(s) for feature transfer;
   - neutral/inert systems where useful.
8. Trace each advantage to a mechanism/feature.

## Comparison table

| System | Main function | MPV performance | Key advantage | Key disadvantage | Principle of operation | Resource burden | Evidence |
|---|---|---|---|---|---|---|---|

## Condition normalization

Before ranking, record:

```text
load / throughput:
scale:
material / feedstock:
temperature / pressure / environment:
required lifetime:
safety/regulation:
cost basis:
measurement method:
```

A benchmark measured under easier conditions is not automatically superior.

## Link to feature transfer

Select an alternative system when it has an advantage needed by the base and a complementary disadvantage that makes direct replacement undesirable. Then load `feature_transfer.md` to transfer the mechanism/feature rather than blindly switching systems.

## Link to S-curve

A competing system may lie on a different S-curve/principle of operation. Compare improvement rate, limits, resources, and adoption before deciding whether to improve the current system or migrate to a new architecture.

## Output

```text
Benchmark goal:
Main function / MPVs:
Systems compared:
Normalized conditions:
Evidence quality:
Base system selected:
Alternative/competing systems:
Advantages to transfer:
Mechanisms behind advantages:
Next TRIZ route:
```

See `sources.md` for public MATRIZ innovative-benchmarking and competing-system terminology.
