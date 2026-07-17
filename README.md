<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="920" />

  <p><strong>将科研问题、证据、数据、图表与结论组织为可验证、可追溯、可复现的研究工作流。</strong></p>

  <p>
    <a href="README_EN.md">English</a> ·
    <a href="docs/ARCHITECTURE.md">架构</a> ·
    <a href="capability-index/capabilities.md">158 项能力</a> ·
    <a href="docs/VALIDATION.md">验证模型</a> ·
    <a href="docs/COMPLIANCE.md">合规映射</a> ·
    <a href="docs/AUDIT_REPORT_V040.md">v0.4.0 审计</a> ·
    <a href="CHANGELOG.md">变更记录</a>
  </p>

  <p>
    <img alt="Version" src="https://img.shields.io/badge/version-0.4.0-0f766e" />
    <img alt="Capabilities" src="https://img.shields.io/badge/capabilities-158-2563eb" />
    <img alt="Workflows" src="https://img.shields.io/badge/workflows-15-7c3aed" />
    <img alt="Schemas" src="https://img.shields.io/badge/schemas-8-9333ea" />
    <img alt="Python" src="https://img.shields.io/badge/Python-3.10--3.13-3776AB?logo=python&logoColor=white" />
    <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-f59e0b" />
    <img alt="CI" src="https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg" />
  </p>
</div>

---

## 定位

**TsaoSciResearcher** 是面向自然科学与工程研究的证据优先 Agent Skill。它把宽泛目标转换为研究问题、证据图谱、实验与统计契约、Figure Contract、论文/报告和项目治理产物；需要真实 DFT、MD、FEM、CFD 或流程模拟时，生成结构化计算交接单，而不伪造计算结果。

它不是自动替代科研人员的“万能提示词”，也不把文件存在、测试通过或交接单生成误写为科学结论已经成立。

## 当前可验证组成

| 组成 | 数量/状态 | 含义 |
|---|---:|---|
| 工作流 | 15 | 渐进式路由到研究问题、综述、设计、分析、绘图、写作、治理等流程 |
| 能力记录 | 158 | 机器可检索的触发、输入、输出、风险、人工审批与计算交接元数据 |
| JSON Schema | 8 | 项目、证据、论断、图表、实验、工件、计算交接、能力记录契约 |
| Python | 3.10–3.13 | CI 覆盖 Linux、Windows、macOS |
| 真实计算 | 委托 | 必须由真实求解器执行并产生可验证工件 |

## 科研真实性边界

- `completed ≠ checked ≠ validated ≠ accepted`。
- “代码可运行”不等于数理逻辑正确；“单元测试通过”不等于测试充分。
- 能力目录表示可路由元数据，不表示外部数据库、实验仪器或求解器已经安装。
- 计算交接单是输入/方法/边界/收敛/验收契约，不是计算结果。
- 本地测试、PR CI、合并后 main CI、Release 资产校验是四个独立证据层。

## 15 个工作流

| Workflow | 目标 |
|---|---|
| `research-question` | 把宽泛主题收敛为可回答、可证伪问题 |
| `deep-research` | 检索、阅读、证据映射与冲突保留 |
| `systematic-review` | 协议化筛选、质量评价与证据综合 |
| `research-design` | 研究范式、技术路线、验证策略与阶段门 |
| `experiment-design` | 因子、响应、对照、重复、功效与质量控制 |
| `data-analysis` | 数据质量、统计、不确定性、因果与模型检查 |
| `scientific-figure` | Figure Contract、统计、单位、可追溯导出 |
| `scientific-writing` | 基于证据链的论文与学术修订 |
| `peer-review` | 方法、统计、图表、引用与复现性审查 |
| `technical-report` | 技术报告、阶段总结与决策材料 |
| `project-management` | 状态、依赖、里程碑、风险、决策与交付 |
| `patent-and-transfer` | 专利检索、地图、交底与 FTO 初筛 |
| `research-integrity` | 引用、数据、统计、图像和来源完整性检查 |
| `laboratory` | SOP、样品编码、仪器数据、QC 与 ELN 流程 |
| `computation-handoff` | 为真实多尺度计算生成严格任务契约 |

## 安全与正确性强化

v0.4.0 的核心变化包括：

- 管理型原子安装/卸载，拒绝删除或覆盖未受管目录；
- Zip Slip、绝对路径、符号链接、重复路径、压缩炸弹与展开大小防护；
- 字节级确定性 ZIP、外部 SHA-256 sidecar 与全新目录解压复验；
- 标准 JSON 有限数约束，拒绝 NaN/Infinity，状态文件采用原子替换；
- 项目状态转换、时间单调性、审批门与幂等性约束；
- Claim–Evidence 双向引用、支持/反驳互斥和孤立节点检查；
- Unicode 归一化路由、词边界、去重计分、稳定 tie-break 与输入上限；
- 属性测试、对抗测试、关键变异测试、性能基线和跨平台矩阵；
- GitHub Actions 最小只读权限与不可变提交 SHA 固定。

## 快速开始

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
```

安装到 Codex 用户目录：

```bash
python scripts/install.py --agent codex --scope user --validate
```

初始化可追溯科研项目：

```bash
python scripts/init_project.py \
  --name "PP conductive shielding" \
  --question "Which formulation and dispersion mechanisms control resistivity stability?" \
  --research-type mechanistic \
  --output .
python scripts/validate_project.py .tsao-research/project.yaml
```

路由任务与能力检索：

```bash
python scripts/route_task.py "检索聚丙烯半导体屏蔽料中炭黑选择性分散的文献"
python scripts/capability_search.py "炭黑 分散"
```

## 证据—论断契约

```bash
python scripts/validate_evidence.py .tsao-research/evidence.jsonl
python scripts/validate_claims.py .tsao-research/claims.jsonl --evidence .tsao-research/evidence.jsonl
python scripts/validate_citations.py .tsao-research/evidence.jsonl
```

物质性事实论断必须绑定证据；推断还必须显式记录假设。证据与论断引用必须双向一致，同一证据不能同时支持和反驳同一论断。

## Figure Contract

```bash
cp templates/figure-contract/figure-contract.json my-figure.json
python scripts/validate_figure.py my-figure.json
```

图表契约要求记录科学结论、Panel ID、数据源、变换、单位、坐标尺度、样本量、不确定性、统计方法、可访问性和原始数据/代码来源。

## 真实计算交接

```bash
python scripts/handoff_to_computation.py \
  --project .tsao-research \
  --out .tsao-research/computation-handoff.json \
  --question "How does carbon-black localization affect conductive percolation?" \
  --property "phase preference and percolation descriptors" \
  --scale multiscale \
  --method "molecular dynamics" \
  --expected-output "validated dispersion metrics"
```

真实计算必须由 TsaoSciComputation 或其他实际求解器执行，并以输入、版本、日志、收敛证据、输出和校验和完成闭环。

## 验证

```bash
python scripts/audit_repository.py
python -m compileall -q scripts tests
python -m pytest -q
python -m ruff check scripts tests
python scripts/run_mutation_smoke.py
python scripts/performance_smoke.py
python scripts/validate_release.py
```

完整分层说明见 [验证模型](docs/VALIDATION.md)。机器可读缺陷登记见 [`docs/audit/defects-v0.4.0.json`](docs/audit/defects-v0.4.0.json)。

## 许可证

Apache-2.0。第三方来源与许可证边界见 `THIRD_PARTY.md` 和 `references/source-map.md`。
