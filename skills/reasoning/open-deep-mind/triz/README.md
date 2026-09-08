# OpenDeepMind TRIZ Module / 完整 TRIZ 工程发明子系统

> **Explicit opt-in only.** This module is loaded only after an explicit TRIZ/ARIZ request or explicit user acceptance of a suggested TRIZ route. The default OpenDeepMind route remains `First Philosophy → First Principles`.

Canonical router: [`ROUTER.md`](ROUTER.md)  
Machine-readable manifest: [`module.json`](module.json)

This subsystem covers **problem identification → problem modeling → inventive synthesis → psychological-inertia breaking → evolution/roadmapping → concept substantiation**. It is intentionally isolated from the First-Principles method body so ordinary OpenDeepMind tasks do not pay the context cost of TRIZ.

## Architecture

```text
triz/
├── ROUTER.md                           # canonical explicit-use router; T1..T10
├── module.json                         # activation and handoff contract
├── README.md                           # this subsystem map
├── VENDORED_LICENSE.md                 # MIT notice for adapted/vendored material
├── resources/
│   ├── modern_problem_identification.md
│   ├── innovative_benchmarking.md
│   ├── function_analysis.md
│   ├── flow_analysis.md
│   ├── cause_effect_chain.md
│   ├── trimming.md
│   ├── feature_transfer.md
│   ├── multiscreen_operator.md
│   ├── psychological_inertia_tools.md
│   ├── ideality_ifr_resources.md
│   ├── contradictions.md
│   ├── 39_parameters.md
│   ├── 40_principles.md
│   ├── contradiction_matrix.json       # full 39×39 transcription, 1190 populated cells
│   ├── matrix_anomalies.json            # documented transcription anomalies/normalization
│   ├── separation_principles.md
│   ├── substance_field_modeling.md
│   ├── 76_standard_solutions.md         # all 76, public MATRIZ 5-class numbering
│   ├── ariz_85c.md
│   ├── clone_problems.md
│   ├── effects_and_fos.md
│   ├── evolution_trends.md
│   ├── s_curve_and_tese.md
│   ├── concept_substantiation.md
│   ├── glossary.md
│   ├── output_template.md
│   └── sources.md
├── examples/
│   ├── brake_disc.md
│   ├── battery_pack.md
│   ├── heat_exchanger_fouling.md
│   └── anti_example_misframed.md
└── scripts/
    ├── lookup_matrix.py
    ├── lookup_standard_solution.py
    └── validate_triz_module.py
```

Root `../TRIZ_ENGINEERING.md` is a compatibility alias only; new maintenance targets `ROUTER.md` and this directory.

## Module coverage

| Layer | Covered tools |
|---|---|
| **Problem identification** | function-cost analysis, flow analysis, CECA, trimming, feature transfer, innovative benchmarking, S-curve/TESE routing |
| **Problem models** | engineering contradiction, physical contradiction, Su-Field, generalized function, trimming/feature-transfer problem, ARIZ mini-problem |
| **Classical solution knowledge** | 39 typical parameters, full contradiction matrix transcription, 40 inventive principles, separation, 76 SIS, ARIZ-85C |
| **Resource/ideality** | IFR vs ideal system; substance, field, space, time, information, functional and supersystem resources |
| **Psychological inertia** | Nine Windows/System Operator, Size–Time–Cost, Smart Little People, contradiction intensification, inversion |
| **Knowledge transfer** | FOS, scientific-effects route, clone-problem transfer, feature transfer, multi-screen operator |
| **Evolution** | S-curve, MPV, TESE, supersystem, trimming, completeness, flow, coordination, controllability, dynamization |
| **Substantiation** | feasibility gates, First-Principles model handoff, UQ, simulation/experiment/prototype, FMEA, prior-art/patent search |
| **Execution** | deterministic matrix/SIS lookup, integrity validator, output template, worked examples |

## Three-layer engineering logic

### Layer A — Problem identification

Do not start with the contradiction matrix by default. Identify the **key problem** using the smallest adequate subset of function analysis, flow analysis, CECA, trimming, feature transfer, innovative benchmarking, and S-curve/TESE.

### Layer B — Problem solving

```text
Engineering contradiction -> 39 parameters -> matrix -> 40 principles
Physical contradiction    -> separation / effects / FOS / clone-problem transfer
Su-Field problem           -> 76 Standard Inventive Solutions
Function problem           -> FOS / scientific effects
Hard minimal-change problem-> ARIZ-85C
Roadmap question           -> S-curve + TESE
```

When the framing is stuck, psychological-inertia operators may deliberately change scale, time, cost assumptions, system screen, or micro-level representation. They generate reframings, not evidence.

### Layer C — Concept substantiation

TRIZ generates **inventive concepts**, not proof. Every leading concept returns to the isolated First Principles module for:

- governing-equation/dimensional checks;
- material and manufacturing feasibility;
- parameter/data provenance;
- initial, boundary and closure assumptions;
- safety/regulatory/lifecycle review;
- uncertainty/sensitivity;
- simulation, experiment, prototype and FMEA;
- patent/novelty search when relevant;
- rival-model and falsification analysis.

## Progressive loading

```text
Engineering contradiction
-> contradictions.md + 39_parameters.md + matrix + 40_principles.md

Physical contradiction
-> contradictions.md + separation_principles.md
   (+ effects/FOS or clone problems if needed)

Harmful/insufficient interaction
-> function/flow/CECA -> substance_field_modeling.md -> 76_standard_solutions.md

Deep stuck problem
-> ariz_85c.md + only resources actually reached by ARIZ

Technology roadmap
-> s_curve_and_tese.md + evolution_trends.md
```

Do not load the full matrix, 76 SIS, ARIZ, effects, and evolution resources simultaneously unless the task truly requires all of them.

## Data-integrity policy

The contradiction matrix is a **vendored historical transcription with explicit provenance**, not silently treated as an infallible canonical dataset. The validator checks 1190 populated cells, ID ranges, anchor cells, and known anomaly documentation.

Known transcription anomalies are stored in [`resources/matrix_anomalies.json`](resources/matrix_anomalies.json). `lookup_matrix.py` preserves the raw source value in output while normalizing documented duplicate IDs for practical lookup. Publication-critical historical claims should independently verify the relevant cell against a primary/reference edition.

## Deterministic tools

Matrix lookup:

```bash
python open-deep-mind/triz/scripts/lookup_matrix.py --improve 10 --worsen 17
```

Standard Inventive Solution lookup:

```bash
python open-deep-mind/triz/scripts/lookup_standard_solution.py 1.2.1
```

Complete module validation:

```bash
python open-deep-mind/triz/scripts/validate_triz_module.py
```

## Completeness boundary

“Complete TRIZ module” means this repository contains the **classical core problem/solution structures plus the current public MATRIZ-style problem-identification, evolution and concept-substantiation routes needed for a full engineering TRIZ workflow**.

It deliberately does not pretend to contain:

- every copyrighted TRIZ book/training text verbatim;
- proprietary commercial knowledge bases;
- every scientific effect as a static database;
- an exhaustive patent corpus;
- every variant created by every TRIZ school.

For FOS, scientific effects, patents, current technical data, or publication-critical historical wording, retrieve and cite primary/current sources instead of fabricating missing knowledge.

## Provenance

The classical implementation/data layer is adapted from the MIT-licensed [`Antropocosmist/triz-engineering-solver`](https://github.com/Antropocosmist/triz-engineering-solver), which documents matrix provenance through an MIT-licensed transcription chain. The extended problem-identification layer, OpenDeepMind handoffs, evidence/uncertainty discipline, concept substantiation, validators and most explanatory text are newly authored for OpenDeepMind.

The 76 Standard Inventive Solutions index was cross-checked against the public MATRIZ five-class/76-item numbering. See [`resources/sources.md`](resources/sources.md), [`VENDORED_LICENSE.md`](VENDORED_LICENSE.md), and root [`NOTICE.md`](../../NOTICE.md).
