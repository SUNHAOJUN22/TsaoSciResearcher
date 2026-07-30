from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "assets" / "ai"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise SystemExit(f"{label}: section markers not found")
    return text[:start_index] + replacement.rstrip() + "\n\n" + text[end_index:]


def svg_shell(title: str, desc: str, subtitle: str, body: str, footer: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="760" viewBox="0 0 1400 760" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#071629"/><stop offset="1" stop-color="#123a59"/></linearGradient><linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#38d9ff"/><stop offset="1" stop-color="#9b7cff"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#66ddff"/></marker></defs>
<rect width="1400" height="760" rx="28" fill="url(#bg)"/>
<g font-family="Inter,Segoe UI,Arial,sans-serif">
<text x="70" y="72" font-size="36" font-weight="700" fill="#f4fbff">{escape(title)}</text>
<text x="70" y="108" font-size="18" fill="#b7cada">{escape(subtitle)}</text>
{body}
<rect x="70" y="682" width="1260" height="44" rx="14" fill="#0b2035" stroke="url(#accent)"/>
<text x="100" y="711" font-size="16" fill="#d7e8f5">{escape(footer)}</text>
</g></svg>
'''


def card(x: int, y: int, w: int, h: int, heading: str, lines: tuple[str, ...], stroke: str = "#3dd9ff") -> str:
    text = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#102d49" stroke="{stroke}" stroke-width="2"/>']
    text.append(f'<text x="{x+24}" y="{y+40}" font-size="21" font-weight="700" fill="#f4fbff">{escape(heading)}</text>')
    for index, line in enumerate(lines):
        text.append(f'<text x="{x+24}" y="{y+70+24*index}" font-size="15" fill="#b7cada">{escape(line)}</text>')
    return "".join(text)


def arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#66ddff" stroke-width="3" fill="none" marker-end="url(#arrow)"/>'


assets: dict[str, str] = {}

body = [
    card(520, 145, 360, 90, "Scientific question", ("observable · tolerance · decision",), "#55e6a5"),
    arrow(700, 235, 700, 285),
]
physics = [
    (50, "Quantum frame", ("electrons · states · bonding", "DFT · TDDFT · GW/BSE"), "#9b7cff"),
    (320, "Statistical frame", ("ensembles · fluctuations", "MD · MC · free energy"), "#ffbe65"),
    (590, "Mesoscale frame", ("fields · domains · topology", "SCFT · phase field · CGMD"), "#55e6a5"),
    (860, "Continuum frame", ("balances · constitutive laws", "reduced model · CFD"), "#3dd9ff"),
    (1130, "Mechanics/process", ("stress · populations · control", "FEM · PBE · flowsheet"), "#ff7fa0"),
]
for x, heading, lines, stroke in physics:
    body.append(card(x, 300, 220, 160, heading, lines, stroke))
    body.append(arrow(700, 285, x + 110, 300))
body.extend([
    card(300, 520, 330, 105, "Minimum sufficient model", ("cheapest falsifiable representation", "explicit assumptions and limits"), "#55e6a5"),
    card(770, 520, 330, 105, "Evidence-driven escalation", ("add physics only after failed validation", "propagate uncertainty across bridges"), "#ffbe65"),
    arrow(630, 572, 760, 572),
])
assets["scientific_problem_method_decision_tree.svg"] = svg_shell(
    "Scientific Problem → Method Decision Tree",
    "A decision tree selects quantum, statistical, mesoscale, continuum, mechanics, or process methods from observables and governing physics.",
    "Start from the decision observable; choose a physical frame before choosing software.",
    "".join(body),
    "Advisory only · every branch requires convergence, falsification, UQ and an external execution receipt",
)

body = [
    card(70, 160, 260, 390, "Uncertainty sources", ("parameters", "numerics", "sampling", "boundary conditions", "model form", "scale transfer"), "#ffbe65"),
    card(470, 205, 460, 170, "Prediction distribution", ("not a single best-fit curve", "propagate covariance to the observable", "report calibration and extrapolation domains"), "#9b7cff"),
    card(1070, 160, 260, 390, "Validation evidence", ("units and limits", "mesh / basis / time-step", "replicates and ESS", "hold-out experiments", "competing mechanisms", "closure tests"), "#55e6a5"),
    arrow(330, 355, 460, 290),
    arrow(930, 290, 1060, 355),
    card(470, 450, 460, 120, "Decision test", ("probability of crossing the decision threshold", "sensitivity, identifiability and model discrepancy"), "#3dd9ff"),
    arrow(700, 375, 700, 440),
]
assets["uncertainty_quantification_validation.svg"] = svg_shell(
    "Uncertainty Quantification & Model Validation",
    "Parameter, numerical, sampling, boundary, model-form, and scale-transfer uncertainty are propagated and tested against independent evidence.",
    "A model is useful only when uncertainty reaches the decision—not when one curve looks convincing.",
    "".join(body),
    "Convergence ≠ validity · agreement with one dataset ≠ mechanism proof · extrapolation must be labelled",
)

body = [
    card(70, 180, 250, 150, "Evidence", ("source identity", "measurement boundary", "negative and null results"), "#55e6a5"),
    card(400, 180, 250, 150, "Claim", ("scope and qualifiers", "support edge", "contradictions retained"), "#3dd9ff"),
    card(730, 180, 250, 150, "Causal test", ("alternatives", "confounders", "intervention / temporal order"), "#ffbe65"),
    card(1060, 180, 250, 150, "Decision", ("risk tier", "approval gate", "accept / reject / supersede"), "#9b7cff"),
    arrow(320, 255, 390, 255), arrow(650, 255, 720, 255), arrow(980, 255, 1050, 255),
    card(160, 440, 240, 130, "Guard: leakage", ("test data contamination", "circular validation"), "#ff7fa0"),
    card(460, 440, 240, 130, "Guard: overclaim", ("correlation → causation", "simulation → experiment"), "#ff7fa0"),
    card(760, 440, 240, 130, "Guard: cherry-pick", ("missing failures", "selective conditions"), "#ff7fa0"),
    card(1060, 440, 240, 130, "Guard: authority", ("software output", "unqualified approval"), "#ff7fa0"),
]
assets["scientific_integrity_causality_guard.svg"] = svg_shell(
    "Scientific Integrity & Causality Guard",
    "Evidence, claims, causal tests, and decisions are separated while leakage, overclaiming, cherry-picking, and authority substitution are blocked.",
    "Preserve the evidence graph before strengthening the language of a conclusion.",
    "".join(body),
    "Correlation, simulation agreement and expert confidence are distinct evidence classes",
)

body = [
    card(55, 175, 220, 150, "Sample provenance", ("identity · batch · history", "chain of custody"), "#55e6a5"),
    card(330, 175, 220, 150, "Calibration", ("reference standard", "traceability · uncertainty"), "#3dd9ff"),
    card(605, 175, 220, 150, "Measurement", ("conditions · instrument", "raw signal retained"), "#9b7cff"),
    card(880, 175, 220, 150, "QC & statistics", ("blanks · controls · replicates", "outlier rule declared"), "#ffbe65"),
    card(1155, 175, 190, 150, "Evidence", ("qualified result", "boundary recorded"), "#55e6a5"),
]
for x in (275, 550, 825, 1100):
    body.append(arrow(x, 250, x+45, 250))
body.extend([
    card(160, 430, 300, 125, "Stop conditions", ("failed calibration · drift · contamination", "missing metadata · unsafe operation"), "#ff7fa0"),
    card(550, 430, 300, 125, "Data-quality outputs", ("uncertainty budget · exclusions", "raw/processed linkage · audit trail"), "#3dd9ff"),
    card(940, 430, 300, 125, "Acceptance gate", ("fit for declared purpose", "qualified human approval where required"), "#9b7cff"),
    arrow(460, 492, 540, 492), arrow(850, 492, 930, 492),
])
assets["laboratory_data_quality.svg"] = svg_shell(
    "Laboratory & Data Quality Chain",
    "Sample provenance, calibration, measurement conditions, raw data, quality control, uncertainty, and acceptance remain traceable.",
    "A result cannot outrun its sample identity, calibration status or measurement boundary.",
    "".join(body),
    "Raw data is immutable evidence · processing is reproducible · exclusions are declared before interpretation",
)

body = [
    card(60, 180, 220, 150, "Source", ("paper · dataset · figure", "stable identifier"), "#55e6a5"),
    card(335, 180, 220, 150, "Evidence ledger", ("exact passage / panel", "conditions · values"), "#3dd9ff"),
    card(610, 180, 220, 150, "Claim sentence", ("scope · modality", "support edge"), "#9b7cff"),
    card(885, 180, 220, 150, "Citation placement", ("at the supported clause", "no citation laundering"), "#ffbe65"),
    card(1160, 180, 180, 150, "Manuscript", ("readable prose", "audit link retained"), "#55e6a5"),
]
for x in (280, 555, 830, 1105):
    body.append(arrow(x, 255, x+45, 255))
body.extend([
    card(170, 440, 310, 120, "Scientific writing layer", ("argument, structure and terminology", "does not alter evidence strength"), "#3dd9ff"),
    card(545, 440, 310, 120, "Audit layer", ("source → evidence → claim → sentence", "conflict and uncertainty record"), "#9b7cff"),
    card(920, 440, 310, 120, "Release gate", ("all claims supported", "references and numbering consistent"), "#ffbe65"),
    arrow(480, 500, 535, 500), arrow(855, 500, 910, 500),
])
assets["scientific_writing_evidence_chain.svg"] = svg_shell(
    "Scientific Writing Evidence Chain",
    "Sources are converted into bounded evidence records, claims, citations, manuscript sentences, and an independent audit trail.",
    "Readable prose and auditable evidence are separate deliverables that must remain linked.",
    "".join(body),
    "No invented citation · no unsupported strengthening · no hidden conflict between manuscript and evidence ledger",
)

body = [
    card(70, 170, 260, 150, "Original figure", ("pixels / vectors / data", "hash and dimensions"), "#55e6a5"),
    card(400, 170, 260, 150, "Edit contract", ("allowed regions", "locked content", "target resolution"), "#3dd9ff"),
    card(730, 170, 260, 150, "Controlled edit", ("labels · defects · layout", "no silent data changes"), "#9b7cff"),
    card(1060, 170, 270, 150, "Visual diff & QA", ("overlay / geometry checks", "legibility and export"), "#ffbe65"),
    arrow(330, 245, 390, 245), arrow(660, 245, 720, 245), arrow(990, 245, 1050, 245),
    card(160, 430, 310, 135, "Locked scientific content", ("curves · scale bars · data points", "panel identity · relative geometry"), "#ff7fa0"),
    card(545, 430, 310, 135, "Permitted presentation edits", ("translation · line repair · spacing", "font clarity · crop contract"), "#55e6a5"),
    card(930, 430, 310, 135, "Approval record", ("before/after hashes", "changed regions and reviewer"), "#3dd9ff"),
]
assets["scientific_figure_edit_guard.svg"] = svg_shell(
    "Scientific Figure Edit Guard",
    "A figure-edit contract locks scientific content, permits only declared presentation changes, and requires a visual diff and approval record.",
    "Fix the requested defect without silently redrawing the experiment.",
    "".join(body),
    "Presentation enhancement is not data reconstruction · every changed region must be declared",
)

body = [
    card(70, 170, 220, 120, "Proposed", ("question and plan",), "#3dd9ff"),
    card(335, 170, 220, 120, "Completed", ("external run or task",), "#3dd9ff"),
    card(600, 170, 220, 120, "Checked", ("files, logs, balances",), "#55e6a5"),
    card(865, 170, 220, 120, "Validated", ("model and evidence",), "#ffbe65"),
    card(1130, 170, 220, 120, "Accepted", ("qualified decision",), "#9b7cff"),
]
for x in (290, 555, 820, 1085):
    body.append(arrow(x, 230, x+35, 230))
body.extend([
    card(140, 420, 300, 130, "Software can verify", ("schema · hashes · tests", "convergence evidence · provenance"), "#55e6a5"),
    card(550, 420, 300, 130, "Domain review must judge", ("governing physics · validity", "causal interpretation · uncertainty"), "#ffbe65"),
    card(960, 420, 300, 130, "Qualified approval required", ("safety · medical · patent/FTO", "high-impact scientific acceptance"), "#ff7fa0"),
    arrow(440, 485, 540, 485), arrow(850, 485, 950, 485),
])
assets["human_approval_acceptance_boundary.svg"] = svg_shell(
    "Human Approval & Scientific Acceptance Boundary",
    "Completion, checking, validation, and scientific acceptance are separate states with different software and human responsibilities.",
    "A passing workflow can establish software evidence; it cannot grant scientific authority.",
    "".join(body),
    "executed ≠ checked ≠ validated ≠ accepted · rejection and supersession remain first-class outcomes",
)

body = [
    card(55, 175, 235, 155, "Å · electronic", ("defects · bonding · trap states", "DFT / hybrid / GW-BSE"), "#9b7cff"),
    card(335, 175, 235, 155, "nm · atomistic", ("chain conformation · interfaces", "MD / enhanced sampling"), "#3dd9ff"),
    card(615, 175, 235, 155, "10 nm–µm · mesoscale", ("lamellae · domains · topology", "CGMD / SCFT / phase field"), "#55e6a5"),
    card(895, 175, 235, 155, "µm–mm · continuum", ("transport · stress · electrothermal", "FEM / drift-diffusion / CFD"), "#ffbe65"),
    card(1175, 175, 170, 155, "m · cable", ("process · ageing", "reliability"), "#ff7fa0"),
]
for x in (290, 570, 850, 1130):
    body.append(arrow(x, 252, x+35, 252))
body.extend([
    card(120, 450, 330, 120, "Bridge variables", ("trap-energy distribution · mobility", "lamellar statistics · crystallinity"), "#3dd9ff"),
    card(535, 450, 330, 120, "Cross-scale closure", ("measurable descriptors only", "uncertainty propagated at each handoff"), "#9b7cff"),
    card(950, 450, 330, 120, "Validation hierarchy", ("spectroscopy / PEA / SAXS / mechanics", "hold-out conditions and failure modes"), "#55e6a5"),
    arrow(450, 510, 525, 510), arrow(865, 510, 940, 510),
])
assets["polymer_multiscale_case_study.svg"] = svg_shell(
    "Polymer Insulation Multiscale Strategy",
    "A polymer-insulation example links electronic defects, chain dynamics, lamellar morphology, continuum fields, process history, and cable reliability.",
    "Bridge scales through measured state variables—not by visual similarity between unrelated simulations.",
    "".join(body),
    "Chemistry → morphology → transport/failure is a hypothesis chain requiring validation at every scale",
)

for name, content in assets.items():
    ET.fromstring(content)
    path = ASSET_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")

strategy_path = ROOT / "tsao_researcher" / "strategy.py"
strategy = strategy_path.read_text(encoding="utf-8")
strategy = replace_once(
    strategy,
    '            "电子结构",\n        ),',
    '''            "电子结构",
            "excited state",
            "optical excitation",
            "absorption spectrum",
            "photophysics",
            "quasiparticle",
            "electron-hole",
            "激发态",
            "光激发",
            "吸收光谱",
            "光物理",
            "准粒子",
            "电子-空穴",
        ),''',
    "electronic triggers",
)
strategy = replace_once(
    strategy,
    '                    "multireference wavefunction methods",\n                    "GW/BSE",',
    '                    "multireference wavefunction methods",\n                    "TDDFT",\n                    "GW/BSE",',
    "TDDFT method",
)
strategy_path.write_text(strategy, encoding="utf-8", newline="\n")

test_strategy_path = ROOT / "tests" / "test_first_principles_strategy.py"
test_strategy = test_strategy_path.read_text(encoding="utf-8")
test_strategy = replace_once(
    test_strategy,
    '    assert "total charge" in result["first_principles_frame"]["conserved_quantities"]\n',
    '''    assert "total charge" in result["first_principles_frame"]["conserved_quantities"]

    excited = advise_computation_strategy(
        "Which excited state controls the optical absorption spectrum and electron-hole response?",
        ["absorption spectrum", "excitation energy"],
        ["room temperature"],
    )
    assert excited["classification"]["primary_regime"] == "electronic-structure"
    methods = " ".join(
        method
        for row in excited["method_ladder"]
        for method in row["representative_methods"]
    )
    assert "TDDFT" in methods
    assert "GW/BSE" in methods
''',
    "excited-state regression",
)
test_strategy_path.write_text(test_strategy, encoding="utf-8", newline="\n")

facts_path = ROOT / "scripts" / "build_readme_facts.py"
facts_script = facts_path.read_text(encoding="utf-8")
facts_script = replace_once(
    facts_script,
    "import sys\nfrom pathlib import Path",
    "import sys\nimport xml.etree.ElementTree as ET\nfrom pathlib import Path",
    "xml import",
)
asset_tuple = '''VISUAL_ATLAS_ASSETS = (
    "docs/assets/ai/research_os_architecture.svg",
    "docs/assets/ai/multi_agent_orchestration.svg",
    "docs/assets/ai/evidence_claim_graph.svg",
    "docs/assets/ai/multiscale_science_pipeline.svg",
    "docs/assets/ai/reproducibility_quality_gates.svg",
    "docs/assets/ai/computation_handoff_boundary.svg",
    "docs/assets/ai/project_state_machine.svg",
    "docs/assets/ai/capability_landscape.svg",
    "docs/assets/ai/original_requirements_coverage.svg",
    "docs/assets/ai/capability_implementation_levels.svg",
    "docs/assets/ai/progressive_routing_loading.svg",
    "docs/assets/ai/project_ledgers_provenance.svg",
    "docs/assets/ai/evidence_citation_integrity_loop.svg",
    "docs/assets/ai/research_production_pipeline.svg",
    "docs/assets/ai/installation_compatibility_matrix.svg",
    "docs/assets/ai/supply_chain_release_attestation.svg",
    "docs/assets/ai/first_principles_strategy_ladder.svg",
    "docs/assets/ai/scientific_problem_method_decision_tree.svg",
    "docs/assets/ai/uncertainty_quantification_validation.svg",
    "docs/assets/ai/scientific_integrity_causality_guard.svg",
    "docs/assets/ai/laboratory_data_quality.svg",
    "docs/assets/ai/scientific_writing_evidence_chain.svg",
    "docs/assets/ai/scientific_figure_edit_guard.svg",
    "docs/assets/ai/human_approval_acceptance_boundary.svg",
    "docs/assets/ai/polymer_multiscale_case_study.svg",
)
'''
facts_script = replace_once(
    facts_script,
    'FACTS_PATH = ROOT / "docs/README_FACTS.json"\n',
    'FACTS_PATH = ROOT / "docs/README_FACTS.json"\n' + asset_tuple,
    "visual atlas manifest",
)
facts_script = replace_once(
    facts_script,
    '            "test_modules": len(test_modules),\n            "references": len(references),',
    '            "test_modules": len(test_modules),\n            "ai_diagrams": len(VISUAL_ATLAS_ASSETS),\n            "references": len(references),',
    "ai diagram fact",
)
facts_script = replace_once(
    facts_script,
    '        str(facts["domain_packs"]["count"]),\n    ]',
    '        str(facts["domain_packs"]["count"]),\n        str(facts["repository_assets"]["ai_diagrams"]),\n    ]',
    "required ai count token",
)
visual_validation = '''    english_atlas = (root / "docs/VISUAL_ATLAS.md").read_text(encoding="utf-8", errors="strict")
    chinese_atlas = (root / "docs/VISUAL_ATLAS.zh-CN.md").read_text(
        encoding="utf-8", errors="strict"
    )
    if len(VISUAL_ATLAS_ASSETS) < 25 or len(set(VISUAL_ATLAS_ASSETS)) != len(VISUAL_ATLAS_ASSETS):
        errors.append("visual atlas must contain at least 25 unique AI diagrams")
    for relative in VISUAL_ATLAS_ASSETS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"visual atlas asset missing or unsafe: {relative}")
            continue
        try:
            svg_root = ET.fromstring(path.read_text(encoding="utf-8", errors="strict"))
        except ET.ParseError as exc:
            errors.append(f"visual atlas SVG is invalid: {relative}: {exc}")
            continue
        if not svg_root.tag.endswith("svg"):
            errors.append(f"visual atlas asset is not SVG: {relative}")
        child_tags = {child.tag.rsplit("}", 1)[-1] for child in svg_root}
        if "title" not in child_tags or "desc" not in child_tags:
            errors.append(f"visual atlas SVG lacks title/desc accessibility metadata: {relative}")
        if relative not in english:
            errors.append(f"README.md does not embed {relative}")
        if relative not in chinese:
            errors.append(f"README.zh-CN.md does not embed {relative}")
        if path.name not in english_atlas:
            errors.append(f"VISUAL_ATLAS.md does not embed {path.name}")
        if path.name not in chinese_atlas:
            errors.append(f"VISUAL_ATLAS.zh-CN.md does not embed {path.name}")
'''
facts_script = replace_once(
    facts_script,
    '    return errors\n\n\ndef main()',
    visual_validation + '    return errors\n\n\ndef main()',
    "visual atlas validation",
)
facts_path.write_text(facts_script, encoding="utf-8", newline="\n")

supply_test_path = ROOT / "tests" / "test_supply_chain.py"
supply_test = supply_test_path.read_text(encoding="utf-8")
supply_test = replace_once(
    supply_test,
    "from scripts import build_sbom, build_validation_evidence, generate_checksums",
    "from scripts import build_readme_facts, build_sbom, build_validation_evidence, generate_checksums",
    "supply chain import",
)
supply_test = replace_once(
    supply_test,
    '    assert value["provenance"]["workflow_run_id"] is None\n'
    '    assert build_validation_evidence.validate(value) == []\n',
    '''    assert value["provenance"]["workflow_run_id"] is None
    assert build_validation_evidence.validate(value) == []
    facts = build_readme_facts.build_facts()
    assert facts["repository_assets"]["ai_diagrams"] == 25
    assert build_readme_facts._readme_errors(facts) == []
''',
    "visual atlas regression",
)
supply_test_path.write_text(supply_test, encoding="utf-8", newline="\n")

english_strategy = r'''## First-principles computation and simulation strategy

The distinctive capability is not a software-name recommender. It reconstructs method choice from the underlying science:

```text
question → decision observable → degrees of freedom/state variables
         → conservation/symmetry → quantum, statistical, thermodynamic or continuum frame
         → length/time/energy scales and model reduction
         → minimum-sufficient model → justified escalation → validation/falsification/UQ
         → external handoff → result review
```

“First principles” does not mean DFT for every problem. The advisor selects the cheapest falsifiable physical representation, then escalates only when validation identifies a missing degree of freedom, coupling or scale. See the [first-principles strategy guide](docs/FIRST_PRINCIPLES_STRATEGY.md).

### Scientific question → minimum-sufficient strategy

| Scientific question | Start from | Minimum-sufficient method | Evidence-driven escalation |
|---|---|---|---|
| Ground-state bonding, defect levels and trap states | charge/spin, symmetry, electrostatics and thermodynamic cycles | periodic/cluster DFT with convergence and finite-size control | hybrid DFT, embedding or higher-level wavefunction treatment |
| Excited states, optical spectra and carrier excitations | state character, selection rules and electron–hole degrees of freedom | TDDFT or a targeted excited-state calculation | GW/BSE, multireference or nonadiabatic dynamics |
| Reaction barriers, catalysis and selectivity | stoichiometry, detailed balance and candidate networks | DFT/wavefunction path search, NEB and transition-state optimisation | enhanced sampling, microkinetics, kinetic Monte Carlo and transport coupling |
| Conformations, solvation, free energies and rare events | ensemble, reservoirs, collective variables and correlation times | MD/Monte Carlo with umbrella, metadynamics or alchemical free energy | QM/MM, ab initio MD or a validated coarse-grained model |
| Polymer morphology, crystallisation and phase separation | entropy–energy competition, chain connectivity and order parameters | scaling/SCFT followed by CGMD, DPD or phase-field kinetics | chemistry-informed mapping, homogenisation and process–structure coupling |
| Flow, heat/mass transfer and pressure drop | conservation laws, constitutive closure and dimensionless groups | control-volume, 1D or reduced-order model | mesh-converged CFD and coupled multiphysics |
| Stress, viscoelasticity, fracture and fatigue | momentum/energy balance, material symmetry and constitutive identifiability | reduced mechanics or FEM with objective constitutive laws | phase-field/cohesive fracture and microstructure-informed mechanics |
| Charge transport, space charge and breakdown | electronic/trap states, electrochemical potential and Poisson/charge balance | hopping/kMC or drift–diffusion–Poisson | electrothermal, morphology-evolution and stochastic failure models |
| Reactors, molecular-weight distributions and process dynamics | mass/energy balances, residence time and identifiability | CSTR/PFR/network plus population-balance model | reactor-CFD, flowsheet dynamics, Bayesian calibration or digital-twin surrogate |
| Mixed or under-specified multiscale problem | observable, units, reservoirs, scales and competing mechanisms | analytical or reduced-order falsifiable model | sequential uncertainty-aware coupling through measurable bridge variables |

The strategy output remains `advisory-only` and records `solver_executed: false`. A recommended DFT, MD, FEM, CFD or process model becomes a real execution only after an approved checksum-bound handoff, external logs and output hashes, convergence review and separate scientific acceptance.
'''

chinese_strategy = r'''## 第一性原理计算与仿真策略

本项目的特色不是简单推荐软件名称，而是从底层物理重建方法选择：

```text
科学问题 → 决策可观测量 → 自由度/状态变量 → 守恒律/对称性
        → 量子、统计物理、热力学或连续介质框架
        → 时间/空间/能量尺度与模型降阶
        → 最低充分模型 → 升级模型 → 验证/证伪/UQ
        → 外部计算 handoff → 结果审查
```

“第一性原理”不等于所有问题都使用 DFT。策略顾问先选择成本最低、能够被证伪的物理表征；只有当验证明确指出缺少自由度、耦合或尺度时才升级。详见[第一性原理策略说明](docs/FIRST_PRINCIPLES_STRATEGY.zh-CN.md)。

### 科学问题 → 最低充分计算/仿真策略

| 科学问题 | 首先从何出发 | 最低充分方法 | 由证据触发的升级方法 |
|---|---|---|---|
| 基态成键、缺陷能级和陷阱态 | 电荷/自旋、对称性、静电和热力学循环 | 经过收敛与有限尺寸控制的周期/团簇 DFT | 杂化泛函、嵌入或更高层级波函数方法 |
| 激发态、光谱和载流子激发 | 态性质、选择定则与电子—空穴自由度 | TDDFT 或针对性的激发态计算 | GW/BSE、多参考方法或非绝热动力学 |
| 反应能垒、催化与选择性 | 化学计量、细致平衡和候选反应网络 | DFT/波函数路径搜索、NEB 与过渡态优化 | 增强采样、微观动力学、动力学 Monte Carlo 与输运耦合 |
| 构象、溶剂化、自由能和稀有事件 | 统计系综、库、集体变量和相关时间 | MD/Monte Carlo、umbrella、metadynamics 或炼金自由能 | QM/MM、从头算 MD 或经验证的粗粒化模型 |
| 高分子形貌、结晶和相分离 | 熵—能竞争、链连接性和序参量 | 标度/SCFT，随后使用 CGMD、DPD 或相场动力学 | 化学信息映射、均匀化和工艺—结构耦合 |
| 流动、传热传质和压降 | 守恒律、本构闭合和无量纲数 | 控制体、1D 或降阶模型 | 网格收敛的 CFD 与耦合多物理场 |
| 应力、黏弹、断裂与疲劳 | 动量/能量平衡、材料对称性和本构可识别性 | 降阶力学或采用客观本构的 FEM | 相场/黏聚断裂和微结构知情力学 |
| 电荷输运、空间电荷和击穿 | 电子/陷阱态、电化学势及 Poisson/电荷守恒 | 跳跃/kMC 或漂移—扩散—Poisson | 电—热、形貌演化和随机失效模型 |
| 反应器、分子量分布和流程动态 | 质量/能量平衡、停留时间和可识别性 | CSTR/PFR/网络与群体平衡模型 | 反应器 CFD、流程动态、贝叶斯校准或数字孪生代理 |
| 混合或定义不足的多尺度问题 | 可观测量、单位、库、尺度和竞争机理 | 可证伪的解析或降阶模型 | 通过可测桥接变量进行顺序、含不确定度的耦合 |

策略输出始终为 `advisory-only`，并明确记录 `solver_executed: false`。推荐 DFT、MD、FEM、CFD 或流程模型不等于已经执行；只有完成经批准的校验和 handoff、外部日志与输出哈希、收敛审查和独立科学接受后，才能进入更高真实性状态。
'''

readme_path = ROOT / "README.md"
english = readme_path.read_text(encoding="utf-8")
english = replace_section(
    english,
    "## First-principles computation and simulation strategy",
    "## Research lifecycle and workflows",
    english_strategy,
    "README English strategy",
)

english_visual = r'''## Scientific capability visual atlas

The following **25 AI-generated, repository-specific conceptual diagrams** describe the actual contracts, control flow, provenance, scientific reasoning and execution boundaries. They are documentation assets—not experimental observations, simulation outputs, or proof that an external engine ran.

<table>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/research_os_architecture.svg" alt="Research OS architecture"/><br/><strong>1 · Research OS architecture</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="Multi-agent orchestration"/><br/><strong>2 · Multi-agent orchestration</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="Evidence–claim graph"/><br/><strong>3 · Evidence–claim graph</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="Multiscale science pipeline"/><br/><strong>4 · Multiscale science pipeline</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="Reproducibility quality gates"/><br/><strong>5 · Reproducibility quality gates</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="Computation handoff boundary"/><br/><strong>6 · Computation handoff boundary</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/project_state_machine.svg" alt="Project state machine"/><br/><strong>7 · Project state machine</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_landscape.svg" alt="Capability landscape"/><br/><strong>8 · Capability landscape</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="Original requirements coverage"/><br/><strong>9 · Original requirements coverage</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="Implementation levels"/><br/><strong>10 · Implementation levels</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="Progressive routing and loading"/><br/><strong>11 · Progressive routing and loading</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="Project ledgers and provenance"/><br/><strong>12 · Project ledgers and provenance</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="Evidence and citation integrity"/><br/><strong>13 · Evidence and citation integrity</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/research_production_pipeline.svg" alt="Research production pipeline"/><br/><strong>14 · Research production pipeline</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="Installation compatibility"/><br/><strong>15 · Installation compatibility</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="Supply-chain attestation"/><br/><strong>16 · Supply-chain attestation</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="First-principles strategy ladder"/><br/><strong>17 · First-principles strategy ladder</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="Scientific problem method decision tree"/><br/><strong>18 · Problem → method decision tree</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="Uncertainty quantification and validation"/><br/><strong>19 · UQ and model validation</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="Scientific integrity and causality guard"/><br/><strong>20 · Integrity and causality guard</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="Laboratory and data quality"/><br/><strong>21 · Laboratory and data quality</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="Scientific writing evidence chain"/><br/><strong>22 · Scientific writing evidence chain</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="Scientific figure edit guard"/><br/><strong>23 · Scientific figure edit guard</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="Human approval and acceptance boundary"/><br/><strong>24 · Human approval boundary</strong></td></tr>
<tr><td colspan="2" valign="top"><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="Polymer insulation multiscale case study"/><br/><strong>25 · Polymer-insulation multiscale strategy case</strong></td></tr>
</table>

The complete bilingual atlas is available in [docs/VISUAL_ATLAS.md](docs/VISUAL_ATLAS.md). Every SVG is self-contained, accessible through `<title>` and `<desc>`, checked into the repository, and validated against the README asset manifest.
'''

english = replace_section(
    english,
    "## Scientific capability visual atlas",
    "## Quick start",
    english_visual,
    "README English visual atlas",
)
readme_path.write_text(english, encoding="utf-8", newline="\n")
(ROOT / "README_EN.md").write_text(english, encoding="utf-8", newline="\n")

chinese_path = ROOT / "README.zh-CN.md"
chinese = chinese_path.read_text(encoding="utf-8")
chinese = replace_section(
    chinese,
    "## 第一性原理计算与仿真策略",
    "## 科研生命周期与工作流",
    chinese_strategy,
    "README Chinese strategy",
)
chinese_visual = r'''## 科研能力 AI 示意图谱

以下为**依据当前仓库代码和能力边界生成的 25 张 AI 概念图**，用于解释能力合同、控制流、溯源、底层科学推理和执行边界；它们属于文档资产，不是实验观测、模拟结果，也不是外部引擎已经运行的证明。

<table>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/research_os_architecture.svg" alt="科研操作系统架构"/><br/><strong>1 · 科研操作系统架构</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="多智能体科研编排"/><br/><strong>2 · 多智能体科研编排</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="证据—论断图"/><br/><strong>3 · 证据—论断图</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="多尺度科研流程"/><br/><strong>4 · 多尺度科研流程</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="可复现质量门"/><br/><strong>5 · 可复现质量门</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="计算交接边界"/><br/><strong>6 · 计算交接边界</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/project_state_machine.svg" alt="项目状态机"/><br/><strong>7 · 项目状态机</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_landscape.svg" alt="科研能力版图"/><br/><strong>8 · 科研能力版图</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="最初需求落实图"/><br/><strong>9 · 最初需求落实图</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="能力实现层级"/><br/><strong>10 · 能力实现层级</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="渐进式路由与加载"/><br/><strong>11 · 渐进式路由与加载</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="项目台账与溯源"/><br/><strong>12 · 项目台账与溯源</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="证据与引文完整性"/><br/><strong>13 · 证据与引文完整性</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/research_production_pipeline.svg" alt="科研产出流水线"/><br/><strong>14 · 科研产出流水线</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="安装兼容矩阵"/><br/><strong>15 · 安装兼容矩阵</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="供应链与发布证明"/><br/><strong>16 · 供应链与发布证明</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="第一性原理策略阶梯"/><br/><strong>17 · 第一性原理策略阶梯</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="科学问题到方法决策树"/><br/><strong>18 · 科学问题—方法决策树</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定度量化与验证"/><br/><strong>19 · UQ 与模型验证</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="科研诚信与因果防护"/><br/><strong>20 · 科研诚信与因果防护</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="实验室与数据质量"/><br/><strong>21 · 实验室与数据质量</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="科研写作证据链"/><br/><strong>22 · 科研写作证据链</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="科学图片编辑防护"/><br/><strong>23 · 科学图片编辑防护</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="人工审批与科学接受边界"/><br/><strong>24 · 人工审批与科学接受边界</strong></td></tr>
<tr><td colspan="2" valign="top"><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="高分子绝缘多尺度案例"/><br/><strong>25 · 高分子绝缘多尺度策略案例</strong></td></tr>
</table>

完整双语图谱见 [docs/VISUAL_ATLAS.zh-CN.md](docs/VISUAL_ATLAS.zh-CN.md)。全部 SVG 均为仓库内自包含资产，具有 `<title>` 与 `<desc>` 可访问性信息，并由 README 图谱清单进行自动验证。
'''
chinese = replace_section(
    chinese,
    "## 科研能力 AI 示意图谱",
    "## 快速开始",
    chinese_visual,
    "README Chinese visual atlas",
)
chinese_path.write_text(chinese, encoding="utf-8", newline="\n")

english_atlas_lines = [
    "# Scientific Capability Visual Atlas",
    "",
    "These 25 AI-generated conceptual diagrams are derived from repository architecture, capability contracts, validators and explicit execution boundaries. They are documentation assets, not scientific results or execution receipts.",
    "",
]
chinese_atlas_lines = [
    "# 科研能力 AI 示意图谱",
    "",
    "以下 25 张 AI 概念图依据仓库架构、能力合同、验证器和明确执行边界生成。它们属于文档资产，不是科学结果，也不是外部执行凭据。",
    "",
]
titles = [
    ("Research OS architecture", "科研操作系统架构", "research_os_architecture.svg"),
    ("Multi-agent orchestration", "多智能体科研编排", "multi_agent_orchestration.svg"),
    ("Evidence–claim graph", "证据—论断图", "evidence_claim_graph.svg"),
    ("Multiscale science pipeline", "多尺度科研流程", "multiscale_science_pipeline.svg"),
    ("Reproducibility quality gates", "可复现质量门", "reproducibility_quality_gates.svg"),
    ("Computation handoff boundary", "计算交接边界", "computation_handoff_boundary.svg"),
    ("Project state machine", "项目状态机", "project_state_machine.svg"),
    ("Capability landscape", "科研能力版图", "capability_landscape.svg"),
    ("Original requirements coverage", "最初需求落实图", "original_requirements_coverage.svg"),
    ("Capability implementation levels", "能力实现层级", "capability_implementation_levels.svg"),
    ("Progressive routing and loading", "渐进式路由与加载", "progressive_routing_loading.svg"),
    ("Project ledgers and provenance", "项目台账与溯源", "project_ledgers_provenance.svg"),
    ("Evidence and citation integrity", "证据与引文完整性", "evidence_citation_integrity_loop.svg"),
    ("Research production pipeline", "科研产出流水线", "research_production_pipeline.svg"),
    ("Installation compatibility", "安装兼容矩阵", "installation_compatibility_matrix.svg"),
    ("Supply-chain and release attestation", "供应链与发布证明", "supply_chain_release_attestation.svg"),
    ("First-principles strategy ladder", "第一性原理策略阶梯", "first_principles_strategy_ladder.svg"),
    ("Scientific problem → method decision tree", "科学问题—方法决策树", "scientific_problem_method_decision_tree.svg"),
    ("Uncertainty quantification and validation", "不确定度量化与验证", "uncertainty_quantification_validation.svg"),
    ("Scientific integrity and causality guard", "科研诚信与因果防护", "scientific_integrity_causality_guard.svg"),
    ("Laboratory and data quality", "实验室与数据质量", "laboratory_data_quality.svg"),
    ("Scientific writing evidence chain", "科研写作证据链", "scientific_writing_evidence_chain.svg"),
    ("Scientific figure edit guard", "科学图片编辑防护", "scientific_figure_edit_guard.svg"),
    ("Human approval and acceptance boundary", "人工审批与科学接受边界", "human_approval_acceptance_boundary.svg"),
    ("Polymer-insulation multiscale strategy", "高分子绝缘多尺度策略", "polymer_multiscale_case_study.svg"),
]
for index, (en_title, zh_title, filename) in enumerate(titles, 1):
    english_atlas_lines.extend([f"## {index}. {en_title}", "", f"![{en_title}](assets/ai/{filename})", ""])
    chinese_atlas_lines.extend([f"## {index}. {zh_title}", "", f"![{zh_title}](assets/ai/{filename})", ""])
(ROOT / "docs/VISUAL_ATLAS.md").write_text("\n".join(english_atlas_lines).rstrip() + "\n", encoding="utf-8")
(ROOT / "docs/VISUAL_ATLAS.zh-CN.md").write_text(
    "\n".join(chinese_atlas_lines).rstrip() + "\n", encoding="utf-8"
)

english_guide_path = ROOT / "docs/FIRST_PRINCIPLES_STRATEGY.md"
english_guide = english_guide_path.read_text(encoding="utf-8")
english_append = r'''
## Scientific question to method ladder

| Regime | Minimum-sufficient start | Escalation when missing physics is demonstrated |
|---|---|---|
| Electronic ground state and defects | exact charge/spin/symmetry bookkeeping; converged DFT | hybrid DFT, embedding or wavefunction benchmarks |
| Excited states and spectra | state-character and selection-rule analysis; TDDFT | GW/BSE, multireference or nonadiabatic dynamics |
| Reactions and catalysis | thermodynamic network consistency; DFT/NEB/TS | enhanced sampling, microkinetics, kMC and reaction–transport coupling |
| Molecular free energy | ensemble definition; MD/MC and free-energy estimation | QM/MM, ab initio MD or validated coarse-graining |
| Polymer morphology | scaling/SCFT and order-parameter selection | CGMD/DPD/phase field, then validated cross-scale closure |
| Continuum transport | balances, constitutive closure and dimensionless analysis | mesh-converged CFD and coupled multiphysics |
| Mechanics and fracture | energy, symmetry and constitutive identifiability | FEM, phase-field/cohesive fracture and microstructure models |
| Charge transport and breakdown | trap/injection state analysis and charge conservation | kMC/drift–diffusion–Poisson, electrothermal and stochastic failure |
| Process and populations | mass/energy balances and identifiability | PBE/reactor networks, CFD/flowsheets and Bayesian calibration |
| Mixed problem | define observable, reservoirs, scales and falsification target | sequential uncertainty-aware multiscale coupling |

## Truth-preserving escalation rule

1. A solver recommendation is a plan, not an execution.
2. An execution receipt proves that a process ran, not that it converged.
3. Numerical convergence does not establish model validity.
4. Model validity for one observable does not establish a causal mechanism.
5. Scientific acceptance requires independent evidence and qualified review appropriate to the claim.
'''
if "## Scientific question to method ladder" not in english_guide:
    english_guide = english_guide.rstrip() + "\n\n" + english_append.strip() + "\n"
english_guide_path.write_text(english_guide, encoding="utf-8", newline="\n")

chinese_guide_path = ROOT / "docs/FIRST_PRINCIPLES_STRATEGY.zh-CN.md"
chinese_guide = chinese_guide_path.read_text(encoding="utf-8")
chinese_append = r'''
## 科学问题到方法阶梯

| 物理区间 | 最低充分起点 | 证明缺少物理后再升级 |
|---|---|---|
| 电子基态与缺陷 | 电荷/自旋/对称性记账；收敛 DFT | 杂化泛函、嵌入或波函数基准 |
| 激发态与光谱 | 态性质和选择定则；TDDFT | GW/BSE、多参考或非绝热动力学 |
| 反应与催化 | 热力学网络一致性；DFT/NEB/过渡态 | 增强采样、微观动力学、kMC 与反应—输运耦合 |
| 分子自由能 | 定义统计系综；MD/MC 与自由能估计 | QM/MM、从头算 MD 或经验证的粗粒化 |
| 高分子形貌 | 标度/SCFT 与序参量选择 | CGMD/DPD/相场，再进行经验证的跨尺度闭合 |
| 连续介质输运 | 守恒平衡、本构闭合和无量纲分析 | 网格收敛 CFD 与耦合多物理场 |
| 力学与断裂 | 能量、对称性和本构可识别性 | FEM、相场/黏聚断裂和微结构模型 |
| 电荷输运与击穿 | 陷阱/注入态分析和电荷守恒 | kMC/漂移—扩散—Poisson、电热与随机失效 |
| 流程与群体 | 质量/能量平衡和可识别性 | PBE/反应器网络、CFD/流程与贝叶斯校准 |
| 混合问题 | 明确可观测量、库、尺度和证伪目标 | 顺序、含不确定度的多尺度耦合 |

## 保持真实性的方法升级规则

1. 推荐求解器只是计划，不是执行。
2. Execution Receipt 只能证明进程运行过，不能证明已经收敛。
3. 数值收敛不能自动证明模型有效。
4. 针对一个可观测量的模型有效性不能自动证明因果机理。
5. 科学接受需要与论断风险相匹配的独立证据和合格审查。
'''
if "## 科学问题到方法阶梯" not in chinese_guide:
    chinese_guide = chinese_guide.rstrip() + "\n\n" + chinese_append.strip() + "\n"
chinese_guide_path.write_text(chinese_guide, encoding="utf-8", newline="\n")

Path(__file__).unlink()
