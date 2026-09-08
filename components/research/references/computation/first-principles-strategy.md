# First-principles strategy guide

“First principles” in TsaoSciResearcher means deriving a model hierarchy from exact constraints and the causal path from state to observable. It is broader than electronic-structure calculation.

## Universal questions

1. What observable changes the scientific or engineering decision?
2. Which degrees of freedom can causally change that observable?
3. Which quantities are conserved, and which reservoirs exchange mass, charge, momentum, energy, or particles?
4. Which symmetries, geometry constraints, positivity conditions, or admissibility rules apply?
5. Which thermodynamic potential or statistical ensemble represents the actual experimental conditions?
6. Is the system at equilibrium, metastable, ageing, transient, or externally driven?
7. What length, time, energy, and correlation scales must be resolved?
8. Which variables can be coarse-grained without losing the mechanism?
9. What observation would falsify the selected model class?
10. What uncertainty reaches the final decision threshold?

## Method-selection principle

Use the lowest-fidelity model that:

- contains the degrees of freedom controlling the observable;
- obeys relevant conservation laws and symmetries;
- can be calibrated and independently falsified;
- resolves required scales;
- propagates uncertainty to the decision.

Escalate only when validation identifies a missing degree of freedom, coupling, or scale. Agreement with one dataset is not proof of mechanism.

## Typical ladders

- Electronic states: charge/symmetry bookkeeping → DFT → hybrid/GW/multireference or excited-state methods.
- Reaction mechanism: stoichiometry/thermodynamics → reaction-path electronic structure → transition-state/microkinetic/kMC.
- Molecular free energy: ensemble definition → MD/MC and enhanced sampling → quantum-informed or coarse-grained extension.
- Polymer morphology: scaling/Flory-Huggins/SCFT → CG/DPD/phase field → validated cross-scale property linkage.
- Flow and transport: balances/dimensionless analysis → reduced model → CFD/FEM → justified multiphysics coupling.
- Mechanics and failure: energy/constitutive screening → FEM/fracture → microstructure-informed homogenisation.
- Dielectric transport: electronic/trap states → hopping/kMC/drift-diffusion → coupled electrothermal/failure model.
- Process distributions: balances/identifiability → population/reactor model → spatial process or calibrated surrogate model.

## Truth boundary

A strategy is `advisory-only`. It cannot be promoted to executed, checked, validated, or accepted without independent execution evidence, checksums, convergence records, validation, and qualified review.
