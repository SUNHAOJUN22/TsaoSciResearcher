# TRIZ Sources and Provenance / TRIZ 来源与证据图谱

This file is the source map for the OpenDeepMind TRIZ module. It distinguishes historical/classical lineage, current MATRIZ terminology, software/data provenance, and modern implementations.

## 1. Historical TRIZ lineage

Primary/classical books commonly used for TRIZ theory:

- Genrich Altshuller, *Creativity as an Exact Science*.
- Genrich Altshuller, *The Innovation Algorithm*.
- Classical works on contradictions, inventive principles, ARIZ, substance–field resources, standard inventive solutions, ideality/IFR, engineering-system evolution, system operator, and psychological-inertia tools.

For exact historical wording, dates, translations, and standard/ARIZ numbering, use the selected primary edition rather than relying on secondary paraphrases.

Official Altshuller Foundation English portal:

- https://www.altshuller.ru/world/eng/index.asp

## 2. MATRIZ public knowledge base — current operational terminology

Primary current web reference:

- MATRIZ TRIZ Knowledge Base: https://wiki.matriz.org/
- Problem-identification tools: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/
- Function analysis: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/function-cost-analysis-7189/function-analysis-5611/
- Function model: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/function-cost-analysis-7189/function-analysis-5611/function-modeling-5810/function-model-6290/
- Flow analysis / flow disadvantages: https://wiki.matriz.org/docs/triz/problem-solving-tools-5807/flow-analysis-5839/
- CECA: https://wiki.matriz.org/docs/triz/problem-solving-tools-5807/cause-effect-chain-analysis-5817/
- Trimming: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/trimming-6398/
- Feature transfer: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/feature-transfer-7060/
- Key problem: https://wiki.matriz.org/knowledge-base/docs/triz/problem-solving-tools-5807/key-problem-7057/
- Contradictions: https://wiki.matriz.org/docs/triz/problem-solving-tools-5890/contradictions/
- Contradiction matrix: https://wiki.matriz.org/docs/triz/problem-solving-tools-5890/contradictions/engineering-contradiction-5995/contradiction-matrix-6026/
- Typical parameters: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5890/contradictions/engineering-contradiction-5995/contradiction-matrix-6026/typical-parameters/
- Su-Field modeling: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5890/substance-field-modeling/
- 76 Standard Inventive Solutions: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5890/substance-field-modeling/standard-inventive-solutions/
- ARIZ: https://wiki.matriz.org/docs/triz/problem-solving-tools-5890/ariz-5892/
- IFR: https://wiki.matriz.org/docs/triz/problem-solving-tools-5890/ariz-5892/ideal-final-result-5922/
- Function-Oriented Search: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5890/function-oriented-search-fos/
- Database of scientific effects: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5890/database-of-scientific-effects/
- S-curve analysis: https://wiki.matriz.org/knowledge-base/triz/problem-solving-tools-5807/s-curve-analysis/
- TESE / trends: https://wiki.matriz.org/docs/triz/trends-of-engineering-systems-evolution-tese-5919/
- Concept substantiation: https://wiki.matriz.org/docs/triz/concept-substantiation/
- MATRIZ glossary: https://wiki.matriz.org/docs/triz/glossary-6146/

### ARIZ-85C source/template

MATRIZ provides public ARIZ-85C material and an editable template from its ARIZ knowledge-base pages. For exact algorithm text, consult that source directly. The MATRIZ ARIZ pages also explicitly frame ARIZ as a tool for overcoming psychological inertia and revealing system/supersystem resources.

## 3. Altshuller Institute / TRIZ Innovation Center

- Altshuller Institute: https://www.aitriz.org/
- Altshuller Institute TRIZ Body of Knowledge: https://www.aitriz.org/triz/triz-body-of-knowledge
- TRIZ Innovation Center / 40 Principles: https://triz.org/principles/
- TRIZ contradictions / separation: https://triz.org/contradictions/
- TRIZ ARIZ overview: https://triz.org/ariz/
- Altshuller Institute Nine Windows article: https://w.aitriz.org/blog/altshuller-institute-blog/nine-windows-technique-framework-for-the-future

These sources are useful cross-checks for classical TRIZ terminology, ARIZ, contradiction/separation, Nine Windows/System Operator, and psychological-inertia practices.

### Psychological-inertia operators

Classical TRIZ literature and Altshuller Institute materials describe deliberate tools for breaking psychological inertia, including:

- Nine Windows / System Operator;
- Size–Time–Cost (STC) operator;
- Smart Little People / little-men modeling;
- contradiction intensification inside ARIZ.

OpenDeepMind consolidates these as auxiliary thinking tools in `psychological_inertia_tools.md`. They generate reframings and mechanism hypotheses; they do not substitute for engineering evidence.

## 4. Software/data provenance

### Antropocosmist/triz-engineering-solver

Repository:

https://github.com/Antropocosmist/triz-engineering-solver

License: MIT (see `../VENDORED_LICENSE.md`).

OpenDeepMind used this repository as an implementation reference for:

- explicit opt-in engineering scope;
- 39 parameters;
- 40 principles;
- contradiction-matrix data structure/provenance;
- separation routes;
- Su-Field/76-SIS organization;
- ARIZ operationalization;
- evolution trends;
- worked-example structure.

OpenDeepMind did **not** simply nest that repository. It adds a separate modern problem-identification layer, explicit First Philosophy/First Principles handoff, evidence/uncertainty discipline, concept substantiation, progressive loading, validation scripts, and stricter provenance labels.

### Contradiction matrix transcription chain

The reference repository documents that its matrix data were imported from the MIT-licensed `kamil-szczepanik/TRIZ-Agents` repository and a Casey Perno transcription lineage of Altshuller's matrix. OpenDeepMind preserves that provenance in the matrix metadata.

When a project requires publication-grade historical matrix fidelity, independently compare anchor cells with a primary/reference edition before citing individual cell ordering as canonical.

## 5. Academic and modern AI-assisted implementations

Recent work is useful for evaluating how TRIZ can be operationalized with AI, while not replacing primary TRIZ theory. Examples include:

- Jiang & Luo, **AutoTRIZ: Artificial Ideation with TRIZ and Large Language Models** (2024), arXiv:2403.13002 — LLM-assisted contradiction detection and TRIZ report generation.
- Szczepanik et al., **TRIZ Agents: A Multi-Agent LLM Approach for TRIZ-Based Innovation** (2025), arXiv:2506.18783 — multi-agent TRIZ implementation and matrix-data lineage used by the referenced GitHub ecosystem.

Use these as implementation/evaluation references, not authorities for changing the historical TRIZ definitions.

## 6. Evidence policy inside OpenDeepMind

Every TRIZ output must distinguish:

```text
historical TRIZ theory
current MATRIZ operational convention
Altshuller Institute / other TRIZ-school convention
matrix-derived lookup
source-repository implementation detail
agent inference / psychological-inertia reframe
current engineering evidence
```

Do not convert one category into another.

## 7. Copyright and quotation policy

The OpenDeepMind files paraphrase and reorganize TRIZ concepts for executable use. They should not reproduce long copyrighted book passages. For exact excerpts, use lawful source access and respect quotation/copyright limits.

The MIT license notice for adapted software/reference material is preserved in `../VENDORED_LICENSE.md` and the root `NOTICE.md`.
