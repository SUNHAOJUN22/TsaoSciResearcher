# Evidence and Reporting

## Evidence Levels

- **A**: accepted real calculation with complete method, convergence, state-specific validation, source artifacts, and hashes.
- **B**: real experiment with sample, process, measurement conditions, and provenance.
- **C**: literature or user-provided evidence not reproduced in the current system.
- **D**: mock data, estimates, failed/incomplete calculations, or mechanism hypotheses.

An accepted minimum, transition state, excited state, and trajectory require different validation. Evidence level A is not granted by normal termination alone.

## Claim-Evidence Contract

For every claim record:

- claim ID and exact wording;
- scope and system;
- evidence grade;
- supporting artifact IDs;
- quantitative value and uncertainty;
- assumptions and competing explanation;
- falsification condition;
- whether it is manuscript-ready.

Separate:

1. observed calculation output;
2. derived quantity;
3. interpretation;
4. hypothesis or recommendation.

## Manuscript Structure

Use:

- concise question-led title;
- abstract with problem, method, principal numerical result, limitation, and conclusion;
- introduction ending in a falsifiable objective;
- methods detailed enough to reproduce charge, multiplicity, method, basis, solvent, standard state, thermochemistry, and validation;
- results organized by claims rather than software;
- discussion separating evidence from extrapolation;
- limitations naming unresolved states, method sensitivity, and missing experiments;
- data availability pointing to source data, structures, inputs, outputs, and hashes.

## Supporting Information

Include:

- complete calculation matrix;
- conformer and reference-state definitions;
- optimized coordinates;
- frequency and TS/IRC validation;
- method-sensitivity tables;
- full orbital/ESP/interaction galleries;
- parser and software versions;
- source-data and SHA256 manifests;
- rejected or unresolved calculations with reasons.

## Literature Integrity

Use primary literature and official software documentation. Verify DOI, authors, title, year, and journal. Record whether the full text, selected sections, abstract, or only metadata were read. Never let literature language outrun the current calculation evidence.

## Final Decision Language

Use one of:

- supported within the stated model and method;
- not supported within the stated model and method;
- unresolved within the numerical or model uncertainty.

Do not convert a static DFT trend into a kinetic, catalytic, biological, or materials-performance claim without the required calculations and experimental bridge.
