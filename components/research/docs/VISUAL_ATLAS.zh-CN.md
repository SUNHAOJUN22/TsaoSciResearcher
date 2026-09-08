# 科研能力 AI 概念图谱

> 正式版本 0.7.4 · 38 张 AI 生成概念示意图

本图谱用于说明仓库架构、科研合同、验证边界与外部执行生命周期。每张 SVG 都是带有 `<title>` 和 `<desc>` 无障碍元数据的概念文档工件。它们均不是实验数据、测量结果、求解器输出，也不能证明外部计算已经执行。

## 科研控制与架构

| 图示 | 用途 |
|---|---|
| ![科研操作架构](assets/ai/research_os_architecture.svg) | 科研控制层总体架构 |
| ![多代理编排](assets/ai/multi_agent_orchestration.svg) | 有界编排与审批边界 |
| ![渐进式路由](assets/ai/progressive_routing_loading.svg) | 先路由、后加载能力 |
| ![项目状态机](assets/ai/project_state_machine.svg) | 保持真实的项目状态转移 |
| ![项目账本](assets/ai/project_ledgers_provenance.svg) | 哈希链接的状态、证据与来源账本 |
| ![科研生产流水线](assets/ai/research_production_pipeline.svg) | 端到端科研生产流程 |

## 能力、证据与需求

| 图示 | 用途 |
|---|---|
| ![能力图谱](assets/ai/capability_landscape.svg) | 能力目录结构 |
| ![实现级别](assets/ai/capability_implementation_levels.svg) | 合同实现边界 |
| ![需求覆盖](assets/ai/original_requirements_coverage.svg) | 原始需求追溯 |
| ![证据主张图](assets/ai/evidence_claim_graph.svg) | 证据到主张的链接 |
| ![证据引文闭环](assets/ai/evidence_citation_integrity_loop.svg) | 引文与证据完整性 |
| ![可复现质量门](assets/ai/reproducibility_quality_gates.svg) | 可复现验收门 |

## 第一性原理与多尺度策略

| 图示 | 用途 |
|---|---|
| ![策略阶梯](assets/ai/first_principles_strategy_ladder.svg) | 最低充分方法阶梯 |
| ![方法决策树](assets/ai/scientific_problem_method_decision_tree.svg) | 问题到方法还原 |
| ![多尺度流水线](assets/ai/multiscale_science_pipeline.svg) | 可测量尺度桥 |
| ![多尺度案例](assets/ai/polymer_multiscale_case_study.svg) | 概念性多尺度工作流示例 |
| ![数理合同目录](assets/ai/mathematical_contract_registry.svg) | 八个机器可读数理合同 |
| ![就绪度格](assets/ai/decision_readiness_lattice.svg) | 保守的阻断—复核—通过顺序 |
| ![不确定性预算](assets/ai/uncertainty_propagation_budget.svg) | 决策观测量不确定性传播 |
| ![尺度桥误差预算](assets/ai/multiscale_bridge_error_budget.svg) | 来源、映射、闭合与目标不确定性 |
| ![Schema 验证流水线](assets/ai/mathematical_contract_schema_pipeline.svg) | 规范 Schema、包内镜像、运行时校验与交付工件 |

## Scientific Passport 与科研诚信门

| 图示 | 用途 |
|---|---|
| ![科学护照矩阵](assets/ai/scientific_passport_matrix.svg) | 模型、证据、尺度桥与不确定性合同 |
| ![证据成熟度](assets/ai/evidence_maturity_ladder.svg) | 声明式 E0–E4 证据阶梯 |
| ![决策就绪度](assets/ai/decision_readiness_gate.svg) | 阻断项与复核项聚合 |
| ![主动证据闭环](assets/ai/active_evidence_learning_loop.svg) | 下一最佳证据规划 |
| ![数量合同](assets/ai/quantity_dimension_contract.svg) | 数量、单位与量纲检查 |
| ![适用域防线](assets/ai/applicability_extrapolation_guard.svg) | 适用域与外推检查 |
| ![证据冲突](assets/ai/evidence_conflict_resolution.svg) | 支持、挑战与未决证据 |
| ![可辨识性门](assets/ai/mechanism_identifiability_gate.svg) | 竞争机制与参数可辨识性 |
| ![不确定性验证](assets/ai/uncertainty_quantification_validation.svg) | 验证与不确定性闭环 |
| ![因果防线](assets/ai/scientific_integrity_causality_guard.svg) | 因果语言与科研诚信边界 |

## 外部执行、实验、写作与发布

| 图示 | 用途 |
|---|---|
| ![交接边界](assets/ai/computation_handoff_boundary.svg) | 校验和绑定的外部执行交接 |
| ![人工审批](assets/ai/human_approval_acceptance_boundary.svg) | 合格人工验收边界 |
| ![实验室质量](assets/ai/laboratory_data_quality.svg) | 实验室数据质量合同 |
| ![写作证据链](assets/ai/scientific_writing_evidence_chain.svg) | 科学写作证据追溯 |
| ![图件编辑防线](assets/ai/scientific_figure_edit_guard.svg) | 科研图件编辑边界 |
| ![兼容性矩阵](assets/ai/installation_compatibility_matrix.svg) | 跨平台安装与 CI 矩阵 |
| ![供应链证明](assets/ai/supply_chain_release_attestation.svg) | 确定性发布与供应链证据 |

## 使用规则

1. 概念图可以解释软件架构或科研控制逻辑。
2. 不得将其描述为实测、仿真或实验验证结果。
3. 公式图必须保留 `python -m tsao_researcher math` 返回的同等局限说明。
4. Schema 图必须保留 `solver_executed=false` 与 `automatic_approval=false`，不得在视觉上暗示真实求解已经发生。
5. 外部执行图必须保留 handoff/receipt 边界。
6. 科学验收始终由合格人员作出。
