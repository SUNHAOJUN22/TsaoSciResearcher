# Reaction mechanism, transition states and IRC

## Mechanism model

Represent each proposed path explicitly:

```text
separated reactants ↔ encounter complex → TS → intermediate/product complex
```

Define the reference state for every barrier. `G(TS)-G(complex)` and
`G(TS)-G(separated reactants)` answer different kinetic questions.

## TS generation routes

- chemically informed TS guess plus `Opt=TS`;
- QST2 from aligned reactant/product structures;
- QST3 with an additional TS guess;
- relaxed coordinate scans to generate a TS seed;
- alternative conformational, regio- and stereochemical approaches.

## Strict evidence chain

```text
TS optimization completed
→ exactly one significant imaginary frequency
→ animated mode shows intended bond-making/breaking/proton transfer
→ forward and reverse IRC
→ IRC endpoint reoptimization
→ endpoints match intended minima
```

Until the mode and connectivity are checked, label the structure
`TS_CANDIDATE`. A methyl rotation or global wobble is not a reaction coordinate.

## Path comparison

- compare paths at one consistent energy protocol and standard state;
- include conformer/pre-equilibrium effects when relevant;
- inspect whether a purported concerted step actually hides an intermediate;
- add explicit solvent or catalyst molecules when the chemistry requires a
  shuttle or coordination environment;
- treat very close barriers as an uncertainty range, not a categorical winner.
