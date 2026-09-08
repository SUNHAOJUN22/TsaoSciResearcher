# Tsao DFT Kinetics and Multiscale

Use for DFT free energies → TST rates → reaction networks → microkinetic, Cantera/RMG, Pyomo/CatMAP, reactor or population-balance handoffs.

```bash
python scripts/validate_reaction_network.py examples/catalysis/network.yaml
python scripts/eyring_rates.py examples/catalysis/barriers.csv --temperature 298.15 --out rates.csv
```

## v0.4 depth

See `SKILL.md`, `manifest.yaml`, `scripts/`, `templates/`, and `tests/` for the deterministic DFT adapters and scientific gates introduced in v0.4.0-alpha.1.
