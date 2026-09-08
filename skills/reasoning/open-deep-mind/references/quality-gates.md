# Quality Gates

Quality is evaluated in two stages:

1. **Red-blocker gate:** pass/fail.
2. **Reasoning quality score:** 0–100.

A high score cannot compensate for a red blocker.

---

## 1. Red blockers

Any one of the following blocks “validated,” “final,” or “first-principles complete” status.

### Foundation blockers

- a load-bearing term changes meaning;
- the target entity/process is undefined or category-confused;
- the question hides a false dichotomy that controls the answer;
- the system boundary, scale, or time horizon is absent where material;
- a value judgment is presented as an objective fact.

### Evidence blockers

- a key factual claim has no accessible support;
- a current or high-stakes fact is not verified;
- a secondary summary is used where a primary source is necessary and available;
- a model output is presented as direct observation;
- uncertainty or contradictory evidence is suppressed;
- a fabricated source, quotation, datum, or experiment is present.

### Reasoning blockers

- the conclusion does not follow from the premises;
- correlation is presented as intervention causality without identification;
- a necessary condition is treated as sufficient, or vice versa;
- the favored model is protected from any possible falsifier;
- a rival explanation capable of changing the decision is ignored;
- the conclusion crosses scales without a bridge.

### Modeling blockers

- units or dimensions are inconsistent;
- governing equations lack required initial/boundary/closure information;
- parameters have no provenance;
- numerical results lack convergence or error checks where required;
- a fitted or learned relation is labeled a fundamental law;
- extrapolation is hidden.

### Decision blockers

- the objective function or stakeholder values are hidden;
- legal, ethical, or safety constraints are deleted without verification;
- irreversible downside is ignored;
- no actionable decision or discriminating next step is supplied;
- recommendation confidence exceeds evidence quality.

---

## 2. Weighted score

Score each dimension from 0 to 5, then apply the weight.

| Dimension | Weight | 0 | 3 | 5 |
|---|---:|---|---|---|
| Foundation clarity | 12 | absent | mostly explicit | definitions, ontology, boundary, values explicit |
| Proposition classification | 8 | types conflated | most claims typed | all load-bearing claims typed and statused |
| Evidence quality | 14 | unsupported | adequate but incomplete | primary/reproducible, scoped, current |
| Decomposition | 8 | surface list | useful hierarchy | dependency-complete with stopping rules |
| Causal/explanatory adequacy | 12 | labels/correlation | plausible mechanism | identified or well-tested rival mechanisms |
| Model completeness | 10 | no model contract | partial | variables, equations/logic, conditions, error |
| Traceability | 8 | opaque | major links visible | conclusion-to-foundation trace complete |
| Alternatives | 6 | single path | weak alternative | strongest rival and structural options |
| Falsifiability and tests | 8 | none | generic | discriminating falsifier/test and signal |
| Uncertainty and robustness | 6 | false certainty | caveats | quantified/bounded, sensitivity and fallback |
| Values and ethics | 4 | hidden | stated | stakeholders, distribution, duties integrated |
| Actionability | 4 | abstract | recommendation | staged action, owner, trigger, review |

Weighted score:

\[
Q =
\sum_i w_i\frac{s_i}{5}
\]

where the weights sum to 100.

---

## 3. Thresholds

| Mode | Threshold | Additional condition |
|---|---:|---|
| Rapid | 70 | no red blocker; decision reversible |
| Standard | 80 | no red blocker; one strong rival |
| Deep | 88 | no red blocker; source and uncertainty audit |
| Research-grade claim | 90 | discriminating evidence and reproducibility record |
| High-stakes recommendation | 90 | professional/jurisdictional verification where applicable |

Scores are diagnostic, not a substitute for judgment.

---

## 4. Scoring anchors

### 0 — absent

The dimension is not addressed.

### 1 — rhetorical

It is mentioned but not operationalized.

### 2 — partial

Some elements exist, but important dependencies are hidden.

### 3 — adequate

Decision can proceed with explicit limitations.

### 4 — strong

Well-supported, traceable, and stress-tested.

### 5 — exemplary

Competing models, boundary conditions, uncertainty, and revision criteria are integrated.

Do not award 5 merely because the answer is long.

---

## 5. Revision algorithm

1. run red-blocker gate;
2. score all dimensions;
3. identify the lowest weighted contribution;
4. choose a method that directly targets it;
5. revise only the affected reasoning;
6. rescore;
7. record the delta and changed premise/model.

Stop or reframe when:

- two passes improve \(Q\) by less than 2;
- evidence cannot distinguish rivals;
- the value of more information is lower than delay cost;
- the frame fails Foundation Charter review.

---

## 6. Reasoning audit template

```markdown
## Quality gate

### Red blockers
- [ ] none
- [ ] unresolved: ...

### Score
| Dimension | Score 0–5 | Evidence |
|---|---:|---|
| Foundation clarity | | |
| Proposition classification | | |
| Evidence quality | | |
| Decomposition | | |
| Causal/explanatory adequacy | | |
| Model completeness | | |
| Traceability | | |
| Alternatives | | |
| Falsifiability and tests | | |
| Uncertainty and robustness | | |
| Values and ethics | | |
| Actionability | | |

**Weighted score:** /100
**Mode threshold:**
**Verdict:** pass / conditional / blocked

### Highest-risk weak link
...

### Revision or next discriminating action
...
```

---

## 7. Anti-inflation rules

- Evidence for each score must cite a specific section or artifact.
- Scores above 4 require an explicit rival or stress test.
- Evidence quality cannot exceed source quality.
- Causal adequacy cannot exceed identification or mechanism evidence.
- Model completeness cannot exceed boundary/parameter completeness.
- Deep mode cannot pass with unknown decision-critical claims hidden in prose.
- A score is lowered, not raised, when complexity obscures traceability.

---

## 8. Convergence record

```text
Pass:
Frame version:
Changed foundation/assumption:
Method used:
Score before:
Score after:
What improved:
What remains:
Stop reason:
```
