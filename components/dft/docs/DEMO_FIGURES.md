# README Demo Figures

Run:

```bash
python scripts/generate_readme_demos.py
```

The deterministic SVG set demonstrates:

- repository workflow and validation rungs;
- matched molecular-orbital and ESP parameters;
- a source-data-backed free-energy profile;
- DFT+ML residual and leakage review;
- periodic DFT convergence/property handoffs;
- a leakage-aware active-learning loop;
- HPC attempt/restart/provenance lineage;
- DFT-to-TST/microkinetic/reactor handoffs.

Every SVG contains `SYNTHETIC DEMO · NOT SCIENTIFIC DATA`. Corresponding CSV files are stored under `assets/demo/source_data/` when the figure is quantitative. These figures are style demonstrations, not computational evidence.
