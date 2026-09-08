# G0–G18 Gate model

A Gate is an evidence-backed decision checkpoint, not a document milestone.

## State semantics

- `NOT_EVALUATED`: decision has not been made.
- `HOLD`: known blocking evidence or work is missing.
- `CONDITIONAL`: limited progression is allowed under explicit conditions and expiry.
- `PASS`: acceptance criteria are met with traceable evidence and approval.
- `FAIL`: route or proposal does not meet criteria.
- `RETIRED`: Gate record is no longer active but remains auditable.

## PASS contract

PASS requires a valid Gate identifier, owner, evidence IDs, explicit acceptance criteria, approval status `APPROVED`, named approver and a continuous assurance path. The system rejects PASS when any element is missing.

## Progression

A downstream Gate cannot PASS while the preceding Gate remains `NOT_EVALUATED`, `HOLD`, `CONDITIONAL` or `FAIL`, unless an approved governance exception explicitly defines the dependency change and its risk controls.

## Reopening

A previous PASS may return to HOLD or FAIL when evidence expires, a contradiction opens, a material/process/customer requirement changes, a model leaves its applicability domain or field monitoring detects drift. Change impact must propagate through the digital thread.
