# TsaoScience

**从科研问题、计算与聚合过程模型，到材料数据和可追溯结果的统一工作仓库。**

版本：`astra-pro-2 / 1.0.0a2`。唯一维护仓库：`SUNHAOJUN22/TsaoSciResearcher`。

这不是七个独立产品的目录集合。研究路由、计算路由、原有领域实现、统一任务图、量纲检查、执行边界、事件账本与 ResinDB 界面在同一个源码树内协同工作。领域源码、方法资料和历史测试保留；新的工作流通过固定适配器调用原实现，不复制其科学算法。

## 运行

Python 3.11 及以上；前端沿用 Node.js 22。从本仓库根目录运行：

```bash
python -m pip install -e '.[test]'
python -m tsao_science doctor
python -m tsao_science catalog --query kinetics
python -m tsao_science route "聚合动力学参数识别与材料性能研究"
python -m tsao_science plan examples/poe-reference-workflow.json
python -m tsao_science demo --workdir work/demo
python -m tsao_science run examples/poe-reference-workflow.json --workdir work/project --execute-local
```

`plan` 不执行计算。`run` 需要显式授权本地参考计算。`demo` 的选择只授权固定的合成参考案例：研究路由 → 计算路由 → 原 POE 一阶模型 → 参数回归 → 材料观测元数据。它不代表实验测量、真实 DFT、Aspen 求解或材料放行。

结果写入唯一运行目录，关联任务输入摘要、输出摘要、代码身份和事务化事件账本。校验结果文件：

```bash
python -m tsao_science verify work/demo/<run-id>/result.json --ledger work/demo/evidence.sqlite3
```

## 统一界面

```bash
python -m tsao_science serve
# 在另一终端运行：
cd apps/resindb
npm ci
npm run dev
```

ResinDB 顶部的“统一科研工作台”读取同源 `/api/science/status`，并向 `/api/science/plan` 提交参考计划。浏览器与 Python 使用同一版本的任务摘要协议；摘要不一致时拒绝接收。网关只绑定回环地址，不提供求解器执行或 AI 转发接口。原有 AI 服务仍要求独立部署的同源 `/api/ai/proxy`。

## 分层与所有权

| 层 | 目录 | 唯一职责 |
|---|---|---|
| 共享基础与任务引擎 | `tsao_science/`、`contracts/` | 严格 JSON、物理量、任务依赖、固定适配器、证据身份、状态与入口 |
| 研究设计 | `components/research/` | 科研路由、研究规约、证据和结论检查 |
| 通用计算 | `components/computation/` | 计算路线、原有执行和资源规约 |
| DFT 领域 | `components/dft/` | 结构、专业引擎解析、方法与计算资格 |
| 聚合与加工 | `components/processing/` | 原有 EPDM、POE 和通用过程模型 |
| 流程软件控制 | `components/aspen/` | Aspen/HYSYS 原有隔离与运行状态采集 |
| 数据与人工入口 | `apps/resindb/` | 材料数据、分析界面、受控 AI 外发和统一计划预览 |
| 可选推理方法 | `skills/reasoning/` | 原有第一哲学、第一性原理及显式选择的 TRIZ |

日常开发只有一个 Git 仓库、一个根入口、一套集成验收。模块中的旧工作流和版本说明是保留的来源记录，不是独立发布入口，也不能替代根目录的本次 CI。

## 原有高级能力仍可调用

```bash
python -m tsao_science component research -- math
python -m tsao_science component computation -- route "DFT to kinetics"
python -m tsao_science component aspen -- demo
python -m tsao_science component processing -- doctor --root . --profile core
python -m tsao_science component dft -- script scripts/validate_catalog.py
python -m tsao_science component reasoning -- script open-deep-mind/scripts/validate_ledger.py <ledger.json>
```

兼容命令在相应组件目录运行，相对文件路径以该目录为基准。组件原有许可证、运行授权和外部执行门不被此入口绕过。新任务引擎只登记已经有固定本地桥接的能力；保留的完整能力目录不被虚报为全部获得了真实求解器资格。

## astra-pro-2：共享实现，而非目录搬运

`contracts/components.json` 是七个领域的唯一目录与归属注册表。`catalog` 从原始能力目录动态读取、命名空间化和检索，不再手工复制一份能力清单。当前固定来源生成 565 条目录记录；这些是方法或功能说明，**不等于 565 个可执行适配器**。统一任务引擎仍明确登记 8 个本地参考适配器和 2 个外部执行 HOLD 项。

Aspen 与 Computation 原哈希入口已转用同一共享实现，保持各自历史 JSON 字节格式和既有摘要兼容。跨语言任务摘要 `tsao.c14n/1` 仍是另一份明确版本的协议，不与旧 JSON 摘要混用。Aspen 缓存读取采用共享严格 JSON；Processing 在换算、求和后检查有限性，不能让溢出或 NaN 通过物料衡算。

每个统一任务的输入和输出均使用 `contracts/payloads.json`。计划阶段允许尚未解析的任务引用，执行前必须将其解析并重新验证；领域输出也必须符合合同。由参考模型或假设派生的数值不能在下游改标为实测或真实模拟。控制依赖与数据来源依赖分开，不强迫无关的前置路由改变观测来源。

新增 `tsao.run/2` 记录绑定完整工作流、解析后的输入、输出、领域验证和数据来源。`verify` 不仅核对自摘要，也核对任务依赖、输入引用、结果合同与资格状态。`--ledger` 进一步以只读方式核对运行账本及事件；缺失账本不会被创建。自洽性验证不是来源认证，记录中的实测声明仍需独立原始证据。

第二个可执行示例使用原 DFT 邻居算法计算合成结构，再生成参考类型的材料观测：

```bash
python -m tsao_science plan examples/structure-reference-workflow.json
python -m tsao_science run examples/structure-reference-workflow.json --workdir work/structure --execute-local
```

两个示例由 `contracts/examples.json` 统一供 CLI/网关使用。ResinDB 不再内置另一份示例，而是从网关读取；“验证运行记录”可导入本地 `result.json`，显示自洽性、领域结果和材料观测，既不自动写入实测数据库，也不赋予科学批准。

astra-pro-1 修复的 Aspen 状态、AI 发送快照、DFT 类型和提前验收、小转化率、研究设计否定语义、论证记录及 Windows 字节边界继续保留。原文件映射见 `migration/source-map.json`；累计变更摘要见 `migration/patches.json`。

## 验证与边界

```bash
python tools/verify_workspace.py
python -m pytest tests
python tools/qualify.py --profile extended
```

根 CI 在 Linux/Windows 上执行根集成和扩展的原有物理量、缓存、哈希、科研路由、回执、数值基准、DFT 动力学及聚合模型回归，另执行 DFT 严格类型与前端类型、完整 Vitest、构建和外发检查。每次运行使用新证据目录并解析真实 JUnit 计数；最终软件回执只在所有必需作业完成后生成。完整的原仓库测试与专用硬件测试仍保留。根集成通过不等于每项旧验收程序在重构后都已重新完成；状态以本次回执的实际执行清单为准，禁止沿用旧统计数字冒充本次结果。

`execution`、数值有效性、`scientific_approval` 和分发许可分开记录。软件成功、结构合法或摘要一致，不能自动升级为科学验证、独立批准或实际外部执行。

受控来源元数据保持原分类。原 Processing 分发策略仍为唯一分类判据；未获相应批准前不生成公开的全量 wheel、sdist、源码发布包或包含受控元数据的发布附件。根 editable 安装用于这个源码工作空间，独立安装的核心 wheel 不包含完整领域工作空间。

## 许可与迁移

新集成代码采用根目录 Apache-2.0 许可；原模块保留各自 LICENSE、NOTICE、署名及第三方例外，不能统一改写其授权。详见 `NOTICE.md`、`docs/ARCHITECTURE.md`、`docs/MIGRATION.md` 与 `docs/VALIDATION.md`。

## 旧仓库对象与维护主线

这里只有一个完整代码维护仓库。六个旧库 `main` 已是迁移入口并保留回滚历史；**REDIRECT_ONLY 不等于 GitHub Archived，也不等于删除仓库对象**。当前连接没有仓库管理写接口，本轮没有声称归档或删除成功。

`tools/archive_legacy_repositories.py` 是未自动执行的所有者工具：默认仅审计；显式 `--archive` 时先验证全部六个旧库仍为正确迁移入口，再通过本地已授权 GitHub CLI 归档并逐一回读。它从不删除仓库、从不处理凭据，不对主仓库执行归档。归档仍保留仓库对象。
