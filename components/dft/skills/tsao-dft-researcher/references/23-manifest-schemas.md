# Manifest Schemas

Operational `.research/` files support resumable execution. The release-layer manifests below support deterministic evidence and figure audits.

## Research Manifest

```json
{
  "schema_version": "1.0",
  "project_id": "project-001",
  "research_question": "One falsifiable question",
  "model_scope": "Declared system, phase and method",
  "calculations": [
    {
      "id": "calc-001",
      "task_type": "minimum",
      "status": "accepted",
      "method": "wB97X-D",
      "basis": "def2-SVP",
      "phase_or_solvent": "SMD(n-heptane)",
      "temperature_K": 350.0,
      "standard_state": "1 M",
      "charge": 0,
      "multiplicity": 1,
      "structure_sha256": "64 lowercase hexadecimal characters",
      "artifact_ids": ["artifact-log-001"],
      "validation": {
        "normal_termination": true,
        "scf_converged": true,
        "optimization_converged": true,
        "imaginary_frequency_count": 0
      }
    }
  ],
  "artifacts": [
    {
      "id": "artifact-log-001",
      "calculation_id": "calc-001",
      "kind": "gaussian_log",
      "path": "calculations/calc-001.log",
      "sha256": "64 lowercase hexadecimal characters",
      "source_type": "calculation",
      "status": "accepted"
    }
  ],
  "claims": [
    {
      "id": "claim-001",
      "text": "Scoped scientific claim",
      "scope": "Defined model and method",
      "evidence_grade": "A",
      "artifact_ids": ["artifact-log-001"],
      "limitations": ["Static model"],
      "falsification_condition": "A reproducible counterexample or failed validation gate",
      "paper_ready": true,
      "is_mock": false
    }
  ]
}
```

Evidence grades are semantic gates:

- A: accepted calculation artifacts backed by accepted calculations;
- B: accepted experimental evidence with measurement provenance;
- C: literature or external evidence not reproduced in the current project;
- D: mock, hypothesis, estimate, failed, incomplete or unresolved evidence.

## Figure Manifest

```json
{
  "schema_version": "1.0",
  "project_id": "project-001",
  "figures": [
    {
      "id": "fig-001",
      "role": "main",
      "title": "Question-led title",
      "conclusion": "One scoped visual claim",
      "evidence_grade": "A",
      "outputs": ["figures/fig-001.svg", "figures/fig-001.png"],
      "panels": [
        {
          "id": "fig-001a",
          "type": "esp",
          "comparison_group": "candidate-series",
          "source_artifact_ids": ["artifact-esp-001"],
          "method": "wB97X-D",
          "basis": "def2-TZVP",
          "phase_or_solvent": "SMD(n-heptane)",
          "renderer": "VMD/Tachyon",
          "camera_id": "candidate-anchor-v1",
          "density_cube": "wavefunctions/a-density.cube",
          "esp_cube": "wavefunctions/a-esp.cube",
          "parameters": {
            "density_isovalue_au": 0.001,
            "esp_min": -35.0,
            "esp_max": 35.0,
            "unit": "kcal mol-1",
            "negative_color": "red",
            "positive_color": "blue",
            "palette": "BGR"
          }
        }
      ]
    }
  ]
}
```

Use stable IDs. A filename alone is not scientific identity. Run both validators and, for final delivery, enable cross-manifest and file checks.
