# TsaoDFT README Visual Design System

This document is the source of truth for the TsaoDFT README visual system. The workflow follows UI/UX Pro Max in the required order: product classification → pattern → style → color → typography → density/effects → anti-pattern filtering → accessibility and pre-delivery review.

Reference methods:

- [`nextlevelbuilder/ui-ux-pro-max-skill`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [`bbylw/ui-ux-pro-max-skill-cn`](https://github.com/bbylw/ui-ux-pro-max-skill-cn)

## 1. Product classification

- Product type: scientific developer tool / computational-research infrastructure / documentation-led research operating system.
- Primary users: computational chemists, materials scientists, scientific-software developers, research supervisors and reviewers.
- Primary context: GitHub README on desktop, tablet and narrow mobile view; figures are commonly rendered at 50–100% content width.
- Decision order: scientific boundary → evidence chain → capability map → deterministic demonstrations → installation and quality gate.
- Trust requirement: high. Any visual ambiguity that could be interpreted as a real scientific result is unacceptable.

## 2. Recommended pattern

### Primary pattern

**Hero-Centric Research Operating System**

The first viewport must establish:

1. DFT-first identity;
2. molecular + periodic + HPC scope;
3. evidence-before-claims positioning;
4. explicit AI-concept boundary.

### Secondary pattern

**Evidence Bento + Technical Architecture Gallery + Trust & Authority**

- a compact capability strip;
- one six-stage evidence workflow;
- a curated deterministic scientific-figure gallery;
- a nine-figure acceleration architecture gallery;
- support levels and quality-gate proof in the README body.

### Design dials

- variance: `6/10` — recognisable identity without visual chaos;
- motion: `1/10` — static GitHub SVG, no decorative animation;
- density: `6/10` — information-rich but readable at 50% width.

## 3. Style synthesis

The v9 visual system combines:

- **Dark OLED Scientific UI** for computational identity;
- **Swiss Modernism 2.0** for hierarchy, alignment and typography;
- **Bento Grid** for capability grouping;
- **Accessible Minimalism** for contrast and readable labels;
- **restrained HUD/FUI motifs** only where they communicate provenance, workflow or engine context.

It deliberately avoids a generic SaaS landing page, uncontrolled neon, crypto/cyberpunk clichés and endless module-card walls.

## 4. Core tokens

### Color

| Token | Value | Use |
|---|---|---|
| Canvas | `#020712` | global background |
| Deep surface | `#07111F` | evidence cards |
| Raised surface | `#0B1930` | capability cards |
| Border | `#294767` | card separation |
| Grid | `#173052` | low-contrast technical grid |
| Primary text | `#F3F8FF` | headings and critical labels |
| Secondary text | `#A9BDD4` | descriptions |
| Cyan | `#62D8FF` | molecular evidence and portability interfaces |
| Blue | `#4EA4FF` | Windows, HPC and engine context |
| Violet | `#8A7CFF` | periodic evidence and registry authority |
| Magenta | `#C277FF` | ML and analysis |
| Teal | `#5BE3C5` | validation, portability and accepted gates |
| Orange | `#FF9A4D` | kinetics, transfer cost and scale |
| Coral | `#FF725E` | catalysis / warning emphasis |

Color is never the only state signal. Every color-coded region also carries a textual label.

### Typography

- Display and body: Inter-compatible system sans stack.
- Technical labels and identifiers: JetBrains Mono-compatible system monospace stack.
- Cover title: 70 px at 1600 px canvas width.
- Section labels: 24 px.
- Card labels: 16 px.
- Minimum text in technical SVGs: 12 px at 1120 px canvas width.
- README prose remains native Markdown/HTML rather than baked into raster images.

### Spacing and geometry

- spacing scale: `8 / 12 / 16 / 24 / 32 / 48 px`;
- card radius: `14–22 px`;
- hero radius: `22 px`;
- border width: `1–1.5 px`;
- shadow: low-opacity vertical depth only;
- glow: reserved for scientific identity and active evidence motifs.

## 5. Composition rules

1. The governed AI asset is exactly one self-contained SVG cover.
2. A fresh AI-generated molecular / lattice / HPC composition was used as visual direction; the repository cover reconstructs those motifs as deterministic vector geometry so it remains self-contained, crisp and reviewable.
3. All project names, skill names, capability labels, states and disclaimers are vector text controlled by repository code—not generated-image text.
4. The cover contains three layers: hero identity, capability strip, and evidence workflow/bento.
5. Quantitative scientific plots remain in deterministic demo SVGs, never in the AI cover.
6. Both README languages embed the same governed cover and the same 14 required deterministic demonstrations.
7. The repository validates 17 deterministic SVG demonstrations by exact dimensions and title; not every demonstration must be embedded.
8. The README uses one 2×2 scientific gallery plus a structured nine-figure acceleration gallery, not an unstructured image wall.
9. Detailed engineering and scientific content is linked to docs instead of overloading the first viewport.
10. Every acceleration figure carries a visible non-data label and an accessible synthetic/non-scientific description.

## 6. Architecture-gallery semantics

The nine acceleration figures are deliberately non-overlapping:

1. hybrid control/native/GPU/external-engine architecture;
2. CUDA-X workload decision map;
3. edge-to-HPC uncertainty and fallback loop;
4. profile-gated native migration roadmap;
5. scoped-L3 evidence qualification pipeline;
6. canonical registry governance and drift prevention;
7. backend-neutral Array API / DLPack portability stack;
8. Windows PowerShell versus Linux/HPC execution matrix;
9. scientific acceleration qualification funnel.

No diagram may imply that a library is installed, a GPU kernel executed, an external engine accelerated, or an L3 scope accepted.

## 7. Anti-patterns

The visual system rejects:

- fake CI, coverage, version, support-level or benchmark claims inside generated imagery;
- AI-generated text for engine names, scientific labels or workflow states;
- screenshots that mimic real Gaussian/VASP/QE/CP2K results;
- pale generic SaaS cards that erase scientific identity;
- uncontrolled purple/pink gradients;
- decorative neon without information meaning;
- repeating the same module list in the cover and README prose without added evidence;
- body text below readable GitHub scale;
- colour-only success/failure encoding;
- unsupported L3 or “production-ready” claims;
- external font, JavaScript or runtime image dependencies inside the SVG.

## 8. Accessibility and pre-delivery checklist

- [x] Dark surfaces and primary text exceed the intended contrast threshold.
- [x] `role="img"`, `<title>` and `<desc>` are present.
- [x] The non-computational-data notice is visible inside the cover.
- [x] Every deterministic SVG has a visible synthetic/non-scientific-data notice.
- [x] The AI declaration appears immediately before the cover in both README files.
- [x] No generated-image text is used as project truth.
- [x] All capability colors also have labels.
- [x] Cover dimensions and SHA-256 are recorded in the AI manifest.
- [x] Deterministic assets are validated by exact title and dimensions.
- [x] Both README files embed the same required asset set.
- [x] All local links are intended to pass the offline link validator.
- [x] The cover and architecture figures cannot be mistaken for scientific or performance results.

## 9. Version

- visual system: `uiux_pro_v9_hero_evidence_architecture_gallery`;
- cover size: `1600 × 900`;
- deterministic demo canvases: fixed per `scripts/generate_readme_demos.py`;
- generation record: [`assets/ai/prompts/README-ai-concept-montage.md`](../assets/ai/prompts/README-ai-concept-montage.md);
- governance: [`AI_IMAGE_GOVERNANCE.md`](AI_IMAGE_GOVERNANCE.md).
