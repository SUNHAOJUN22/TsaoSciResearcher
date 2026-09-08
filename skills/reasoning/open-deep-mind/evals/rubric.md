# OpenDeepMind Benchmark Rubric

Use this rubric for model-judge or human grading after deterministic route/module checks.

## 1. Case-level hard gate

Before scoring, check red blockers. Any material red blocker forces `case_passed = false`, even if the numeric rubric score is high.

Red blockers include fabricated evidence, unqualified causal claims, model-output/observation confusion, unbridged scale jumps, hidden normative objectives, unauthorized TRIZ activation, treating TRIZ lookup as feasibility proof, omission of an explicitly required rival/falsifier, or unsafe removal of verified constraints.

## 2. Semantic quality score — 100 points

| Dimension | Weight | 0 | Mid | Full |
|---|---:|---|---|---|
| Route/task fit | 10 | wrong method dominates | partly appropriate | method depth and module route fit the task |
| Foundation clarity | 12 | terms/boundary hidden | some audit | material definitions, ontology, evidence status, boundary and values explicit |
| Claim/evidence discipline | 12 | facts/assumptions conflated | mostly distinguished | load-bearing claims correctly typed and evidential strength calibrated |
| Decomposition/model quality | 12 | surface list | useful structure | dependency/mechanism/model contract fits the question |
| Causal/explanatory adequacy | 10 | label/correlation | plausible mechanism | causal role/identification or mechanism and limits are explicit |
| Alternatives/rival quality | 10 | single favored answer | weak alternative | serious structurally different rival/baseline could change decision |
| Falsifiability/testability | 10 | no disconfirming condition | generic test | discriminating falsifier/test and observable signal |
| Uncertainty/validity domain | 8 | false certainty | caveats | uncertainty, scope, sensitivity or failure domain materially integrated |
| Decision/actionability | 8 | abstract | recommendation | staged action/experiment/guardrail/review trigger |
| Traceability | 8 | opaque | partial | conclusion can be traced to premises/models/evidence and status |

Score each dimension 0–5, then multiply by `weight/5`.

## 3. Module-specific grading

### First Philosophy cases

Reward:

- neutral and rival framing;
- semantic/ontological distinctions;
- observation vs inference vs value separation;
- logic/causal-role audit;
- boundary/scale/time specification;
- explicit Foundation Charter verdict.

Do not reward encyclopedic history unless it changes the analysis.

### First Principles cases

Reward:

- requirement deletion/justification test;
- outcome not solution-shaped;
- D/O/L/C/A/E/V/U discipline;
- explicit stopping reasons in decomposition;
- model contract/constraints where appropriate;
- minimum/balanced/frontier or otherwise structurally distinct alternatives;
- derivation trace;
- falsifier and review trigger.

### TRIZ cases

Reward only when TRIZ is explicitly authorized. Check:

- engineering scope;
- correct problem-model choice: engineering contradiction, physical contradiction, Su-Field, ARIZ/function/evolution route;
- IFR/resources where relevant;
- traceable principle/matrix/SIS/separation route;
- concrete mechanism, not principle-name decoration;
- secondary contradictions;
- mandatory return to First-Principles engineering validation.

A matrix cell, inventive principle, standard solution or evolution trend is a search direction, not proof.

### TRIZ near-miss cases

The best behavior is often **not to invoke TRIZ**. A sophisticated but unauthorized TRIZ analysis is a failure.

## 4. Blind pairwise comparison

When comparing Output A and Output B, hide configuration labels and ask:

1. Which output better identifies the real problem rather than accepting the prompt's frame?
2. Which better separates facts, assumptions, constraints, values and unknowns?
3. Which has the stronger mechanism/model/derivation?
4. Which considers the stronger rival or baseline?
5. Which is easier to falsify or test?
6. Which is more actionable without overstating certainty?
7. Which is more efficient and less method-theatrical?

Return:

```json
{
  "winner": "A|B|tie",
  "confidence": 0.0,
  "reasons": ["..."],
  "material_defects_A": ["..."],
  "material_defects_B": ["..."]
}
```

## 5. Anti-gaming rules

- Do not award points for merely naming Φ, P, TRIZ, a principle, or a rubric dimension.
- Do not require exact wording from the Skill.
- A longer answer is not inherently better.
- Evidence for a PASS or high score must identify what the output actually did.
- Assertions that always pass across all configurations should be removed or tightened.
- Assertions that no configuration can satisfy should be repaired rather than used to inflate difficulty.
- Holdout prompts must not be converted into special-case instructions in the Skill.
