<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher 标志" width="118" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先的科研策略、合同、交接与验证控制层</strong></p>
  <p>科学问题 → 模型合同 → 证据合同 → 受控外部执行 → 回执 → 验收证据</p>

[English](README.md) · [文档](docs/index.md) · [架构](docs/ARCHITECTURE.md) · [数理合同](docs/MATHEMATICAL_CONTRACTS.md) · [验证](docs/VALIDATION.md) · [视觉图谱](docs/VISUAL_ATLAS.zh-CN.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **正式版本 0.7.4** · Apache-2.0 · Python 3.10–3.13 · 确定性 CLI 与 Python API

## 1. 面向验收的项目总览

TsaoSciResearcher 是一个**科研控制层**，不是数值求解器。它负责科研问题路由、能力合同检索、第一性原理策略护照生成、矛盾证据保留、数量与单位防线、适用域与可辨识性边界、校验和绑定的外部计算交接、执行回执验证，以及确定性可复现胶囊导出。

除非用户提供外部产生且可通过校验和核验的执行证据，本仓库不会声称 DFT、量子化学、分子动力学、FEM、CFD、流程模拟、HPC、数据库检索或实验室工作已经发生。

以下实现规模由机器自动校验：

| 交付事实 | 已核验值 |
|---|---:|
| 能力合同 | **341** |
| 保留的旧版/通用合同 | **158** |
| 保留的工作簿命名 | **322** |
| 领域计算/工程合同 | **164** |
| 通用领域占位项 | **0** |
| 运行时新增能力 | **19** |
| 主工作流 | **15** |
| JSON Schema | **19** |
| 领域包 | **7** |
| AI 生成概念示意图 | **37** |

验收证据文件：[README 审计](docs/README_AUDIT_REPORT.md)、[能力覆盖矩阵](docs/CAPABILITY_COVERAGE_MATRIX.md)、[架构映射](docs/README_ARCHITECTURE_MAPPING.md)、[验证证据](docs/VALIDATION_EVIDENCE.json)、[HTML 测试仪表板](docs/test-dashboard.html)与 [SVG 测试仪表板](docs/test-dashboard.svg)。

> 仓库中的全部图示均为**用于文档说明的 AI 生成概念示意图**。它们不是实验观测、测量数据、数值求解结果，也不能证明外部计算已经执行。

## 2. 仓库实际实现的职责

| 层次 | 已实现职责 | 明确边界 |
|---|---|---|
| 路由层 | 中英文确定性分类、正负语义、优先级与澄清状态 | 分类不会执行被选择的方法 |
| 能力检索层 | 已验证 v2 能力目录、有界过滤和防御性复制 | 能力相关性不等于科学证明 |
| 策略顾问层 | 方法阶梯、观测量、条件、假设、证伪、验证与不确定性合同 | 输出始终为建议性 |
| Scientific Passport | 模型、尺度桥、证据、不确定性、适用域、冲突与可辨识性合同 | 自动批准被结构性禁用 |
| 项目状态层 | 标准 `.tsao-research/` 状态、哈希链接事件和受控转移 | 状态词不能替代证据 |
| 交接与回执层 | 输入校验和合同和用户提供的外部执行回执 | 仓库不会启动外部引擎 |
| 可复现层 | 确定性胶囊、安全归档、SBOM 和发布验证 | 可复现证据不等于物理真实性 |

```text
科学问题
    ↓
决策关键观测量、单位与验收阈值
    ↓
状态变量、控制规律、储库和约束
    ↓
最低充分、可证伪模型
    ↓
适用域、证据冲突、可辨识性和尺度桥质量门
    ↓
合格人工评审
    ↓
校验和绑定的外部交接 → 回执 → 独立验收
```

## 3. 系统架构

```text
CLI / Python API
      │
      ├── router.py ───────────────> 有界主工作流
      ├── capabilities.py ─────────> 已验证能力合同
      ├── strategy.py ─────────────> Scientific Passport 与科研质量门
      ├── mathematical_contracts.py> 版本化方程与解释边界
      ├── state.py ─────────────────> 哈希链接项目状态
      ├── handoff.py / receipts.py ─> 外部执行证据边界
      └── capsule.py ───────────────> 确定性可复现归档
```

![科研操作控制架构](docs/assets/ai/research_os_architecture.svg)

![渐进式路由与加载](docs/assets/ai/progressive_routing_loading.svg)

![计算交接边界](docs/assets/ai/computation_handoff_boundary.svg)

## 4. 机器可读数理合同

`math` 命令公开八个稳定、双语的数理合同。它们属于**解释与决策支持合同**，不会执行求解器、拟合参数、自动传播数值协方差，也不会独立验证用户提供的证据。

```bash
python -m tsao_researcher math
python -m tsao_researcher math --contract decision-readiness --language en
python -m tsao_researcher math --contract quantity-dimension --language zh-CN
```

每个响应固定声明科研边界：

```json
{
  "schema_version": "1.0",
  "advisory_only": true,
  "solver_executed": false,
  "automatic_approval": false
}
```

### 4.1 能力排序抽象

\[
S(c\mid q,o,e)=w_qR(q,c)+w_oR(o,c)+w_eM(e,c)-w_xC(c)
\]

- \(c\)：候选能力
- \(q\)：科研问题
- \(o\)：决策关键观测量
- \(e\)：已声明证据上下文
- \(C(c)\)：冲突或排除惩罚

该式是对确定性路由与有界排序的教学抽象。运行时不会声称这些权重是已经拟合的统计参数。

### 4.2 数量、单位与量纲合同

\[
x=(v,u,d), \qquad d_{\mathrm{left}}=d_{\mathrm{right}}
\]

当决策依赖定量比较时，科研主张应明确数值 \(v\)、单位 \(u\) 与物理量纲 \(d\)。缺失单位需要复核；同一比较标签下的量纲不相容会被阻断。

### 4.3 适用域与外推风险

\[
r_{\mathrm{extra}}=\frac{d(x,\mathcal A)}{\max(s_{\mathcal A},\varepsilon)}
\]

其中 \(x\) 是目标条件，\(\mathcal A\) 是声明适用域，\(s_{\mathcal A}\) 是适用域特征尺度。当前运行时采用保守的词汇与结构化外推标记，不会在缺少数据时伪装成已经计算了该归一距离。

### 4.4 证据三分与冲突账本

\[
E=(E_{+},E_{-},E_{0}),\qquad
\kappa=\mathbf 1[E_{+}\neq\varnothing\land E_{-}\neq\varnothing]
\]

- \(E_+\)：支持证据
- \(E_-\)：挑战或反驳证据
- \(E_0\)：中性或未决证据

负结果和矛盾证据始终保持可见，不会被静默平均成正向结论。

### 4.5 机制与参数可辨识性

\[
D_{ij}(O,C)>\tau
\qquad\text{或}\qquad
\operatorname{rank}(J_{\theta})=p
\]

竞争机制 \(i\) 与 \(j\) 必须在条件 \(C\) 下具有区分性观测量 \(O\)。唯一参数结论需要足够的敏感性秩。仓库负责记录要求和保守警告；数值雅可比矩阵仍需外部分析工具计算。

### 4.6 决策观测量不确定性预算

\[
\Sigma_y\approx
J\Sigma_{\theta}J^{\mathsf T}
+\Sigma_{\mathrm{num}}
+\Sigma_{\mathrm{sample}}
+\Sigma_{\mathrm{model}}
+\Sigma_{\mathrm{transfer}}
\]

不确定性必须传播到真正用于接受或拒绝的观测量。合同区分参数、数值、采样、模型形式和尺度传递不确定性，避免它们被一个笼统的“置信度”词语掩盖。

### 4.7 多尺度桥接误差预算

\[
U_{\mathrm{bridge}}^2=
U_{\mathrm{source}}^2+
U_{\mathrm{mapping}}^2+
U_{\mathrm{closure}}^2+
U_{\mathrm{target}}^2
\]

微观结果不能直接跳到工业结论。每个尺度桥都必须声明可测桥接变量、映射假设、闭合验证和目标尺度验收证据。

### 4.8 保守决策就绪度聚合

\[
G=\min\left(
 g_{\mathrm{quantity}},
 g_{\mathrm{applicability}},
 g_{\mathrm{evidence}},
 g_{\mathrm{identifiability}},
 g_{\mathrm{bridge}}
\right)
\]

最弱的强制合同决定整体就绪度：

```text
BLOCK < REVIEW < PASS
```

软件 `PASS` 仅表示当前声明中没有剩余软件阻断项，不等于科学证明，也不能绕过合格人工评审。

![数理合同目录](docs/assets/ai/mathematical_contract_registry.svg)

![决策就绪度格](docs/assets/ai/decision_readiness_lattice.svg)

![不确定性传播预算](docs/assets/ai/uncertainty_propagation_budget.svg)

![多尺度桥接误差预算](docs/assets/ai/multiscale_bridge_error_budget.svg)

详细双语解释见：[docs/MATHEMATICAL_CONTRACTS.md](docs/MATHEMATICAL_CONTRACTS.md)。

## 5. 科学模型还原策略

本仓库从决策问题背后的物理结构选择方法，而不是从流行软件名称选择方法。

### 5.1 从控制结构出发

一般状态模型可写为：

\[
\dot{x}=f(x,u,\theta)+\epsilon_{\mathrm{model}},
\qquad y=h(x,\theta)+\epsilon_{\mathrm{measurement}}
\]

策略必须声明：

1. 状态变量 \(x\)、控制量 \(u\) 与参数 \(\theta\)；
2. 观测量 \(y\) 与验收阈值；
3. 储库、约束、边界条件与初始条件；
4. 能够证伪候选机制的最小模型；
5. 数值、实验与尺度传递验证要求。

对守恒广延量 \(\phi\)，控制体结构为：

\[
\frac{\mathrm d}{\mathrm dt}\int_{\Omega}\rho\phi\,\mathrm dV
+\int_{\partial\Omega}\mathbf J_{\phi}\cdot\mathbf n\,\mathrm dA
=\int_{\Omega}s_{\phi}\,\mathrm dV
\]

该式不表示已经存在网格、本构关系或求解器运行。它用于规定外部 CFD、FEM、传递过程或流程模拟交接前必须具备哪些守恒与闭合声明。

### 5.2 最低充分方法阶梯

| 问题类型 | 最低充分起始模型 | 需要升级的证据 |
|---|---|---|
| 电子结构、缺陷与界面 | 经收敛验证的团簇或周期 DFT | 泛函敏感性、有限尺寸和参考态失效 |
| 反应机制与选择性 | 路径/过渡态能量学和微观动力学骨架 | 缺失路径、溶剂/动力学效应和传递耦合 |
| 构象与自由能 | 带收敛估计的系综 MD/MC | 采样不足、力场失效或电子反应性 |
| 形貌与相演化 | 标度/SCFT/CGMD/DPD/相场 | 映射失效、化学分辨不足或工艺耦合 |
| 流动、传热与传质 | 解析/控制体/一维降阶模型 | 闭合失效、几何效应、不稳定性或多物理耦合 |
| 力学与断裂 | 降阶力学或 FEM | 本构不可辨识、局域化、黏聚或相场需求 |
| 反应工程 | 质量/能量平衡加动力学/群体模型 | 停留时间非均匀、反应器 CFD 或装置数据标定 |
| 混合多尺度问题 | 成本最低的可证伪降阶模型 | 已验证桥接变量与量化传递不确定性 |

## 6. Scientific Passport 与验收策略

每个策略记录：

| 合同 | 必须声明的内容 | 典型阻断项 |
|---|---|---|
| 模型合同 | 变量、控制规律、假设、适用域和失效条件 | 未定义观测量或适用域 |
| 数量合同 | 数值、单位、量纲和比较标签 | 缺失单位或量纲不相容 |
| 适用域合同 | 标定域、迁移证据和外推标记 | 在域外进行无支撑迁移 |
| 证据合同 | 支持、挑战与未决证据 ID | 隐藏冲突或缺失证据 |
| 可辨识性合同 | 竞争机制与区分性观测量 | 等效多解或无依据唯一机制 |
| 尺度桥合同 | 来源/目标尺度、桥接变量和验收测试 | 直接从微观跳到工业结论 |
| 不确定性合同 | 参数、数值、采样、模型与传递不确定性 | 不确定性未传播到决策量 |

推荐使用策略：

```text
1. 先路由，再加载
2. 定义决策观测量、单位和阈值
3. 还原控制结构与竞争机制
4. 选择最低充分、可证伪模型
5. 暴露证据冲突、适用域、可辨识性和尺度桥
6. 定义验证与不确定性验收阈值
7. 获得合格人工审批
8. 创建校验和绑定的外部交接
9. 记录回执和输出哈希
10. 仅在独立验证后接受结果
```

![Scientific Passport 合同矩阵](docs/assets/ai/scientific_passport_matrix.svg)

![证据成熟度阶梯](docs/assets/ai/evidence_maturity_ladder.svg)

![科研诚信与因果防线](docs/assets/ai/scientific_integrity_causality_guard.svg)

## 7. CLI 使用方法

### 安装

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
```

### 路由科研任务

```bash
python -m tsao_researcher route \
  "设计一个可追溯的陷阱控制电荷输运多尺度研究"
```

### 检索能力合同

```bash
python -m tsao_researcher search \
  "polymer molecular dynamics" \
  --workflow computation-handoff \
  --limit 10
```

### 生成策略但不执行求解器

```bash
python -m tsao_researcher strategy \
  "界面陷阱态如何控制电导率和击穿？" \
  --observable "trap energy 1.0 eV" \
  --observable "conductivity S/m" \
  --condition "303 K" \
  --condition "20 kV/mm" \
  --evidence "independent experiment measurement" \
  --output strategy.json
```

### 查询数理合同

```bash
python -m tsao_researcher math
python -m tsao_researcher math --contract uncertainty-budget --language both
```

### 初始化并验证项目

```bash
python -m tsao_researcher init \
  --name "Mechanism study" \
  --question "Which mechanism is identifiable?" \
  --research-type mechanistic \
  --output study

python -m tsao_researcher verify study
```

### 记录外部执行证据

```bash
python -m tsao_researcher receipt record study/.tsao-research \
  --handoff computation/job.json \
  --engine Gaussian \
  --engine-version 16 \
  --command g16 \
  --command job.com \
  --exit-code 0 \
  --output computation/result.out \
  --started-at 2026-08-06T00:00:00Z \
  --finished-at 2026-08-06T00:10:00Z

python -m tsao_researcher receipt verify study/.tsao-research
```

### 导出确定性胶囊

```bash
python -m tsao_researcher capsule export study/.tsao-research \
  --output study.zip \
  --mode full
python -m tsao_researcher capsule verify study.zip
```

## 8. Python API

```python
from tsao_researcher.mathematical_contracts import get_mathematical_contract
from tsao_researcher.strategy import advise_computation_strategy

contract = get_mathematical_contract("decision-readiness", "zh-CN")
assert contract["solver_executed"] is False
assert contract["automatic_approval"] is False

strategy = advise_computation_strategy(
    "一个测量能否区分两个机制？",
    ["rate constant 1/s", "selectivity %"],
    ["350 K", "1 bar"],
    ["必须保留矛盾证据"],
    ["independent experiment"],
)
assert strategy["status"] == "advisory-only"
```

## 9. 测试与交付门禁

永久 CI 覆盖：

- Ubuntu / Python 3.10
- Ubuntu / Python 3.13
- Windows / Python 3.12
- macOS / Python 3.12

Linux 完整资格门包括：

```text
全量 pytest 回归
行覆盖率与分支覆盖率
逆序与固定随机顺序测试
Ruff format 与 lint
Mypy 严格类型检查
Bandit 源码安全检查
严格 pip-audit
19 个 Schema 校验
README 与生成工件一致性
SBOM 与仓库树摘要
MkDocs strict 构建
变异冒烟测试
性能冒烟测试
确定性源码发行包
wheel 和 sdist 隔离安装
```

本地执行：

```bash
python -m pip install -r requirements-ci.lock
python -m pip install -e . --no-deps
python -m pytest -q -p hypothesis.extra.pytestplugin
python -m pytest -q -p hypothesis.extra.pytestplugin -p pytest_cov \
  --cov=tsao_researcher --cov-branch
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python scripts/performance_smoke.py
python scripts/run_mutation_smoke.py
python scripts/build_readme_facts.py --check
python scripts/generate_checksums.py --check
mkdocs build --strict
```

## 10. 性能指标的真实含义

性能测试覆盖 Python 控制层：

- 科研任务路由；
- 能力目录加载与检索；
- 策略构建；
- Schema 与归档验证；
- 确定性打包。

这些指标**不代表** DFT、MD、FEM、CFD、流程模拟、GPU、MPI 或实验室执行获得加速。外部引擎必须有各自固定输入、软硬件环境、收敛容差、许可证与合格基准。

## 11. 完整 AI 概念图谱

### 科研控制与架构

<table>
<tr><td><img src="docs/assets/ai/research_os_architecture.svg" alt="科研操作系统架构"/></td><td><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="多代理编排"/></td></tr>
<tr><td><img src="docs/assets/ai/progressive_routing_loading.svg" alt="渐进式路由加载"/></td><td><img src="docs/assets/ai/project_state_machine.svg" alt="项目状态机"/></td></tr>
<tr><td><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="项目账本与来源链"/></td><td><img src="docs/assets/ai/research_production_pipeline.svg" alt="科研生产流水线"/></td></tr>
</table>

### 能力、证据与需求

<table>
<tr><td><img src="docs/assets/ai/capability_landscape.svg" alt="能力图谱"/></td><td><img src="docs/assets/ai/capability_implementation_levels.svg" alt="能力实现级别"/></td></tr>
<tr><td><img src="docs/assets/ai/original_requirements_coverage.svg" alt="原始需求覆盖"/></td><td><img src="docs/assets/ai/evidence_claim_graph.svg" alt="证据主张图"/></td></tr>
<tr><td><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="证据引文完整性闭环"/></td><td><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="可复现质量门"/></td></tr>
</table>

### 策略、数理与多尺度推理

<table>
<tr><td><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="第一性原理策略阶梯"/></td><td><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="科学方法决策树"/></td></tr>
<tr><td><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="多尺度科学流水线"/></td><td><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="多尺度案例图"/></td></tr>
<tr><td><img src="docs/assets/ai/mathematical_contract_registry.svg" alt="数理合同目录"/></td><td><img src="docs/assets/ai/decision_readiness_lattice.svg" alt="决策就绪度格"/></td></tr>
<tr><td><img src="docs/assets/ai/uncertainty_propagation_budget.svg" alt="不确定性传播预算"/></td><td><img src="docs/assets/ai/multiscale_bridge_error_budget.svg" alt="多尺度桥接误差预算"/></td></tr>
</table>

### 科研诚信与定量质量门

<table>
<tr><td><img src="docs/assets/ai/scientific_passport_matrix.svg" alt="Scientific Passport 矩阵"/></td><td><img src="docs/assets/ai/evidence_maturity_ladder.svg" alt="证据成熟度阶梯"/></td></tr>
<tr><td><img src="docs/assets/ai/decision_readiness_gate.svg" alt="决策就绪度门"/></td><td><img src="docs/assets/ai/active_evidence_learning_loop.svg" alt="主动证据学习闭环"/></td></tr>
<tr><td><img src="docs/assets/ai/quantity_dimension_contract.svg" alt="数量量纲合同"/></td><td><img src="docs/assets/ai/applicability_extrapolation_guard.svg" alt="适用域外推防线"/></td></tr>
<tr><td><img src="docs/assets/ai/evidence_conflict_resolution.svg" alt="证据冲突处理"/></td><td><img src="docs/assets/ai/mechanism_identifiability_gate.svg" alt="机制可辨识性门"/></td></tr>
<tr><td><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定性量化与验证"/></td><td><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="科研诚信因果防线"/></td></tr>
</table>

### 外部执行、实验、写作与发布

<table>
<tr><td><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="计算交接边界"/></td><td><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="人工审批边界"/></td></tr>
<tr><td><img src="docs/assets/ai/laboratory_data_quality.svg" alt="实验室数据质量"/></td><td><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="科学写作证据链"/></td></tr>
<tr><td><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="科研图件编辑防线"/></td><td><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="安装兼容性矩阵"/></td></tr>
<tr><td><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="供应链发布证明"/></td><td></td></tr>
</table>

> 以上均为用于仓库文档说明的 AI 生成概念示意图，不代表实验数据、测量结果、求解器云图、轨迹或已完成的外部执行。

## 12. 仓库结构

```text
.
├── tsao_researcher/
│   ├── router.py
│   ├── capabilities.py
│   ├── strategy.py
│   ├── mathematical_contracts.py
│   ├── state.py
│   ├── handoff.py
│   ├── receipts.py
│   └── capsule.py
├── scripts/
├── tests/
├── schemas/
├── workflows/
├── domain-packs/
├── docs/
├── examples/
├── README.md
├── README.zh-CN.md
├── VERSION
└── SHA256SUMS
```

## 13. 科学与交付边界

软件质量门可以证明确定性行为、Schema 一致性、可追溯性、安全状态、打包可复现性和当前声明中不存在阻断项，但不能证明一个物理机制为真。

最终科学验收仍需按任务提供：

- 合格领域专家评审；
- 固定外部输入和引擎版本；
- 收敛性与敏感性证据；
- 校准测量与不确定性；
- 独立复现或验证；
- 校验和绑定的回执与输出。

**TsaoSciResearcher 控制科研工作流，但不会冒充仍需真实执行和验证的科学过程。**
