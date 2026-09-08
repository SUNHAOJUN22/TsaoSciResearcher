# First-principles computation strategy and external handoff

Use this workflow when a scientific question may benefit from quantum, molecular, mesoscopic, continuum, process, statistical, or multiscale computation. TsaoSciResearcher **advises, specifies, and reviews**; it does not run a solver or fabricate results.

Indexed capabilities routed here: **169**.

## Modes

1. **strategy** — derive the lowest-sufficient method hierarchy from the observable and governing physics.
2. **handoff-spec** — convert an approved strategy into a checksum-bound external task specification.
3. **result-intake** — register returned inputs, logs, versions, receipts, raw outputs, and provenance.
4. **result-review** — assess method fit, convergence, scale coverage, uncertainty, validation, and conclusion strength.

## Required strategy inputs

- scientific question and decision context;
- decision-critical observables, units, tolerances, and comparison baseline;
- material/system identity, composition, geometry, thermodynamic and operating conditions;
- available experimental, literature, or prior-computation evidence;
- resource, licence, privacy, and time constraints.

## First-principles reasoning order

1. Define the observable before choosing a method.
2. Identify relevant degrees of freedom and state variables.
3. Apply conservation laws, symmetry, admissibility, and exact limiting constraints.
4. Decide whether quantum, statistical-mechanical, thermodynamic, continuum, or mixed physics controls the observable.
5. Select the appropriate thermodynamic potential or statistical ensemble and state whether the problem is equilibrium, metastable, or driven non-equilibrium.
6. Compare length, time, energy, and correlation scales; use dimensionless groups where appropriate.
7. State model-reduction and closure assumptions.
8. Build a method ladder from the lowest sufficient model to justified escalation.
9. Define numerical/model convergence, validation, falsification, and uncertainty propagation.
10. Separate advisory strategy, prepared handoff, executed receipt, checked result, validated result, and accepted conclusion.

**Important:** first-principles reasoning does not mean every problem needs DFT. A pressure-drop question may be governed by conservation laws and constitutive rheology; a polymer morphology problem may require statistical physics and mesoscale fields; an electronic trap question may need quantum states linked to mesoscopic transport.

## Required strategy outputs

- problem/regime classification and clarification questions;
- first-principles frame: degrees of freedom, governing principles, conserved quantities, symmetries, state variables, potential/ensemble, equilibrium status, and scales;
- ranked method ladder with rationale, assumptions, inputs, validation, falsification, uncertainty, and escalation triggers;
- cross-scale bridge variables and coupling rule where needed;
- explicit no-execution boundary and human review points.

## Deterministic commands

```bash
python -m tsao_researcher strategy \
  "How do trap states and morphology control space charge and breakdown?" \
  --observable "space charge" \
  --observable "breakdown strength" \
  --condition "applied electric field" \
  --evidence "thermally stimulated current"

python scripts/validate_computation_strategy.py strategy.json
```

## External handoff

After qualified review, use `scripts/handoff_to_computation.py` to create a task specification with checksum-bound inputs, methods, conditions, convergence, validation, UQ, expected outputs, and approval points. Real execution remains external.

## Result review gate

Do not accept a returned result until all of the following are visible:

- exact method and software version;
- input and output checksums;
- convergence and finite-size/time/sampling checks;
- parameter, numerical, sampling, boundary, and model-form uncertainty;
- physical validation against experiment, benchmark, conservation law, limiting case, or independent model;
- competing mechanism or alternative method comparison;
- limitations and the domain of applicability.

## Load on demand

References:
- `references/computation/first-principles-strategy.md`
- `references/computation/handoff-protocol.md`
- `references/project-governance/scientific-validation.md`

Templates:
- `templates/computation-handoff/first-principles-strategy.json`
- `templates/computation-handoff/computation-handoff.json`

Schemas:
- `schemas/v2/computation-strategy.schema.json`
- `schemas/v2/handoff.schema.json`
- `schemas/v2/execution-receipt.schema.json`

## Completion criteria

- the observable and decision threshold are explicit;
- the method follows from governing physics and scales rather than software popularity;
- assumptions, validation, falsification, UQ, and escalation triggers are recorded;
- no planned calculation is represented as executed;
- external results remain separate from scientific validation and final acceptance.
