# tsao-dft-researcher

Universal TsaoDFT Agent Skill for auditable Gaussian/Multiwfn/VMD research. Start with `SKILL.md`, then use `manifest.yaml` to load only the references needed for the current route.

Key commands:

```bash
python scripts/init_project.py ./project
python scripts/preflight_project.py ./project --json
python scripts/parse_gaussian.py job.log --json
python scripts/validate_research_manifest.py research-manifest.json
python scripts/validate_figure_manifest.py figure-manifest.json --research-manifest research-manifest.json
```

## v0.4 depth

See `SKILL.md`, `manifest.yaml`, `scripts/`, `templates/`, and `tests/` for the deterministic DFT adapters and scientific gates introduced in v0.4.0-alpha.1.
