# Claim Ledger Template

The ledger is the minimum auditable unit of OpenDeepMind.

---

## Markdown form

| ID | Type | Claim | Status | Scope | Evidence/source | Dependencies | Falsifier | Owner/review |
|---|---|---|---|---|---|---|---|---|
| D1 | D |  |  |  |  |  |  |  |
| O1 | O |  |  |  |  |  |  |  |
| L1 | L |  |  |  |  |  |  |  |
| C1 | C |  |  |  |  |  |  |  |
| A1 | A |  |  |  |  |  |  |  |
| E1 | E |  |  |  |  |  |  |  |
| V1 | V |  |  |  |  |  |  |  |
| U1 | U |  |  |  |  |  |  |  |

Allowed types:

- `D` definition;
- `O` observation;
- `L` law/invariant;
- `C` constraint;
- `A` assumption;
- `E` empirical closure/estimate;
- `V` value;
- `U` unknown.

Allowed statuses:

- `verified`;
- `supported`;
- `plausible`;
- `contested`;
- `unknown`.

---

## JSON form

```json
{
  "analysis_id": "example-001",
  "question": "What decision is being evaluated?",
  "domain": "engineering",
  "scale": "system",
  "purpose": "decision",
  "claims": [
    {
      "id": "O1",
      "type": "O",
      "claim": "Measured statement",
      "status": "verified",
      "scope": "Conditions and population",
      "source": "Source or measurement record",
      "dependencies": [],
      "confidence": 0.95,
      "falsifier": "Observation that would contradict the claim",
      "owner": "role-or-name",
      "review_date": "2027-01-01"
    },
    {
      "id": "A1",
      "type": "A",
      "claim": "Model assumption",
      "status": "plausible",
      "scope": "Model validity range",
      "source": "Rationale",
      "dependencies": ["O1"],
      "confidence": 0.65,
      "falsifier": "Test that challenges the assumption",
      "owner": "model-owner",
      "review_date": "2027-01-01"
    }
  ],
  "inferences": [
    {
      "id": "I1",
      "premises": ["O1", "A1"],
      "rule": "abduction",
      "conclusion": "CANDIDATE1",
      "confidence": 0.60,
      "defeaters": ["Alternative mechanism"]
    }
  ],
  "decision": {
    "recommendation": "Action",
    "foundation_trace": ["O1", "A1", "I1"],
    "uncertainty": "Material uncertainty",
    "review_trigger": "Condition that reopens the decision"
  }
}
```

Validate a ledger with:

```bash
python open-deep-mind/scripts/validate_ledger.py path/to/ledger.json
```

---

## Inference form

```text
Inference ID:
Premise IDs:
Inference rule: deduction / induction / abduction / analogy / simulation / optimization / normative
Intermediate result:
Conclusion:
Confidence:
Defeaters:
Falsifier:
Decision implication:
```

---

## Evidence map form

| Evidence ID | Claim IDs | Source type | Direct/indirect | Conditions | Limitations | Date/version |
|---|---|---|---|---|---|---|

A citation attached to a paragraph is not sufficient when it is unclear which claim it supports.

---

## Scale bridge form

| Bridge ID | From | To | Mapping | Closure/assumption | Information lost | Validation | Uncertainty |
|---|---|---|---|---|---|---|---|

---

## Decision change log

| Version | Date | Changed claim/model | Evidence | Decision effect | Author |
|---|---|---|---|---|---|
