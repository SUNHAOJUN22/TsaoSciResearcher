# Validation ladder and status rules

## Four rungs

1. **Exists:** expected file is present and nonempty.
2. **Completed:** program/script ended normally.
3. **Validated:** engine- and property-specific checks passed.
4. **Accepted:** evidence answers the registered scientific observable.

## Gaussian validation examples

- minimum: normal termination, converged geometry, zero meaningful imaginary
  modes, intended structure and valid electronic state;
- TS: normal termination, exactly one target mode, mode animation, IRC/endpoints
  when required;
- open shell: S²/stability/spin distribution;
- TD state: state character/NTO and state tracking;
- thermochemistry: same geometry/state, temperature, standard state and
  correction protocol.

## Multiwfn/VMD validation

- source wavefunction is validated and correctly indexed;
- analysis parameters and version are recorded;
- cube grids and signs are consistent;
- render uses the registered isovalue, camera and scale;
- output is nonblank and visually inspected.

## Claim gate outcomes

- `addresses`: evidence directly answers the question;
- `inconclusive`: technically sound but insufficient;
- `needs-follow-up`: create a new task rather than polishing prose;
- `contradicts`: stop automated synthesis and escalate;
- `accepted`: claim may enter the final report with stated limits.
