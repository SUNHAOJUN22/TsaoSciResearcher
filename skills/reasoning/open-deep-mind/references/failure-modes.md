# Failure Modes and Repairs

This catalog diagnoses errors that commonly masquerade as deep or first-principles reasoning.

---

## 1. Foundational errors

| Failure | Diagnostic symptom | Why it fails | Repair |
|---|---|---|---|
| False foundation | “This is obviously true” | familiarity is not warrant | classify, source, scope, counterexample |
| Infinite regress | every premise requires an endless deeper premise | no task-relative stopping rule | state domain, scale, purpose, and stopping criterion |
| Dogmatic reduction | lower-scale explanation declared universally sufficient | explanatory needs differ by level | audit adequacy and scale bridges |
| Foundation by authority | title or institution substitutes for evidence | authority may be fallible or out of scope | inspect source, method, and current validity |
| Foundation by popularity | “everyone does it” | frequency does not establish necessity | compare constraints and outcomes |
| Metaphysical overreach | working model described as ultimate reality | evidence underdetermines ontology | label as working commitment |
| Frame capture | stakeholder wording determines the solution | excluded alternatives remain invisible | neutral and rival reframing |
| Deletion fetish | requirement removal treated as inherently intelligent | some constraints encode safety, law, or duty | verify source and downside before deletion |

---

## 2. Semantic and logical errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Equivocation | one term changes meaning across premises | definition table and substitution test |
| Category mistake | process treated as object; value as fact; proxy as target | ontology map |
| Reification | score, latent variable, or model component treated as concrete entity | restore measurement/model relation |
| False dichotomy | only two options presented | generate third frame and continuum |
| Necessary/sufficient reversal | “X is required” from “X can produce Y” | formalize conditions |
| Circularity | conclusion embedded in definition or premise | independent operational test |
| Quantifier shift | “some” becomes “all” | state population and quantifier |
| Is–ought leap | descriptive result directly yields duty | explicit value premise |
| Motte-and-bailey | strong claim retreats to weak claim under criticism | lock claim version and scope |
| Performative contradiction | statement undermines its own possibility | self-application test |

---

## 3. Evidence errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Citation theater | many citations, weak claim fit | evidence map claim by claim |
| Source laundering | many pages repeat one upstream source | provenance graph |
| Cherry-picking | only confirming studies/cases | search rival and negative evidence |
| Absence fallacy | no evidence treated as proof of no effect | detection-power analysis |
| Measurement substitution | proxy treated as target | operational/construct validity audit |
| Survivorship bias | only successful examples | define sampling frame |
| Recency blindness | current fact answered from memory | current source verification |
| Precision theater | exact estimate from uncertain inputs | ranges and uncertainty propagation |
| Anecdote universalization | exceptional story becomes general law | base rates and mechanism |
| Model-output realism | simulation result called observed fact | label conditional output |

---

## 4. Causal and explanatory errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Correlation causation | predictive association becomes intervention claim | identification assumptions or experiment |
| Post hoc | temporal sequence taken as cause | rival mechanisms and controls |
| Single root cause | complex failure forced into one chain | branching causal graph |
| Mechanism by naming | “synergy,” “emergence,” or “AI” replaces mechanism | entities–activities–organization |
| Confounder omission | common cause ignored | causal graph |
| Collider conditioning | selection creates association | graph and sampling audit |
| Mediator confusion | total and direct effects mixed | define estimand |
| Purpose projection | natural process described as designed goal | distinguish function, selection, intention |
| Constitutive/causal mix | what something is confused with what produced it | explanatory-role table |
| Feedback blindness | one-way chain in adaptive system | loop and delay model |

---

## 5. Modeling and computation errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Equation decoration | symbols with no defined variables or units | model contract |
| Closure concealment | empirical relation presented as law | classify as `E` |
| Parameter orphan | value with no source or calibration | provenance |
| Boundary omission | PDE/dynamic model with no conditions | IC/BC ledger |
| Identifiability blindness | many parameter sets fit equally | structural/practical identifiability |
| Overfit validation | construction and test data overlap | independent/prospective test |
| Extrapolation silence | prediction beyond domain | validity warning and stress test |
| Numerical convergence neglect | one mesh/timestep/seed | refinement and repeatability |
| Solver truth fallacy | converged algorithm assumed physically correct | model discrepancy check |
| Scale teleportation | microscopic result asserted as macroscopic property | bridge model and uncertainty |
| Learned-law confusion | neural model called physical law | separate approximation and invariance |
| Digital-twin inflation | dashboard labeled twin without bidirectional validated model | define synchronization, model, uncertainty |

---

## 6. Decision and optimization errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Proxy optimization | metric rises, real goal falls | objective hierarchy and Goodhart test |
| Hidden utility | “optimal” with no beneficiary or weighting | value ledger |
| Average-case tyranny | vulnerable tails ignored | distribution and worst-case |
| Irreversibility neglect | downside cannot be undone | real-options/staging |
| Cost-of-delay neglect | endless analysis | VOI versus delay |
| Sunk-cost reasoning | past spend justifies future spend | forward marginal analysis |
| Solutionism | every issue becomes a technical product | policy/process/do-nothing alternatives |
| Complexity prestige | elaborate solution favored over sufficient one | component justification |
| Menu without judgment | many options, no recommendation | explicit decision rule |
| Confidence theater | decisive tone hides underdetermination | calibrated status and next test |

---

## 7. Ethical and social errors

| Failure | Diagnostic symptom | Repair |
|---|---|---|
| Stakeholder erasure | affected parties absent | power and stakeholder map |
| Aggregate washing | total benefit hides concentrated harm | distributional table |
| Consent fiction | formal agreement under coercion or asymmetry | meaningful-consent test |
| Externality hiding | cost exported to others/future | boundary expansion |
| Ethics as afterthought | moral review after design lock-in | ethical-first phase |
| Neutrality claim | value-laden system presented as neutral | expose objectives and classifications |
| Automation bias | machine output outranks accountable judgment | human review and contestability |
| Responsibility gap | no owner for harms or overrides | accountability map |
| Reversibility asymmetry | errors harm one group more | error-cost matrix |
| Future discounting | long-horizon harm made invisible | multi-horizon scenarios |

---

## 8. “First principles” misuse detector

Flag the phrase when any of these are present:

- no proposition ledger;
- no stated scale or domain;
- inherited facts are selectively accepted only when convenient;
- founder anecdotes replace evidence;
- “atoms” or “physics” are invoked for nonphysical choices without a bridge;
- all social/legal/ethical constraints are dismissed as artificial;
- decomposition ends at arbitrary preferred components;
- reconstruction simply returns the original favored solution;
- no rival model or falsifier;
- certainty exceeds source quality.

Repair by returning to:

\[
\text{type}
+
\text{scope}
+
\text{support}
+
\text{derivation}
+
\text{test}
\]

---

## 9. Rapid diagnostic questions

1. Which word is doing too much work?
2. Which “fact” is actually an assumption or value?
3. Where does the argument change scale?
4. What would a strong rival say?
5. What observation would change the conclusion?
6. Who benefits from the objective?
7. Which constraint can truly not be changed?
8. What is the do-nothing baseline?
9. What is the earliest failure signal?
10. Is the recommendation more precise than the evidence?
