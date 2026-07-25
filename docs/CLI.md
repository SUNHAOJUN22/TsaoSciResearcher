# CLI reference

```bash
python -m tsao_researcher --version
python -m tsao_researcher route "design a multiscale study"
python -m tsao_researcher search "molecular dynamics" --limit 10
python -m tsao_researcher init --name Demo --question "What changes?" --output .
python -m tsao_researcher verify .
```

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
