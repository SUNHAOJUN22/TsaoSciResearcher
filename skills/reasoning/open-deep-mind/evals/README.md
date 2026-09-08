# OpenDeepMind Benchmark / Evals

This directory is the **behavioral evaluation layer** for OpenDeepMind. It evaluates the three reasoning modules; it is **not a fourth reasoning module** and is never loaded as a problem-solving method.

The layout follows the Agent Skills evaluation pattern: author realistic cases in `evals.json`, run each case under comparable configurations, record grading/timing, aggregate results, inspect failures, revise the skill, and repeat.

Primary reference: <https://agentskills.io/skill-creation/evaluating-skills>

## 1. What this benchmark tests

OpenDeepMind is not a trivia skill. The benchmark therefore measures behavior rather than recall:

| Dimension | Question |
|---|---|
| Routing | Did the production agent select Φ, P, Φ→P, or explicit TRIZ correctly? |
| Foundation quality | Did it expose semantic, ontological, epistemic, logical, boundary and value defects? |
| First-principles quality | Did it test requirements, type claims, decompose, model, reconstruct alternatives and falsify? |
| TRIZ quality | When explicitly requested, did it select an appropriate TRIZ problem model and return concepts to engineering validation? |
| TRIZ false activation | Did TRIZ appear where it was not explicitly authorized? |
| Module leakage | Did a module silently import another module's method body or authority? |
| Evidence discipline | Were observations, assumptions, closures, laws, values and unknowns kept distinct? |
| Rival/falsifier coverage | Was at least one serious competing model or falsifier supplied where material? |
| Efficiency | What quality improvement was purchased with additional tokens and time? |

## 2. Initial benchmark set

`evals.json` contains **60 realistic cases**:

```text
12 routing / activation
10 First Philosophy
12 First Principles
 8 Dual Engine Φ→P
10 explicit TRIZ
 8 TRIZ anti-trigger / near-miss
-------------------------------
60 total
```

Split policy:

```text
train      36
validation 12
holdout    12
```

Train cases may guide revisions. Validation cases measure generalization during development. Holdout cases are for release evaluation; do not patch the Skill around individual holdout prompts.

## 3. Configurations and ablation design

`benchmark-config.json` defines exactly four configurations:

1. **`no_skill`** — same prompt and tool access, no reasoning Skill;
2. **`first_principles_baseline`** — commit-pinned external lightweight first-principles Skill;
3. **`opendeepmind_full`** — production OpenDeepMind on all cases, with TRIZ remaining explicit-only;
4. **`opendeepmind_no_triz_ablation`** — research ablation on the same ten `triz-positive` cases; TRIZ is disabled and the First-Principles route is forced.

The declared comparisons are:

```text
opendeepmind_full  vs  no_skill
opendeepmind_full  vs  first_principles_baseline
opendeepmind_full  vs  opendeepmind_no_triz_ablation  [triz-positive]
```

The final pair directly measures the marginal contribution of the TRIZ module on tasks that explicitly request TRIZ. The no-TRIZ ablation is intentionally not production behavior, so routing accuracy is not scored for that ablation.

Use the same model, model version, sampling/reasoning settings, tool access, input files and repetition count across each comparable pair.

## 4. Repetitions

Default:

```text
repetitions = 3
```

A single successful response is not evidence of reliability. Multiple repetitions expose stochastic/flaky behavior and support paired comparisons.

## 5. Workspace and run artifact contract

Create the workspace with `create_workspace.py`. Its `manifest.json` enumerates **every expected run slot**; the aggregator uses that manifest as the source of truth, so a missing run directory cannot silently disappear from the denominator.

A benchmark harness writes one `run_record.json` for each expected case/configuration/repetition:

```json
{
  "case_id": "R01",
  "configuration": "opendeepmind_full",
  "repetition": 1,
  "model": "model-name",
  "model_version": "provider-version-or-snapshot",
  "route": "phi",
  "loaded_modules": ["first-philosophy"],
  "response_text": "...",
  "total_tokens": 4200,
  "duration_ms": 18000,
  "repository_commit": "..."
}
```

A grader then writes `grading.json` conforming to `grading.schema.json`.

## 6. Grading layers

### Layer A — deterministic

Use code for mechanically verifiable facts:

- case/config/repetition metadata;
- production expected route;
- explicit-only TRIZ policy;
- module-load leakage;
- artifact existence;
- valid JSON where a structured artifact is required;
- intentional route override for the no-TRIZ ablation.

### Layer B — rubric/model judge

Use `rubric.md` for semantic quality:

- foundation audit quality;
- typed-claim discipline;
- causal/mechanistic adequacy;
- decomposition/model quality;
- rival model;
- falsifiability;
- uncertainty;
- actionability.

Every PASS or high score requires concrete evidence from the response.

### Layer C — blind pairwise review

For `opendeepmind_full` versus the no-skill baseline, pinned first-principles baseline, or no-TRIZ ablation, hide configuration labels and ask the judge/human reviewer which output is stronger and why.

## 7. Red blockers

Any of the following can force a case failure regardless of average rubric score:

- fabricated source/data/experiment;
- unsupported load-bearing factual claim presented as verified;
- correlation promoted to intervention causality without identification;
- model output presented as observation;
- unbridged scale jump;
- hidden value/objective controlling the recommendation;
- TRIZ auto-activation without explicit authorization in production behavior;
- TRIZ principle/matrix/SIS treated as proof of engineering feasibility;
- no serious rival/falsifier where the case explicitly requires one;
- unsafe removal of a verified legal/safety/ethical constraint.

The intentional no-TRIZ ablation is not scored as a TRIZ false-activation/routing failure merely because the experiment disables the module; its purpose is causal contribution measurement.

## 8. Key metrics

The aggregator reports at least:

```text
case_pass_rate
assertion_pass_rate
red_blocker_rate
routing_accuracy
triz_false_activation_rate
module_leakage_rate
judge_score_mean
rival_model_coverage
falsifier_coverage
mean_tokens
mean_duration_ms
```

For each declared comparison it also computes common-case/repetition paired deltas for assertion score, judge score, tokens and duration. Blind pairwise results remain a separate grading artifact when supplied.

Do not publish benchmark scores until actual runs and grading artifacts exist.

## 9. Commands

Validate the authored benchmark:

```bash
python open-deep-mind/evals/scripts/validate_evals.py
```

Create an empty iteration workspace:

```bash
python open-deep-mind/evals/scripts/create_workspace.py \
  --iteration 1 --split validation
```

Aggregate completed run artifacts:

```bash
python open-deep-mind/evals/scripts/aggregate_benchmark.py \
  ../OpenDeepMind_skill-workspace/iteration-1
```

The scripts are dependency-free and do not call any model API. The actual model/agent harness is intentionally external so the benchmark can run across different Agent-Skills-compatible runtimes or model providers without changing the benchmark definitions.

## 10. Publication rule

A public benchmark result must record:

```text
repository commit
benchmark version
model/provider/version
configuration
repetitions
sampling/reasoning settings
tool access
run date
raw run records
raw grading artifacts
aggregated benchmark.json
human/model-judge rubric and identity when applicable
```

`artifact_set_complete=true` means only that every expected run slot has consistent run and grading artifacts. The dependency-free aggregator deliberately keeps `publication_ready=false` until a separate, independently verified publication attestation binds the exact repository revision, model/provider settings, raw artifacts, holdout seal, grader identity and release authority.

Authored cases, complete slots, or aggregated scores are not themselves a published model result. Do not claim that a benchmark result proves universal superiority. It establishes performance only on the disclosed task distribution, models, settings and graders.
