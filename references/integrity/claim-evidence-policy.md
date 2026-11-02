# Claim-evidence policy

Claim classes:

- observation: directly measured or recorded;
- calculation: produced by an identified executed computation;
- sourced fact: supported by a traceable external source;
- inference: reasoned from evidence with assumptions;
- hypothesis: testable proposition not yet established;
- recommendation: proposed action based on criteria;
- open question: unresolved issue.

Observation, calculation and sourced-fact claims require evidence IDs. Inferences require evidence IDs plus assumptions. Hypotheses and recommendations must never be phrased as established facts.

Keep claim and evidence links reciprocal in both directions. Every evidence record that supports or refutes a claim must appear in that claim's `evidence_ids`; do not hide contrary evidence by omitting its ID. A complete graph may contain conflicting evidence and still pass structural validation. Local positive-support verification must block unresolved refutations; neither structural validity nor byte integrity establishes scientific truth. Unlinked background records may remain in the evidence ledger.
