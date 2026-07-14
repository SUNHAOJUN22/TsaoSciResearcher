<div align="center"><img src="assets/logo.svg" alt="TsaoSciResearcher" width="920" />
<p><strong>Evidence-first research architecture for questions, literature, experiments, data, figures, writing and validation.</strong></p>
<p><a href="README.md">中文</a> · <a href="docs/ARCHITECTURE.md">Architecture</a> · <a href="capability-index/capabilities.md">158 capabilities</a></p></div>

## Overview

TsaoSciResearcher is a progressive-disclosure Agent Skill for full-lifecycle scientific research. It provides 15 workflows, 158 indexed capabilities, durable project state, evidence/claim/figure schemas, deterministic validators, bilingual documentation and cross-platform installation.

It does not claim to replace scientific experts or to execute unavailable tools. Real DFT, molecular dynamics, finite-element, CFD and process-simulation tasks are delegated through a structured TsaoSciComputation handoff.

## Objective capability boundary

| Layer | Status |
|---|---|
| Routing, indexes, state, schemas, validators, templates, installation | Native and executable in this repository |
| Literature retrieval, statistics, plotting, document generation | Orchestrated; depends on tools and data available to the active agent |
| Multiscale simulation | Delegated to TsaoSciComputation or real solvers |
| Medical, patent/FTO, safety and integrity decisions | Qualified human review required |

## Install and test

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -r requirements.txt
python scripts/run_tests.py
python scripts/install.py --agent codex --scope user --validate
```

## Core principle

`completed` is not `checked`; `checked` is not `validated`; `validated` is not automatically `accepted`.

See the Chinese README for the full workflow, capability and usage documentation.

## License

Original code and documentation are Apache-2.0. No upstream skill prompts or code are bundled. See `THIRD_PARTY.md`.
