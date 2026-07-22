<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="120" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>证据优先、全生命周期、可追溯的科研智能体平台</strong></p>
  <p>从科学问题、文献证据和实验设计，到统计分析、科研写作、跨尺度计算交接与项目审计。</p>
</div>

> **当前版本：0.5.1** ｜ [English README](README_EN.md) ｜ [能力目录](capabilities/v2/index.json) ｜ [架构说明](docs/ARCHITECTURE.md) ｜ [安全策略](SECURITY.md)

## 为什么存在

科研智能体真正困难的部分，不是生成一段听起来像论文的文字，而是保持完整的逻辑链：

`问题 → 假设 → 证据 → 方法 → 数据 → 检查 → 验证 → 结论 → 交付物`

TsaoSciResearcher 把这条链建模为可检查的工作流、能力契约、Schema、项目状态和计算交接文件。它优先保证：

- **证据真实性**：重要事实必须能回到论文、数据、实验记录或计算产物；
- **状态不混淆**：`completed` 不等于 `validated`，`validated` 也不等于 `accepted`；
- **物理与数理一致性**：单位、守恒、统计假设、收敛性和不确定度均是阻断性检查；
- **跨尺度可追溯**：电子结构、分子/链结构、介观形貌、连续体、反应器和产品性能之间保留参数来源；
- **不伪造执行**：没有真实运行记录时，只能给出计划或交接，不能声称实验、检索或模拟已经完成。

## 能力概览

| 组件 | 数量 | 用途 |
|---|---:|---|
| v2 能力契约 | **340** | 通用科研能力与计算/工程领域能力，含输入输出、验证器、失败模式和人工审批点 |
| 兼容能力目录 | **158** | 保留 v0.4 调用、脚本与外部集成兼容性 |
| 主工作流 | **15** | 科学问题、深度研究、系统综述、实验、数据、写作、专利、实验室、计算交接等 |
| JSON Schema | **15** | 8 个成熟兼容 Schema + 7 个 v2 路由、状态、工件、工作流和交接 Schema |
| 领域包 | **7** | 聚合物/催化、计算化学、MD/多尺度、FEM、CFD、过程数字孪生、HPC 复现 |

### 15 个主工作流

- `research-question`：科学问题、可证伪假设和决策边界；
- `deep-research`：可审计检索、证据抽取、冲突综合和停止规则；
- `systematic-review`：PRISMA、协议、筛选、偏倚与 Meta 分析；
- `research-design`：端到端研究架构、变量、里程碑和验证路线；
- `experiment-design`：对照、随机化、样本量、DOE 和测量计划；
- `data-analysis`：清洗、统计、因果、机器学习、不确定度和可视化；
- `scientific-figure`：出版级图表、机理图、数据映射和导出合同；
- `scientific-writing`、`peer-review`、`technical-report`：论文、审稿、技术报告；
- `project-management`、`patent-and-transfer`、`research-integrity`：治理、专利和诚信；
- `laboratory`：SOP、仪器、校准、样品和实验室质量控制；
- `computation-handoff`：DFT、MD、FEM、CFD、Aspen/过程模拟等真实计算的受控交接。

## 架构

```text
用户任务
   │
   ▼
Unicode 规范化 + 双语规则路由（缓存、正/负触发、确定性优先级）
   │
   ├── 主工作流 WORKFLOW.md
   ├── v2 工作流合同 workflow.yaml.json
   └── Gate：entry / blocking / completion
   │
   ▼
340 项能力目录 + 7 个领域包
   │
   ▼
项目状态 .tsao-research/
   ├── project.yaml
   ├── state/events.jsonl（SHA-256 哈希链）
   ├── evidence / claims / decisions / approvals
   └── data / computation / artifacts / figures / reports
   │
   ▼
验证、人工审批或受控计算交接
```

运行内核位于 [`tsao_researcher/`](tsao_researcher/)；兼容且更细粒度的研究脚本位于 [`scripts/`](scripts/)；工作流位于 [`workflows/`](workflows/)。

## 环境要求

- Python **3.10–3.13**；
- 核心依赖：PyYAML、jsonschema；
- 可选绘图依赖：Matplotlib、NumPy；
- Windows、Linux、macOS 均纳入 CI 兼容矩阵。

## 最快开始

### 1. 安装运行包

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
```

只检查 Skill 安装位置而不写入：

```bash
python scripts/install.py --agent codex --scope user --dry-run --validate
```

正式安装到受管理目录：

```bash
python scripts/install.py --agent codex --scope user
```

安装器使用暂存目录、原子替换、唯一备份和回滚；不会删除未标记为 TsaoSciResearcher 管理的目录。

### 2. 路由科研任务

```bash
python -m tsao_researcher route "请对聚烯烃催化—链增长—形貌—反应器—性能进行全尺度研究设计"
```

输出包含：主工作流、次工作流、置信度、命中触发词、是否需要澄清、是否需要人工审批，以及最小加载计划。

### 3. 搜索 340 项能力

```bash
python -m tsao_researcher search "polymer molecular dynamics" \
  --domain molecular-dynamics-multiscale \
  --limit 10
```

能力目录按内容哈希/文件状态缓存；每次调用返回防御性副本，调用方修改不会污染共享缓存。

### 4. 初始化可追溯项目

```bash
python -m tsao_researcher init \
  --name "Polyolefin multiscale study" \
  --question "How do active-site kinetics and chain statistics propagate to reactor and product properties?" \
  --output .
```

状态目录：

```text
.tsao-research/
├── project.yaml
├── state/events.jsonl
├── registry/
├── literature/
├── data/
├── computation/
├── artifacts/
├── figures/
├── reports/
└── protocols/
```

推进状态：

```bash
python -m tsao_researcher transition . planned --reason "question and evidence plan approved"
python -m tsao_researcher transition . running --reason "registered work started"
python -m tsao_researcher verify .
```

合法状态链：

```text
proposed → planned → running → completed → checked → validated → accepted
```

也可以进入 `rejected` 或 `superseded`。进入 `accepted` 必须记录人工审批。每次变更使用互斥锁、原子文件替换和 SHA-256 事件链；篡改历史记录会被 `verify` 检出。

## 计算与工程交接

TsaoSciResearcher 可以设计、审查和解释计算研究，但不会假装运行外部求解器。真实 DFT、MD、FEM、CFD、Aspen、数字孪生或 HPC 作业需要结构化交接。

Python 示例：

```python
from pathlib import Path

from tsao_researcher import create_handoff, initialize

root = initialize(
    "Polymer process model",
    "Which kinetic and transport parameters control molecular-weight distribution?",
    ".",
)
Path(root / "data/feed.json").write_text('{"ethylene": 1.0}\n', encoding="utf-8")

handoff = create_handoff(
    root,
    "computation/process-handoff.json",
    "Which kinetic and transport parameters control molecular-weight distribution?",
    "molecular-weight distribution",
    "process-kinetics-digital-twin",
    ["population balance", "dynamic reactor model"],
    ["data/feed.json"],
)
```

交接文件记录输入 SHA-256、候选方法、收敛检查、不确定度、物理验证、验收标准和人工审批点。路径逃逸、符号链接输入、占位问题或“ready 但无验证输入”会被拒绝。

## 领域包

- [催化、聚合物与复合材料](domain-packs/catalysis-polymers-composites/README.md)
- [计算化学与材料](domain-packs/computational-chemistry-materials/README.md)
- [分子动力学与多尺度](domain-packs/molecular-dynamics-multiscale/README.md)
- [有限元与多物理场](domain-packs/fem-multiphysics/README.md)
- [CFD、颗粒与加工](domain-packs/cfd-particles-processing/README.md)
- [过程动力学与数字孪生](domain-packs/process-kinetics-digital-twin/README.md)
- [HPC 与可复现计算](domain-packs/hpc-reproducibility/README.md)

每个领域包均包含方法选择、验证检查、结果解释和图形指南。聚合物/催化领域把统计热力学、链统计与不确定度作为跨尺度一致性基础，同时保持工艺、反应器与产品性能为工程主线。

## 证据与科研诚信

核心原则：

1. 不伪造论文、DOI、页码、数据、图像、实验或软件访问；
2. 引文必须支持具体论断，而不是“主题相关”即可；
3. 事实、推断、假设、外推和建议必须区分；
4. 保留相反证据、空结果、失败验证和限制；
5. 统计方法由数据生成过程和假设决定，而不是由期望结论决定；
6. 医疗、安全、科研不端、FTO 和高影响决策要求合格人员复核。

详见 [`workflows/research-integrity/WORKFLOW.md`](workflows/research-integrity/WORKFLOW.md) 和 [`SECURITY.md`](SECURITY.md)。

## 性能与可靠性设计

- 路由规则、JSON 和能力目录按文件状态缓存；
- 规则在首次加载时预编译，避免每次调用重复构造正则；
- 能力检索使用预构建规范化 token 索引；
- 校验和采用流式读取，不把大文件一次性载入内存；
- JSON/JSONL 有大小与记录数上限，拒绝 NaN/Infinity；
- 项目变更使用有界锁等待、原子替换和 `fsync`；
- 发布 ZIP 固定时间戳、排序、权限和压缩参数，可重复构建；
- ZIP 解包检查路径穿越、符号链接、重复成员和解压炸弹。

运行性能烟雾测试：

```bash
python scripts/performance_smoke.py --json-out artifacts/performance.json
```

阈值是回归保护线，不是跨硬件的营销基准。任何性能提升百分比都必须来自同一环境下的实际前后测量。

## 开发与验证

```bash
python -m pip install -r requirements-dev.txt
python scripts/audit_repository.py
python scripts/generate_checksums.py --check
python scripts/build_capability_index.py --check
python scripts/run_tests.py --jobs 4 --module-timeout 120
python -m pytest -q  # 单进程交叉模块状态污染回归
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python scripts/run_mutation_smoke.py --jobs 4
python scripts/performance_smoke.py
```

确定性发布：

```bash
python scripts/package_release.py --out dist
python scripts/validate_release.py
```

CI 采用分层策略：跨操作系统/关键 Python 版本做兼容性烟雾测试；完整回归、逆序/随机顺序、静态类型、安全、变异、性能和可重复打包分别只在必要环境运行，避免把同一套昂贵测试无意义地重复十几次。

## 目录

```text
TsaoSciResearcher/
├── tsao_researcher/       # v2 运行包与 CLI
├── scripts/               # 审计、安装、兼容路由、验证、发布与性能工具
├── capabilities/v2/       # 340 项能力契约
├── capability-index/      # 158 项兼容目录
├── workflows/             # 15 个工作流、Gate 和机器合同
├── domain-packs/          # 7 个计算/工程领域包
├── schemas/               # 兼容与 v2 JSON Schema
├── templates/             # 项目、证据、实验、图形、报告模板
├── references/            # 方法与治理参考说明
├── tests/                 # 单元、属性、安全、隔离、发布和性能回归
└── .github/workflows/     # 分层 CI 与单 main 分支治理
```

## 常见问题

### 路由返回 `unknown`

任务没有命中足够具体的正向触发词，或多个工作流同分。补充对象、目标输出和是否需要真实执行。

### 为什么不自动运行 GROMACS、DFT 或 Aspen？

仓库不假设外部商业软件、许可证、HPC 资源或求解器已安装。它生成可验证的执行合同和输入清单；真实执行必须发生在已授权环境中。

### 为什么同时保留 340 和 158 两套能力目录？

340 项目录是正式 v2 能力面；158 项目录用于兼容既有脚本、Skill 调用和外部集成。新开发优先使用 `capabilities/v2/`。

### 是否能保证科研结论正确？

不能。软件可以强制记录证据、假设、状态、收敛与审批，但不能替代领域专家、真实实验、可靠数据和同行评议。

## 贡献、许可与引用

- 贡献流程：[CONTRIBUTING.md](CONTRIBUTING.md)
- 行为准则：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 安全报告：[SECURITY.md](SECURITY.md)
- 许可证：[Apache-2.0](LICENSE)
- 第三方与来源边界：[THIRD_PARTY.md](THIRD_PARTY.md)
- 引用元数据：[CITATION.cff](CITATION.cff)

本仓库的正式开发分支为 **`main`**。历史功能分支在能力吸收、验证和合并完成后自动清理，避免多个“看似最新版”长期并存。
