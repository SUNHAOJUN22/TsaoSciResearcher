# TsaoSciComputation handoff protocol

A handoff must include scientific question, target physical quantity, required scale, candidate methods, available structures/data, boundary and initial conditions, parameter sources, required convergence checks, uncertainty analysis, expected artifacts, acceptance criteria and approval points.

The receiving computation system returns method fingerprint, environment, inputs, execution state, raw outputs, parsed outputs, convergence evidence, physical validation, uncertainty and limitations. TsaoSciResearcher accepts only artifacts that are explicitly marked validated or supplies a reasoned rejection.

A canonical v2 handoff records the scientific question, target property, execution profile, physical/computational scale, candidate methods, checksum-bound inputs, boundary and initial conditions, evaluation metrics, expected outputs, convergence checks, uncertainty analysis, physical validation, evidence level and human approval points. The handoff path is registered in `project.yaml` and `artifacts.jsonl`.
