# TRIZ Engineering Output Template / TRIZ 工程输出模板

Use this template for explicit TRIZ analyses. Keep the distinction between **problem identification**, **inventive synthesis**, and **engineering validation** visible.

```markdown
# TRIZ Engineering Analysis: [system / problem]

## 0. Activation and scope
- Explicit TRIZ trigger:
- Canonical engineering TRIZ or analogical transfer:
- System / subsystem / supersystem:
- Main function:
- Project goal:
- Allowed degree of system change:

## 1. Evidence and foundation handoff
| ID | Type | Claim / measurement / constraint | Status | Source / condition |

- Safety / legal / lifecycle constraints:
- Unknowns that can invalidate the problem model:

## 2. Problem identification
### Function model
| Carrier | Action | Object | Useful/harmful | Performance | Cost / evidence |

### Flow disadvantages, if relevant
...

### CECA
[initial disadvantage → branched causal disadvantages]

### Selected key disadvantage / key problem
- Why selected:
- Problem model: engineering contradiction | physical contradiction | Su-Field | function | trimming | feature transfer | ARIZ mini-problem

## 3. Ideality and resources
- Baseline useful effects:
- Baseline harmful effects / payment factors:
- IFR:
- System resources:
- Supersystem resources:
- Space/time/information resources:
- Harmful resources that may be converted:

## 4. Contradiction / problem model
### Engineering contradiction
IF ...
THEN ... improves
BUT ... worsens

Inverted contradiction:
...

Matrix mapping:
- Improving parameter #:
- Worsening parameter #:
- Matrix cell:
- Recommended principles:

### Physical contradiction, if applicable
- Element:
- Parameter:
- State A because:
- State not-A because:
- Separation axis:

### Su-Field, if applicable
- S1:
- S2:
- F:
- Model type: incomplete | insufficient | harmful | measurement
- Selected SIS class/number:

## 5. Route selected
- matrix / 40 principles
- separation
- 76 SIS / Su-Field
- ARIZ-85C
- FOS / scientific effects
- trimming / feature transfer
- S-curve / TESE

Why this route:
Provenance:

## 6. Inventive concepts
| # | Concept | TRIZ source | Concrete mechanism | Existing resource | Contradiction resolved | New contradiction / risk |
|---|---|---|---|---|---|---|

For each shortlisted concept:

### Concept [N] — [name]
- Principle / standard / separation / trend:
- Source status: matrix-derived | inferred | standard-solution-* | separation-* | ARIZ-derived | FOS-derived | effect-derived | trend-derived
- Physical/process embodiment:
- Mechanism chain:
- Resource utilized:
- Added substance/field/component:
- Expected useful effects:
- Harmful effects / payment factors:
- Relative ideality change:
- Manufacturability/integration issues:
- Validation risk:
- Falsifier:

## 7. Rejected compromises and concepts
| Candidate | Why rejected | Evidence / blocker |

## 8. Concept substantiation
### Hard gate
- [ ] physical feasibility
- [ ] dimensions / orders of magnitude
- [ ] safety
- [ ] regulation
- [ ] materials compatibility
- [ ] operating envelope
- [ ] manufacturability
- [ ] reliability/lifecycle
- [ ] maintainability
- [ ] no hidden scale jump

### Quantitative / model checks
- Governing equations:
- Parameters and provenance:
- Boundary/initial conditions:
- Sensitivity / uncertainty:

### Verification ladder
- Lowest-cost discriminating test:
- Simulation / experiment / prototype:
- Acceptance threshold:
- Rejection threshold:

## 9. Recommendation
- Leading concept:
- Why it best resolves the contradiction:
- Remaining blockers:
- Next discriminating action:
- Patent / prior-art work required:
- Escalation rule:
- Review trigger:

## 10. Return to OpenDeepMind quality gate
- Foundation IDs relied upon:
- Remaining assumptions:
- Rival concept / null model:
- Red blockers:
- Evidence still missing:
- Final status: TRIZ-derived | conditionally supported | validated only if separately established
```

## Minimal quick format

For a narrow explicit contradiction with adequate data:

```text
Contradiction:
IFR:
Matrix/separation/SIS route:
3 concept families:
Top concept:
Mechanism:
Resource:
Secondary contradiction:
Next calculation/test:
Falsifier:
```

Never omit source status and validation requirements merely for brevity.
