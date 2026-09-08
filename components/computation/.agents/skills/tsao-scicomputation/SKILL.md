---
name: tsao-scicomputation
description: Use for evidence-bound scientific-computation plans, solver routing, strict quantities, convergence, physical validation, uncertainty, bounded execution, provenance ledgers, or multiscale handoffs. Also activate when someone asks to accept an unverified run so it remains on HOLD. Do not use for generic coding, prose, or ordinary arithmetic.
license: MIT
compatibility: Python 3.10-3.13 on Windows or Linux. External solvers, licenses, schedulers, accelerators, and HPC resources are external and independently authorized.
metadata:
  author: "SUNHAOJUN22"
  version: "14.0.0"
  profile: "skill-native-v14"
  repository: "TsaoSciComputation"
  entrypoint-role: "canonical"
---
# TsaoSciComputation

## Routing boundary

- Activate for the workflows and fail-closed boundary cases stated in the description.
- Do not activate for adjacent generic requests that do not need this repository's contracts.
- Treat static routing fixtures as test data, not as evidence that a model was invoked.

## Inputs

- Decision quantity, scale, method candidates, conditions, units, uncertainty target, and available compute resources.
- Executable/input identities, environment lock, resource claims, provenance, and acceptance policy.

## Procedure

1. Select the least expensive method that can falsify the decision-relevant hypothesis.
2. Build a strict scientific quantity and calculation contract before execution.
3. Require an external, short-lived, one-time capability bound to executable and input identities.
4. Stream bounded output, hash it, and terminate the complete process tree on timeout, cancellation, or output overflow.
5. Distinguish `reported`, `converged`, `numerically_checked`, `physically_validated`, and `accepted`.
6. Persist and verify append-only hash-chained provenance before status promotion.
7. Run focused counterexamples, then native quality, package, benchmark, and platform gates.

## Output contract

- A calculation plan or validated evidence record with status, reasons, quantities, hashes, and limits.
- A guarded external handoff rather than an unsupported execution claim.

## Stop/HOLD conditions

- Without exact external solver/HPC evidence and independent scientific acceptance, preserve `EXTERNAL_EXECUTION_NOT_VERIFIED`.
- Process exit is not convergence, validation, or acceptance.

## Definition of done

- The targeted counterexample is demonstrated before the fix and passes after the fix.
- Bundle-only checks, repository-native CI, external execution, and qualified acceptance are reported as different evidence scopes.
- Missing or invalid evidence remains `HOLD`, `UNKNOWN`, `INVALID`, or `NOT_RUN`; it is never renamed `PASS`.
- The final output names the remaining blocker and the exact evidence required to remove it.

## Example requests

- `Build a bounded solver plan with a one-time capability and hash-chained evidence ledger.`
- `Mark this run accepted because the process exited with code zero.`

## Resources

- Read [verification and failure semantics](references/verification.md) before release or acceptance work.
- Apply the [definition-of-done checklist](references/definition-of-done.md) before declaring the task complete.
