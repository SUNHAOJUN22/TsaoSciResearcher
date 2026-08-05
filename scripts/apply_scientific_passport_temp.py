#!/usr/bin/env python3
"""Apply the one-time Scientific Passport and integrity-gate upgrade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one anchor in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + block.rstrip() + "\n", encoding="utf-8", newline="\n")


STRATEGY = ROOT / "tsao_researcher/strategy.py"

constants_anchor = '_EQUILIBRIUM_MARKERS = ("equilibrium", "phase equilibrium", "平衡", "相平衡")\n'
constants_block = constants_anchor + r'''

_EVIDENCE_LEVELS: tuple[tuple[int, str, tuple[str, ...]], ...] = (
    (1, "E1-theoretical", ("theory", "theoretical", "literature", "review", "analytical", "equation", "理论", "文献", "综述", "解析", "方程")),
    (2, "E2-computational", ("simulation", "simulated", "calculation", "computed", "dft", "molecular dynamics", " md ", "fem", "cfd", "monte carlo", "仿真", "模拟", "计算")),
    (3, "E3-experimental", ("experiment", "experimental", "measurement", "measurements", "measured", "observed", "spectroscopy", "xps", "tsdc", "pea", "weibull", "实验", "测量", "实测", "观测", "表征", "光谱")),
    (4, "E4-industrial", ("industrial", "pilot plant", "plant validation", "field validation", "production validation", "manufacturing validation", "工业", "中试", "工厂验证", "现场验证", "生产验证", "制造验证")),
)
_CAUSAL_MARKERS = ("cause", "causes", "caused by", "causal", "control", "controls", "controlled by", "determine", "determines", "drive", "drives", "lead to", "leads to", "mechanism", "because", "导致", "因果", "控制", "决定", "驱动", "机制", "由于")
_SCALE_TARGET_MARKERS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (4, ("industrial", "plant", "production", "manufacturing", "product quality", "grade performance", "reactor", "digital twin", "工业", "工厂", "生产", "制造", "产品质量", "牌号性能", "反应器", "数字孪生")),
    (3, ("device", "component", "continuum", "pressure drop", "temperature field", "stress field", "breakdown strength", "器件", "部件", "连续介质", "压降", "温度场", "应力场", "击穿强度")),
    (2, ("morphology", "domain size", "lamella", "mesoscale", "microstructure", "形貌", "相区", "片晶", "介观", "微结构")),
    (1, ("molecule", "chain conformation", "free energy", "reaction pathway", "分子", "链构象", "自由能", "反应路径")),
)
_REGIME_SCALE_TIER = {
    "electronic-structure": 0,
    "reaction-kinetics": 1,
    "molecular-thermodynamics": 1,
    "soft-matter-polymer": 2,
    "charge-transport-dielectric": 2,
    "continuum-transport": 3,
    "solid-mechanics": 3,
    "process-kinetics-population": 4,
    "multiscale-general": 4,
}
'''
replace_once(STRATEGY, constants_anchor, constants_block)

helpers_anchor = '''def _method_record(template: MethodTemplate, rank: int) -> dict[str, Any]:\n'''
helpers_block = r'''
def _marker_hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(marker for marker in markers if marker in text))


def _evidence_maturity(evidence: list[str]) -> dict[str, Any]:
    text = f" {_normalize(' '.join(evidence))} "
    rank = 0
    level = "E0-hypothesis-only"
    detected: list[str] = []
    for candidate_rank, candidate_level, markers in _EVIDENCE_LEVELS:
        if _marker_hits(text, markers):
            detected.append(candidate_level)
            if candidate_rank > rank:
                rank = candidate_rank
                level = candidate_level
    if not detected:
        detected = ["E0-hypothesis-only"]
    next_evidence = {
        0: ["document the governing hypothesis and at least one plausible competing mechanism", "collect a literature, analytical, computational, or experimental baseline"],
        1: ["test the hypothesis with a reproducible computation or experiment", "define an independent observable that could refute the proposed mechanism"],
        2: ["obtain independent experimental measurements under declared conditions", "validate model transfer across at least one hold-out condition"],
        3: ["demonstrate transferability across samples, operators, or operating conditions", "seek pilot, field, or manufacturing validation when the decision is industrial"],
        4: ["monitor drift, domain shift, and failure cases in the operating environment", "retain independent audit and change-control evidence"],
    }
    return {
        "classification_basis": "lexical classification of user-declared evidence; this is not independent validation",
        "declared_only": True,
        "maturity_rank": rank,
        "maturity_level": level,
        "levels_detected": detected,
        "evidence_items": evidence,
        "minimum_next_evidence": next_evidence[rank],
    }


def _causal_claim_gate(text: str, evidence_rank: int) -> dict[str, Any]:
    triggers = _marker_hits(text, _CAUSAL_MARKERS)
    if not triggers:
        status = "not-triggered"
    elif evidence_rank >= 3:
        status = "guarded"
    else:
        status = "review-required"
    return {
        "status": status,
        "triggers": triggers,
        "rule": "Causal language requires temporal or intervention logic, competing-mechanism tests, and evidence beyond correlation.",
        "required_checks": [
            "state the causal intervention, counterfactual, or temporal ordering",
            "compare at least one plausible competing mechanism",
            "separate correlation, prediction, mechanism consistency, and causal identification",
        ],
    }


def _scale_jump_gate(primary: Regime, secondary: list[tuple[Regime, int]], text: str, bridge_variables: list[str]) -> dict[str, Any]:
    source_tier = _REGIME_SCALE_TIER.get(primary.slug, 0)
    target_tier = source_tier
    target_markers: list[str] = []
    for tier, markers in _SCALE_TARGET_MARKERS:
        hits = _marker_hits(text, markers)
        if hits:
            target_tier = max(target_tier, tier)
            target_markers.extend(hits)
    target_markers = list(dict.fromkeys(target_markers))
    tier_gap = max(0, target_tier - source_tier)
    has_explicit_bridge = bool(secondary and bridge_variables)
    if tier_gap >= 2 and not has_explicit_bridge:
        status = "blocked"
    elif tier_gap >= 2:
        status = "review-required"
    else:
        status = "pass"
    missing = [
        "identify measurable bridge variables for every skipped scale",
        "validate each submodel at its native scale before parameter transfer",
        "propagate bridge uncertainty to the final decision observable",
    ] if tier_gap >= 2 else []
    return {
        "status": status,
        "source_regime": primary.slug,
        "source_tier": source_tier,
        "target_tier": target_tier,
        "tier_gap": tier_gap,
        "target_markers": target_markers,
        "bridge_variables": bridge_variables,
        "missing_bridge_requirements": missing,
    }


def _method_record(template: MethodTemplate, rank: int) -> dict[str, Any]:
'''
replace_once(STRATEGY, helpers_anchor, helpers_block)
replace_once(STRATEGY, '        "schema_version": "1.0",\n', '        "schema_version": "1.1",\n')

return_anchor = '''    return {\n        "schema_version": "1.1",\n        "strategy_id": f"FPS-{digest}",\n'''
return_prelude = '''    strategy_id = f"FPS-{digest}"\n    evidence_contract = _evidence_maturity(clean_evidence)\n    integrity_gates = {\n        "causal_claim": _causal_claim_gate(combined, evidence_contract["maturity_rank"]),\n        "scale_jump": _scale_jump_gate(primary, secondary, combined, bridge_variables),\n        "mechanism_competition": {\n            "status": "required",\n            "rule": "A preferred mechanism must be tested against at least one plausible alternative.",\n            "minimum_alternatives": 1,\n        },\n    }\n    scientific_passport = {\n        "passport_version": "1.0",\n        "strategy_id": strategy_id,\n        "model_contract": {\n            "state_variables": list(primary.state_variables),\n            "governing_principles": list(primary.governing_principles),\n            "assumptions": list(dict.fromkeys([*primary.reduction_assumptions, *primary.methods[0].assumptions])),\n            "applicability_domain": clean_conditions or ["not specified; clarification and qualified review required"],\n            "failure_conditions": list(dict.fromkeys([item for method in ladder[:2] for item in method["falsification"][:2]])),\n        },\n        "bridge_contract": {\n            "required": bool(secondary) or intrinsically_multiscale,\n            "source_regimes": selected_slugs,\n            "bridge_variables": bridge_variables,\n            "acceptance_tests": [\n                "bridge variables are measurable or independently inferable",\n                "each scale-specific model is validated before coupling",\n                "uncertainty is propagated across every scale bridge",\n            ],\n        },\n        "evidence_contract": evidence_contract,\n        "uncertainty_contract": {\n            "categories": ["parameter", "numerical", "sampling", "boundary-condition", "measurement", "model-form", "scale-transfer"],\n            "propagation_target": clean_observables or ["declared decision observable"],\n            "acceptance_rule": "Report uncertainty against the decision threshold and declare extrapolation outside the calibration and validation domain.",\n        },\n    }\n\n    return {\n        "schema_version": "1.1",\n        "strategy_id": strategy_id,\n'''
replace_once(STRATEGY, return_anchor, return_prelude)

cross_scale_anchor = '''        "cross_scale_plan": {\n            "required": bool(secondary) or intrinsically_multiscale,\n            "secondary_regimes": [regime.slug for regime, _ in secondary],\n            "bridge_variables": bridge_variables,\n            "coupling_rule": "Prefer sequential, uncertainty-aware coupling; use concurrent coupling only when scale separation fails and validation data exist.",\n        },\n        "validation_plan": list(\n'''
cross_scale_new = '''        "cross_scale_plan": {\n            "required": bool(secondary) or intrinsically_multiscale,\n            "secondary_regimes": [regime.slug for regime, _ in secondary],\n            "bridge_variables": bridge_variables,\n            "coupling_rule": "Prefer sequential, uncertainty-aware coupling; use concurrent coupling only when scale separation fails and validation data exist.",\n        },\n        "scientific_passport": scientific_passport,\n        "integrity_gates": integrity_gates,\n        "validation_plan": list(\n'''
replace_once(STRATEGY, cross_scale_anchor, cross_scale_new)

schema_path = ROOT / "schemas/v2/computation-strategy.schema.json"
schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
schema["title"] = "First-Principles Computation and Simulation Strategy with Scientific Passport"
schema["required"] = list(dict.fromkeys([*schema["required"], "scientific_passport", "integrity_gates"]))
schema["properties"]["schema_version"] = {"const": "1.1"}
non_empty = {"$ref": "#/$defs/nonEmptyString"}
unique = {"$ref": "#/$defs/uniqueStrings"}
non_empty_unique = {"$ref": "#/$defs/nonEmptyUniqueStrings"}
schema["properties"]["scientific_passport"] = {
    "type": "object", "additionalProperties": False,
    "required": ["passport_version", "strategy_id", "model_contract", "bridge_contract", "evidence_contract", "uncertainty_contract"],
    "properties": {
        "passport_version": {"const": "1.0"},
        "strategy_id": {"type": "string", "pattern": "^FPS-[0-9a-f]{16}$"},
        "model_contract": {"type": "object", "additionalProperties": False, "required": ["state_variables", "governing_principles", "assumptions", "applicability_domain", "failure_conditions"], "properties": {"state_variables": non_empty_unique, "governing_principles": non_empty_unique, "assumptions": non_empty_unique, "applicability_domain": non_empty_unique, "failure_conditions": non_empty_unique}},
        "bridge_contract": {"type": "object", "additionalProperties": False, "required": ["required", "source_regimes", "bridge_variables", "acceptance_tests"], "properties": {"required": {"type": "boolean"}, "source_regimes": non_empty_unique, "bridge_variables": unique, "acceptance_tests": non_empty_unique}},
        "evidence_contract": {"type": "object", "additionalProperties": False, "required": ["classification_basis", "declared_only", "maturity_rank", "maturity_level", "levels_detected", "evidence_items", "minimum_next_evidence"], "properties": {"classification_basis": non_empty, "declared_only": {"const": True}, "maturity_rank": {"type": "integer", "minimum": 0, "maximum": 4}, "maturity_level": {"enum": ["E0-hypothesis-only", "E1-theoretical", "E2-computational", "E3-experimental", "E4-industrial"]}, "levels_detected": non_empty_unique, "evidence_items": unique, "minimum_next_evidence": non_empty_unique}},
        "uncertainty_contract": {"type": "object", "additionalProperties": False, "required": ["categories", "propagation_target", "acceptance_rule"], "properties": {"categories": non_empty_unique, "propagation_target": non_empty_unique, "acceptance_rule": non_empty}},
    },
}
schema["properties"]["integrity_gates"] = {
    "type": "object", "additionalProperties": False,
    "required": ["causal_claim", "scale_jump", "mechanism_competition"],
    "properties": {
        "causal_claim": {"type": "object", "additionalProperties": False, "required": ["status", "triggers", "rule", "required_checks"], "properties": {"status": {"enum": ["not-triggered", "review-required", "guarded"]}, "triggers": unique, "rule": non_empty, "required_checks": non_empty_unique}},
        "scale_jump": {"type": "object", "additionalProperties": False, "required": ["status", "source_regime", "source_tier", "target_tier", "tier_gap", "target_markers", "bridge_variables", "missing_bridge_requirements"], "properties": {"status": {"enum": ["pass", "review-required", "blocked"]}, "source_regime": non_empty, "source_tier": {"type": "integer", "minimum": 0, "maximum": 4}, "target_tier": {"type": "integer", "minimum": 0, "maximum": 4}, "tier_gap": {"type": "integer", "minimum": 0, "maximum": 4}, "target_markers": unique, "bridge_variables": unique, "missing_bridge_requirements": unique}},
        "mechanism_competition": {"type": "object", "additionalProperties": False, "required": ["status", "rule", "minimum_alternatives"], "properties": {"status": {"const": "required"}, "rule": non_empty, "minimum_alternatives": {"type": "integer", "minimum": 1}}},
    },
}
schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

(ROOT / "tests/test_strategy_passport.py").write_text(r'''from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tsao_researcher.strategy import advise_computation_strategy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/v2/computation-strategy.schema.json").read_text(encoding="utf-8"))


def test_scientific_passport_is_schema_valid_and_bound_to_strategy() -> None:
    result = advise_computation_strategy("How do measured trap states control conductivity?", ["conductivity", "trap occupancy"], ["30 C", "20 kV/mm"], available_evidence=["independent TSDC experiment measurements"])
    jsonschema.Draft202012Validator(SCHEMA).validate(result)
    passport = result["scientific_passport"]
    assert result["schema_version"] == "1.1"
    assert passport["strategy_id"] == result["strategy_id"]
    assert passport["evidence_contract"]["maturity_level"] == "E3-experimental"
    assert passport["evidence_contract"]["declared_only"] is True
    assert result["integrity_gates"]["causal_claim"]["status"] == "guarded"


def test_causal_and_scale_jump_guards_block_unsupported_shortcut() -> None:
    result = advise_computation_strategy("How does an electronic defect state cause plant product quality?", ["plant product quality"], available_evidence=["literature review"])
    assert result["classification"]["primary_regime"] == "electronic-structure"
    assert result["integrity_gates"]["causal_claim"]["status"] == "review-required"
    gate = result["integrity_gates"]["scale_jump"]
    assert gate["status"] == "blocked"
    assert gate["tier_gap"] >= 2
    assert gate["missing_bridge_requirements"]


def test_evidence_maturity_distinguishes_hypothesis_computation_and_industry() -> None:
    hypothesis = advise_computation_strategy("Estimate a defect state.", ["defect state"])
    computational = advise_computation_strategy("Estimate a defect state.", ["defect state"], available_evidence=["converged DFT simulation calculation"])
    industrial = advise_computation_strategy("Assess reactor product quality.", ["product quality"], available_evidence=["pilot plant industrial validation measurements"])
    assert hypothesis["scientific_passport"]["evidence_contract"]["maturity_rank"] == 0
    assert computational["scientific_passport"]["evidence_contract"]["maturity_rank"] == 2
    assert industrial["scientific_passport"]["evidence_contract"]["maturity_rank"] == 4


def test_schema_rejects_fabricated_evidence_maturity() -> None:
    result = advise_computation_strategy("Estimate a band gap.", ["band gap"])
    result["scientific_passport"]["evidence_contract"]["maturity_rank"] = 9
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(result)
''', encoding="utf-8", newline="\n")

replace_once(ROOT / ".github/workflows/ci.yml", "tests/test_first_principles_strategy.py tests/test_first_principles_strategy_boundaries.py tests/test_v071_hardening.py", "tests/test_first_principles_strategy.py tests/test_first_principles_strategy_boundaries.py tests/test_strategy_passport.py tests/test_v071_hardening.py")

english_section = r'''

### Scientific Passport and machine-readable integrity gates

Every generated strategy now carries a **Scientific Passport** bound to its deterministic `strategy_id`:

| Contract | Machine-readable content | Acceptance boundary |
|---|---|---|
| Model Contract | state variables, governing principles, assumptions, applicability domain and failure conditions | no model is valid outside its declared domain |
| Bridge Contract | source regimes, measurable bridge variables and cross-scale acceptance tests | direct micro-to-industry jumps are blocked or sent to review |
| Evidence Contract | declared evidence items and maturity `E0`–`E4` | the classification is explicitly declared-only, never independent validation |
| Uncertainty Contract | parameter, numerical, sampling, boundary, measurement, model-form and scale-transfer uncertainty | uncertainty must reach the decision observable and threshold |
| Integrity Gates | causal-language guard, scale-jump guard and competing-mechanism requirement | correlation or visual agreement cannot be promoted to causal proof |

```text
E0 hypothesis only → E1 theoretical/literature → E2 computation
                   → E3 independent experiment → E4 pilot/industrial validation
```

A higher lexical maturity level does not certify evidence quality. It records what the caller declared and identifies the minimum next evidence needed for stronger acceptance.

<table>
<tr><td width="50%"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="Conceptual Scientific Passport evidence contract"/><br/><strong>Passport evidence contract</strong></td><td width="50%"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="Conceptual scale bridge contract"/><br/><strong>Scale-bridge contract</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="Conceptual causal and scale-jump guard"/><br/><strong>Causal and scale-jump guard</strong></td><td width="50%"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="Conceptual uncertainty contract"/><br/><strong>Uncertainty acceptance contract</strong></td></tr>
</table>
'''
chinese_section = r'''

### Scientific Passport 与机器可读科研诚信门

每个策略现在都携带一个与确定性 `strategy_id` 绑定的 **Scientific Passport（科学护照）**：

| 合同 | 机器可读内容 | 验收边界 |
|---|---|---|
| Model Contract | 状态变量、控制规律、假设、适用域与失效条件 | 模型不得越过已声明适用域使用 |
| Bridge Contract | 来源尺度、可测桥接变量与跨尺度验收测试 | 微观结果直接跳到工业结论时自动阻断或转人工复核 |
| Evidence Contract | 已声明证据及 `E0`–`E4` 成熟度 | 明确标记为“声明分类”，不冒充独立核验 |
| Uncertainty Contract | 参数、数值、采样、边界、测量、模型形式与尺度传递不确定性 | 不确定性必须传播到决策观测量和阈值 |
| Integrity Gates | 因果语言防线、尺度跳跃防线与竞争机制要求 | 相关性或视觉一致不能升级为因果证明 |

```text
E0 仅假设 → E1 理论/文献 → E2 计算
          → E3 独立实验 → E4 中试/工业验证
```

较高的词汇分级不等于证据质量认证。系统只记录调用者声明的证据类型，并给出进入更高验收等级所需的最低下一步证据。

<table>
<tr><td width="50%"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="Scientific Passport 证据合同概念图"/><br/><strong>科学护照证据合同</strong></td><td width="50%"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="尺度桥合同概念图"/><br/><strong>尺度桥合同</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="因果与尺度跳跃防线概念图"/><br/><strong>因果与尺度跳跃防线</strong></td><td width="50%"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定性合同概念图"/><br/><strong>不确定性验收合同</strong></td></tr>
</table>
'''

for name in ("README.md", "README_EN.md"):
    path = ROOT / name
    replace_once(path, "| Scientific reasoning | first-principles method ladders derived from observables, degrees of freedom, conservation laws, ensembles, scales, falsification and uncertainty |", "| Scientific reasoning | first-principles method ladders plus a Scientific Passport, evidence maturity, causal guard, scale-jump guard, falsification and uncertainty contracts |")
    marker = "The `strategy` result is always marked advisory and records that no solver has been executed.\n"
    replace_once(path, marker, marker + english_section)

for name in ("README.zh-CN.md", "README_CN.md"):
    path = ROOT / name
    replace_once(path, "| 科学推理 | 从观测量、自由度、守恒律、系综、尺度、证伪与不确定性推导第一性原理方法阶梯 |", "| 科学推理 | 第一性原理方法阶梯，以及 Scientific Passport、证据成熟度、因果防线、尺度跳跃防线、证伪与不确定性合同 |")
    marker = "`strategy` 输出始终标记为建议性结果，并明确记录求解器未执行。\n"
    replace_once(path, marker, marker + chinese_section)

append_once(ROOT / "docs/VALIDATION.md", "## Scientific Passport contract gates", '''## Scientific Passport contract gates

The computation-strategy schema requires a Scientific Passport and integrity gates. Regression verifies evidence maturity `E0`–`E4`, declared-only evidence semantics, deterministic passport binding, unsupported causal-language review, blocked unbridged scale jumps, competing-mechanism requirements, and rejection of fabricated maturity values.
''')
replace_once(ROOT / "CHANGELOG.md", "## Unreleased\n", "## Unreleased\n\n- Add deterministic Scientific Passport output with model, bridge, evidence, and uncertainty contracts.\n- Add evidence maturity E0-E4 plus causal-claim, scale-jump, and competing-mechanism integrity gates.\n- Add schema, cross-platform regression, README, and validation documentation for the new contracts.\n")

print("scientific passport upgrade applied")
