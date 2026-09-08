# Initial qualification summary — 0.1.0-alpha.1

## Scope

This report qualifies the TSAO Process Intelligence OS software artifact and its open-source project structure. It does **not** approve a chemical process, catalyst, experiment, equipment design, safety case, patent position, customer product or industrial guarantee.

## Local reference qualification

The complete qualified distribution was built from the integrated mother skill and the EPDM, POE and general-polymer source trees.

- qualified release SHA-256: `630e5a87f8b9214950d4dde8f6d0312c0e80f89a31540bd417c538d14764b63b`;
- frozen core hash: `bb178beccaf72e7debf9451b30dd8086bf41e5ade69d1bbfec6eeddcba4ef344`;
- automated tests: **362/362 passed**;
- root OS tests: 48;
- POE regression tests: 2;
- general-polymer regression tests: 6;
- EPDM selected scientific/governance regression tests: 306;
- deterministic build: passed;
- ZIP CRC, path safety, manifest, SBOM and per-file checksum verification: passed;
- cleanroom extraction and revalidation: passed.

The active Git source tree intentionally excludes duplicated historical ZIP binaries. Their names and immutable hashes are preserved in `vendor/releases/SHA256SUMS.tsv`; the full qualified distribution contains the archive identities and integrated source trees.

## Qualification claims

The following software claims are supported:

1. the project can initialize a process-development workspace;
2. the route classifier can select mother/subskill paths without assigning technical approval;
3. Gate state validation is fail-closed;
4. evidence, model, digital-thread and change-impact objects have machine contracts;
5. scientific kernels have known-solution, conservation, boundary or rejection tests;
6. the package can be deterministically built and independently verified;
7. imported historical skills do not transfer technical Gate status.

## Explicit non-claims

```text
scientific_technical_approval: NOT_EVALUATED
laboratory_execution: NOT_EVALUATED
pilot_and_demonstration: NOT_EVALUATED
commercial_process_simulation: NOT_EVALUATED
engineering_design_approval: NOT_EVALUATED
relief_hazop_lopa_sil: NOT_EVALUATED
freedom_to_operate: NOT_EVALUATED
regulatory_and_customer_qualification: NOT_EVALUATED
industrial_performance_guarantee: NOT_EVALUATED
```

## Review expectation

The initial pull request is intentionally a Draft. Review should focus on lifecycle logic, scientific contracts, licence isolation, subskill boundaries, safety wording, test adequacy and contribution ergonomics before the first tagged release.
