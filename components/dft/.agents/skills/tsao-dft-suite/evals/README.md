# Routing evaluation

`evals.json` is a bilingual static routing contract. It does not invoke Gaussian, VASP, Quantum ESPRESSO, CP2K, or a model.

A real routing result must be captured from an authenticated model environment and must include the model and version, run ID, UTC capture time, instruction digest, complete decisions, and request/response SHA-256 bindings. Score it with:

```bash
python .agents/skills/tsao-dft-suite/evals/score_model_routing.py \
  captured-decisions.json \
  --report model-routing-score.json
```

Static fixtures, parser tests, and scorer self-tests are not empirical model-routing or external DFT evidence.
