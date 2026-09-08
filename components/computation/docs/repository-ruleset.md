# Repository Ruleset desired state

This document records the desired GitHub platform policy. Repository files and tests do not prove that a platform setting is enabled; maintainers must verify the Settings UI or repository API.

The `main` Ruleset should:

- prevent force pushes;
- prevent deletion of `main`;
- require the production CI and CodeQL checks;
- restrict changes to workflow, release, security, contract, Schema, state, and validation paths to reviewed maintainers;
- prevent deletion or movement of published `vX.Y.Z` tags;
- avoid routine administrator bypass;
- retain `main` as the only upstream branch.

Private Vulnerability Reporting should be enabled independently. Until the platform confirms both controls, reports must list them as administrator actions and must not claim they are active.

External contributors use branches in their own forks. The upstream repository remains single-`main`.
