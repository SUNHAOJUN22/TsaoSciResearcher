<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先的科研工作控制层</strong></p>
  <p>科学问题 → 证据 → 设计 → 受控执行 → 验证 → 可复现交付物</p>

[English](README.md) · [项目文档](docs/index.md) · [最初需求落实审计](docs/ORIGINAL_REQUIREMENTS_AUDIT.zh-CN.md) · [架构](docs/ARCHITECTURE.md) · [验证](docs/VALIDATION.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **正式版本 0.7.0** · Apache-2.0 · Python 3.10–3.13 · Windows、Linux、macOS

## 实际代码到底实现了什么

TsaoSciResearcher 是一个**单入口科研路由器、项目状态系统、验证层、能力目录和可复现边界**。它不是把所有科学数据库、求解器、仪器驱动、绘图引擎和 Office 渲染器打包在一起的单体软件。

已将最初设计文档、322 项 AI for Science Skill 目录与当前源码逐项对照：

| 审计事实 | 已核实结果 |
|---|---:|
| Excel Skill Slug 覆盖 | **322 / 322** |
| 缺失 Skill Slug | **0** |
| 通用科研具名合同 | **158** |
| 计算/工程领域具名合同 | **164** |
| 通用领域占位合同 | **0** |
| 运行时/核心新增能力 | **19** |
| 能力合同总数 | **341** |
| 原生科研/运行时合同 | **148** |
| 外部计算委托合同 | **170** |
| 强制人工审核合同 | **23** |
| 带 Gate 工作流 | **15** |
| JSON Schema | **19** |
| 确定性脚本 | **39** |

完整结果见[最初功能定义落实审计](docs/ORIGINAL_REQUIREMENTS_AUDIT.zh-CN.md)。能力合同表示“可检索、可路由、可验证的任务合同”，**不代表**外部数据库、模型、求解器、仪器或计算已经安装或运行。

## 能力边界

| 层级 | 实际实现 |
|---|---|
| **原生核心** | 确定性双语路由、能力搜索、项目初始化、状态转换、哈希事件链、Schema 验证、证据/论断检查、Figure Contract、执行凭据、可复现胶囊、安全归档和确定性打包 |
| **科研控制层** | 科学问题、文献、综述、研究设计、实验、数据、绘图、写作、评审、报告、项目、专利、诚信、实验室和计算交接工作流及其入口/阻断/完成门 |
| **宿主工具执行** | 实时检索、PDF 解析、数值统计/DOE/ML、绘图、DOCX/PPT/LaTeX 生产和外部应用连接 |
| **外部科学执行** | DFT、量子化学、MD、FEM、CFD、流程模拟、HPC、云任务、仪器和实验室自动化 |
| **合格人员审批** | 医疗、安全、专利/FTO、高影响因果、科研诚信和最终科学接受 |

## 核心架构

- **先路由，后加载**：先选择一个主工作流，再读取该工作流明确列出的参考资料和模板。
- **322 项精确目录合同**：Excel 中的全部 Slug 均保留；另有 19 项路由、安全、溯源、第一性原理策略和接受控制能力。
- **统一 `.tsao-research/` 状态**：问题、假设、证据、论断、决策、审批、风险、产物、凭据和哈希事件相互分离。
- **第一性原理策略顾问**：先定义可观测量、自由度、守恒律、量子/统计物理、热力学势、系综、尺度和证伪，再提出最低充分的计算/仿真方法阶梯；不运行求解器。
- **受控计算交接**：真实计算前记录输入哈希、尺度、方法、条件、收敛/UQ、预期输出和审批点。
- **Execution Receipt v2**：把真实外部执行绑定到 handoff、引擎、参数、时间、退出状态和输出哈希。
- **Reproducibility Capsule**：确定性 metadata/full ZIP，拒绝路径逃逸、符号链接、重复成员和校验和篡改。
- **真实性状态机**：`completed`、`checked`、`validated`、`accepted` 不能互相替代。

## 第一性原理计算与仿真策略

本项目的特色不是简单推荐软件名称，而是从底层物理重建方法选择：

```text
科学问题 → 决策可观测量 → 自由度/状态变量 → 守恒律/对称性
        → 量子、统计物理、热力学或连续介质框架
        → 时间/空间/能量尺度与模型降阶
        → 最低充分模型 → 升级模型 → 验证/证伪/UQ
        → 外部计算 handoff → 结果审查
```

“第一性原理”不等于所有问题都使用 DFT。策略顾问先选择成本最低、能够被证伪的物理表征；只有当验证明确指出缺少自由度、耦合或尺度时才升级。详见[第一性原理策略说明](docs/FIRST_PRINCIPLES_STRATEGY.zh-CN.md)。

### 科学问题 → 最低充分计算/仿真策略

| 科学问题 | 首先从何出发 | 最低充分方法 | 由证据触发的升级方法 |
|---|---|---|---|
| 基态成键、缺陷能级和陷阱态 | 电荷/自旋、对称性、静电和热力学循环 | 经过收敛与有限尺寸控制的周期/团簇 DFT | 杂化泛函、嵌入或更高层级波函数方法 |
| 激发态、光谱和载流子激发 | 态性质、选择定则与电子—空穴自由度 | TDDFT 或针对性的激发态计算 | GW/BSE、多参考方法或非绝热动力学 |
| 反应能垒、催化与选择性 | 化学计量、细致平衡和候选反应网络 | DFT/波函数路径搜索、NEB 与过渡态优化 | 增强采样、微观动力学、动力学 Monte Carlo 与输运耦合 |
| 构象、溶剂化、自由能和稀有事件 | 统计系综、库、集体变量和相关时间 | MD/Monte Carlo、umbrella、metadynamics 或炼金自由能 | QM/MM、从头算 MD 或经验证的粗粒化模型 |
| 高分子形貌、结晶和相分离 | 熵—能竞争、链连接性和序参量 | 标度/SCFT，随后使用 CGMD、DPD 或相场动力学 | 化学信息映射、均匀化和工艺—结构耦合 |
| 流动、传热传质和压降 | 守恒律、本构闭合和无量纲数 | 控制体、1D 或降阶模型 | 网格收敛的 CFD 与耦合多物理场 |
| 应力、黏弹、断裂与疲劳 | 动量/能量平衡、材料对称性和本构可识别性 | 降阶力学或采用客观本构的 FEM | 相场/黏聚断裂和微结构知情力学 |
| 电荷输运、空间电荷和击穿 | 电子/陷阱态、电化学势及 Poisson/电荷守恒 | 跳跃/kMC 或漂移—扩散—Poisson | 电—热、形貌演化和随机失效模型 |
| 反应器、分子量分布和流程动态 | 质量/能量平衡、停留时间和可识别性 | CSTR/PFR/网络与群体平衡模型 | 反应器 CFD、流程动态、贝叶斯校准或数字孪生代理 |
| 混合或定义不足的多尺度问题 | 可观测量、单位、库、尺度和竞争机理 | 可证伪的解析或降阶模型 | 通过可测桥接变量进行顺序、含不确定度的耦合 |

策略输出始终为 `advisory-only`，并明确记录 `solver_executed: false`。推荐 DFT、MD、FEM、CFD 或流程模型不等于已经执行；只有完成经批准的校验和 handoff、外部日志与输出哈希、收敛审查和独立科学接受后，才能进入更高真实性状态。

## 科研生命周期与工作流

```text
问题形成 → 证据映射 → 研究设计 → 执行/分析 → 检查 → 验证
        → 接受/拒绝 → 沟通 → 归档
```

```text
proposed → planned → running → completed → checked → validated → accepted
                                      ↘ rejected / superseded
```

15 个主工作流：

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

### 各工作流能力合同数量

| 工作流 | 合同数 |
|---|---:|
| `computation-handoff` | 169 |
| `data-analysis` | 52 |
| `project-management` | 35 |
| `deep-research` | 16 |
| `scientific-writing` | 14 |
| `research-design` | 10 |
| `laboratory` | 8 |
| `research-integrity` | 8 |
| `patent-and-transfer` | 7 |
| `research-question` | 6 |
| `systematic-review` | 5 |
| `experiment-design` | 3 |
| `peer-review` | 3 |
| `technical-report` | 3 |
| `scientific-figure` | 2 |

### Excel 能力类别

| 一级目录 | 具名合同数 |
|---|---:|
| 催化、高分子与复合材料 | 30 |
| 计算化学与材料计算 | 30 |
| 分子动力学与多尺度 | 24 |
| 科研管理、专利与诚信 | 24 |
| 化工流程、动力学与数字孪生 | 22 |
| AI与机器学习科研 | 20 |
| HPC、云计算与可重复性 | 20 |
| 实验室自动化与仪器 | 20 |
| 数据统计与可视化 | 20 |
| 有限元与多物理场 | 20 |
| 科研写作与出版 | 20 |
| CFD、颗粒与加工过程 | 18 |
| 文献与知识工程 | 18 |
| 生物信息与医学科研 | 18 |
| 科研Agent与编排 | 18 |

## 科研能力 AI 示意图谱

以下为**依据当前仓库代码和能力边界生成的 25 张 AI 概念图**，用于解释能力合同、控制流、溯源、底层科学推理和执行边界；它们属于文档资产，不是实验观测、模拟结果，也不是外部引擎已经运行的证明。

<table>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/research_os_architecture.svg" alt="科研操作系统架构"/><br/><strong>1 · 科研操作系统架构</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="多智能体科研编排"/><br/><strong>2 · 多智能体科研编排</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="证据—论断图"/><br/><strong>3 · 证据—论断图</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="多尺度科研流程"/><br/><strong>4 · 多尺度科研流程</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="可复现质量门"/><br/><strong>5 · 可复现质量门</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="计算交接边界"/><br/><strong>6 · 计算交接边界</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/project_state_machine.svg" alt="项目状态机"/><br/><strong>7 · 项目状态机</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_landscape.svg" alt="科研能力版图"/><br/><strong>8 · 科研能力版图</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="最初需求落实图"/><br/><strong>9 · 最初需求落实图</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="能力实现层级"/><br/><strong>10 · 能力实现层级</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="渐进式路由与加载"/><br/><strong>11 · 渐进式路由与加载</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="项目台账与溯源"/><br/><strong>12 · 项目台账与溯源</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="证据与引文完整性"/><br/><strong>13 · 证据与引文完整性</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/research_production_pipeline.svg" alt="科研产出流水线"/><br/><strong>14 · 科研产出流水线</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="安装兼容矩阵"/><br/><strong>15 · 安装兼容矩阵</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="供应链与发布证明"/><br/><strong>16 · 供应链与发布证明</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="第一性原理策略阶梯"/><br/><strong>17 · 第一性原理策略阶梯</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="科学问题到方法决策树"/><br/><strong>18 · 科学问题—方法决策树</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="不确定度量化与验证"/><br/><strong>19 · UQ 与模型验证</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="科研诚信与因果防护"/><br/><strong>20 · 科研诚信与因果防护</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="实验室与数据质量"/><br/><strong>21 · 实验室与数据质量</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="科研写作证据链"/><br/><strong>22 · 科研写作证据链</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="科学图片编辑防护"/><br/><strong>23 · 科学图片编辑防护</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="人工审批与科学接受边界"/><br/><strong>24 · 人工审批与科学接受边界</strong></td></tr>
<tr><td colspan="2" valign="top"><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="高分子绝缘多尺度案例"/><br/><strong>25 · 高分子绝缘多尺度策略案例</strong></td></tr>
</table>

完整双语图谱见 [docs/VISUAL_ATLAS.zh-CN.md](docs/VISUAL_ATLAS.zh-CN.md)。全部 SVG 均为仓库内自包含资产，具有 `<title>` 与 `<desc>` 可访问性信息，并由 README 图谱清单进行自动验证。

## 快速开始

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
python -m tsao_researcher route "设计一个可追溯的聚烯烃多尺度研究"
python -m tsao_researcher search "聚合物 分子动力学" --limit 10
```

初始化并验证项目状态：

```bash
python -m tsao_researcher init   --name "聚烯烃多尺度研究"   --question "加工历史通过哪些机制影响结构与性能？"   --research-type mechanistic   --output .
python -m tsao_researcher verify .
```

形成第一性原理计算/仿真策略（只建议，不运行求解器）：

```bash
python -m tsao_researcher strategy \
  "陷阱态和形貌如何控制空间电荷与击穿？" \
  --observable "空间电荷" \
  --observable "击穿强度" \
  --condition "外加电场" \
  --evidence "PEA 电荷分布" \
  --output strategy.json
python scripts/validate_computation_strategy.py strategy.json
```

创建受控计算交接：

```bash
python scripts/handoff_to_computation.py   --project .tsao-research   --out computation/handoff.json   --question "需要计算哪个性质？"   --property "目标性质"   --profile MD   --scale atomistic   --method "候选方法"   --boundary-condition "周期性边界"   --metric "收敛指标"   --expected-output "经验证的结果文件"   --input-file data/input.dat
```

记录并验证真实外部执行：

```bash
python -m tsao_researcher receipt record .   --handoff computation/handoff.json   --engine gromacs --engine-version 2026.1   --command gmx --command mdrun --exit-code 0   --output computation/result.dat   --started-at 2026-07-24T01:00:00Z   --finished-at 2026-07-24T01:10:00Z
python -m tsao_researcher receipt verify .
```

导出并验证可复现胶囊：

```bash
python -m tsao_researcher capsule export . --mode metadata --output project-metadata.zip
python -m tsao_researcher capsule export . --mode full --output project-full.zip
python -m tsao_researcher capsule verify project-full.zip
```

## 安装

```bash
python install.py --agent codex --scope user --dry-run
python install.py --agent claude --scope project --validate
python install.py --agent open-agent --scope project --target ./skills --force
```

同时提供 `install.ps1` 和 `install.sh`。

## 验证结果

0.7.0 版本质量基线已由 GitHub Actions 运行 `30525731965` 在 Ubuntu / Python 3.12 与精确锁定工具链下完成验证：

| Gate | 结果 |
|---|---:|
| 测试 | **240 通过；0 failure；0 error；0 skip** |
| 项目综合覆盖率 | **95.726%** |
| 分支覆盖率 | **92.708%** |
| 质量门槛 | **95% 行 / 90% 分支** |
| 关键 Mutation | **24 / 24 killed；0 survivor** |
| 性能基线 | **PASS** |
| 两次源码 ZIP | **逐字节一致** |
| wheel 与 sdist 隔离安装 | **PASS** |
| Ruff / Mypy / Bandit | **PASS** |
| 精确锁依赖审计 | **PASS；未发现已知漏洞** |

当前 `main` 提交由[精确主线证明工作流](.github/workflows/main-attestation.yml)独立验证。成功运行会发布名为 `exact-main-attestation-<提交 SHA>` 的产物，从而避免在被证明的提交内部写入自引用运行号。

仓库内 `docs/VALIDATION_EVIDENCE.json` 有意保留为 `preflight/PARTIAL`；与提交绑定的 PASS 证明由 CI 外部生成，避免在提交内部制造自引用 SHA。

## 机器可读证据与映射

- [README 审计报告](docs/README_AUDIT_REPORT.md)
- [能力覆盖矩阵](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [README—架构映射](docs/README_ARCHITECTURE_MAPPING.md)
- [验证证据](docs/VALIDATION_EVIDENCE.json)
- [交互式测试仪表板](docs/test-dashboard.html)
- [测试仪表板 SVG](docs/test-dashboard.svg)
- [最初需求审计 JSON](docs/ORIGINAL_REQUIREMENTS_AUDIT.json)
- [科研能力 AI 示意图谱](docs/VISUAL_ATLAS.zh-CN.md)

## 已知限制

- 不捆绑实时文献数据库、PDF 解析器和引用网络服务。
- 统计、因果、DOE 和 ML 属于方法合同与质量门，数值执行使用宿主工具。
- 绘图具备合同、导出校验和可运行示例，但不捆绑通用绘图守护进程。
- DOCX、PPTX 和 LaTeX 渲染依赖宿主能力。
- DFT、MD、FEM、CFD、流程模拟器、HPC 调度器、仪器和实验室机器人保持外部执行。
- 专利/FTO、医疗、安全和科研诚信的最终接受需要合格人员审批。
- handoff 不是完成计算；receipt 是执行证据，不是科学有效性的充分证明。

## 许可证与来源边界

TsaoSciResearcher 是原创的 **Apache-2.0** 实现，不捆绑上游源代码或提示词语料。公开项目仅用于架构和能力分类研究，详见 [THIRD_PARTY.md](THIRD_PARTY.md) 和 [references/source-map.md](references/source-map.md)。
