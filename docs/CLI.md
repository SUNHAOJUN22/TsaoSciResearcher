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
python -m tsao_researcher math --contract decision-readiness --language en
python -m tsao_researcher math --contract quantity-dimension --language zh-CN
```

The `math` command is advisory and machine-readable. Every response declares:

```json
{
  "advisory_only": true,
  "solver_executed": false,
  "automatic_approval": false
}
```

It explains the repository's scoring, quantity/dimension, applicability, evidence-conflict, identifiability, uncertainty, multiscale-bridge, and readiness contracts. It does not calculate scientific results.

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
