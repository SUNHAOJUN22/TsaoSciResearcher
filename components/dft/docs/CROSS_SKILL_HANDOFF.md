# Cross-Skill DFT Handoffs

Every transition between Skills is an evidence-bearing contract rather than an informal statement.

```text
structure review
  -> molecular/periodic method fingerprint
  -> engine input and preflight
  -> HPC run record
  -> engine parser and technical validation
  -> property/wavefunction analysis
  -> accepted artifact
  -> ML or kinetics
```

Required fields are defined by `skills/tsao-dft-suite/templates/handoff.yaml`. Handoffs carry artifact hashes, accepted parent status, unresolved assumptions, support level, success criteria, cost estimate and approval status.

## Blocking examples

- a structure is visually plausible but not accepted;
- charge/multiplicity or periodic termination is unresolved;
- method fingerprints differ across an energy expression;
- engine support is only L0/L1 but execution is described as validated;
- ML rows lack parent IDs or DFT fidelity;
- kinetic species/TS artifacts are not accepted;
- a restart changes method while claiming exact checkpoint continuity.
