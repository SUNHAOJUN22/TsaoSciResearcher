<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先的科研工作控制层</strong></p>
  <p>科学问题 → 证据 → 设计 → 受控执行 → 验证 → 可复现交付物</p>

[English](README.md) · [文档](docs/index.md) · [架构](docs/ARCHITECTURE.md) · [验证](docs/VALIDATION.md) · [安全](SECURITY.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **正式版本 0.6.0** · Apache-2.0 · Python 3.10–3.13 · Windows、Linux、macOS

## 项目定位与真实性边界

TsaoSciResearcher 将科研请求转换为有边界、可追溯的合同与项目状态。没有可复核的执行凭据时，它不会把检索、实验、求解器、仪器或外部计算描述为“已经完成”。软件 PASS 不等于科学事实成立，也不等于最终接受。

## 已核实的仓库范围

| 项目 | 已核实数量 |
|---|---:|
| 能力合同总数 | **340** |
| AI for Science 目录具名合同 | **322** |
| 通用科研合同 | **158** |
| 具名计算与工程合同 | **164** |
| 通用领域占位合同 | **0** |
| 原生运行时/核心合同 | **18** |
| 带 Gate 科研工作流 | **15** |
| JSON Schema | **18** |
| 领域包 | **7** |
| 测试模块 | **32** |

```text
340 = 322 项具名 AI for Science 合同 + 18 项运行时/核心合同
322 = 158 项通用科研合同 + 164 项具名领域合同
```

能力合同定义路由、输入、输出、门禁、验证与委托边界，不代表外部科学引擎已经安装，更不代表已经执行。

## v0.6.0 核心架构

- **确定性双语路由**：有界 Unicode 规范化输入、否定意图识别与稳定决胜规则。
- **可追溯项目状态**：原子写入、有限锁、显式生命周期转换与 SHA-256 事件链。
- **科研质量门控**：Measurement Boundary、Structure–Property Planner、Causality Guard、Evidence Traceability。
- **受控计算交接**：常规文件与路径约束、输入哈希、收敛/UQ 要求和审批点。
- **Execution Receipt v2**：把真实外部运行绑定到 handoff、引擎、参数向量、时间、退出状态和输出哈希。
- **Reproducibility Capsule**：确定性 metadata/full ZIP，逐文件哈希、树摘要、安全校验和旁路校验和。
- **Validation Evidence 1.6**：源码树摘要、依赖锁摘要、工作流 attempt 和外部提交证明，避免自引用 SHA。
- **供应链控制**：固定 Action 提交、精确直接 CI 工具链、解析环境 `pip-audit`、确定性直接依赖 CycloneDX 1.6 SBOM、wheel/sdist/source ZIP 验证。
- **永久幂等自动化**：push CI、人工审计、每周健康检查和 Tag 发布；验证流程不写回仓库。

## 能力边界

| 能力 | 状态 |
|---|---|
| 路由、合同、状态、验证、凭据、胶囊和交付物治理 | 原生实现 |
| 文献检索、绘图和 Office 生产 | 使用宿主 Agent 提供的工具 |
| DFT、MD、FEM、CFD、流程模拟、HPC 和实验室执行 | 外部执行；必须有 handoff 与 receipt |
| 医疗、安全、法律/FTO、科研诚信和最终科学接受 | 合格人员审批 |

## 快速开始

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
python -m tsao_researcher route "设计一个可追溯的聚烯烃多尺度研究"
python -m tsao_researcher search "GROMACS 轨迹分析" --limit 10
```

初始化并验证项目：

```bash
python -m tsao_researcher init   --name "聚烯烃多尺度研究"   --question "加工历史通过哪些机制影响结构与性能？"   --research-type mechanistic --output .
python -m tsao_researcher verify .
```

生命周期：

```text
proposed → planned → running → completed → checked → validated → accepted
```

`accepted` 必须有审批记录；另支持 `rejected` 和 `superseded`。

## 外部执行凭据

receipt 命令只记录外部引擎真实运行后提供的证据，不负责启动引擎：

```bash
python -m tsao_researcher receipt record .   --handoff computation/job.json   --engine gromacs --engine-version 2026.1   --command gmx --command mdrun --exit-code 0   --output computation/result.dat   --started-at 2026-07-24T01:00:00Z   --finished-at 2026-07-24T01:10:00Z
python -m tsao_researcher receipt verify .
```

成功凭据要求退出码为 0 且至少有一个输出。验证会重新读取 handoff，并复算时间、文件大小和 SHA-256。详见 [执行凭据](docs/EXECUTION_RECEIPTS.md)。

## 可复现胶囊

```bash
python -m tsao_researcher capsule export . --mode metadata --output project-metadata.zip
python -m tsao_researcher capsule export . --mode full --output project-full.zip
python -m tsao_researcher capsule verify project-full.zip
```

metadata 模式排除原始 data/figures/artifacts 目录；full 模式包含所有满足上限的普通项目文件。两种模式均为确定性输出，并拒绝路径逃逸、符号链接、重复成员和哈希篡改。详见 [可复现胶囊](docs/REPRODUCIBILITY_CAPSULE.md)。

## 15 个科研工作流

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

## 验证与质量基线

仓库核心检查：

```bash
python scripts/sync_version.py --check
python scripts/validate_schemas.py
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/build_sbom.py --check
python scripts/build_validation_evidence.py --check
python scripts/build_test_dashboard.py --check
python scripts/build_research_quality_dashboard.py --check
python scripts/build_engineering_report.py --check
python scripts/generate_checksums.py --check
```

完整本地发布门禁：

```bash
mkdir -p artifacts
python -m pytest -q -p hypothesis.extra.pytestplugin --junitxml=artifacts/junit.xml
python -m pytest -q -p hypothesis.extra.pytestplugin -p pytest_cov \
  --ignore=tests/test_import_isolation.py --cov=tsao_researcher --cov-branch \
  --cov-report=json:artifacts/coverage.json
python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.reverse_order_plugin
TSR_TEST_ORDER_SEED=20260724 python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.random_order_plugin
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python -m pip_audit --strict
python scripts/run_mutation_smoke.py --json-out artifacts/mutation-results.json
python scripts/performance_smoke.py --json-out artifacts/performance.json
python scripts/check_quality_baseline.py
mkdocs build --strict
python scripts/package_release.py --out dist-a
python -m build --sdist --wheel --outdir dist-python
python scripts/validate_distribution.py dist-python
```

质量基线约束行覆盖率、分支覆盖率、**18/18** 个关键突变、性能和零 JUnit 失败；降低阈值必须在 Changelog 中明确说明。

## 自动化模型

- `ci.yml`：只读 push/PR 验证和四平台兼容性。
- `audit.yml`：只读、人工触发的完整审计。
- `nightly.yml`：每周检查依赖、覆盖率、突变、性能、文档和分发漂移。
- `release.yml`：仅 Tag 发布 source ZIP、wheel、sdist、SBOM、证据、PDF、校验和和外部证明。
- `cleanup-branches.yml`：维持仓库仅保留 `main` 的治理策略。

验证、审计和夜间流程均为幂等流程，不会生成仓库提交。

## 可视化与机器证据

![自动测试仪表板](docs/test-dashboard.svg)

- [可交互测试仪表板](docs/test-dashboard.html)
- [科研质量仪表板](docs/research-quality-dashboard.html)
- [科研质量 SVG](docs/research-quality-dashboard.svg)
- [科研质量示例](docs/SCIENTIFIC_QUALITY_EXAMPLES.json)
- [工程审计 PDF](docs/engineering-audit-report.pdf)
- [验证证据 1.6](docs/VALIDATION_EVIDENCE.json)
- [CycloneDX SBOM](docs/SBOM.cdx.json)
- [质量基线](docs/QUALITY_BASELINE.json)
- [质量历史](docs/QUALITY_HISTORY.json)
- [README 审计报告](docs/README_AUDIT_REPORT.md)
- [能力覆盖矩阵](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [设计 → 代码 → 测试映射](docs/README_ARCHITECTURE_MAPPING.md)

## 文档

- [架构](docs/ARCHITECTURE.md)
- [CLI 参考](docs/CLI.md)
- [验证模型](docs/VALIDATION.md)
- [科研质量](docs/SCIENTIFIC_QUALITY.md)
- [供应链](docs/SUPPLY_CHAIN.md)
- [发布流程](docs/RELEASE_PROCESS.md)
- [路线图](docs/ROADMAP.md)

## 已知限制

- 不内置外部科学引擎、仪器和数据库。
- handoff 不是完成的计算；receipt 是执行证据，不是科学正确性证明。
- SBOM 是清单，不是无漏洞保证。
- 覆盖率和突变分数衡量测试强度，不代表科学真理。
- 材料特定趋势和机制结论必须有项目证据、不确定度和适用域支撑。

## 安全、贡献和许可证

详见 [SECURITY.md](SECURITY.md)、[CONTRIBUTING.md](CONTRIBUTING.md)、[THIRD_PARTY.md](THIRD_PARTY.md) 和 [references/source-map.md](references/source-map.md)。TsaoSciResearcher 是 Apache-2.0 原创实现，受到公开科研 Agent 和科研工具项目启发，但不是其官方分支或替代品。
