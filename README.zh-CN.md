<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先的科研工作控制层</strong></p>
  <p>科学问题 → 证据 → 设计 → 分析/执行 → 验证 → 交付物</p>

[English](README.md) · [架构](docs/ARCHITECTURE.md) · [验证](docs/VALIDATION.md) · [安全](SECURITY.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **正式版本 0.5.3** · Apache-2.0 · Python 3.10–3.13 · Windows、Linux、macOS

## 项目定位

TsaoSciResearcher 将科研请求转化为有边界、可追溯、可验证的工作流，显式管理证据、项目状态、质量门控和人工审批。没有真实执行记录时，它不会把检索、实验、求解器、仪器或外部计算描述为“已经完成”。

## 已核实的仓库范围

以下数量来自仓库合同，并由验证工具检查。

| 项目 | 已核实数量 |
|---|---:|
| 能力合同总数 | **340** |
| AI for Science 目录具名合同 | **322** |
| 通用科研/兼容合同 | **158** |
| 具名计算与工程领域合同 | **164** |
| 通用领域占位合同 | **0** |
| 原生运行时/核心合同 | **18** |
| 带 Gate 工作流 | **15** |
| JSON Schema | **15** |
| 领域包 | **7** |
| 渐进加载参考文件 | **22** |
| 模板 | **13** |

```text
340 = 322 项具名 AI for Science 合同 + 18 项运行时/核心合同
322 = 158 项通用科研合同 + 164 项具名领域合同
```

能力合同描述路由、输入、输出、验证和委托边界，不代表外部科学计算引擎已经安装，更不代表计算已经执行。

## 已实现架构

- **单入口、渐进加载**：根 `SKILL.md` 先确定一个主工作流，再加载必要的详细参考资料。
- **确定性双语路由**：输入长度限制、缓存规则、否定意图识别和稳定优先级。
- **完整科研生命周期**：科学问题、证据、研究/实验设计、统计、绘图、写作、审稿、实验室治理、科研诚信、专利和项目管理。
- **可追溯项目状态**：原子写入、文件锁、生命周期转换和 SHA-256 事件链。
- **证据与论断控制**：Schema、双向链接、来源定位、引用检查和失败非零退出码。
- **科研绘图门控**：Figure Contract、单位/统计检查及 PNG、SVG、PDF、TIFF 导出验证。
- **受控计算交接**：输入校验和、路径约束、收敛/UQ 要求和人工审批点。
- **可重复工程验证**：仓库审计、静态分析、突变测试、顺序无关测试、性能门和逐字节一致发布。

## 可执行科研质量门控

`quality` 命令提供四类确定性检查：

| 门控 | 作用 |
|---|---|
| **Measurement Boundary** | 明确被测量、方法、样品、条件、单位、校准/参考、不确定度、适用域、排除项及可选追溯信息。 |
| **Structure–Property Planner** | 记录干预变量、结构、可测中介、响应、混杂因素、备择解释、验证、不确定度、尺度桥接、统计基础和守恒约束。 |
| **Causality Guard** | 区分相关性、机制一致推断与有边界的因果结论，并检测缺乏支持的中英文因果措辞。 |
| **Evidence Traceability** | 建立论断、证据 ID 与来源定位之间的关联，并阻止没有执行凭据的“已完成”表述。 |

```bash
python -m tsao_researcher quality examples/scientific-quality-check.json
```

这些能力将科研方法规则通用化，而不会把某一种材料体系的结论硬编码为普遍规律。统计物理可提供守恒、分布和不确定度约束，但项目结论仍必须受证据和适用域限制。

## 明确边界

| 能力 | 状态 |
|---|---|
| 科研编排、验证和交付物治理 | 原生实现 |
| 文献检索、绘图和 Office 生产 | 使用宿主 Agent 已提供的工具 |
| DFT、MD、FEM、CFD、流程模拟、HPC 和真实实验 | 通过 `computation-handoff` 交接 |
| 医疗、安全、法律/FTO、科研诚信和最终科学接受 | 必须由合格人员审批 |

科学计算引擎目录是生态集成目标，不是仓库内置求解器。

## 快速开始

### 安装

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
```

### 路由和搜索

```bash
python -m tsao_researcher route "设计一个可追溯的聚烯烃多尺度研究"
python -m tsao_researcher search "GROMACS 轨迹分析" --limit 10
python -m tsao_researcher search "非牛顿流" --domain cfd-particles-processing
```

### 初始化项目

```bash
python -m tsao_researcher init \
  --name "聚烯烃多尺度研究" \
  --question "加工历史通过哪些机制影响产品结构与性能？" \
  --research-type mechanistic \
  --output .
```

统一项目目录位于 `.tsao-research/`，包含科学问题、假设、证据、论断、决策、交付物、风险、审批、状态事件、数据、计算记录、图件、报告和协议。

### 推进和验证状态

```bash
python -m tsao_researcher transition . planned --reason "问题与计划已批准"
python -m tsao_researcher transition . running --reason "登记工作已启动"
python -m tsao_researcher verify .
```

```text
proposed → planned → running → completed → checked → validated → accepted
```

另支持 `rejected` 和 `superseded`；进入 `accepted` 必须有审批记录。

## 15 个工作流

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

每个工作流均包含人类可读政策、机器合同以及 entry、blocking、completion Gate。

## 自动验证

```bash
python scripts/validate_schemas.py
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/build_test_dashboard.py --check
python scripts/build_validation_evidence.py --check
python scripts/build_research_quality_dashboard.py --check
python scripts/build_engineering_report.py --check
python scripts/generate_checksums.py --check
python -m pytest -q -p hypothesis.extra.pytestplugin
python scripts/performance_smoke.py
```

CI 还执行 Windows、Linux、macOS 的 Python 兼容性测试、Ruff 格式/静态检查、严格 Mypy、Bandit、关键突变测试、逆序与固定随机种子测试、性能门和逐字节一致发布。

可重复发布检查：

```bash
VERSION="$(cat VERSION)"
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp "dist-a/TsaoSciResearcher-v${VERSION}.zip" \
    "dist-b/TsaoSciResearcher-v${VERSION}.zip"
```

## 测试与科研质量可视化

![自动测试仪表板](docs/test-dashboard.svg)

- [打开可交互测试仪表板](docs/test-dashboard.html)
- [查看静态测试仪表板](docs/test-dashboard.svg)
- [打开科研质量交互式仪表板](docs/research-quality-dashboard.html)
- [查看科研质量 SVG 图像报告](docs/research-quality-dashboard.svg)
- [查看机器可读科研质量示例](docs/SCIENTIFIC_QUALITY_EXAMPLES.json)
- [下载工程审计 PDF 报告](docs/engineering-audit-report.pdf)
- [查看机器可读验证证据](docs/VALIDATION_EVIDENCE.json)

仪表板是确定性生成产物，用于展示软件门禁和科研方法约束；它们不能代替科学审查，也不能证明外部任务已经执行。

## 设计和审计证据

- [README 审计报告](docs/README_AUDIT_REPORT.md)
- [能力覆盖矩阵](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [设计 → 代码 → 测试映射](docs/README_ARCHITECTURE_MAPPING.md)
- [机器可读 README 事实](docs/README_FACTS.json)
- [项目整合审计](docs/PROJECT_INTEGRATION_2026-07-23.md)
- [最新验证证据](docs/VALIDATION_EVIDENCE.json)

## 已知限制

- 不内置外部科学计算引擎、实验仪器和数据库。
- 计划中的计算交接不等于执行凭据。
- 科研质量门控可约束措辞和完整度，但不能单独建立科学事实。
- 材料特定趋势、晶相归属和机制结论必须有项目证据、不确定度和适用域支撑。

## 开发、安全与许可证

修改应保持确定性输出、跨平台路径、严格验证，并维护“计划/交接不等于执行”的真实性边界。详见 [SECURITY.md](SECURITY.md)、[CONTRIBUTING.md](CONTRIBUTING.md)、[THIRD_PARTY.md](THIRD_PARTY.md) 和 [references/source-map.md](references/source-map.md)。

TsaoSciResearcher 是 Apache-2.0 原创实现，受到公开科研 Agent 和科研工具项目启发，但不是它们的官方分支或替代品。
