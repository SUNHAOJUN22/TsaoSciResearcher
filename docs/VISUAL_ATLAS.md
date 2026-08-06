# Scientific Capability Visual Atlas

> Release 0.7.4 · 37 AI-generated conceptual illustrations

This atlas documents the repository's architecture, scientific contracts, validation boundaries, and external-execution lifecycle. Every SVG is a conceptual documentation artifact with accessible `<title>` and `<desc>` metadata. None of these figures is experimental data, a measured result, a solver output, or proof that an external computation ran.

## Research control and architecture

| Figure | Purpose |
|---|---|
| ![Research OS](assets/ai/research_os_architecture.svg) | Overall scientific control-layer architecture |
| ![Multi-agent orchestration](assets/ai/multi_agent_orchestration.svg) | Bounded orchestration and approval boundaries |
| ![Progressive routing](assets/ai/progressive_routing_loading.svg) | Route before loading capabilities |
| ![Project state machine](assets/ai/project_state_machine.svg) | Truth-preserving project transitions |
| ![Project ledgers](assets/ai/project_ledgers_provenance.svg) | Hash-linked state, evidence, and provenance ledgers |
| ![Research production pipeline](assets/ai/research_production_pipeline.svg) | End-to-end research production flow |

## Capability, evidence, and requirements

| Figure | Purpose |
|---|---|
| ![Capability landscape](assets/ai/capability_landscape.svg) | Capability catalog structure |
| ![Implementation levels](assets/ai/capability_implementation_levels.svg) | Contract implementation boundaries |
| ![Requirements coverage](assets/ai/original_requirements_coverage.svg) | Traceability from original requirements |
| ![Evidence claim graph](assets/ai/evidence_claim_graph.svg) | Evidence-to-claim linkage |
| ![Evidence citation loop](assets/ai/evidence_citation_integrity_loop.svg) | Citation and evidence integrity |
| ![Reproducibility gates](assets/ai/reproducibility_quality_gates.svg) | Reproducibility acceptance gates |

## First-principles and multiscale strategy

| Figure | Purpose |
|---|---|
| ![Strategy ladder](assets/ai/first_principles_strategy_ladder.svg) | Minimum-sufficient method ladder |
| ![Method decision tree](assets/ai/scientific_problem_method_decision_tree.svg) | Problem-to-method reconstruction |
| ![Multiscale pipeline](assets/ai/multiscale_science_pipeline.svg) | Measurable scale bridges |
| ![Multiscale case study](assets/ai/polymer_multiscale_case_study.svg) | Conceptual multiscale workflow example |
| ![Mathematical registry](assets/ai/mathematical_contract_registry.svg) | Eight machine-readable mathematical contracts |
| ![Readiness lattice](assets/ai/decision_readiness_lattice.svg) | Conservative BLOCK–REVIEW–PASS ordering |
| ![Uncertainty budget](assets/ai/uncertainty_propagation_budget.svg) | Decision-observable uncertainty propagation |
| ![Bridge error budget](assets/ai/multiscale_bridge_error_budget.svg) | Source, mapping, closure, and target uncertainty |

## Scientific Passport and integrity gates

| Figure | Purpose |
|---|---|
| ![Passport matrix](assets/ai/scientific_passport_matrix.svg) | Model, evidence, bridge, and uncertainty contracts |
| ![Evidence maturity](assets/ai/evidence_maturity_ladder.svg) | Declared E0–E4 evidence ladder |
| ![Decision readiness](assets/ai/decision_readiness_gate.svg) | Blocker and review aggregation |
| ![Active evidence loop](assets/ai/active_evidence_learning_loop.svg) | Next-best evidence planning |
| ![Quantity contract](assets/ai/quantity_dimension_contract.svg) | Quantity, unit, and dimension checks |
| ![Applicability guard](assets/ai/applicability_extrapolation_guard.svg) | Applicability and extrapolation checks |
| ![Evidence conflict](assets/ai/evidence_conflict_resolution.svg) | Support, challenge, and unresolved evidence |
| ![Identifiability gate](assets/ai/mechanism_identifiability_gate.svg) | Competing mechanism and parameter identifiability |
| ![UQ validation](assets/ai/uncertainty_quantification_validation.svg) | Validation and uncertainty loop |
| ![Causality guard](assets/ai/scientific_integrity_causality_guard.svg) | Causal-language and scientific-integrity boundary |

## External execution, laboratory, writing, and release

| Figure | Purpose |
|---|---|
| ![Handoff boundary](assets/ai/computation_handoff_boundary.svg) | Checksum-bound external execution handoff |
| ![Human approval](assets/ai/human_approval_acceptance_boundary.svg) | Qualified human acceptance boundary |
| ![Laboratory quality](assets/ai/laboratory_data_quality.svg) | Laboratory data-quality contract |
| ![Writing evidence chain](assets/ai/scientific_writing_evidence_chain.svg) | Scientific writing evidence traceability |
| ![Figure edit guard](assets/ai/scientific_figure_edit_guard.svg) | Scientific-figure edit boundary |
| ![Compatibility matrix](assets/ai/installation_compatibility_matrix.svg) | Cross-platform installation and CI matrix |
| ![Supply-chain attestation](assets/ai/supply_chain_release_attestation.svg) | Deterministic release and supply-chain evidence |

## Use rules

1. A conceptual figure may explain software architecture or scientific-control logic.
2. It must not be described as a measured, simulated, or experimentally validated result.
3. Formula diagrams must preserve the same limitations returned by `python -m tsao_researcher math`.
4. External-execution diagrams must preserve the handoff/receipt boundary.
5. Scientific acceptance remains a qualified human decision.
