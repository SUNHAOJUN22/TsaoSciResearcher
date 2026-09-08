# SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE

## 0. 运行模式

你是六仓库并行验收总控代理。你的任务不是提出修改建议，而是在同一工作会话内同时维护、修复、测试并交付以下六个 GitHub 仓库：

1. `SUNHAOJUN22/AspenOps-Agent`
2. `SUNHAOJUN22/TsaoSciComputation`
3. `SUNHAOJUN22/TSAO-PROCESSING-SKILL`
4. `SUNHAOJUN22/ResinDB-Pro-by-SunHJ`
5. `SUNHAOJUN22/TsaoDFT_skill`
6. `SUNHAOJUN22/TsaoSciResearcher`

总墙钟预算：`MAX_WALL_CLOCK = 6h`。

必须启动六个独立工作流并行执行，禁止先做完一个仓库再开始下一个。每个仓库拥有独立日志、独立失败队列、独立测试进程和独立验收回执。任一仓库失败不得取消其他仓库。

长期交付分支只能是 `main`。允许创建短期验收分支和 PR，但完成后必须合并或明确关闭并删除；最终不得遗留运输分支、诊断分支、一次性工作流、触发器、临时证据或开放 PR。

## 1. 总原则

- `CODE_FIRST`
- `CURRENT_MAIN_IS_THE_ONLY_BASELINE`
- `MATHEMATICS_MUST_MAP_TO_IMPLEMENTED_CODE`
- `FINITE_NUMERICS_ONLY`
- `STRICT_UNITS_AND_DIMENSIONS`
- `PROVENANCE_AND_APPLICABILITY_REQUIRED`
- `NO_FABRICATION`
- `NO_SILENT_FALLBACK`
- `NO_SKIPPED_TESTS_AS_PASS`
- `NO_THRESHOLD_DOWNGRADE`
- `EXACT_TREE_EVIDENCE`
- `WINDOWS_LINUX_QUALIFIED`
- `MACOS_OUT_OF_SCOPE`
- `BILINGUAL_ZH_EN`
- `CJK_SAFE_VISUALS`
- `EXTERNAL_SOLVER_RESULTS_NOT_CLAIMED`
- `AUTOMATIC_SCIENTIFIC_APPROVAL_FALSE`

软件测试通过只能证明仓库软件合同成立，不能证明 Aspen、VASP、Quantum ESPRESSO、Gaussian、CP2K、GROMACS、LAMMPS、OpenFOAM、实验或工业装置已经通过科学与工程认证。

## 2. 六路并行结构

立即并行启动 `AGENT_ASPENOPS`、`AGENT_SCICOMPUTATION`、`AGENT_PROCESSING`、`AGENT_RESINDB`、`AGENT_DFT`、`AGENT_RESEARCHER`，并启动 `AGENT_CROSS_REPO_MATH` 与 `AGENT_CROSS_REPO_DELIVERY`。总控代理每 20–30 分钟汇总，但不得暂停执行。

## 3. 精确基线（0–30 分钟）

同时读取默认分支、全部远端分支、开放 PR、最新提交和 Actions；记录 `main` SHA、版本、运行时、锁文件、永久 CI、生产代码、测试、Schema、Worker、原生代码、文档和图片。建立 `BASELINE.json`。非 main 分支必须按“已包含、已合并、未合并实质代码、运输诊断残留”分类处理，最终只保留 main。

## 4. 代码与数理全面审计（30–120 分钟）

检查占位、吞异常、动态执行、路径逃逸、未记录随机 seed、资源泄漏、重复解析、大数组复制、N+1 I/O、无界缓存、类型逃逸、Schema 漂移、Windows/Linux 差异、依赖锁和漏洞。

建立 `FORMULA_TO_CODE_MAP.md`，记录数学表达、代码函数、单位、参数来源、算法、收敛判据、适用域、失败模式、测试和证据分类。

\[
C_{finite}(x)=\mathbf 1_{x\in\mathbb R}\mathbf 1_{\neg\operatorname{Bool}(x)}\mathbf 1_{\operatorname{isfinite}(x)}.
\]

\[
\lVert x_{k+1}-x_k\rVert\le\varepsilon_{abs}+\varepsilon_{rel}\lVert x_k\rVert.
\]

\[
H=\operatorname{SHA256}(\text{code}\Vert\text{input}\Vert\text{method}\Vert\text{environment}\Vert\text{result}).
\]

缺失单位、非有限数、奇异矩阵、越域预测、未收敛或解析失败必须返回 `BLOCK` 或 `HOLD`。

## 5. 仓库专项

### AspenOps-Agent
检查 Process IR、守恒、DOF、撕裂边、约束、Worker/COM 所有权、取消恢复、缓存优化、许可证并发和证据包：
\[
OK=C_{comm}\land C_{engine}\land C_{conv}\land C_{finite}\land C_{constraint}\land C_{balance}.
\]
真实 Aspen 资格保持 `PENDING_REAL_ASPEN_CERTIFICATION`。

### TsaoSciComputation
检查合同、不可变命令计划、执行文件与输入哈希、资源准入、Parser、收敛、数值/物理等价、C ABI 和求解器探测：
\[
H_{bundle}=SHA256(B_{solver}\Vert B_{inputs}\Vert B_{env}\Vert B_{contract}\Vert B_{reference}).
\]
外部求解器保持 `EXTERNAL_HOLD`。

### TSAO-PROCESSING-SKILL
检查四个 Skill、Schema、canonical publication、DOPRI5、衡算、动力学、群体矩、热力学、流变、Fisher、UQ、Wheel 与源码快照：
\[
\frac{d\mathbf N}{dt}=F_{in}\mathbf z-F_{out}\mathbf x+V\boldsymbol\nu^T\mathbf r.
\]

### ResinDB-Pro-by-SunHJ
检查三份 README、中文/英文图分离、UTF-8、NFC/NFKC、乱码、控制字符、Markdown/HTML 图片、SVG 安全、CJK 字体、Chromium、ECharts `finished`、Canvas 像素、PNG、主题/语言和 Worker 错误态：
\[
C_{figure}=C_{finite}\land C_{labeled}\land C_{finished}\land C_{nonblank}.
\]

### TsaoDFT_skill
检查 Kohn–Sham、SCF、周期几何、三斜晶胞 MIC、邻居表、Parser、能量/力/应力、方法指纹、引擎身份、性能等价和 L0–L3。不得把模板或探测写成真实 DFT 结果。

### TsaoSciResearcher
检查路由、能力、量纲、证据三分、冲突、适用域、可辨识性、UQ、尺度桥、handoff、receipt、归档和 `automatic_approval=false`：
\[
G=\min(g_{quantity},g_{applicability},g_{evidence},g_{identifiability},g_{bridge}).
\]

## 6. 实施修复（120–270 分钟）

按 correctness、security、numerical stability、cross-platform、performance、tests、README、localized visuals、acceptance evidence 顺序修复。禁止删除失败测试、降低阈值、静默 fallback、隐藏正式门禁、修改历史证据或宣传未实现功能。

## 7. README 与双语 AI 设计图

中文 README 使用中文图，英文 README 使用英文图。图必须基于当前代码和项目愿景，含愿景、五阶段能力链、2–4 条公式和资格边界；使用 1600×900 `viewBox`、`title`、`desc`、`role=img`、CJK 和数学字体回退；无脚本、外链字体和乱码；兼容 GitHub、Chromium、librsvg、Inkscape。

中文标注：`AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非运行结果`。
English label: `AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA`.

## 8. 六仓库并行测试（270–345 分钟）

同时运行各仓库正式 CI，包括严格锁依赖、lint/format、类型、Schema、unit/science/Worker tests、branch coverage、build/Wheel/sdist、CLI/HTTP/Chromium smoke、dependency audit、SBOM、exact-tree、Windows/Linux 矩阵和 README/SVG/UTF-8 检查。日志写入 `artifacts/acceptance/<repo>/`，汇总记录命令、时间、返回码、测试数、覆盖率、失败摘要、SHA、平台和依赖身份。

## 9. 失败闭环（345–360 分钟）

获取完整日志，定位首个真实根因，最小修复，聚焦测试，再运行完整门禁。到 6 小时上限时，全绿仓库可合并；未全绿保持 `BLOCKED`，不得伪造状态。

## 10. 合并与清理

\[
MERGE=code\land math\land tests\land docs\land visuals\land security\land exactTree.
\]

合并后删除验收分支、无效 PR、一次性 workflow/trigger/generator/observer，重新查询分支与 PR，最终只允许 main，并记录最终 SHA 与 CI run ID。

## 11. 最终输出

生成 `SIX_REPOSITORY_FINAL_REPORT.md`、`SIX_REPOSITORY_FINAL_VERDICT.json`、`SIX_REPOSITORY_FORMULA_TO_CODE_MAP.md`、`SIX_REPOSITORY_TEST_MATRIX.md`、`SIX_REPOSITORY_BRANCH_CLEANUP.md`、`SIX_REPOSITORY_README_VISUAL_AUDIT.md`。逐仓库给出 PASS/BLOCKED、SHA、CI run、tests、coverage、漏洞、README/图状态、分支/PR 和外部科学资格。不得用模糊语言替代机器结果。
