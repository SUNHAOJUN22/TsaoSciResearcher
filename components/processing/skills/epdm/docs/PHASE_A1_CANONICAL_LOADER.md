# EPDM V2 transactional canonical loader

## Purpose

`canonical_loader.py` converts a structurally valid EPDM V2 JSON project into an immutable, typed publication without exposing partial state. It is a software-contract boundary only; it does not calibrate parameters, run a thermodynamic backend, integrate a reactor model, or authorize engineering use.

## Transaction

1. Copy the input through finite JSON canonicalization so caller-owned objects cannot alias the published state.
2. Require an explicit `schema_version`; Phase A1 supports only the identity migration `2.0.0 → 2.0.0`. Unknown or missing versions fail closed.
3. Validate the complete project against the governed Draft 2020-12 schema registry.
4. Convert stable records into frozen contract dataclasses with strict enum, boolean, numeric, tuple and mapping coercion. Empty `extensions` and non-core extension metadata remain bound by the source hash but are not injected into stable dataclasses.
5. Register evidence, applicability domains, catalysts, dienes, rate laws, kinetic parameters, thermo passports and datasets in a temporary `ContractRegistry`.
6. Reject duplicate global IDs, parameter references that escape their local parameter set, and every unresolved cross-registry reference.
7. Build typed state-definition, calibration-plan and model-qualification snapshots.
8. Publish immutable mappings and deterministic source, registry and publication SHA-256 identities only after all prior steps succeed.

## Entry points

- `load_canonical_project(project)` for an already parsed mapping;
- `load_canonical_project_json(text)` for strict JSON text, including duplicate-key rejection;
- `load_canonical_project_file(path)` for UTF-8 files.

`validate_v2_project()` retains its existing structural and semantic error behavior. For any project with no hard validation error, it additionally requires canonical publication. A canonical publication failure is converted into a fail-closed V2 validation issue.

## Identity model

- `source_sha256` binds the entire normalized project, including `extensions` and list order;
- `registry_content_sha256` binds stable typed registry content and is independent of registration order;
- `publication_sha256` binds the loader version, migration receipt, source identity, registry identity, typed auxiliary identity and explicit approval boundaries.

## Truth boundary

A successful publication proves only that the JSON, dataclass and registry software contracts are internally closed and reproducible. Scientific technical approval, engineering design approval, customer qualification, HSE approval and industrial performance guarantee remain `NOT_EVALUATED`.
