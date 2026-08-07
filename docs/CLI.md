# CLI reference

```bash
python -m tsao_researcher --version
python -m tsao_researcher route "design a multiscale study"
python -m tsao_researcher search "molecular dynamics" --limit 10
python -m tsao_researcher strategy \
  "Can one observable distinguish two mechanisms?" \
  --observable "rate constant 1/s" \
  --condition "350 K" \
  --evidence "independent experiment"
python -m tsao_researcher init --name Demo --question "What changes?" --output .
python -m tsao_researcher verify .
```

## Mathematical explanation contracts

```bash
python -m tsao_researcher math
python -m tsao_researcher math --schema
python -m tsao_researcher math --contract decision-readiness --language en
python -m tsao_researcher math --contract quantity-dimension --language zh-CN
python -m tsao_researcher math --contract uncertainty-budget --output contract.json
python scripts/validate_mathematical_contracts.py --check
```

The `math` command is advisory and machine-readable. Contract responses declare a stable schema identifier and the fixed scientific boundary:

```json
{
  "schema_id": "https://sunhaojun22.github.io/TsaoSciResearcher/schemas/v2/mathematical-contract-registry.schema.json",
  "advisory_only": true,
  "solver_executed": false,
  "automatic_approval": false
}
```

`--schema` emits the packaged Draft 2020-12 contract. `--output` persists the same JSON object that is emitted to stdout. The offline validator checks the canonical Schema, package mirror, three language modes, single-contract payloads, the canonical example, and the fixed false execution/approval boundaries.

The equations explain the repository's scoring, quantity/dimension, applicability, evidence-conflict, identifiability, uncertainty, multiscale-bridge, and readiness contracts. They do not calculate scientific results.

## Acceptance evidence modes

```bash
python scripts/build_validation_evidence.py --check
python scripts/generate_checksums.py --check
```

The checked-in acceptance hardening record may use `validation_scope="composite"`: a pinned full-repository baseline is combined with a SHA-256-bound focused regression. Composite evidence never claims that current-tree end-to-end CI ran when it did not.

## Execution evidence

```bash
python -m tsao_researcher receipt record . \
  --handoff computation/job.json --engine gromacs --engine-version 2026.1 \
  --command gmx --command mdrun --exit-code 0 \
  --output computation/result.dat \
  --started-at 2026-07-24T01:00:00Z --finished-at 2026-07-24T01:10:00Z
python -m tsao_researcher receipt verify .
```

## Reproducibility capsule

```bash
python -m tsao_researcher capsule export . --mode metadata --output project-metadata.zip
python -m tsao_researcher capsule export . --mode full --output project-full.zip
python -m tsao_researcher capsule verify project-full.zip
```
