# Routing evaluation

`evals.json` is a bilingual static routing contract. It does not invoke a model, execute a solver, retrieve evidence, or constitute human acceptance.

A real routing result must be captured from an authenticated model environment and must include the model and version, run ID, UTC capture time, instruction digest, complete decisions, and request/response SHA-256 bindings. Score it with:

```bash
python .agents/skills/tsao-sci-researcher/evals/score_model_routing.py \
  captured-decisions.json \
  --report model-routing-score.json
```

Static fixtures and scorer self-tests are not empirical routing evidence.
