# TsaoSciComputation handoff protocol

A handoff is created **after** a first-principles strategy has defined the observable, governing physics, scales, candidate method hierarchy, assumptions, convergence, validation, falsification and uncertainty requirements.

A canonical v2 handoff records the scientific question, target property, execution profile, physical/computational scale, candidate methods, checksum-bound inputs, boundary and initial conditions, evaluation metrics, expected outputs, convergence checks, uncertainty analysis, physical validation, evidence level and human approval points. The handoff path is registered in `project.yaml` and `artifacts.jsonl`.

The receiving computation system returns method fingerprint, environment, inputs, execution state, raw outputs, parsed outputs, convergence evidence, physical validation, uncertainty and limitations. TsaoSciResearcher must keep these states distinct:

`strategy → prepared handoff → executed receipt → checked result → validated result → accepted/rejected conclusion`

A completed process is not automatically a scientifically valid answer.
