<p align="center">
  <img src="open-deep-mind/assets/diagrams/homepage-bilingual.svg" alt="OpenDeepMind_skill 中英双语方法总览 / Bilingual methodology overview" width="100%">
</p>

<h1 align="center">OpenDeepMind_skill</h1>

<p align="center">
  <strong>先审查什么有资格成为基础，再从基础向上推导；需要发明时，显式进入 TRIZ。</strong><br>
  <strong>Qualify foundations, derive from them, and enter TRIZ only by explicit choice.</strong>
</p>

<p align="center">
  <a href="open-deep-mind/SKILL.md">Agent Skill Router</a> ·
  <a href="open-deep-mind/ARCHITECTURE.md">Architecture</a> ·
  <a href="open-deep-mind/MODULES.json">MODULES.json</a> ·
  <a href="open-deep-mind/first-philosophy/METHOD.md">第一哲学 / First Philosophy</a> ·
  <a href="open-deep-mind/first-principles/METHOD.md">第一性原理 / First Principles</a> ·
  <a href="open-deep-mind/triz/ROUTER.md">TRIZ Router</a> ·
  <a href="open-deep-mind/triz/README.md">完整 TRIZ / Full TRIZ</a> ·
  <a href="BENCHMARK.md">Benchmark</a>
</p>

<p align="center">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Agent_Skills-compatible-6f5cff?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-1.2.0-2a8cff?style=flat-square">
  <img alt="Reasoning modules" src="https://img.shields.io/badge/reasoning_modules-3-f2a649?style=flat-square">
  <img alt="TRIZ activation" src="https://img.shields.io/badge/TRIZ-explicit--only-e75f3c?style=flat-square">
  <img alt="Behavioral evals" src="https://img.shields.io/badge/behavioral_evals-60_cases-2fbf9f?style=flat-square">
  <img alt="Published benchmark" src="https://img.shields.io/badge/published_benchmark-none_yet-91a7bd?style=flat-square">
  <img alt="TRIZ matrix" src="https://img.shields.io/badge/TRIZ_matrix-1190_cells-1565c0?style=flat-square">
  <img alt="TRIZ SIS" src="https://img.shields.io/badge/TRIZ_SIS-76-7b61ff?style=flat-square">
</p>

<!-- CLOSURE_STATUS_START -->
## Current code qualification / 当前代码资格

- Benchmark aggregation accepts only finite real metrics; booleans, `NaN` and infinities are excluded, and generated JSON is serialized with `allow_nan=False`.
- Artifact completeness remains distinct from publication readiness. The dependency-free aggregator always requires independent publication attestation and cannot publish a behavioral model score by itself.
- 已提交的 60 个 case、Schema 和验证器证明评测框架可执行，不证明任何外部模型已经运行；没有原始输出、独立 grader、holdout seal 与签名 attestation 时，状态保持 `NO_PUBLISHED_BEHAVIORAL_SCORE`.
<!-- CLOSURE_STATUS_END -->

> **Independent project / 独立项目：** OpenDeepMind_skill is not affiliated with, sponsored by, or endorsed by Google DeepMind, OpenAI, Anthropic, MATRIZ, the Altshuller Institute, or the maintainers of referenced repositories.

> **Benchmark status / 评测状态：** the evaluation framework and 60 authored cases are committed. **No behavioral performance score is published yet.** Real scores require controlled model runs, raw outputs, grading artifacts, model/settings metadata, and complete aggregate results.

---

## 1. What OpenDeepMind is / 项目定位

OpenDeepMind is a domain-general reasoning system for problems where definitions, evidence, mechanisms, constraints, values, uncertainty, and decision consequences matter.

It deliberately separates three jobs that are often collapsed into one prompt:

| Module | Core question | Canonical entry |
|---|---|---|
| **Φ First Philosophy / 第一哲学** | What is qualified to count as a foundation? | [`first-philosophy/METHOD.md`](open-deep-mind/first-philosophy/METHOD.md) |
| **P First Principles / 第一性原理** | What follows from qualified foundations, and how can it be tested? | [`first-principles/METHOD.md`](open-deep-mind/first-principles/METHOD.md) |
| **T TRIZ Engineering** | When explicitly requested, what inventive engineering concepts resolve the selected problem model? | [`triz/ROUTER.md`](open-deep-mind/triz/ROUTER.md) |

The normal reasoning loop is:

```text
problem/frame
    ↓
First Philosophy Φ
    ↓ Foundation Charter
First Principles P
    ↓
competing models / alternatives
    ↓
falsification + uncertainty + quality gate
    ↓
action / experiment / revision
```

TRIZ sits outside the default route:

```text
explicit TRIZ request or explicit acceptance
    ↓
Φ/P qualification
    ↓
TRIZ inventive synthesis
    ↓
First-Principles physical/evidential validation
    ↓
shared quality gate
```

The repository therefore rejects three common shortcuts:

```text
first-principles vocabulary ≠ proof
TRIZ pattern ≠ validated engineering solution
high model fit ≠ causal/mechanistic truth
```

---

## 2. Physical module isolation / 模块隔离

Canonical architecture:

```text
OpenDeepMind_skill/
│
├── README.md
├── BENCHMARK.md
├── VERSION
├── CHANGELOG.md
├── LICENSE.md
├── NOTICE.md
│
└── open-deep-mind/
    ├── SKILL.md                    # thin runtime router
    ├── ARCHITECTURE.md             # dependency / handoff contract
    ├── MODULES.json                # exactly 3 reasoning modules
    │
    ├── first-philosophy/
    │   ├── METHOD.md
    │   ├── README.md
    │   ├── module.json
    │   ├── foundation-charter.schema.json
    │   ├── example-foundation-charter.json
    │   └── scripts/validate_module.py
    │
    ├── first-principles/
    │   ├── METHOD.md
    │   ├── README.md
    │   ├── module.json
    │   ├── model-contract.schema.json
    │   ├── decision-record.schema.json
    │   ├── example-model-contract.json
    │   ├── example-decision-record.json
    │   └── scripts/validate_module.py
    │
    ├── triz/
    │   ├── ROUTER.md
    │   ├── README.md
    │   ├── module.json
    │   ├── VENDORED_LICENSE.md
    │   ├── resources/
    │   ├── examples/
    │   └── scripts/
    │
    ├── evals/                      # measurement plane; NOT a reasoning module
    │   ├── evals.json
    │   ├── benchmark-config.json
    │   ├── rubric.md
    │   ├── *.schema.json
    │   └── scripts/
    │
    ├── references/                 # shared method-neutral references
    ├── assets/                     # shared schemas/templates/visuals
    ├── scripts/                    # repository + ledger validation
    └── tests/                      # regression tests
```

The historical files below are compatibility aliases only:

```text
open-deep-mind/FIRST_PHILOSOPHY.md -> first-philosophy/METHOD.md
open-deep-mind/FIRST_PRINCIPLES.md -> first-principles/METHOD.md
open-deep-mind/TRIZ_ENGINEERING.md -> triz/ROUTER.md
```

The benchmark/evals layer is **not** registered in [`MODULES.json`](open-deep-mind/MODULES.json) and must never enter runtime reasoning context.

Full dependency contract: [`open-deep-mind/ARCHITECTURE.md`](open-deep-mind/ARCHITECTURE.md).

---

## 3. Module Φ — First Philosophy / 第一哲学

First Philosophy does not begin with “How do I solve this?” It asks:

> **What must be clarified, justified, or accepted before this is a coherent problem and before a solution can count as warranted?**

Its protocol is exactly:

```text
Φ0  Suspend the inherited frame
Φ1  Semantic audit
Φ2  Ontology map
Φ3  Epistemic audit
Φ4  Logical audit
Φ5  Causality and explanation audit
Φ6  Boundary, scale and time audit
Φ7  Value, ethics and praxis audit
```

So:

\[
\Phi8 = \{\Phi_0,\Phi_1,\ldots,\Phi_7\}
\]

The principal output is the **Foundation Charter**:

```text
question + rival frames
definitions / operationalization
ontology
claim/evidence status
logic / causal commitments
boundary / scale / time
values / duties / stakeholders
accepted / conditional / rejected foundations
blocking unknowns
```

Machine-readable contract:

- [`foundation-charter.schema.json`](open-deep-mind/first-philosophy/foundation-charter.schema.json)
- [`example-foundation-charter.json`](open-deep-mind/first-philosophy/example-foundation-charter.json)

**Isolation invariant:** canonical Φ contains no TRIZ procedure.

---

## 4. Module P — First Principles / 第一性原理

The canonical First-Principles protocol is normalized to exactly nine stages:

```text
P1  Delete, modify, or justify the requirement
P2  Define outcome and boundary
P3  Expose assumptions and proposition types
P4  Decompose to irreducibles
P5  Qualify foundations
P6  Build the model
P7  Reconstruct alternatives
P8  Derive, trace, falsify, and stress-test
P9  Decide, act, monitor, and update
```

\[
P9 = \{P_1,P_2,\ldots,P_9\}
\]

### Typed proposition ledger

Every load-bearing claim should be distinguished before inference:

\[
\mathcal B=\{D,O,L,C,A,E,V,U\}
\]

| Code | Meaning |
|---|---|
| `D` | Definition |
| `O` | Observation |
| `L` | Law / invariant |
| `C` | Constraint |
| `A` | Assumption |
| `E` | Empirical closure / estimate / proxy |
| `V` | Value / objective / duty |
| `U` | Unknown |

This is intended to block moves such as:

```text
fitted correlation → “law”
model output → “observation”
preference → “hard constraint”
metric → underlying phenomenon
```

### Model contract

Quantitative work exposes the relevant subset of:

\[
\mathcal M=
\{\mathbf x,\mathbf u,\boldsymbol\theta,
\mathbf F,\mathbf h,\mathbf g,
IC,BC,\mathcal O,\mathcal E\}
\]

with parameter provenance, assumptions/closures, observation/error model, validity domain, and falsifiers.

Machine-readable contracts:

- [`model-contract.schema.json`](open-deep-mind/first-principles/model-contract.schema.json)
- [`decision-record.schema.json`](open-deep-mind/first-principles/decision-record.schema.json)

**Isolation invariant:** P never auto-loads TRIZ.

---

## 5. Module T — Complete opt-in TRIZ Engineering

TRIZ is an engineering invention subsystem, not a foundational philosophy engine.

Canonical router:

[`open-deep-mind/triz/ROUTER.md`](open-deep-mind/triz/ROUTER.md)

Full subsystem map:

[`open-deep-mind/triz/README.md`](open-deep-mind/triz/README.md)

### Activation

```text
TRIZ / ARIZ / contradiction matrix / inventive principles / Su-Field /
IFR / explicit engineering-system-evolution request
        ↓
TRIZ may run
```

Ordinary language such as “there is a contradiction” does **not** authorize TRIZ.

### T10

```text
T1   explicit activation / engineering scope
T2   identify the key problem
T3   resources / ideality / IFR
T4   construct the problem model
T5   select matrix / separation / SIS / ARIZ / FOS / TESE route
T6   generate distinct concept families
T7   translate abstractions into concrete mechanisms
T8   apply physical / safety / manufacturing gates
T9   define discriminating validation
T10  return to First Principles
```

### Included TRIZ knowledge/tools

- function and function-cost analysis;
- flow analysis;
- CECA;
- trimming and feature transfer;
- innovative benchmarking;
- Nine Windows/System Operator, Size–Time–Cost, Smart Little People;
- ideality / IFR / resource analysis;
- engineering and physical contradictions;
- complete 39 typical engineering parameters;
- complete 40 inventive principles;
- 39×39 contradiction-matrix transcription with **1190 populated cells**;
- separation principles;
- Su-Field modeling;
- **76 Standard Inventive Solutions**;
- ARIZ-85C;
- FOS / scientific-effects routing / clone problems;
- S-curve and TESE/evolution;
- concept substantiation;
- deterministic matrix and SIS lookup utilities.

Known historical/transcription anomalies are tracked separately rather than silently edited:

[`matrix_anomalies.json`](open-deep-mind/triz/resources/matrix_anomalies.json)

A TRIZ concept is only a candidate:

\[
C_{TRIZ}
\not\Rightarrow
\text{validated engineering solution}
\]

It must return to P for governing physics, materials, manufacturing, uncertainty, safety, experiment/simulation, rival models, and falsification.

---

## 6. Behavioral Benchmark / 行为评测

Benchmark entrypoint:

[`BENCHMARK.md`](BENCHMARK.md)

Evaluation package:

[`open-deep-mind/evals/README.md`](open-deep-mind/evals/README.md)

### 60 authored cases

```text
12 routing / activation
10 First Philosophy
12 First Principles
 8 Dual Engine Φ→P
10 explicit TRIZ
 8 TRIZ near-miss / anti-trigger
--------------------------------
60 total

36 train / 12 validation / 12 holdout
3 repetitions by default
```

### Four experimental configurations

```text
no_skill
first_principles_baseline
opendeepmind_full
opendeepmind_no_triz_ablation   [TRIZ-positive only]
```

The external baseline is commit-pinned. `opendeepmind_full` is production behavior. The no-TRIZ ablation is an experimental intervention that disables T and forces P on the same ten explicit-TRIZ cases.

Declared paired comparisons:

```text
OpenDeepMind full  vs  no skill
OpenDeepMind full  vs  pinned first-principles baseline
OpenDeepMind full  vs  no-TRIZ ablation  [explicit TRIZ cases]
```

The last comparison is designed to estimate the marginal contribution of the TRIZ module:

\[
\Delta Q_{TRIZ}
=
Q_{full,T-cases}
-
Q_{no\text{-}TRIZ\ ablation,T-cases}
\]

### Metrics

- case/assertion pass rate;
- red-blocker rate;
- routing accuracy;
- TRIZ false-activation rate;
- module-leakage rate;
- semantic judge score;
- rival-model and falsifier coverage;
- token/time cost;
- paired common-case deltas;
- blind pairwise result when supplied.

### Experiment completeness

`create_workspace.py` writes all expected run slots into the workspace manifest. `aggregate_benchmark.py` checks every expected slot.

For the validation split:

```text
12 cases × 3 full-scope configurations × 3 repetitions = 108
2 validation TRIZ-positive cases × ablation × 3 repetitions = 6
----------------------------------------------------------------
114 expected run slots
```

If any expected `run_record.json` or `grading.json` is absent, `publication_ready=false`.

**No benchmark score is published yet.** This repository currently contains the benchmark definition and machinery, not fabricated performance evidence.

---

## 7. Shared quality gate / 共享质量门

Quality rules:

[`open-deep-mind/references/quality-gates.md`](open-deep-mind/references/quality-gates.md)

Red blockers dominate any numeric score. Examples:

- undefined load-bearing terms;
- fabricated sources/data/experiments;
- key facts without suitable support;
- invalid inference;
- correlation written as causal intervention;
- model output written as observation;
- cross-scale conclusion without a bridge;
- hidden objective/value;
- missing rival/falsifier where decision-relevant;
- unsafe deletion of verified safety/legal/ethical constraints;
- TRIZ pattern presented as engineering proof.

A score is a diagnostic; it does not create evidence.

---

## 8. Cross-scale discipline / 跨尺度纪律

A familiar multiscale chain might be written schematically as:

\[
\hat H\Psi=E\Psi
\rightarrow
m_i\ddot{\mathbf r}_i=-\nabla_iU
\rightarrow
\frac{\partial\phi}{\partial t}
=-L\frac{\delta\mathcal F}{\delta\phi}
\rightarrow
\frac{\partial u}{\partial t}+\nabla\cdot F=S
\rightarrow
x^*=\arg\min J
\]

But every arrow needs its own bridge:

```text
mapping variables
coarse-graining / closure
information lost
parameter or calibration source
uncertainty propagation
validation domain
failure conditions
```

OpenDeepMind treats an unbridged scale jump as a reasoning defect rather than an impressive-looking scientific story.

---

## 9. Deterministic validation / 确定性验证

```bash
# repository architecture + owned validators
python open-deep-mind/scripts/validate_repository.py .

# shared reasoning ledger
python open-deep-mind/scripts/validate_ledger.py \
  open-deep-mind/assets/example-ledger.json

# module invariants
python open-deep-mind/first-philosophy/scripts/validate_module.py
python open-deep-mind/first-principles/scripts/validate_module.py
python open-deep-mind/triz/scripts/validate_triz_module.py

# behavioral benchmark definition
python open-deep-mind/evals/scripts/validate_evals.py

# deterministic TRIZ lookups
python open-deep-mind/triz/scripts/lookup_matrix.py \
  --improve 1 --worsen 3 --json
python open-deep-mind/triz/scripts/lookup_standard_solution.py \
  1.2.1 --json

# regression / syntax
python -m unittest discover -s open-deep-mind/tests -p "test_*.py"
python -m compileall -q open-deep-mind
```

GitHub Actions is configured to run these structural checks on push and pull request.

The benchmark model executions themselves remain a separate experiment because they require a chosen model/provider/runtime and matched run settings.

---

## 10. Installation / 安装

```bash
git clone https://github.com/SUNHAOJUN22/OpenDeepMind_skill.git
```

Point an Agent-Skills-compatible runtime at:

```text
open-deep-mind/SKILL.md
```

The router progressively loads only the selected reasoning module and necessary shared resources. The `evals/` package is excluded from runtime reasoning context.

---

## 11. Invocation examples / 调用示例

### Φ — First Philosophy

```text
调用 OpenDeepMind 第一哲学模块。
先审查定义、本体、认识状态、逻辑、因果/解释、边界尺度、价值与实践条件；
输出 Foundation Charter，不要提前优化解决方案。
```

### P — First Principles

```text
调用 OpenDeepMind 第一性原理 P9。
拆解需求与假设，建立 D/O/L/C/A/E/V/U 命题账本与模型契约，
从合格基础重构多个方案，建立竞争模型、证伪条件、不确定性与决策记录。
不要调用 TRIZ。
```

### T — Explicit TRIZ

```text
明确调用 OpenDeepMind TRIZ 工程模块。
先做必要的 Φ/P 资格审查，再按 T1..T10 识别关键问题、IFR、资源和矛盾，
按需使用矩阵/40原理、分离、Su-Field/76标准解、ARIZ、FOS/效应或 TESE，
生成具体工程机制概念，最后返回 P 做物理、证据、安全和试验验证。
```

---

## 12. Completeness boundary / 完备性边界

Repository completeness means the repository has explicit boundaries and executable checks for its claimed architecture:

```text
module contracts
manifests
schemas / fixtures
validators
provenance / license controls
deterministic utilities
regression tests
CI definitions
behavioral benchmark definitions
```

It does **not** mean:

- every philosophical dispute has been solved;
- every domain shares one evidence model;
- first-principles models are approximation-free;
- every TRIZ publication/patent/effect database has been copied;
- green CI proves a real engineering claim;
- 60 authored benchmark cases prove superiority before the runs happen.

The repository's operational standard is:

\[
\boxed{
\text{explicit boundary}
+
\text{traceable reasoning}
+
\text{falsifiable failure}
+
\text{reproducible evaluation}
+
\text{revision}
}
\]

Detailed current audit:

[`open-deep-mind/COMPLETENESS_AUDIT.md`](open-deep-mind/COMPLETENESS_AUDIT.md)

---

## 13. Provenance and licensing / 来源与许可

Important influences and source families include:

- first-principles Agent Skill implementations;
- `smixs/creative-director-skill` for routing/evaluation/documentation patterns;
- `Antropocosmist/triz-engineering-solver` for MIT-licensed TRIZ implementation/data reference;
- public MATRIZ terminology/routing and Altshuller/TRIZ theoretical lineage;
- Agent Skills evaluation guidance for eval-driven iteration.

See:

- [`NOTICE.md`](NOTICE.md)
- [`LICENSE.md`](LICENSE.md)
- [`open-deep-mind/triz/VENDORED_LICENSE.md`](open-deep-mind/triz/VENDORED_LICENSE.md)
- [`open-deep-mind/triz/resources/sources.md`](open-deep-mind/triz/resources/sources.md)
- [`open-deep-mind/references/intellectual-lineage.md`](open-deep-mind/references/intellectual-lineage.md)

---

<p align="center">
  <strong>Foundation → Principle → Model → Test → Action → Revision</strong><br>
  <sub>Module-isolated · Explicit provenance · Falsifiable reasoning · Eval-driven revision</sub>
</p>
