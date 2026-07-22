# TsaoSciResearcher

**Evidence-first, full-lifecycle and traceable scientific research platform.**

The canonical, most detailed project page is [README.md](README.md). It includes English commands and architecture diagrams alongside the Chinese explanation.

Version 0.5.1 provides:

- 340 v2 capability contracts plus a 158-capability compatibility catalog;
- 15 gated research workflows;
- 15 JSON Schemas;
- 7 domain packs for polymers/catalysis, computational chemistry, MD/multiscale modelling, FEM, CFD, process digital twins and HPC reproducibility;
- cached bilingual routing, hash-linked project state, guarded computation handoffs and deterministic releases.

Quick start:

```bash
python -m pip install -e .
python -m tsao_researcher route "design a traceable multiscale polymer study"
python -m tsao_researcher search "polymer molecular dynamics" --limit 10
python -m tsao_researcher init --name demo --question "What is being tested?" --output .
python -m tsao_researcher verify .
```

TsaoSciResearcher never treats an unexecuted search, experiment or simulation as completed. External solvers and laboratory systems require a validated handoff and an actual execution artifact.
