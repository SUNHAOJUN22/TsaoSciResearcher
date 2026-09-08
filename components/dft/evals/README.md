# TsaoDFT Agent Evals

`cases.yaml` contains versioned positive and adversarial policy contracts. Every case has:

- a stable ID and category;
- an input request;
- required behavior;
- forbidden behavior;
- a deterministic grader contract;
- failure evidence that must be preserved.

The repository validator checks schema completeness, category coverage, unique IDs, prompt-injection and destructive-action safeguards, and explicit live-model status.

These files do not claim that an LLM was executed. `live_model_execution: NOT_VERIFIED` remains until a real model/version run stores trace hashes and grader results. A schema pass is not a behavioral model pass.

Required categories cover routing, ambiguity, multi-Skill ownership, Profile isolation, prompt injection, unauthorized tools, destructive operations, support-level escalation, fabricated data, provenance loss, interruption/recovery, idempotency and version stability.
