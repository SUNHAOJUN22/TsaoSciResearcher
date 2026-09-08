# Worked Examples

These examples demonstrate structure, not universal answers. Real cases require current evidence and domain verification.

---

## Example 1 — Should a small team adopt microservices?

### Route

`P` with a brief `Φ` audit because “independent service” and “scalability” are often ambiguous.

### Foundation Charter excerpt

- **Outcome:** reliable delivery and ability to change components without excessive coordination.
- **Scale:** three developers, one product, moderate traffic.
- **Values:** delivery speed, operability, fault isolation.
- **Contested term:** “scalable” may mean traffic, team, deployment, or organization.

### Proposition ledger

| ID | Type | Claim | Status |
|---|---|---|---|
| O1 | O | Team has three developers | verified |
| O2 | O | Components scale at similar rates | supported |
| C1 | C | Strong consistency is required for core transactions | verified |
| A1 | A | Microservices will increase team autonomy | contested |
| V1 | V | Minimize operational burden | explicit |
| U1 | U | Future team size in two years | unknown |

### Derivation

1. Independent scaling provides little current benefit.
2. Distributed consistency and observability add concrete burden.
3. A modular monolith satisfies current functional separation.
4. Boundaries can be designed so later extraction remains possible.

### Rival

Microservices may be justified if regulatory isolation or sharply different scaling is confirmed.

### Recommendation

Use a modular monolith with explicit module contracts, ownership, telemetry, and extraction triggers. Review when team count, deployment contention, or scaling divergence crosses defined thresholds.

---

## Example 2 — Does a microscopic calculation explain macroscopic material performance?

### Route

`Φ→P` because the word “explain” and the scale relation are foundational.

### Foundation audit

Distinguish:

- electronic state;
- atomistic configuration;
- microstructure;
- constitutive property;
- device-level performance.

A computed defect level may support one link; it does not by itself establish a complete macroscopic mechanism.

### Scale bridge

| From | To | Required bridge | Main uncertainty |
|---|---|---|---|
| electronic structure | trap descriptor | localization/energy definition | functional, finite size |
| trap descriptor | transport rate | kinetic model | prefactor, morphology |
| transport rate | space-charge behavior | continuum or stochastic model | boundary, injection |
| space charge | breakdown outcome | electro-thermal failure model | stochastic defects |

### Recommendation

State the microscopic calculation as conditional evidence for a mechanism. Add the bridge models, independent observables, and uncertainty before claiming macro-level explanation.

---

## Example 3 — Should a company enter a new market?

### Route

`Φ→P`.

### Foundation questions

- Is “market” defined by customer job, product category, geography, or regulation?
- Is the objective growth, margin, capability, or strategic option?
- Who bears downside?
- Which assumptions are reversible through a pilot?

### Ground truths

- verified regulatory entry conditions;
- unit economics with ranges;
- customer adoption mechanism;
- available capability and cash runway;
- explicit risk tolerance.

### Alternatives

1. full entry;
2. partner-led pilot;
3. capability acquisition without market launch;
4. wait with option-preserving research;
5. no entry.

### Recommendation form

Choose the smallest staged commitment that tests the highest-value uncertainty while capping irreversible downside. Set expansion and exit triggers before launch.

---

## Example 4 — Is an AI hiring system “fair”?

### Route

`Φ→P`, with ethical-first analysis.

### First Philosophy

“Fair” may refer to:

- equal treatment;
- equal error rates;
- equal opportunity;
- calibration;
- procedural transparency;
- accommodation;
- historical repair.

These criteria can conflict.

### Proposition ledger

- legal protections are `C`;
- fairness definition is `V/D`;
- historical outcome data are `O` with measurement caveats;
- model assumptions are `A`;
- observed error gaps are `O`;
- causal explanation for gaps may be `U`.

### Required analysis

- protected and affected groups;
- data-generation process;
- error-cost asymmetry;
- appeal and human review;
- distributional effects;
- alternative non-automated process;
- monitoring and withdrawal trigger.

### Recommendation

Do not answer with one aggregate score. Select and justify the fairness conception, verify legal duties, compare against the existing process, and preserve contestability and human accountability.

---

## Example 5 — Should I commit to a long educational program?

### Route

`P` with values audit.

### Foundations

- desired capability and life direction (`V`);
- time, money, health, and dependent obligations (`C`);
- actual behavior in related work (`O`);
- beliefs about prestige, employability, or enjoyment (`A`);
- future labor market (`U`).

### First-principles move

Replace “Do I want the credential?” with:

> What capability, community, option, or identity change am I seeking, and is this program the best risk-adjusted path?

### Low-cost discriminating actions

- complete a representative project;
- interview graduates and non-completers;
- simulate the weekly schedule;
- compare alternative pathways;
- define withdrawal and review conditions.

### Recommendation

Commit in stages when possible. Preserve exit options until evidence from representative work supports the long-horizon decision.

---

## Example 6 — Rapid protocol

**Question:** Should we add another approval step?

1. **Outcome:** reduce a defined error without unacceptable delay.
2. **Deletion test:** remove the proposed step and identify the failure it uniquely prevents.
3. **Foundations:** current error rate, error cost, review latency.
4. **Assumptions:** reviewer catches errors; step does not shift errors elsewhere.
5. **Alternatives:** automated check, sampled review, risk-tiered review.
6. **Decision:** use risk-tiered review if it dominates full review on expected error cost plus delay.
7. **Falsifier:** no measurable reduction after the trial period.
8. **Review:** pre-specified date and thresholds.
