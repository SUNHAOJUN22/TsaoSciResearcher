# Scientific confidence levels

TsaoSciComputation uses a fail-closed C0–C5 scale. The scale records the highest evidence level actually satisfied; it does not infer missing evidence from a successful process exit, parser result, or solver claim.

| Level | Minimum evidence | Permitted interpretation |
|---|---|---|
| UNASSESSED | No completed result | No scientific claim. |
| C0 | Completed | Process completion only. |
| C1 | Parsed and numerically converged | Numerical result only; physical validity is not established. |
| C2 | Physical validation added | Numerical and physical checks passed; uncertainty is incomplete. |
| C3 | Uncertainty, applicability, and evidence lineage added | Bounded research evidence; no expert acceptance is implied. |
| C4 | Named expert review and structured approvals added | Expert-reviewed scientific acceptance; no engineering authorization is implied. |
| C5 | Decision scope, safety review, and independent reproduction added | Engineering-decision readiness only within the documented applicability domain. |

The assessment is sequential. A record cannot reach C3 by supplying uncertainty while omitting convergence, and malformed or empty approvals cannot satisfy C4. C5 is deliberately strict and remains separate from ordinary scientific publication.

```python
from tsao_computation.validation import assess_confidence

assessment = assess_confidence(record)
print(assessment.to_dict())
```

Machine-readable assessments validate against `schemas/confidence-assessment.schema.json`. High-risk reactor, control, runaway, digital-twin, plant-safety, and commercial decisions still require qualified domain governance outside this software.
