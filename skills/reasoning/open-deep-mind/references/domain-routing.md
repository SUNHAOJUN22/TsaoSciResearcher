# Domain Routing

The core method is domain-general; evidence standards, model classes, and stopping rules are not. Route by task.

> **TRIZ isolation rule:** no domain route below activates TRIZ by default. Canonical TRIZ is available only through explicit user activation and the isolated [`../triz/ROUTER.md`](../triz/ROUTER.md).

---

## 1. Science and research

### Foundation questions

- What is the target phenomenon?
- How is it operationalized?
- Which observations are theory-laden?
- What rival mechanisms fit the same data?
- At what scale is the explanation intended?
- What evidence would discriminate models?

### Default proposition mix

`D`, `O`, `L`, `A`, `E`, `U`.

### Default methods

- conceptual and measurement audit;
- mechanism map;
- causal graph where interventions are meaningful;
- governing equations;
- uncertainty and sensitivity;
- rival model and prospective prediction.

### Required outputs

- research question;
- observable and measurement model;
- mechanism candidates;
- parameter and assumption provenance;
- discriminating experiment or analysis;
- validity range.

### Red blockers

- hypothesis cannot be falsified;
- model is evaluated only on construction data;
- causal language from association alone;
- unbridged scale claim;
- omitted negative or conflicting evidence.

---

## 2. Engineering and software architecture

### Foundation questions

- What function and service level are required?
- Which constraints are physical, contractual, legal, or merely historical?
- What failure modes dominate risk?
- What complexity is earned?
- What must be reversible or maintainable?

### Default proposition mix

`D`, `C`, `O`, `A`, `E`, `V`.

### Default methods

- requirement deletion/justification test;
- functional decomposition;
- constraint map;
- minimum sufficient system;
- morphological architecture;
- FMEA/pre-mortem;
- load, boundary, and recovery tests.

### Optional explicit TRIZ route

If and only if the user explicitly requests/accepts TRIZ for a physical or technical engineering contradiction, load [`../triz/ROUTER.md`](../triz/ROUTER.md). TRIZ is **not** a default engineering step.

### Required outputs

- outcome and service-level contract;
- architecture/design options;
- trace from component to requirement;
- failure and recovery model;
- build/buy/reuse decision where applicable;
- test plan.

### Red blockers

- technology named as outcome;
- no baseline or do-nothing option;
- no failure recovery path;
- hidden operational burden;
- security/safety treated as optional decoration.

---

## 3. Business and strategy

### Foundation questions

- What stakeholder outcome creates value?
- What is scarce, substitutable, defensible, or regulated?
- What assumptions drive unit economics?
- Which advantages persist under competitor response?
- What value objective is being optimized?

### Default proposition mix

`O`, `C`, `A`, `E`, `V`, `U`.

### Default methods

- job/outcome reframing;
- value-chain decomposition;
- should-cost and unit economics;
- competitor counter-model;
- scenario and real-options analysis;
- pre-mortem.

### Required outputs

- strategic thesis;
- critical assumptions;
- economics with ranges;
- alternative moves;
- leading indicators;
- staged commitment and exit triggers.

### Red blockers

- market-size arithmetic without adoption mechanism;
- static strategy with no competitor response;
- average customer treated as a real person;
- sunk cost as justification;
- “optimal” without explicit objective and downside.

**TRIZ policy:** do not use canonical TRIZ. Only an explicitly requested analogical transfer is allowed, and it must be labeled non-canonical.

---

## 4. Policy, law, and ethics

### Foundation questions

- What rights, duties, authorities, and jurisdictions apply?
- Who is affected but underrepresented?
- What causal effect is the policy expected to produce?
- What distributional and long-horizon consequences follow?
- Which protections are non-tradeable?

### Default proposition mix

`D`, `O`, `C`, `V`, `A`, `U`.

### Default methods

- legal/source verification;
- stakeholder and power map;
- ethical-first audit;
- causal policy model;
- role reversal;
- scenario and implementation analysis.

### Required outputs

- authority and jurisdiction;
- evidence map;
- rights/duties constraints;
- policy alternatives;
- distributional effects;
- review, appeal, and sunset mechanisms.

### Red blockers

- outdated law or policy source;
- affected groups absent;
- is–ought leap;
- aggregate benefit used to erase concentrated harm;
- no implementation or enforcement model.

**TRIZ policy:** never auto-route policy, law, or ethics through TRIZ.

---

## 5. Personal decisions and learning

### Foundation questions

- What life value or capability is the decision meant to serve?
- Which preference is stable and which is situational?
- What is reversible?
- What evidence comes from actual behavior rather than self-narrative?
- What small experiment can reduce uncertainty?

### Default proposition mix

`O`, `A`, `V`, `C`, `U`.

### Default methods

- value clarification;
- time-horizon and identity audit;
- option map;
- pre-mortem;
- reversible experiment;
- review trigger.

### Required outputs

- decision criteria;
- trade-offs;
- small test;
- downside guardrail;
- review date.

### Red blockers

- external status goal presented as intrinsic value;
- irreversible commitment before cheap learning;
- single mood treated as stable preference;
- advice beyond available personal context;
- no consideration of health, safety, or dependent parties.

**TRIZ policy:** never auto-route personal decisions through TRIZ.

---

## 6. Creative and product innovation

### Foundation questions

- What human or system tension is real?
- What utility must remain after novelty fades?
- Which category assumptions can be removed?
- What is structurally new versus cosmetically different?
- Can the idea be explained and tested simply?

### Default proposition mix

`D`, `O`, `A`, `C`, `V`.

### Default methods

- semantic reframing;
- first-principles outcome reconstruction;
- morphological analysis;
- bisociation/structural analogy;
- inversion/worst idea;
- feasibility and usefulness calibration.

### Optional explicit TRIZ route

Only when the user explicitly requests/accepts TRIZ **and** the task contains a canonical physical/technical engineering system should [`../triz/ROUTER.md`](../triz/ROUTER.md) be loaded. Otherwise use the default creative methods above.

### Required outputs

- insight or tension;
- explicit principle/constraint set;
- multiple structurally distinct concepts;
- one recommended concept;
- proof-of-value experiment;
- failure and imitation risks.

### Red blockers

- novelty with no utility;
- generic solution transferable to every category;
- surface analogy treated as originality;
- evaluation by volume alone;
- no recommendation.

---

## 7. Quantitative and computational modeling

### Foundation questions

- What are states, controls, parameters, and observables?
- Which equations are laws and which are closures?
- What are initial and boundary conditions?
- Are parameters identifiable?
- How does numerical error compare with model discrepancy?

### Default methods

- model contract;
- dimensional analysis;
- limiting cases;
- convergence;
- sensitivity and UQ;
- cross-validation or prospective testing;
- scale-bridge audit.

### Required outputs

\[
\{\mathbf x,\mathbf u,\boldsymbol\theta,
\mathbf F,\mathbf h,\mathbf g,\mathrm{IC},\mathrm{BC},
\mathcal O,\mathcal E\}
\]

plus solver settings, provenance, validation, and validity range.

### Red blockers

- missing units;
- unknown parameter source;
- no convergence check;
- fitted closure called a law;
- extrapolation beyond calibration domain without warning.

TRIZ does not replace a model contract.

---

## 8. Explicit TRIZ engineering route

This is the **only shared-domain route that may activate canonical TRIZ**, and it still requires explicit user authorization.

### Required preconditions

- explicit TRIZ-family request/acceptance;
- a physical or technical engineering system;
- primary function and system boundary;
- measured or otherwise justified harmful/insufficient effect;
- hard constraints and safety conditions;
- enough information to formulate a real problem model.

### Route

Load [`../triz/ROUTER.md`](../triz/ROUTER.md) and progressive-load only the resources reached by T1..T10.

### Required return

TRIZ concepts must return to [`../first-principles/METHOD.md`](../first-principles/METHOD.md) for physical/evidence/uncertainty/falsification validation.

---

## 9. Cross-domain routing

Use `Φ→P` and multiple domain sections when:

- a scientific model drives a policy decision;
- a technical architecture encodes ethical trade-offs;
- a business strategy depends on physical scale-up;
- a personal decision depends on legal or medical facts;
- a creative concept makes measurable causal claims.

Cross-domain rule:

> **The strictest evidence, safety, legal, and ethical standard among the active domains governs the shared decision.**

TRIZ activation does not override this rule.
