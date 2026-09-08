# Definition of done

- Strict quantities, convergence, execution, evidence and acceptance remain separate machine states.
- Timeout, cancellation and output overflow terminate the full process tree and retain bounded evidence.
- The ledger survives concurrent append tests without loss or silent reordering.
- Repository-native CI and real solver/HPC evidence are recorded separately; unresolved execution remains `EXTERNAL_EXECUTION_NOT_VERIFIED`.

## Evidence scopes

- **Bundle-level:** deterministic overlay, static Skill, contract, Unicode, visual and archive checks.
- **Repository-native:** the repository's own lock, lint, type, unit, integration, package and platform gates on an exact checkout.
- **External:** licensed software, solver/HPC, laboratory, engineering/HSE, regulatory or qualified-human evidence when required.

A lower evidence scope must never claim a higher one.
