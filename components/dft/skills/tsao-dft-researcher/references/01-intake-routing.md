# Intake and file routing

## Inspect before generating

| Input | What can be established | Limits |
|---|---|---|
| `.gjf/.com` | route, resources, charge/multiplicity, coordinates | may be historical or scientifically unsuitable |
| `.xyz/.sdf/.mol` | geometry and identity clues | charge, protonation, bond orders and state may be missing |
| `.log/.out` | energies, convergence, frequencies, TD/NMR text | not always sufficient for real-space wavefunction analysis |
| `.chk` | restart/wavefunction container | binary; use matching `formchk` |
| `.fchk/.wfn/.wfx/.molden` | wavefunction/property analysis input | upstream convergence and state still require validation |
| `.cube` | one scalar field on one grid | may omit method/state provenance; grid and sign matter |
| trajectory + topology | time-resolved ensemble | must unwrap/align and establish equilibration |
| CSV/XLSX/JSON | numerical plotting or ML data | verify units, missingness, grouping and leakage |
| paper/SI | method fingerprint and claims | source wording does not prove reproduction correctness |

## Route rules

- Existing valid `.fchk`: skip duplicate Gaussian calculations when the requested
  property is present; proceed to Multiwfn/VMD after provenance checks.
- Only `.log`: parse textual values; do not promise ESP/ELF/NCI surfaces unless a
  wavefunction-capable file can be regenerated.
- Existing failed job: diagnose the exact error before changing inputs; one fix
  at a time.
- Paper-derived reproduction: capture the original method fingerprint, then list
  every missing or reconstructed choice.
- Multiple molecules/structures: define whether the goal is a conformer ensemble,
  substituent comparison, reaction path or dataset. Different goals imply
  different reference states and figure contracts.
