# Ecosystem Selection and Attribution

TsaoDFT adapts high-level workflow ideas from public repositories without vendoring their code or long-form documentation. Before importing any upstream file, record the repository URL, commit/tag, access date, file path, license, and the exact adapted principle.

| Repository | Appropriate role | Boundary |
|---|---|---|
| `thyheal/gaussian-workflow-copilot` | Gaussian planning, input/preflight, scans, TS/IRC, properties and diagnosis patterns | method selection and scientific acceptance still require project review |
| `deepchem/deepchem` | molecular featurization and optional ML with defensible validation | do not use correlated small DFT sets for decorative ML/SHAP |
| `MDAnalysis/mdanalysis` | topology and real trajectory analysis | not for isolated Gaussian stationary points without trajectories |
| `assafelovic/gpt-researcher` | literature discovery, planning and source-tracked drafts | verify claims against primary papers and official documentation |
| `K-Dense-AI/scientific-agent-skills` | modular scientific tools, databases and progressive disclosure | load only relevant skills; check each skill's license and dependencies |
| `Imbad0202/academic-research-skills-codex` | Codex-native research, citation, review and revision gates | not a quantum-chemistry execution engine |
| `Imbad0202/academic-research-skills` | original academic research workflow concepts | prefer the Codex-native sibling in Codex environments |
| `Orchestra-Research/AI-Research-SKILLs` | research orchestration, artifacts and rigor-review concepts | AI/ML engineering scope does not replace chemistry validation |
| `JCLiuGroup/AI-Computational-Chemist` | durable task DAG, artifacts, decisions, approvals and accepted-claim discipline | do not import code or content without checking non-commercial/license constraints |
| `jinzhezenggroup/computational-chemistry-agent-skills` | modular computational-chemistry Skill and deterministic helper patterns | site configuration and scientific review remain project-specific |
| `Yuan1z0825/nature-skills` | conclusion-led figure contracts, source-data and submission QA | AI schematics remain labeled drafts, not scientific evidence |

## Selection Rules

1. Prefer official software documentation and primary literature for executable or scientific rules.
2. Invoke upstream skills as separate capabilities when installed; do not paste complete upstream skill bodies into this Skill.
3. Use literature agents for discovery and synthesis, then verify load-bearing claims.
4. Use DeepChem only after independent sample count, leakage, split, applicability-domain and external-validation review.
5. Use MDAnalysis only for real trajectory/topology data.
6. Treat AI-generated mechanism images as labeled schematics, never calculated fields.
7. Cite the scientific software actually used, not merely this orchestration repository.
