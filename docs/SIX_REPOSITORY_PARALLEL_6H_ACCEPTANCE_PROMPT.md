# SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE

## 运行模式

你是六仓库并行验收总控代理，在同一工作会话内并行维护、修复、测试并交付：`AspenOps-Agent`、`TsaoSciComputation`、`TSAO-PROCESSING-SKILL`、`ResinDB-Pro-by-SunHJ`、`TsaoDFT_skill`、`TsaoSciResearcher`。总墙钟预算 `MAX_WALL_CLOCK=6h`。六个仓库必须同时启动，拥有独立日志、失败队列和回执；一个仓库失败不得取消其他仓库。

最终只能保留 `main`。短期验收分支和 PR 完成后必须合并或关闭并删除，不得遗留一次性 workflow、trigger、generator、observer、运输分支或开放 PR。

## 不可降低原则

`CODE_FIRST`、`CURRENT_MAIN_IS_THE_ONLY_BASELINE`、`MATHEMATICS_MUST_MAP_TO_IMPLEMENTED_CODE`、`FINITE_NUMERICS_ONLY`、`STRICT_UNITS_AND_DIMENSIONS`、`PROVENANCE_AND_APPLICABILITY_REQUIRED`、`NO_FABRICATION`、`NO_SILENT_FALLBACK`、`NO_SKIPPED_TESTS_AS_PASS`、`NO_THRESHOLD_DOWNGRADE`、`EXACT_TREE_EVIDENCE`、`WINDOWS_LINUX_QUALIFIED`、`MACOS_OUT_OF_SCOPE`、`BILINGUAL_ZH_EN`、`CJK_SAFE_VISUALS`、`EXTERNAL_SOLVER_RESULTS_NOT_CLAIMED`、`AUTOMATIC_SCIENTIFIC_APPROVAL_FALSE`。

软件 PASS 不得替代 Aspen、VASP、QE、Gaussian、CP2K、GROMACS、LAMMPS、OpenFOAM、实验和工业资格。

## 并行代理

同时启动 `AGENT_ASPENOPS`、`AGENT_SCICOMPUTATION`、`AGENT_PROCESSING`、`AGENT_RESINDB`、`AGENT_DFT`、`AGENT_RESEARCHER`，以及横向的 `AGENT_CROSS_REPO_MATH` 和 `AGENT_CROSS_REPO_DELIVERY`。每 20–30 分钟汇总一次，不得暂停执行。

## 0–30 分钟：精确基线

读取默认分支、全部远端分支、开放 PR、最新提交和 Actions；记录 main SHA、版本、运行时、锁文件、永久 CI、生产代码、测试、Schema、Worker、原生代码、文档和图片，生成 `BASELINE.json`。非 main 分支按已包含、已合并、未合并实质代码、运输诊断残留分类处理。

## 30–120 分钟：代码与数理审计

检查占位、吞异常、动态执行、路径逃逸、随机 seed、资源泄漏、重复解析、大数组复制、N+1 I/O、无界缓存、类型逃逸、Schema 漂移、Windows/Linux 差异、依赖锁和漏洞。

建立 `FORMULA_TO_CODE_MAP.md`，记录公式、实现函数、单位、参数来源、算法、收敛、适用域、失败模式、测试和 measured/reference/proxy/fit/scenario/template 分类。

\[
C_{finite}(x)=\mathbf1_{x\in\mathbb R}\mathbf1_{\neg Bool(x)}\mathbf1_{isfinite(x)}
\]

\[
\lVert x_{k+1}-x_k\rVert\le\varepsilon_{abs}+\varepsilon_{rel}\lVert x_k\rVert
\]

\[
H=SHA256(code\Vert input\Vert method\Vert environment\Vert result)
\]

缺失单位、非有限数、奇异矩阵、越域、未收敛或解析失败必须返回 `BLOCK` 或 `HOLD`。

## 仓库专项

- **AspenOps-Agent**：Process IR、守恒、DOF、撕裂边、约束、Worker/COM、取消恢复、缓存优化、许可证并发、证据包；保持 `PENDING_REAL_ASPEN_CERTIFICATION`。
- **TsaoSciComputation**：计算合同、不可变命令计划、执行文件与输入哈希、资源准入、Parser、收敛、数值/物理等价、C ABI、求解器探测；外部引擎保持 `EXTERNAL_HOLD`。
- **TSAO-PROCESSING-SKILL**：四个 Skill、Schema、canonical publication、DOPRI5、衡算、动力学、群体矩、热力学、流变、Fisher、UQ、Wheel 与源码快照。
- **ResinDB-Pro-by-SunHJ**：三份 README、中文/英文图分离、UTF-8、NFC/NFKC、乱码、控制字符、Markdown/HTML 图片、SVG 安全、CJK 字体、Chromium、ECharts `finished`、Canvas 像素、PNG、主题/语言、Worker 错误态。
- **TsaoDFT_skill**：Kohn–Sham、SCF、周期几何、三斜晶胞 MIC、邻居表、Parser、能量/力/应力、方法指纹、引擎身份、性能等价和 L0–L3。
- **TsaoSciResearcher**：路由、能力、量纲、证据三分、冲突、适用域、可辨识性、UQ、尺度桥、handoff、receipt、归档和 `automatic_approval=false`。

关键合同：

\[
OK=C_{comm}\land C_{engine}\land C_{conv}\land C_{finite}\land C_{constraint}\land C_{balance}
\]

\[
\frac{d\mathbf N}{dt}=F_{in}\mathbf z-F_{out}\mathbf x+V\boldsymbol\nu^T\mathbf r
\]

\[
C_{figure}=C_{finite}\land C_{labeled}\land C_{finished}\land C_{nonblank}
\]

\[
G=\min(g_{quantity},g_{applicability},g_{evidence},g_{identifiability},g_{bridge})
\]

## 120–270 分钟：实施修复

按 correctness、security、numerical stability、cross-platform、performance、tests、README、localized visuals、acceptance evidence 顺序修复。禁止删除失败测试、降低阈值、静默 fallback、隐藏正式门禁、篡改历史证据或宣传未实现功能。

## README 与双语 AI 设计图

中文 README 使用中文图，英文 README 使用英文图。图必须基于当前代码与项目愿景，包含愿景、五阶段能力链、2–4 条公式和资格边界；采用 1600×900 `viewBox`、`title`、`desc`、`role=img`、CJK 与数学字体回退；无脚本、外链字体和乱码；兼容 GitHub、Chromium、librsvg、Inkscape。

中文标注：`AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非运行结果`。English: `AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA`。

## 270–345 分钟：六仓库并行测试

同时运行仓库正式 CI：严格锁依赖、lint/format、类型、Schema、unit/science/Worker tests、branch coverage、build/Wheel/sdist、CLI/HTTP/Chromium smoke、dependency audit、SBOM、exact-tree、Windows/Linux 矩阵、README/SVG/UTF-8。日志写入 `artifacts/acceptance/<repo>/`，汇总记录命令、时间、返回码、测试数、覆盖率、失败摘要、SHA、平台和依赖身份。

## 345–360 分钟：失败闭环

获取完整日志，定位首个真实根因，最小修复，聚焦测试并重跑完整门禁。达到上限时，全绿仓库可合并；未全绿保持 `BLOCKED`，不得伪造状态。

## 合并与最终输出

\[
MERGE=code\land math\land tests\land docs\land visuals\land security\land exactTree
\]

合并后删除验收分支、无效 PR 和一次性文件，重新查询分支/PR，最终只允许 main。生成 `SIX_REPOSITORY_FINAL_REPORT.md`、`SIX_REPOSITORY_FINAL_VERDICT.json`、`SIX_REPOSITORY_FORMULA_TO_CODE_MAP.md`、`SIX_REPOSITORY_TEST_MATRIX.md`、`SIX_REPOSITORY_BRANCH_CLEANUP.md`、`SIX_REPOSITORY_README_VISUAL_AUDIT.md`。逐仓库给出 PASS/BLOCKED、SHA、CI run、tests、coverage、漏洞、README/图、分支/PR 和外部科学资格，不得用模糊语言替代机器结果。
