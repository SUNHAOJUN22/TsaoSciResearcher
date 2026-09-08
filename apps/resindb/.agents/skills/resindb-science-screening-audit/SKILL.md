---
name: resindb-science-screening-audit
description: Use for ResinDB-Pro scientific data validation, quantity conversion, formula states, TOPSIS eligibility, source lineage, AI egress, screening worksheets, or claims that imply certification or regulatory release. Activate on requests to certify materials without complete evidence so the claim is blocked. Do not use for generic polymer questions, unrelated UI work, or prose-only editing.
license: MIT
compatibility: Browser application and repository-local Skill. It validates data quality and screening logic; it does not issue laboratory, regulatory, or material-release decisions.
metadata:
  author: "SUNHAOJUN22"
  version: "16.0.0"
  repository: "ResinDB-Pro-by-SunHJ"
---
# ResinDB science screening audit

## Workflow

1. Preserve the raw value, unit, method, conditions, and provenance before canonicalization.
2. Convert both value and unit only between compatible dimensions; reject unknown or incomplete quantities.
3. Keep formula missing/cycle/parse/domain/non-finite states distinct from a true numerical zero.
4. Exclude incomplete records from ranking unless an explicit evidence-bound imputation policy is declared.
5. Propagate source type, record status, confidentiality, license, and provenance through storage, ranking, export, and AI egress.
6. Render only a Data Quality / Screening Worksheet unless complete external evidence and qualified approval exist.
7. Run focused counterexamples, then the repository-native TypeScript, Node, UI, build, and audit gates.

## Truth boundary

The strongest software status is `SOFTWARE_VALIDATED_FOR_SCREENING`. It is not `certified`, `compliant`, `approved`, or `material release`.

## Quantity contract

\[
x_{target}=x_{raw}\frac{s_{raw}}{s_{target}}
\]

is valid only when source and target share the same physical dimension.
