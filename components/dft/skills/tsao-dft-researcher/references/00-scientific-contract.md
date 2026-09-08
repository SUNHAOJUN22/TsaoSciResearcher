# Scientific contract and calculation passport

Before any input or figure is made, convert the request into a scientific
contract.

## Contract fields

- **Question:** the mechanism, property, comparison or decision.
- **Observable:** the quantity that can answer it, such as ΔG‡, redox potential,
  oscillator strength, ESP extrema, interaction energy or trajectory contact
  probability.
- **Model:** molecular identity, protonation/tautomer, fragments, environment,
  charge, multiplicity, state and conformer ensemble.
- **Method fingerprint:** code/version, functional or Hamiltonian, basis/ECP,
  dispersion, solvation, integration grid, SCF policy, temperature, pressure and
  standard state.
- **Validation target:** what must be true before the value is usable.
- **Figure claim:** one sentence that the final panel should support.
- **Acceptance criteria:** magnitude/plausibility, benchmark, experiment or
  internal consistency checks.
- **Non-goals:** analyses that will not be run merely because a program offers them.

## Calculation passport

Maintain `calculation-passport.yaml` with:

- source structures and hashes;
- every Gaussian input/log/chk/fchk relation;
- method and state metadata;
- software versions and execution host;
- parser/analysis commands;
- Multiwfn menu scripts and VMD/Tachyon render parameters;
- raw, processed and final figure paths;
- claim-to-artifact links;
- known limitations and human approvals.

## Evidence statuses

- `planned`: scientifically scoped but not executed.
- `completed`: a program or script finished.
- `validated`: technical/scientific checks defined for the artifact passed.
- `accepted`: a reviewer/user/orchestrator judged that it answers the registered
  observable.
- `contradicted`: reliable evidence conflicts with the intended claim.
- `rejected`: artifact is unusable.

Never collapse these states. A completed job can still be a wrong electronic
state, wrong conformer, wrong TS or misleading figure.
