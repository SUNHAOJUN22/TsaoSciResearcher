"""Versioned mathematical contracts used to explain the scientific control layer.

The equations in this module are documentation and decision-support contracts.
They make the repository's reasoning vocabulary machine-readable, but they do
not claim that a numerical solver, Bayesian inference engine, experiment, or
external simulation has been executed.
"""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal

import jsonschema

Language = Literal["en", "zh-CN", "both"]

_SCHEMA_VERSION = "1.0"
_SCHEMA_ID = (
    "https://sunhaojun22.github.io/TsaoSciResearcher/schemas/v2/mathematical-contract-registry.schema.json"
)
_SCHEMA_RESOURCE = ("data", "schemas", "mathematical-contract-registry.schema.json")

_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "contract_id": "capability-ranking",
        "title": {"en": "Capability-ranking abstraction", "zh-CN": "能力排序抽象"},
        "equation": "S(c|q,o,e)=w_q R(q,c)+w_o R(o,c)+w_e M(e,c)-w_x C(c)",
        "symbols": {
            "c": {"en": "candidate capability", "zh-CN": "候选能力"},
            "q": {"en": "scientific question", "zh-CN": "科学问题"},
            "o": {"en": "decision-critical observable", "zh-CN": "决策关键观测量"},
            "e": {"en": "declared evidence context", "zh-CN": "声明的证据上下文"},
            "R": {"en": "relevance term", "zh-CN": "相关性项"},
            "M": {"en": "evidence-match term", "zh-CN": "证据匹配项"},
            "C": {"en": "conflict or exclusion penalty", "zh-CN": "冲突或排除惩罚"},
        },
        "decision_use": {
            "en": "Explains deterministic bounded capability ranking without pretending the weights were statistically fitted.",
            "zh-CN": "解释确定性有界能力排序, 不声称权重来自统计拟合。",
        },
        "implementation_relation": {
            "en": "The runtime performs lexical and contract-aware ranking; this equation is the stable explanatory abstraction.",
            "zh-CN": "运行时执行词法与合同感知排序; 该方程是稳定的解释性抽象。",
        },
    },
    {
        "contract_id": "quantity-dimension",
        "title": {"en": "Quantity, unit, and dimension contract", "zh-CN": "数值、单位与量纲合同"},
        "equation": "x=(v,u,d), d_left=d_right",
        "symbols": {
            "x": {"en": "declared physical quantity", "zh-CN": "声明的物理量"},
            "v": {"en": "numeric value", "zh-CN": "数值"},
            "u": {"en": "unit", "zh-CN": "单位"},
            "d": {"en": "physical dimension", "zh-CN": "物理量纲"},
        },
        "decision_use": {
            "en": "Blocks quantitative comparison when units are absent or physical dimensions are incompatible.",
            "zh-CN": "当单位缺失或量纲不兼容时阻止定量比较。",
        },
        "implementation_relation": {
            "en": "Backs the strategy adviser's quantity extraction, missing-unit warnings, and dimension-conflict gates.",
            "zh-CN": "对应策略模块的物理量提取、单位缺失警告与量纲冲突门。",
        },
    },
    {
        "contract_id": "applicability-risk",
        "title": {"en": "Applicability and extrapolation risk", "zh-CN": "适用域与外推风险"},
        "equation": "r_extra=d(x,A)/max(s_A,epsilon)",
        "symbols": {
            "r_extra": {"en": "normalized extrapolation risk", "zh-CN": "归一化外推风险"},
            "x": {"en": "target condition", "zh-CN": "目标条件"},
            "A": {"en": "declared applicability domain", "zh-CN": "声明的适用域"},
            "s_A": {"en": "characteristic domain scale", "zh-CN": "适用域特征尺度"},
            "epsilon": {"en": "positive numerical guard", "zh-CN": "正数值保护项"},
        },
        "decision_use": {
            "en": "Requires review when the target condition lies outside a declared or validated domain.",
            "zh-CN": "当目标条件位于声明或验证域外时要求复核。",
        },
        "implementation_relation": {
            "en": "The current runtime uses conservative lexical and structural extrapolation markers rather than fabricating a distance from absent calibration data.",
            "zh-CN": "当前运行时采用保守的词法与结构外推标记, 不会在缺失标定数据时伪造距离。",
        },
    },
    {
        "contract_id": "evidence-triad",
        "title": {"en": "Evidence triad and conflict ledger", "zh-CN": "证据三分法与冲突台账"},
        "equation": "E=(E_plus,E_minus,E_zero), kappa=1[E_plus!=empty and E_minus!=empty]",
        "symbols": {
            "E_plus": {"en": "supporting evidence", "zh-CN": "支持性证据"},
            "E_minus": {"en": "challenging or refuting evidence", "zh-CN": "挑战或反驳性证据"},
            "E_zero": {"en": "neutral or unresolved evidence", "zh-CN": "中性或未决证据"},
            "kappa": {"en": "conflict indicator", "zh-CN": "冲突指示量"},
        },
        "decision_use": {
            "en": "Prevents contradictory evidence from being silently averaged into a positive claim.",
            "zh-CN": "防止相互矛盾的证据被静默平均为正面结论。",
        },
        "implementation_relation": {
            "en": "Matches the Scientific Passport evidence ledger and conflict gate.",
            "zh-CN": "对应 Scientific Passport 的证据台账与冲突门。",
        },
    },
    {
        "contract_id": "identifiability",
        "title": {"en": "Mechanism and parameter identifiability", "zh-CN": "机理与参数可辨识性"},
        "equation": "D_ij(O,C)>tau or rank(J_theta)=p",
        "symbols": {
            "D_ij": {"en": "discrimination between mechanisms i and j", "zh-CN": "机理 i 与 j 的可区分度"},
            "O": {"en": "discriminating observables", "zh-CN": "判别观测量"},
            "C": {"en": "experimental or computational conditions", "zh-CN": "实验或计算条件"},
            "tau": {"en": "decision threshold", "zh-CN": "决策阈值"},
            "J_theta": {"en": "parameter-sensitivity Jacobian", "zh-CN": "参数敏感性雅可比矩阵"},
            "p": {"en": "number of free parameters", "zh-CN": "自由参数个数"},
        },
        "decision_use": {
            "en": "Requires discriminating observables for unique mechanism or parameter claims.",
            "zh-CN": "唯一机理或参数结论必须具有可判别观测量。",
        },
        "implementation_relation": {
            "en": "The runtime records competing mechanisms and conservative identifiability warnings; numerical Jacobian construction remains external.",
            "zh-CN": "运行时记录竞争机理与保守可辨识性警告; 数值雅可比矩阵仍由外部分析构建。",
        },
    },
    {
        "contract_id": "uncertainty-budget",
        "title": {"en": "Decision-observable uncertainty budget", "zh-CN": "决策观测量不确定性预算"},
        "equation": "Sigma_y≈J Sigma_theta J^T+Sigma_num+Sigma_sample+Sigma_model+Sigma_transfer",
        "symbols": {
            "Sigma_y": {"en": "uncertainty of the decision observable", "zh-CN": "决策观测量不确定性"},
            "J": {"en": "local sensitivity map", "zh-CN": "局部敏感性映射"},
            "Sigma_theta": {"en": "parameter uncertainty", "zh-CN": "参数不确定性"},
            "Sigma_num": {"en": "numerical uncertainty", "zh-CN": "数值不确定性"},
            "Sigma_sample": {"en": "sampling uncertainty", "zh-CN": "采样不确定性"},
            "Sigma_model": {"en": "model-form uncertainty", "zh-CN": "模型形式不确定性"},
            "Sigma_transfer": {"en": "scale-transfer uncertainty", "zh-CN": "尺度传递不确定性"},
        },
        "decision_use": {
            "en": "Forces uncertainty sources to propagate to the quantity used for acceptance or rejection.",
            "zh-CN": "要求各类不确定性传播到真正用于接受或拒绝决策的量。",
        },
        "implementation_relation": {
            "en": "Defines the required uncertainty categories and propagation intent; numerical covariance propagation remains an external analysis task.",
            "zh-CN": "定义必需的不确定性类别与传播意图; 数值协方差传播仍属于外部分析任务。",
        },
    },
    {
        "contract_id": "scale-bridge",
        "title": {"en": "Multiscale bridge error budget", "zh-CN": "多尺度桥接误差预算"},
        "equation": "U_bridge^2=U_source^2+U_mapping^2+U_closure^2+U_target^2",
        "symbols": {
            "U_bridge": {"en": "total bridge uncertainty", "zh-CN": "总桥接不确定性"},
            "U_source": {"en": "source-scale uncertainty", "zh-CN": "源尺度不确定性"},
            "U_mapping": {"en": "mapping uncertainty", "zh-CN": "映射不确定性"},
            "U_closure": {"en": "closure-model uncertainty", "zh-CN": "闭合模型不确定性"},
            "U_target": {"en": "target-scale validation uncertainty", "zh-CN": "目标尺度验证不确定性"},
        },
        "decision_use": {
            "en": "Blocks a direct microscopic-to-industrial conclusion unless bridge variables and target-scale validation are declared.",
            "zh-CN": "若未声明桥接变量与目标尺度验证, 则阻止从微观结果直接跳到工业结论。",
        },
        "implementation_relation": {
            "en": "Backs the strategy adviser's bridge contracts and direct-scale-jump warnings.",
            "zh-CN": "对应策略模块的桥接合同与直接跨尺度警告。",
        },
    },
    {
        "contract_id": "decision-readiness",
        "title": {"en": "Conservative decision-readiness aggregation", "zh-CN": "保守决策就绪度聚合"},
        "equation": "G=min(g_quantity,g_applicability,g_evidence,g_identifiability,g_bridge)",
        "symbols": {
            "G": {"en": "overall readiness gate", "zh-CN": "总体就绪度门"},
            "g_quantity": {"en": "quantity and dimension gate", "zh-CN": "数量与量纲门"},
            "g_applicability": {"en": "applicability gate", "zh-CN": "适用域门"},
            "g_evidence": {"en": "evidence-conflict gate", "zh-CN": "证据冲突门"},
            "g_identifiability": {"en": "identifiability gate", "zh-CN": "可辨识性门"},
            "g_bridge": {"en": "scale-bridge gate", "zh-CN": "尺度桥门"},
        },
        "decision_use": {
            "en": "The weakest mandatory contract controls readiness: BLOCK precedes REVIEW, and REVIEW precedes PASS.",
            "zh-CN": "最弱的强制合同决定整体就绪度: 阻断优先于复核, 复核优先于通过。",
        },
        "implementation_relation": {
            "en": "Matches the repository's conservative blocker/review aggregation and fixed automatic_approval=false boundary.",
            "zh-CN": "对应仓库的保守阻断/复核聚合逻辑, 以及 automatic_approval=false 的固定边界。",
        },
    },
)


@lru_cache(maxsize=1)
def _load_mathematical_contract_schema() -> dict[str, Any]:
    resource = files("tsao_researcher")
    for part in _SCHEMA_RESOURCE:
        resource = resource.joinpath(part)
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("mathematical contract schema root must be an object")
    jsonschema.Draft202012Validator.check_schema(value)
    return value


def get_mathematical_contract_schema() -> dict[str, Any]:
    """Return a defensive copy of the packaged Draft 2020-12 schema."""

    return deepcopy(_load_mathematical_contract_schema())


def validate_mathematical_contract_payload(payload: dict[str, Any]) -> None:
    """Validate one mathematical-contract registry payload."""

    jsonschema.Draft202012Validator(_load_mathematical_contract_schema()).validate(payload)


def _localized(value: Any, language: Language) -> Any:
    if isinstance(value, dict):
        if set(value) == {"en", "zh-CN"}:
            if language == "both":
                return deepcopy(value)
            return value[language]
        return {key: _localized(item, language) for key, item in value.items()}
    return deepcopy(value)


def get_mathematical_contracts(language: Language = "both") -> dict[str, Any]:
    """Return the stable mathematical contract registry in one language."""

    if language not in {"en", "zh-CN", "both"}:
        raise ValueError("language must be en, zh-CN, or both")
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "schema_id": _SCHEMA_ID,
        "language": language,
        "advisory_only": True,
        "solver_executed": False,
        "automatic_approval": False,
        "contracts": [_localized(contract, language) for contract in _CONTRACTS],
    }
    validate_mathematical_contract_payload(payload)
    return payload


def get_mathematical_contract(contract_id: str, language: Language = "both") -> dict[str, Any]:
    """Return one named contract while preserving the registry envelope."""

    payload = get_mathematical_contracts(language)
    matches = [
        contract for contract in payload["contracts"] if contract["contract_id"] == contract_id
    ]
    if not matches:
        raise KeyError(contract_id)
    payload["contracts"] = matches
    validate_mathematical_contract_payload(payload)
    return payload


__all__ = [
    "Language",
    "get_mathematical_contract",
    "get_mathematical_contract_schema",
    "get_mathematical_contracts",
    "validate_mathematical_contract_payload",
]
