# TSAO README visual system

This document is the persistent source of truth for the repository-owned README diagrams. It applies the workflow and quality priorities of [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) and its [Chinese tutorial project](https://github.com/bbylw/ui-ux-pro-max-skill-cn) to a scientific-engineering developer tool. No upstream code or artwork is copied.

## Product classification

- Product type: scientific engineering developer tool / AI-assisted process-package platform.
- Primary audience: polymer scientists, process engineers, model developers, reviewers and maintainers.
- Usage context: technical README, audit evidence, model explanation and release qualification.
- Visual objective: make complex engineering relationships understandable without making software qualification look like scientific or industrial approval.

## Selected design system

| Dimension | Decision |
|---|---|
| Pattern | Decision-centered technical narrative with Bento-style cards and explicit Gate bands |
| Style | Swiss/Minimal + restrained AI-native data UI |
| Variance | 4/10 — balanced, systematic, no decorative asymmetry |
| Motion | 1/10 — static SVG; no ornamental animation |
| Density | 7/10 — information-dense but grouped on an 8 px rhythm |
| Theme | Scientific Midnight Bento |
| Typography | Inter / Segoe UI for labels; JetBrains Mono / Consolas for states, IDs and metrics |
| Icon language | Original inline SVG geometry only; no emoji and no external icon dependency |

## Core tokens

| Token | Value | Use |
|---|---|---|
| Background | `#07111F` → `#0B1729` | dark scientific canvas |
| Surface | `#101E33`, `#14243B` | cards and central nodes |
| Border | `#263A55` | restrained separation |
| Primary | `#4F7CFF` | platform, source and model structure |
| Cyan | `#22D3EE` | kinetics, calculation and interfaces |
| Teal | `#2DD4BF` | batch computing and process flow |
| Green | `#34D399` | qualified software evidence and accepted outputs |
| Amber | `#FBBF24` | caution, Gate and conditional status |
| Red | `#FB7185` | failure, deactivation and safety-critical paths |
| Purple | `#A78BFA` | detailed models, uncertainty and specialist computation |
| Main text | `#F8FAFC` | titles and critical labels |
| Muted text | `#A8B5C7` | descriptions and secondary metadata |

## Layout contract

1. Every SVG uses a `1200 × 720` view box.
2. The header contains a category pill, one dominant title and one concise subtitle.
3. The body uses cards, nodes or a flow—not paragraph-shaped artwork.
4. Every diagram ends with a persistent responsibility or fail-closed band.
5. Color is never the only carrier of status; labels such as `PASS`, `HOLD`, `FAIL` and `NOT_EVALUATED` remain visible.
6. Body text stays at or above 12 px; principal labels stay at or above 15 px.
7. Connectors use consistent arrowheads and avoid crossing wherever practical.
8. The same semantic color means the same thing across all 29 diagrams.

## Accessibility and quality checks

- Every README reference has non-empty alt text.
- Every SVG contains `<title>` and `<desc>` elements.
- The palette uses high-contrast light text on dark surfaces.
- No information relies on hover, animation or color alone.
- No external font, image, JavaScript or network request is required.
- The master generator is deterministic and produces the complete 29-file set.
- English and Chinese READMEs must reference exactly the same SVG filenames.

## Anti-patterns

- Do not mix unrelated visual styles between diagrams.
- Do not use decorative purple/pink AI gradients as a substitute for hierarchy.
- Do not use emoji as icons.
- Do not place dense explanatory paragraphs inside SVG cards.
- Do not show software `PASS` as scientific, engineering, HSE, customer or industrial approval.
- Do not hand-edit generated SVG files; change the master generator instead.

## Generation workflow

```bash
python scripts/generate_readme_assets.py
python scripts/generate_extended_readme_assets.py
python scripts/generate_decision_readme_assets.py
python scripts/generate_performance_readme_assets.py
python scripts/generate_uiux_readme_assets.py
python scripts/harden_readme_svg_accessibility.py
python scripts/verify_readme_visual_accessibility.py
python scripts/sync_readme_visuals.py --check
```

The four historical generators remain available for lineage and focused maintenance. `generate_uiux_readme_assets.py` remains the master visual-normalization layer for all 29 files; `harden_readme_svg_accessibility.py` then adds stable responsive/rendering metadata, and `verify_readme_visual_accessibility.py` fail-closes on contrast, text size, external resources, emoji, missing title/description or inconsistent root attributes. The committed palette exceeds 4.5:1 for primary text and 3:1 for secondary text and semantic glyphs on the dark surfaces.

---

# TSAO README 视觉系统

本文档是仓库 README 配图的持久化设计系统。它将 UI/UX Pro Max 的“先识别产品类型、再生成设计系统、最后进行无障碍与反模式检查”的方式应用到科研与化工工艺软件中。

核心口径：**Swiss/Minimal + Bento Grid + 克制的 AI-Native Data UI**。采用深海军蓝背景、蓝青色计算链、绿色合格软件证据、琥珀色条件门和红色失败路径；使用 Inter 与 JetBrains Mono；全部图标均为仓库内原创 SVG 几何，不使用 emoji、外链图片或装饰性动效。

所有 29 幅图必须保持统一层级、统一语义色、明确文字标签和底部责任边界。修改图形时只修改主生成器，不得直接手工改写生成后的 SVG。软件通过状态不得被视觉上包装成科学、工程、HSE、客户或工业批准。


## AI-native scientific visual family

The eight AI-native diagrams are not decorative illustrations. They formalize the platform's reasoning, inverse-design, active-learning, knowledge-graph and model-governance contracts. Each diagram preserves the same fail-closed color semantics and explicitly separates software execution from scientific, engineering, HSE and customer authority.

- `ai-scientific-reasoning-loop.svg`
- `agentic-qualification-orchestrator.svg`
- `multiscale-digital-thread.svg`
- `law-to-grade-inverse-design.svg`
- `autonomous-experiment-loop.svg`
- `process-knowledge-graph.svg`
- `uncertainty-decision-landscape.svg`
- `model-risk-governance.svg`
