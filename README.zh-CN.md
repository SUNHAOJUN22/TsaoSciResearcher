<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher 标志" width="118" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先的科研控制层</strong></p>
  <p>科学问题 → 证据 → 策略 → 受控执行 → 验证 → 可复现实体</p>

[English](README.md) · [文档](docs/index.md) · [架构](docs/ARCHITECTURE.md) · [验证](docs/VALIDATION.md) · [科研图谱](docs/VISUAL_ATLAS.zh-CN.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **正式版本 0.7.1** · Apache-2.0 · Python 3.10–3.13 · 确定性 CLI 与 Python API

## 系统总览

TsaoSciResearcher 是一个**科研任务路由器、研究状态机、证据合同系统、第一性原理策略顾问、受控计算交接层与可复现边界**。它用于回答：需要知道什么、最低充分方法是什么、哪类证据能够证伪机制、在接受结果前必须记录哪些信息。

它不会在缺少可校验外部执行证据时，声称数据库已查询、仪器已运行，或 DFT、MD、FEM、CFD、流程模拟已经完成。

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/research_os_architecture.svg" alt="科研操作系统概念架构"/><br/><strong>科研操作控制层</strong></td>
<td width="50%"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="多尺度科学管线概念图"/><br/><strong>尺度感知的科学还原</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="证据与主张图概念图"/><br/><strong>证据—主张可追溯</strong></td>
<td width="50%"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="可复现质量门概念图"/><br/><strong>通过显式质量门验收</strong></td>
</tr>
</table>

> 仓库中的全部科研图均为**用于文档说明的 AI 生成概念示意图**，不是实验观测、测量数据、数值求解结果，也不能证明外部计算已经执行。

## 实际实现的能力

运行时提供一个确定性入口和机器可读的科研控制模型：

| 已实现层 | 可核验能力 |
|---|---|
| 任务路由 | 中英文确定性路由；支持正向/负向语义、优先级、置信度和明确的澄清状态 |
| 能力检索 | 共 **341** 个能力合同，其中保留 **322** 个工作簿命名、**164** 个领域计算/工程合同、**158** 个旧版/通用合同，并新增 **19** 个运行时能力 |
| 合同质量 | 通用领域占位项为 **0**；对实现级别、来源链、审批要求和计算交接等嵌套结构进行验证 |
| 研究状态 | 标准 `.tsao-research/` 项目状态、哈希链接事件、受控状态转移与失败回滚 |
| 科学推理 | 从观测量、自由度、守恒律、系综、尺度、证伪与不确定性推导第一性原理方法阶梯 |
| 外部计算 | 为 DFT、量子化学、MD、FEM、CFD、流程/HPC 与仪器运行提供校验和绑定的交接与执行回执 |
| 可复现性 | 确定性胶囊、安全归档、内容哈希、SBOM、发布验证和隔离安装验证 |
| 质量控制 | 证据/主张一致性、科研质量阻断、图件合同、引文边界与人工审批门 |

仓库当前包含 **15** 个主工作流、**19** 个 JSON Schema、**7** 个领域包和 **25** 张 AI 生成概念图。

详细证据见：[原始需求审计](docs/ORIGINAL_REQUIREMENTS_AUDIT.md)、[能力覆盖矩阵](docs/CAPABILITY_COVERAGE_MATRIX.md)、[架构映射](docs/README_ARCHITECTURE_MAPPING.md)和 [README 审计报告](docs/README_AUDIT_REPORT.md)。

## 科学推理模型

方法选择由决策问题背后的物理决定，而不是由流行软件名称决定。

```text
科学问题
    ↓
决策关键观测量与可接受证据
    ↓
自由度、状态变量、储库和约束
    ↓
守恒律、对称性、热力学与统计力学
    ↓
长度 / 时间 / 能量尺度及尺度桥
    ↓
最低充分、可证伪模型
    ↓
验证、不确定性量化与升级条件
    ↓
经批准的外部交接 → 执行回执 → 独立科学验收
```

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="第一性原理策略阶梯概念图"/><br/><strong>最低充分方法阶梯</strong></td>
<td width="50%"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="科学问题方法决策树概念图"/><br/><strong>问题—方法决策树</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定性量化与验证概念图"/><br/><strong>验证与不确定性闭环</strong></td>
<td width="50%"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="科研诚信与因果边界概念图"/><br/><strong>因果与科研诚信防线</strong></td>
</tr>
</table>

### 科学问题 → 推荐起始模型

| 科学问题 | 首先还原 | 最低充分起始方法 | 仅在证据要求时升级 |
|---|---|---|---|
| 电子结构、缺陷、陷阱与界面 | 电荷/自旋、对称性、静电与边界条件 | 经收敛验证的周期或团簇 DFT | 杂化泛函、嵌入、GW/BSE 或更高等级波函数方法 |
| 反应势垒与选择性 | 化学计量、候选网络与详细平衡 | 过渡态/路径搜索与能量学 | 增强采样、微观动力学、动力学蒙特卡洛与传递耦合 |
| 构象、溶剂化与自由能 | 系综、储库、集体变量和相关时间 | 配套自由能估计的 MD/Monte Carlo | QM/MM、从头算 MD 或经验证的粗粒化 |
| 聚合物形貌与结晶 | 链连接性、熵—焓竞争与序参量 | 标度/SCFT，随后使用 CGMD、DPD 或相场 | 化学映射、均匀化与工艺耦合 |
| 流动、传热与传质 | 守恒律、无量纲数和本构闭合 | 解析/控制体/一维降阶模型 | 网格收敛 CFD 与耦合多物理场 |
| 力学、黏弹与断裂 | 动量/能量平衡、材料对称性和可辨识性 | 降阶力学或 FEM | 相场/黏聚断裂与微结构本构 |
| 电荷输运与击穿 | 电子/陷阱态、电化学势、Poisson 与电荷守恒 | 跳跃/kMC 或漂移—扩散—Poisson | 电—热、形貌演化与随机失效耦合 |
| 反应器与分子量分布 | 质量/能量平衡、停留时间和群体状态 | CSTR/PFR/网络加群体平衡 | 反应器 CFD、流程动态、贝叶斯标定或数字孪生 |
| 欠定的混合多尺度问题 | 观测量、单位、储库、竞争机制 | 成本最低的可证伪降阶模型 | 通过可测桥接变量进行不确定性驱动的逐级耦合 |

`strategy` 输出始终标记为建议性结果，并明确记录求解器未执行。

## 架构与数据流

```text
CLI / Python API
      │
      ├── router ──> 一个主工作流 + 有界次级工作流
      ├── capability search ──> 已验证合同和实现边界
      ├── strategy adviser ──> 方法阶梯、假设、验证与 UQ
      ├── project state ──> 哈希事件、审批、风险和产物
      ├── handoff / receipt ──> 外部执行边界和输出哈希
      └── capsule / verification ──> 确定性归档与完整性检查
```

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="渐进路由与加载概念图"/><br/><strong>先路由，再加载</strong></td>
<td width="50%"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="项目账本与来源链概念图"/><br/><strong>分离且哈希链接的账本</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="计算交接边界概念图"/><br/><strong>受控外部执行</strong></td>
<td width="50%"><img src="docs/assets/ai/project_state_machine.svg" alt="项目状态机概念图"/><br/><strong>保持事实语义的状态转移</strong></td>
</tr>
</table>

## 科研生命周期

15 个主工作流覆盖完整控制链：

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

```text
proposed → planned → running → completed → checked → validated → accepted
                                      ↘ rejected / superseded
```

状态词不能替代证据。`completed`、`checked`、`validated` 和 `accepted` 是不同状态。

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/research_production_pipeline.svg" alt="科研生产管线概念图"/><br/><strong>端到端科研生产流</strong></td>
<td width="50%"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="多智能体编排概念图"/><br/><strong>有边界的智能体编排</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="证据引文完整性概念图"/><br/><strong>引文与证据完整性</strong></td>
<td width="50%"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="人工审批边界概念图"/><br/><strong>合格人员验收边界</strong></td>
</tr>
</table>

## 安装

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
```

运行时依赖仅保留 PyYAML 和 jsonschema。开发、文档、绘图和构建依赖定义在 `pyproject.toml`，CI 精确版本锁定在 `requirements-ci.lock`。

## 快速开始

### 1. 路由科研任务

```bash
python -m tsao_researcher route \
  "设计一个可追溯的陷阱控制电荷输运多尺度研究"
```

### 2. 检索经过验证的能力合同

```bash
python -m tsao_researcher search \
  "polymer molecular dynamics" \
  --workflow computation-handoff \
  --limit 10
```

### 3. 推导第一性原理策略

```bash
python -m tsao_researcher strategy \
  "界面陷阱态如何控制电荷输运？" \
  --observable "陷阱能级分布" \
  --observable "空间电荷密度" \
  --condition "外加电场" \
  --evidence "TSDC 与 PEA 测量"
```

### 4. 初始化并验证项目

```bash
python -m tsao_researcher init \
  --name pp-cable-study \
  --question "哪一种机制抑制空间电荷？" \
  --research-type mixed \
  --output work

python -m tsao_researcher verify work/pp-cable-study
```

### 5. 记录外部执行证据

```bash
python -m tsao_researcher receipt record work/pp-cable-study \
  --handoff HANDOFF-001 \
  --engine gromacs \
  --engine-version 2026.1 \
  --command "gmx" --command "mdrun" --command "-deffnm" --command "prod" \
  --exit-code 0 \
  --output results/prod.log \
  --started-at 2026-08-05T01:00:00Z \
  --finished-at 2026-08-05T02:00:00Z

python -m tsao_researcher receipt verify work/pp-cable-study
```

### 6. 导出并验证确定性胶囊

```bash
python -m tsao_researcher capsule export work/pp-cable-study \
  --output pp-cable-study.zip \
  --mode full

python -m tsao_researcher capsule verify pp-cable-study.zip
```

## 输入与输出

| 输入 | 输出 |
|---|---|
| 科学问题或任务文本 | 主工作流、次级工作流、置信度、澄清和审批标志 |
| 能力检索词 | 按相关度排序的能力合同、领域、工作流、实现级别与交接边界 |
| 观测量、条件、约束和证据 | 科学域、模型阶梯、假设、必要输入、验证、证伪与 UQ 方案 |
| 项目元数据和状态请求 | 标准项目目录与哈希链接事件 |
| 经批准的外部运行元数据 | 与交接和输出哈希绑定的执行回执 |
| 项目状态 | 确定性元数据/完整可复现胶囊 |
| 质量请求、证据和主张注册表 | 带明确原因的通过/阻断结果，而非静默接受 |

## 性能与效率设计

优化后的运行时保持确定性输出，同时消除不必要工作：

- 路由规则和正则表达式仅编译一次并缓存；
- 字面量预筛选在不可能命中时避免正则开销；
- 仅在正向触发后扫描负向触发条件；
- 内置默认规则不再反复解析路径和读取文件状态；
- 能力目录使用缓存的不可变源记录和有界防御性复制；
- 科学策略触发词按科学域一次性归一化和编译；
- 基准采用中英文混合任务与混合能力查询，避免单一热缓存输入制造虚假加速；
- 超过阈值时性能门直接失败，而不是只打印耗时。

这些优化加速的是**科研控制层**，不会改变外部 DFT、MD、FEM、CFD 或流程求解器的物理精度与本体运行时间。

## 质量保证

`main` 质量管线包括：

- 仓库与结构审计；
- 19 个 JSON Schema 验证；
- 完整、逆序和固定随机顺序回归；
- 行覆盖与分支覆盖，最低门槛 85%；
- Ruff 格式与静态检查；
- Mypy strict 类型检查；
- Bandit 源码安全检查；
- 排除本地 editable 包后，对解析出的第三方依赖环境执行漏洞审计；
- 确定性 SBOM 与校验和；
- 面向关键科学与来源链不变量的变异测试；
- 混合输入的有界性能基准；
- 两次源码发布包逐字节一致性；
- wheel/sdist 构建、隔离安装与真实 CLI 验收。

机器可读与可视化证据：

- [验证证据](docs/VALIDATION_EVIDENCE.json)
- [测试仪表板 HTML](docs/test-dashboard.html)
- [测试仪表板 SVG](docs/test-dashboard.svg)
- [验证协议](docs/VALIDATION.md)
- [科研质量示例](docs/SCIENTIFIC_QUALITY_EXAMPLES.json)
- [SBOM](docs/SBOM.cdx.json)

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="供应链与发布证明概念图"/><br/><strong>供应链证据</strong></td>
<td width="50%"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="安装兼容性矩阵概念图"/><br/><strong>安装合同</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="实验室与数据质量概念图"/><br/><strong>实验与数据质量</strong></td>
<td width="50%"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="科研图件编辑防线概念图"/><br/><strong>图件诚信边界</strong></td>
</tr>
</table>

## 能力模型

| 实现级别 | 含义 |
|---|---|
| `native-research` | 在本仓库内提供确定性实现 |
| `computation-delegated` | 需要外部科学引擎；仓库提供规划、校验和绑定交接与回执验证 |
| `human-review` | 必须由合格人员审批，不能自动接受 |

能力目录明确区分“可发现的能力合同”和“外部系统已执行的证据”。

<table>
<tr>
<td width="50%"><img src="docs/assets/ai/capability_landscape.svg" alt="能力全景概念图"/><br/><strong>能力全景</strong></td>
<td width="50%"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="能力实现层级概念图"/><br/><strong>实现层级</strong></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="原始需求覆盖概念图"/><br/><strong>原始需求覆盖</strong></td>
<td width="50%"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="科研写作证据链概念图"/><br/><strong>写作—证据链</strong></td>
</tr>
</table>

## 科研 AI 示意图谱

完整的 **25 张图**图谱如下，并在 [docs/VISUAL_ATLAS.zh-CN.md](docs/VISUAL_ATLAS.zh-CN.md) 中提供双语说明。每张 SVG 均保存在仓库内、完全自包含，并包含可访问性的 `<title>` 和 `<desc>` 元数据。

<table>
<tr><td width="50%"><img src="docs/assets/ai/research_os_architecture.svg" alt="科研操作系统架构"/><br/><strong>1 · 科研操作系统架构</strong></td><td width="50%"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="多智能体编排"/><br/><strong>2 · 多智能体编排</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="证据主张图"/><br/><strong>3 · 证据—主张图</strong></td><td width="50%"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="多尺度科学管线"/><br/><strong>4 · 多尺度科学管线</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="可复现质量门"/><br/><strong>5 · 可复现质量门</strong></td><td width="50%"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="计算交接边界"/><br/><strong>6 · 计算交接</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/project_state_machine.svg" alt="项目状态机"/><br/><strong>7 · 项目状态机</strong></td><td width="50%"><img src="docs/assets/ai/capability_landscape.svg" alt="能力全景"/><br/><strong>8 · 能力全景</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="原始需求覆盖"/><br/><strong>9 · 需求覆盖</strong></td><td width="50%"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="能力实现级别"/><br/><strong>10 · 实现级别</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="渐进路由与加载"/><br/><strong>11 · 渐进路由</strong></td><td width="50%"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="项目账本与来源"/><br/><strong>12 · 账本与来源链</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="证据引文完整性"/><br/><strong>13 · 引文完整性</strong></td><td width="50%"><img src="docs/assets/ai/research_production_pipeline.svg" alt="科研生产管线"/><br/><strong>14 · 科研生产</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="安装兼容性矩阵"/><br/><strong>15 · 安装矩阵</strong></td><td width="50%"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="供应链发布证明"/><br/><strong>16 · 发布证明</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="第一性原理策略阶梯"/><br/><strong>17 · 策略阶梯</strong></td><td width="50%"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="科学问题方法决策树"/><br/><strong>18 · 方法决策树</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定性量化与验证"/><br/><strong>19 · UQ 与验证</strong></td><td width="50%"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="科研诚信与因果防线"/><br/><strong>20 · 诚信防线</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="实验室数据质量"/><br/><strong>21 · 实验室质量</strong></td><td width="50%"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="科研写作证据链"/><br/><strong>22 · 写作证据链</strong></td></tr>
<tr><td width="50%"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="科研图件编辑防线"/><br/><strong>23 · 图件编辑防线</strong></td><td width="50%"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="人工审批验收边界"/><br/><strong>24 · 人工验收</strong></td></tr>
<tr><td colspan="2"><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="聚合物多尺度案例"/><br/><strong>25 · 聚合物绝缘多尺度案例</strong></td></tr>
</table>

## 已知限制与科研诚信边界

- 实时文献检索、专有数据库与连接器访问取决于宿主环境。
- PDF 解析、绘图和 DOCX/PPT/LaTeX 渲染委托给宿主工具。
- 仓库推荐科学方法，但不内置所有求解器、力场、赝势、仪器驱动或实验方案。
- 在有效回执和输出哈希存在前，外部计算不能视为已执行。
- 软件质量门通过不等于物理正确、临床有效、专利自由实施、安全或科学结论已经成立。
- 高影响因果、医疗、安全、科研诚信和专利决策需要合格人员复核。

## 仓库证据与来源

- [README 审计](docs/README_AUDIT_REPORT.md)
- [能力覆盖](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [架构映射](docs/README_ARCHITECTURE_MAPPING.md)
- [机器可读 README 事实](docs/README_FACTS.json)
- [验证证据](docs/VALIDATION_EVIDENCE.json)
- [工程审计报告](docs/engineering-audit-report.pdf)
- [更新日志](CHANGELOG.md)
- [安全策略](SECURITY.md)
- [引用元数据](CITATION.cff)

代码采用 Apache-2.0 许可证。能力名称用于标识科研任务和接口，不代表对第三方科学软件或服务的所有权、隶属关系或内置访问权。
