# TsaoDFT Full Repository and Agent Skill Audit

Date: 2026-07-31  
Version: `0.4.0-alpha.2`  
Branch: `main`  
Pre-freeze qualification source commit: `3cb0925acd8605a897163e9a48f33c0a689c6454`  
Pre-freeze qualification GitHub Actions run: `30595469898`  
Release-snapshot source commit: `d02abc442f017f839311f3d52e172eb1d015a259`  
Release-snapshot GitHub Actions run: `30597772162`

## Audit rule

Repository engineering evidence is not scientific evidence. Passing tests do not prove legal real-engine execution, measured acceleration, a mechanism, an experimental result or an account-level GitHub setting. Unverified facts are recorded as `NOT VERIFIED`.

No branch or pull request was created. The user-mandated main-only policy was preserved.

## Acceptance summary

The pre-freeze qualification run and the alpha.2 release-snapshot run both passed:

- Python 3.10, 3.12 and 3.13 permanent quality gates;
- 325 tests across nine non-empty suites;
- Ruff lint and formatting;
- ordinary mypy across 18 targets;
- strict mypy across four trust-boundary targets;
- repository coverage at 92.48% statement and 80.18% branch;
- six core trust/execution modules at 100% statement and 98.53%–100% branch;
- Bandit and strict repository audit;
- CodeQL Python `security-extended`;
- runtime, development and exact locked-environment `pip-audit`;
- locked CycloneDX JSON SBOM generation and upload.

The release snapshot is `d02abc442f017f839311f3d52e172eb1d015a259`, validated by run `30597772162`. Its exact artifact IDs and SHA-256 digests are recorded in `docs/RELEASE_EVIDENCE_0.4.0-alpha.2.json` and `docs/RELEASE_SHA256_0.4.0-alpha.2.txt`.

`.github/workflows/ci.yml` is the only permanent workflow. It has read-only repository contents permission and no repository write/push step.

## Repository architecture

TsaoDFT is a repository-style collection of eight independently installable Agent Skills, not an electronic-structure engine and not a wheel-style scientific solver. Python owns the control plane: manifests, validation, parsing, provenance, scheduling, evidence packaging and experiment control. Gaussian, VASP, Quantum ESPRESSO and CP2K remain external compiled engines.

## Closed findings

### Installer ownership and transactions

The installer records ownership, refuses foreign destinations and unsafe roots, verifies symlink targets and modified copies, stages replacements atomically, restores the previous destination when marker publication fails and rejects concurrent installation locks.

### Prompt-injection boundary

Every Skill declares that web pages, PDFs, logs, README content and tool output are untrusted data. Retrieved content cannot override higher-priority instructions, request secrets, weaken scientific gates or authorize destructive/expensive execution.

### Dependency and supply-chain evidence

Runtime/development declarations remain compatible ranges; Python 3.10/3.12/3.13 CI uses exact reviewed constraints. CI runs `pip check`, three `pip-audit` modes, CodeQL and a CycloneDX SBOM. Reusable Actions are pinned to complete commit SHAs.

### Shell and scheduler safety

Formal HPC execution uses structured argv and validated scheduler/environment/path fields. Raw shell commands, control characters, scheduler-header injection, unsafe environment names and path escapes are rejected. Generated scripts remain approval-gated and never auto-submit.

### Signed approval and review

Execution approval is bound to Manifest SHA-256, plan, candidate and method fingerprint. Independent performance review uses Ed25519 verification and binds reviewer identity, scope, time, policy, benchmark plan, candidates and evidence root.

### Executable Schemas and Policy

Benchmark, performance Policy, engine Parser and attestation Schemas are executed at runtime. Semantic validation follows Schema validation. Policy fields are consumed by qualification code; unknown/incomplete formal contracts fail closed.

### Content-addressed evidence

Evidence publication is staged, verified and atomically moved to a directory named by the root SHA-256. Records, summary, Policy, review, qualification and file metadata are covered. Altered, missing or extra files and directory/root mismatch are detected by an independent verifier.

### Parser state machines and bridges

Gaussian, VASP, Quantum ESPRESSO and CP2K share a versioned Parser result contract. Final/fatal state takes precedence over earlier success markers. Deterministic bridges combine Parser evidence with Manifest, method fingerprint, runtime, scheduler, GPU and artifact provenance. Missing data remains explicit.

### Capability claims

The root capability validator enforces:

- exact L0–L3 support levels;
- generic L3 execution evidence;
- the complete signed acceleration L3 evidence-field contract whenever HPC capability is declared;
- valid implementation scripts;
- prohibition of execution evidence below L3;
- evidence SHA-256 formats and signed-review approval booleans;
- forbidden unsupported wording in public documents.

The HPC capability remains `L2_VALIDATED_ADAPTER`. Scoped performance eligibility never changes the public support level automatically.

## Test distribution

| Suite | Tests |
|---|---:|
| Root repository and governance/security contracts | 99 |
| `tsao-dft-suite` | 4 |
| `tsao-dft-researcher` | 32 |
| `tsao-structure-prep` | 5 |
| `tsao-periodic-dft-materials` | 11 |
| `tsao-dft-ml-active-learning` | 16 |
| `tsao-dft-hpc-provenance` | 148 |
| `tsao-dft-kinetics-multiscale` | 5 |
| `tsao-dft-catalysis-profile` | 5 |
| **Total** | **325** |

## Coverage evidence

| Scope | Statement | Branch |
|---|---:|---:|
| Entire repository | 92.48% | 80.18% |
| `shell_contract.py` | 100.00% | 100.00% |
| `trust_boundary.py` | 100.00% | 100.00% |
| `engine_parser_contract.py` | 100.00% | 100.00% |
| `benchmark_bridge.py` | 100.00% | 100.00% |
| `generate_job_script.py` | 100.00% | 98.53% |
| `validate_hpc_manifest.py` | 100.00% | 98.57% |

## Version-freeze scope

The alpha.2 phase changed only release/version metadata, Skill metadata/catalog/manifest versions, CHANGELOG and release/audit evidence. Two tests received mechanical exact-version assertion updates. Production Parser, trust-boundary, HPC generation, automatic-tuning, coverage, mypy, Bandit and workflow logic were not changed.

Historical CHANGELOG versions, Schema versions, Policy IDs, benchmark-result Schema versions, engine examples and external software versions were preserved. README and README_EN contain no current project-version field and therefore required no mechanical version edit.

## Scientific non-claims

The repository does not distribute restricted engines, POTCAR, pseudopotentials or licensed basis/potential libraries. It does not claim that normal termination, scheduler completion, an attractive figure, a model score, GPU allocation or a generated candidate establishes scientific acceptance or measured acceleration.

`QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE` means only that a bounded evidence package passed eligibility rules. Public L3 additionally requires legal real-engine/site execution, exact build and hardware identity, repeated numerical equivalence, verified artifacts and evidence root, signed independent review and explicit registration.

## Remaining external risks

- real-engine, real-GPU and real-HPC regression evidence remains external;
- live-model Agent execution remains `NOT VERIFIED`;
- branch protection, signed-commit enforcement, Dependabot alert state, secret scanning/push protection and private vulnerability reporting remain `NOT VERIFIED`;
- external link availability is not part of deterministic offline CI;
- main-only direct writes reduce review separation by explicit user policy.
