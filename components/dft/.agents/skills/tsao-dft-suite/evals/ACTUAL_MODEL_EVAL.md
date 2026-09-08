# Actual model-routing evaluation

No authenticated model-routing capture is committed. The truthful routing status is `NOT_RUN`; the external scientific execution status remains `EXTERNAL_DFT_EXECUTION_NOT_VERIFIED`.

When an authorized model environment is available, run all cases without changing IDs, prompts, splits, languages, or expected activations. Preserve model identity, run ID, UTC, instruction digest, and request/response hashes. Then run `score_model_routing.py` and retain its machine-readable report.
