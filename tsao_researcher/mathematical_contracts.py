"""Versioned mathematical contracts used to explain the scientific control layer.

The equations in this module are documentation and decision-support contracts.
They make the repository's reasoning vocabulary machine-readable, but they do
not claim that a numerical solver, Bayesian inference engine, experiment, or
external simulation has been executed.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

Language = Literal["en", "zh-CN", "both"]

_SCHEMA_VERSION = "1.0"

_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "contract_id": "capability-ranking",
        "title": {
            "en": "Capability-ranking abstraction",
            "zh-CN": "能力排序抽象",
        },
        "equation": "S(c|q,o,e)=w_q R(q,c)+w_o R(o,c)+w_e M(e,c)-w_x C(c)",
        "symbols": {
            "c": {"en": "candidate capability", "zh-CN": "候选能力"},
            "q": {"en": "scientific question", "zh-CN": "科学问题"},
            "o": {"en": "decision-critical observable", "zh-CN": "决策关键观测量"},
            "e": {"en": "declared evidence context", "zh-CN": "已声明证据上下文"},
            "R": {"en": "relevance term", "zh-CN": "相关性项"},
            "M": {"en": "evidence-method compatibility", "zh-CN": "证据—方法相容性"},
            "C": {"en": "conflict or exclusion penalty", "zh-CN": "冲突或排除惩罚"},
        },
        "decision_use": {
            "en": "Explains why routing and capability retrieval combine relevance, observability, evidence fit, and negative semantics.",
            "zh-CN": "说明路由和能力检索为何同时考虑相关性、可观测性、证据匹配与负向语义。",
        },
        "implementation_relation": {
            "en": "Pedagogical abstraction of deterministic rules and bounded ranking; weights are not exposed as a fitted statistical model.",
            "zh-CN": "对确定性规则和有界排序的教学抽象; 这些权重不是已拟合统计模型的公开参数。",
        },
    },
    {
        "contract_id": "quantity-dimension",
        "title": {"en": "Quantity, unit, and dimension contract", "zh-CN": "数量、单位与量纲合同"},
        "equation": "x=(v,u,d),  d_left=d_right",
        "symbols": {
            "v": {"en": "numerical value", "zh-CN": "数值"},
            "u": {"en": "unit", "zh-CN": "单位"},
            "d": {"en": "physical dimension", "zh-CN": "物理量纲"},
        },
        "decision_use": {
            "en": "Prevents comparisons between missing-unit quantities or incompatible physical dimensions.",
            "zh-CN": "防止对缺失单位或物理量纲不相容的数量进行比较。",
        },
        "implementation_relation": {
            "en": "The runtime parses declared quantities and applies conservative structural guards; it is not a general symbolic-units algebra system.",
            "zh-CN": "运行时解析已声明数量并执行保守结构化防线; 它不是通用符号单位代数系统。",
        },
    },
    {
        "contract_id": "applicability-extrapolation",
        "title": {"en": "Applicability and extrapolation risk", "zh-CN": "适用域与外推风险"},
        "equation": "r_extra=d(x,A)/max(s_A,epsilon)",
        "symbols": {
            "x": {"en": "target condition", "zh-CN": "目标条件"},
            "A": {"en": "declared applicability domain", "zh-CN": "声明适用域"},
            "s_A": {"en": "characteristic domain scale", "zh-CN": "适用域特征尺度"},
            "epsilon": {"en": "positive numerical guard", "zh-CN": "正数值保护项"},
        },
        "decision_use": {
            "en": "Shows why transfer beyond a calibrated domain requires evidence, uncertainty inflation, and human review.",
            "zh-CN": "说明为何超出标定域的迁移必须具有证据、不确定性膨胀与人工复核。",
        },
        "implementation_relation": {
            "en": "The equation is a conceptual normalized-distance model; the current runtime uses explicit lexical and structural extrapolation markers.",
            "zh-CN": "该方程是概念性归一距离模型; 当前运行时使用显式词汇与结构化外推标记。",
        },
    },
    {
        "contract_id": "evidence-conflict",
        "title": {"en": "Evidence triad and conflict ledger", "zh-CN": "证据三分与冲突账本"},
        "equation": "E=(E_plus,E_minus,E_zero),  kappa=1[E_plus!=empty and E_minus!=empty]",
        "symbols": {
            "E_plus": {"en": "supporting evidence", "zh-CN": "支持证据"},
            "E_minus": {"en": "challenging or refuting evidence", "zh-CN": "挑战或反驳证据"},
            "E_zero": {"en": "neutral or unresolved evidence", "zh-CN": "中性或未决证据"},
            "kappa": {"en": "conflict indicator", "zh-CN": "冲突指示量"},
        },
        "decision_use": {
            "en": "Preserves negative results and contradictory observations instead of silently pooling them into a positive conclusion.",
            "zh-CN": "保留负结果和矛盾观测, 避免将其静默合并成正向结论。",
        },
        "implementation_relation": {
            "en": "Maps directly to supporting, challenging, and neutral evidence identifiers in the strategy contract.",
            "zh-CN": "直接对应策略合同中的支持、挑战和中性证据标识。",
        },
    },
    {
        "contract_id": "mechanism-identifiability",
        "title": {"en": "Mechanism and parameter identifiability", "zh-CN": "机制与参数可辨识性"},
        "equation": "D_ij(O,C)>tau  or  rank(J_theta)=p",
        "symbols": {
            "D_ij": {"en": "distinguishability of mechanisms i and j", "zh-CN": "机制 i 与 j 的可区分度"},
            "O": {"en": "observable set", "zh-CN": "观测量集合"},
            "C": {"en": "conditions and constraints", "zh-CN": "条件与约束"},
            "J_theta": {"en": "parameter-sensitivity Jacobian", "zh-CN": "参数敏感性雅可比矩阵"},
            "p": {"en": "number of parameters under consideration", "zh-CN": "待辨识参数数量"},
        },
        "decision_use": {
            "en": "Requires discriminating observables before selecting one mechanism or unique parameter set.",
            "zh-CN": "在选择单一机制或唯一参数组之前, 要求具备区分性观测量。",
        },
        "implementation_relation": {
            "en": "The runtime currently applies conservative warnings for competing mechanisms, equifinality, and missing discriminating observables; it does not compute a numerical Jacobian.",
            "zh-CN": "当前运行时对竞争机制、等效多解和缺失区分性观测量执行保守警告; 并不计算数值雅可比矩阵。",
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
        "contract_id": "multiscale-bridge",
        "title": {"en": "Multiscale bridge error budget", "zh-CN": "多尺度桥接误差预算"},
        "equation": "U_bridge^2=U_source^2+U_mapping^2+U_closure^2+U_target^2",
        "symbols": {
            "U_source": {"en": "source-scale uncertainty", "zh-CN": "来源尺度不确定性"},
            "U_mapping": {"en": "mapping or coarse-graining uncertainty", "zh-CN": "映射或粗粒化不确定性"},
            "U_closure": {"en": "closure-model uncertainty", "zh-CN": "闭合模型不确定性"},
            "U_target": {"en": "target-scale validation uncertainty", "zh-CN": "目标尺度验证不确定性"},
        },
        "decision_use": {
            "en": "Prevents an unvalidated micro-to-industrial jump by requiring measurable bridge variables and acceptance tests at each scale.",
            "zh-CN": "通过要求每个尺度具备可测桥接变量和验收测试, 防止未经验证的微观到工业尺度跳跃。",
        },
        "implementation_relation": {
            "en": "Represents the bridge-contract design principle; the repository records bridge requirements but does not execute homogenisation or process simulation.",
            "zh-CN": "表达尺度桥合同的设计原则; 仓库记录桥接要求, 但不执行均匀化或流程模拟。",
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


def _localized(value: Any, language: Language) -> Any:
    if isinstance(value, dict):
        if set(value) == {"en", "zh-CN"}:
            if language == "both":
                return deepcopy(value)
            return value[language]
        return {key: _localized(item, language) for key, item in value.items()}
    return deepcopy(value)


def list_mathematical_contracts(language: Language = "both") -> dict[str, Any]:
    """Return a deterministic, defensive copy of all mathematical contracts."""

    if language not in {"en", "zh-CN", "both"}:
        raise ValueError("language must be one of: en, zh-CN, both")
    return {
        "schema_version": _SCHEMA_VERSION,
        "language": language,
        "advisory_only": True,
        "solver_executed": False,
        "automatic_approval": False,
        "contracts": [_localized(contract, language) for contract in _CONTRACTS],
    }


def get_mathematical_contract(contract_id: str, language: Language = "both") -> dict[str, Any]:
    """Return one contract by stable identifier."""

    payload = list_mathematical_contracts(language)
    for contract in payload["contracts"]:
        if contract["contract_id"] == contract_id:
            payload["contracts"] = [contract]
            return payload
    available = ", ".join(contract["contract_id"] for contract in _CONTRACTS)
    raise KeyError(f"unknown mathematical contract: {contract_id}; available: {available}")
