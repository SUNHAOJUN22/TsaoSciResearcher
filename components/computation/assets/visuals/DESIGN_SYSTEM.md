# Scientific Research Console V13 visual system

This repository-local system applies the current
[UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
priority model together with the
[Chinese tutorial](https://github.com/bbylw/ui-ux-pro-max-skill-cn)
to TsaoSciComputation README illustrations.

## Product and audience

- Product type: scientific developer tool, workflow orchestrator and evidence-governance platform.
- Audience: researchers, simulation engineers, software reviewers and technical decision makers.
- Context: GitHub README at desktop, tablet and narrow browser widths.
- Primary task: understand scope, sequence, evidence strength and failure boundaries without zooming.

## Design dials

- Variance: 5/10 — five information layouts share one visual grammar.
- Motion: 0/10 — static SVGs make no interaction or live-execution claim.
- Density: 4/10 — generous spacing protects legibility after GitHub scaling.

## Priority decisions

1. Accessibility: high contrast, unique titles/descriptions and no color-only meaning.
2. Progressive disclosure: the root READMEs surface 12 representative diagrams while the atlas retains all 43.
3. Performance: self-contained SVG, with no network resources, filters, raster images or external fonts.
4. Style: technical editorial + Swiss grid + restrained Bento hierarchy.
5. Responsive layout: the hero and nine detailed diagrams are full width; only two architecture overviews share a row.
6. Typography: minimum 16 px, concise two-line stage copy and system font stacks.
7. Icons: one consistent line-icon family; no emoji or decorative pseudo-data.

## Layout families

| Layout | Purpose |
|---|---|
| Hero | Establish product scope and cross-scale handoffs |
| Bento | Compare architecture, registries and decision responsibilities |
| Workflow | Explain ordered computation and evidence transfer |
| Loop | Show bounded iteration, updating and revalidation |
| Risk | Separate initiating conditions, barriers, consequences and authority |

## Tokens

| Role | Token |
|---|---|
| Canvas | `#07111F` |
| Surface | `#0F1B2D` |
| Raised surface | `#162338` |
| Border | `#334865` |
| Primary text | `#F8FAFC` |
| Secondary text | `#D1D9E6` |
| Muted text | `#93A4BB` |
| Blue | `#60A5FA` |
| Cyan | `#22D3EE` |
| Teal | `#2DD4BF` |
| Green | `#4ADE80` |
| Amber | `#FBBF24` |
| Orange | `#FB923C` |
| Risk red | `#F87171` |

## Accessibility and trust rules

- Meaning is encoded by labels, shapes and position as well as color.
- Every illustration has a unique accessible `<title>` and `<desc>`.
- Every SVG declares its design system, icon system, family and layout.
- SVGs contain no scripts, event handlers, external URLs, raster images, gradients or filters.
- Diagrams explain architecture and scientific boundaries; they are not solver screenshots,
  benchmark plots or evidence of live DFT, MD, CFD or HPC execution.

## Anti-patterns

- Purple/pink AI gradients, neon glow, glass decoration and simulated dashboards.
- Emoji as icons or mixed icon styles.
- Detailed workflows in narrow half-width README cells.
- Dense paragraphs inside diagrams or body labels below 16 px.
- Fabricated curves, numerical values, badges or external-engine screenshots.
