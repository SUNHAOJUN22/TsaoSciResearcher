# Anti-Example — When TRIZ Should Not Be Forced

## User problem

> “Our SaaS onboarding asks for more profile information, which improves data completeness but increases user drop-off. Use TRIZ to solve the contradiction.”

## Scope diagnosis

This is not automatically a canonical engineering TRIZ contradiction:

- “data completeness” and “conversion” are behavioral/product metrics rather than Altshuller engineering parameters;
- the relevant mechanism is human behavior and interface design, not necessarily a physical substance–field interaction;
- forcing the 40 principles risks turning ordinary UX tactics into pseudo-TRIZ language.

## Correct response

```text
The problem is outside canonical engineering TRIZ unless you explicitly want an analogical transfer.

Recommended default route:
1. define the product/decision objective;
2. analyze user behavior and funnel evidence;
3. test which information is truly required;
4. use progressive disclosure, prefill, staged collection, experiment/A-B test, or other UX methods based on evidence.

If you still want TRIZ analogically, I can map the trade-off to TRIZ heuristics,
but the result will be labeled “analogical TRIZ” and not engineering proof.
```

## What not to do

Do not claim:

```text
#1 Segmentation proves we should split the form.
#10 Preliminary action proves we should prefill.
#25 Self-service proves users should validate their own profile.
```

Those may be useful design ideas, but the TRIZ principle does not establish their effectiveness.

## Boundary cases where TRIZ may be canonical

| Problem | Canonical engineering TRIZ? | Reason |
|---|---|---|
| onboarding drop-off | usually no | human/UX mechanism |
| pricing-page conversion | no | business/behavioral problem |
| compressor surge at high demand | yes | fluid/thermodynamic engineering system |
| coating delaminates during thermal cycling | yes | materials/thermal/mechanical contradiction |
| PID controller must be fast yet stable in a physical thermal system | potentially yes | measurable control–physical system contradiction |
| software service architecture | usually no | use First Principles/system architecture; TRIZ only if explicitly analogical |

## Router rule

A hard engineering problem need not use the 39 parameters if another TRIZ model fits, but canonical TRIZ should still have an engineering system, measurable/physical or functional interactions, and a valid problem model. When that boundary is unclear, use OpenDeepMind First Philosophy/First Principles first rather than forcing TRIZ.
