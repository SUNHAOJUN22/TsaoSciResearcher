# 最初功能定义落实审计

本审计以最初的 `TsaoSciResearcher Design(2).docx`、322 项 AI for Science Skill 目录和当前 v0.7.0 源码为对象。判断严格区分：**原生确定性实现、科研控制/合同层、宿主工具执行、外部计算执行和人工审批**。

## 总结

- Excel 中 **322/322** 个 Skill Slug 已进入机器可读能力目录，缺失 **0**。
- 代码另增加 **19** 个运行时/治理能力，总能力合同 **341**。
- 实现层级：原生科研/运行时 **147**，外部计算委托 **170**，强制人工审核 **23**。
- 最初定义的目录、路由、项目状态、Schema、验证器、安装、打包和计算交接已经落实。
- 实时数据库、PDF 解析、统计/DOE 求解、Office 渲染、图像取证、仪器驱动和科学求解器不在仓库内执行；它们通过宿主工具、外部计算或人工审核完成。

## 逐项审计

| 编号 | 最初定义领域 | 结论 | 基于实际代码的判断 | 主要证据 |
|---|---|---|---|---|
| A01 | 综合科研方法学中枢 | **完整实现** | 已建立单入口 Skill、15 个科研工作流、341 个能力合同和统一状态/验证层。 | `SKILL.md`<br>`workflows/`<br>`capabilities/v2/index.json`<br>`tsao_researcher/` |
| A02 | 单入口路由与渐进加载 | **完整实现** | 根 SKILL 只负责路由、门控和按需加载；v2 路由器含正向、负向和优先级规则。 | `SKILL.md`<br>`routing/router-rules-v2.json`<br>`tsao_researcher/router.py` |
| A03 | 科学问题、假设与研究范式 | **控制层完整，执行依赖宿主** | 问题类型、问题树、假设与研究设计合同已实现；科学内容仍由 Agent 基于用户证据形成，不是固定算法自动发现。 | `workflows/research-question/`<br>`templates/research-question/`<br>`references/research-paradigms/` |
| A04 | 深度研究与文献证据 | **方法/合同已实现，执行依赖宿主** | 检索策略、证据记录、文献矩阵、引用/论断检查已实现；实时数据库连接、PDF 解析、去重与引用网络依赖宿主工具。 | `workflows/deep-research/`<br>`templates/literature-matrix/`<br>`scripts/validate_citations.py`<br>`scripts/validate_claims.py` |
| A05 | 系统综述与 PRISMA | **方法/合同已实现，执行依赖宿主** | 系统综述工作流、纳排标准和证据门控已实现；自动筛选 UI、PRISMA 图和 Meta 分析计算引擎未内置。 | `workflows/systematic-review/`<br>`references/literature/systematic-review.md` |
| A06 | 研究设计与实验设计 | **控制层完整，执行依赖宿主** | 变量、对照、随机化、盲法、功效、DOE、质量控制和风险合同已覆盖；数值 DOE/功效计算由宿主统计工具执行。 | `workflows/research-design/`<br>`workflows/experiment-design/`<br>`templates/experiment-protocol/`<br>`references/experimental-design/` |
| A07 | 数据统计、因果与机器学习 | **方法/合同已实现，执行依赖宿主** | 52 个数据分析合同和质量门已建立；仓库不捆绑 pandas/scipy/statsmodels/ML 训练流水线，实际分析由宿主工具执行。 | `workflows/data-analysis/`<br>`references/statistics/`<br>`tsao_researcher/scientific_quality.py` |
| A08 | 科研绘图 | **控制层完整，执行依赖宿主** | Figure Contract、450 DPI/矢量导出规范、格式验证和可运行 Matplotlib 示例已实现；通用绘图执行仍使用宿主 Python/R 工具。 | `workflows/scientific-figure/`<br>`schemas/figure-contract.schema.json`<br>`scripts/validate_figure.py`<br>`scripts/validate_export.py`<br>`examples/scientific_figure/plot_example.py` |
| A09 | 科研写作与出版 | **方法/合同已实现，执行依赖宿主** | 论文、技术报告、审稿回复和专利交底模板已实现；DOCX/PPT/LaTeX 渲染和期刊投稿接口由宿主工具完成。 | `workflows/scientific-writing/`<br>`workflows/technical-report/`<br>`templates/manuscript/`<br>`templates/technical-report/`<br>`templates/review-response/` |
| A10 | 同行评审与科研诚信 | **控制层完整，执行依赖宿主** | 引用、论断、统计、可复现性和真实性门控已实现；图像重复/拼接的计算机视觉检测器未捆绑。 | `workflows/peer-review/`<br>`workflows/research-integrity/`<br>`references/integrity/`<br>`tsao_researcher/scientific_quality.py` |
| A11 | 项目状态、审计与知识管理 | **完整实现** | 统一 .tsao-research 目录、九类状态、哈希事件链、决策/审批/风险/产物登记和并发锁已实现。 | `tsao_researcher/state.py`<br>`schemas/v2/project.schema.json`<br>`schemas/v2/state-event.schema.json`<br>`docs/REPRODUCIBILITY_CAPSULE.md` |
| A12 | 计算任务交接 | **交接与验证完整，真实计算外部执行** | 标准 handoff、输入哈希、边界条件、收敛/UQ 要求、Execution Receipt v2 和结果校验已实现；求解器与网络传输层不捆绑。 | `tsao_researcher/handoff.py`<br>`tsao_researcher/receipts.py`<br>`scripts/handoff_to_computation.py`<br>`schemas/v2/handoff.schema.json`<br>`schemas/v2/execution-receipt.schema.json` |
| A13 | 能力索引 | **完整实现** | Excel 的 322 个 Skill Slug 全部进入 v2 目录，缺失 0；另增加 19 个运行时核心能力，总计 341。 | `capabilities/v2/capabilities.json`<br>`capabilities/v2/index.json`<br>`tests/test_design_compliance.py` |
| A14 | 确定性脚本与 Schema | **完整实现** | 37 个脚本、18 个 Draft 2020-12 Schema、非零错误码、结构/证据/论断/图件/安装/打包验证均已实现。 | `scripts/`<br>`schemas/`<br>`tests/test_schemas.py`<br>`tests/test_repository_audit.py` |
| A15 | 安装与平台兼容 | **完整实现** | 支持 Codex、Claude Code、Open Agent Skills，用户级/项目级安装，PowerShell 与 shell，以及全部要求的安装参数。 | `install.py`<br>`install.ps1`<br>`install.sh`<br>`tests/test_install.py` |
| A16 | 科学引擎、仪器与实验室自动化 | **按设计保持外部** | 能力合同覆盖 DFT、MD、FEM、CFD、流程模拟、HPC 和仪器分析，但不捆绑 32 个外部引擎、设备驱动或真实执行。 | `domain-packs/`<br>`workflows/computation-handoff/`<br>`THIRD_PARTY.md`<br>`references/source-map.md` |
| A17 | 许可证与第三方边界 | **完整实现** | 核心实现为 Apache-2.0；未捆绑上游代码/提示词，受限许可证仅作为架构参考并在 THIRD_PARTY 中记录。 | `LICENSE`<br>`NOTICE`<br>`THIRD_PARTY.md`<br>`references/source-map.md` |
| A18 | 测试、发布与可复现性 | **完整实现** | 最终验证为 262 项测试、项目覆盖率 95.406%、分支覆盖率 91.458%、24/24 Mutation、确定性 ZIP、wheel/sdist 安装验证。 | `docs/QUALITY_BASELINE.json`<br>`scripts/run_tests.py`<br>`scripts/package_release.py`<br>`scripts/validate_distribution.py` |

## 结论

TsaoSciResearcher 已经实现为一个**证据优先、可恢复、可审计、可复现的科研控制层**，不是内置所有数据库和科学求解器的单体平台。最初设计中要求的完整科研生命周期被落实为路由、工作流、能力合同、项目状态、验证门、交接协议和可复现交付；真实检索、统计计算、绘图、Office 生产、实验和多尺度求解继续由可验证的外部工具执行。
