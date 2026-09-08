# Architecture

TsaoSciComputation uses eight responsibility layers:

1. **Skill and CLI entry** — capture intent without eagerly loading the full knowledge base.
2. **Contracts and state** — machine-readable calculation, result, and handoff contracts with guarded transitions.
3. **Registries and routing** — 164 differentiated capabilities, 27 solver adapters, 20 workflows, and unit records.
4. **Scientific workflows** — method assumptions, required evidence, failure modes, and acceptance gates by domain.
5. **Adapter boundary** — executable discovery, argv-only command planning, and conservative output parsing.
6. **Execution and security** — path confinement, atomic writes, bounded subprocesses, timeouts, and immutable records.
7. **Validation and uncertainty** — numerical convergence, conservation, units, UQ, applicability, and human approval.
8. **Provenance and release** — event ledgers, manifests, reproducible archives, isolated wheel installation, and CI.

Runtime code has no mandatory third-party dependency. Solver executables, commercial licenses, pseudopotentials, basis databases, and proprietary manuals are never bundled.
