# TsaoDFT Full Numerical Correctness, Performance and Real Acceleration Master Prompt V2

下面的正文是一个可直接粘贴执行的主控 Prompt。它适用于继续审查和改造 `SUNHAOJUN22/TsaoDFT_skill`，也可作为后续数理正确性、算法效率、解析器性能、HPC/GPU 真实性能和证据闭环工作的统一协议。

---

## 可直接执行的主控 Prompt

```text
TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2

仓库：SUNHAOJUN22/TsaoDFT_skill
目标分支：现有 main
工作方式：立即执行，不要只给计划；不要重新开始；以执行时最新 main HEAD 为唯一代码基线。

总目标：
对整个 TsaoDFT 仓库开展一次可追溯、分阶段、证据优先的数理正确性、数值稳定性、算法复杂度、内存与 I/O 效率、解析器可扩展性、HPC 资源匹配、性能证据可信度和真实硬件加速审计；发现问题后直接实现修复。任何性能优化必须先证明科学结果等价，任何真实加速结论必须由真实硬件、真实软件构建、真实输入和可复核测量支持。

============================================================
一、不可违反的仓库操作约束
============================================================

1. 只在现有 main 上顺序快进提交。
2. 禁止创建分支、PR、fork、临时分支或隐藏工作树。
3. 禁止 force push、历史改写、rebase 已发布历史或删除已有提交。
4. 每一次写入前必须重新读取最新 main HEAD。
5. 若 main 在准备写入期间发生变化：
   - 立即停止该次写入；
   - 重新读取最新 HEAD 和目标文件；
   - 审查并发提交；
   - 在最新内容上重新同步；
   - 不得覆盖、回退或丢失他人的修改。
6. 每个阶段的代码必须在该阶段最新 HEAD 自己的永久 CI 全部通过后，才可进入下一阶段。
7. 最终结论必须来自最终 HEAD 自己的 CI，禁止使用上一提交、旧 run 或局部测试代替。
8. 禁止删除测试、降低覆盖率阈值、排除原本计入覆盖率的文件、操纵分母或添加 blanket ignore。
9. 禁止降低 Ruff、mypy、strict mypy、Bandit、CodeQL、依赖审计、SBOM、仓库审计或信任边界质量门。
10. 禁止为了“通过”而弱化科学验证、输入验证、证据资格或失败关闭语义。
11. 不要因任务复杂而停在计划阶段；在安全和权限允许的范围内持续执行，直到当前阶段完整闭环。

============================================================
二、真实性和能力声明边界
============================================================

1. 必须清楚区分以下证据等级：
   A. 静态代码审计；
   B. 数学推导或独立闭式基准；
   C. 单元/性质/极端值测试；
   D. 合成工作负载 benchmark；
   E. 仓库代码在真实 CPU 上的实测 benchmark；
   F. 仓库代码在真实 GPU/加速器上的实测 benchmark；
   G. VASP、Quantum ESPRESSO、CP2K、Gaussian 等外部引擎在真实构建和真实硬件上的端到端 benchmark。
2. 合成夹具和模拟数据必须明确标记：
   - SIMULATION_ONLY
   - NOT_REAL_HARDWARE
   - NOT_PERFORMANCE_EVIDENCE
3. 未获得真实硬件记录时，禁止声称：
   - GPU 加速已实现；
   - CUDA/HIP/SYCL 已获得速度提升；
   - 多 GPU 强缩放有效；
   - 边缘设备部署性能已验证；
   - VASP/QE/CP2K/Gaussian 获得任何数值加速比。
4. 不得把算法复杂度改善、内存下降或 Python 循环向量化表述为外部 DFT 引擎加速。
5. 公共能力等级不得因模拟、单元测试或未签名 benchmark 自动升级。
6. L3 或更高性能证据必须同时满足：
   - 真实引擎或真实目标程序；
   - 不可变输入哈希；
   - 引擎版本和构建指纹；
   - 编译器、MPI、OpenMP、加速运行时版本；
   - CPU/GPU 型号和唯一身份；
   - 节点、rank、thread、GPU 绑定和互连拓扑；
   - 至少规定次数的成功重复；
   - 失败运行完整保留；
   - 科学观测量在明确容差内等价；
   - 独立审核或既定签名审批；
   - 证据包内容寻址和校验和闭环。

============================================================
三、强制执行顺序
============================================================

必须严格按照以下优先级执行，不得先追求速度再补正确性：

1. 科学公式和量纲正确性；
2. 单位、常数、符号、参考态和标准态一致性；
3. 精确类型合同与 NaN/Inf 失败关闭；
4. 数值稳定性、条件数、溢出、下溢和抵消；
5. 收敛、统计、误差和不确定度语义；
6. 算法复杂度、内存复杂度和 I/O 复杂度；
7. 流式处理、向量化、批处理、缓存和并行；
8. profile 支持下的原生 CPU/C++/OpenMP/Kokkos 边界；
9. profile 支持下的 CUDA/HIP/SYCL 或供应商数学库边界；
10. 真实硬件 benchmark 和性能证据资格。

当较早阶段存在阻断性错误时，暂停后续加速开发，先修复并验证阻断项。

============================================================
四、Phase 0：初始化、基线冻结和执行清单
============================================================

1. 读取执行时最新 main HEAD，并记录：
   - 起始 commit SHA；
   - 最新永久 CI run；
   - Python 3.10/3.12/3.13 状态；
   - 测试数、套件数和失败数；
   - statement/branch coverage；
   - 六个信任核心覆盖率；
   - Ruff、mypy、strict mypy、Bandit、CodeQL、依赖审计和 SBOM 状态。
2. 从真实 coverage artifact 恢复全部可执行 Python 文件，区分生产和测试文件，统计：
   - 文件数；
   - 可执行语句；
   - 分支；
   - 低覆盖热点。
3. 盘点非 Python 文件：
   - shell；
   - JSON/YAML schema；
   - 模板；
   - CI；
   - C/C++/CUDA/HIP/SYCL/Fortran 或 native extension（若存在）；
   - 外部引擎调用边界。
4. 建立模块级审计表，至少包含：
   - 文件/函数；
   - 科学或控制平面角色；
   - 输入/输出；
   - 公式或算法；
   - 单位；
   - 参考态/标准态；
   - 时间复杂度；
   - 空间复杂度；
   - 数值风险；
   - 性能风险；
   - 证据等级；
   - 建议动作；
   - 状态。

============================================================
五、Phase 1：公式、单位、常数和参考态总审计
============================================================

逐个审查所有实现科学或统计关系的模块，不得只搜索明显公式。

必须检查：

1. 量纲一致性：
   - eV、Hartree、kcal/mol、kJ/mol、J/mol；
   - Å、bohr、nm、m；
   - Pa、GPa；
   - K、°C；
   - s、ps、fs；
   - concentration、pressure 和 standard-state convention。
2. 常数：
   - k_B、h、R、Avogadro 常数；
   - Hartree/eV/kcal/mol 转换；
   - 任何经验常数、阈值和默认容差。
3. 符号和方向：
   - 正负号；
   - forward/reverse；
   - adsorption/desorption；
   - reaction/activation free energy；
   - total energy/energy difference；
   - stress、force、charge 和电势符号。
4. 参考态：
   - first/min/指定结构；
   - gas/solution/surface 标准态；
   - 零点、温度和压力；
   - 相同方法指纹和模型身份。
5. 公式实现与标签必须一致，禁止输入标签写一种单位、内部计算使用另一种单位。
6. 每个高风险公式必须建立独立参考：
   - SI 闭式计算；
   - 高精度或可信库对照；
   - 手算可验证案例；
   - 极限值和不变量。
7. 输出 `docs/TSAODFT_FORMULA_UNIT_REFERENCE_STATE_LEDGER.md`，逐条记录公式、单位、参考态、依据、测试和状态。

============================================================
六、Phase 2：精确类型、有限值和输入合同
============================================================

所有科学值、性能值和资源值必须失败关闭。

强制检查：

1. Python bool 是 int 子类，所有数值入口必须明确拒绝 True/False。
2. 声明为整数的字段必须是精确整数，禁止：
   - 1.5 经 int() 变成 1；
   - 1.0 被当作整数；
   - "1" 被隐式转换；
   - bool 被当作 0/1。
3. 所有浮点字段必须拒绝 NaN、+Inf、-Inf。
4. 科学观测量必须覆盖：
   - energy；
   - forces；
   - stress；
   - properties；
   - convergence thresholds；
   - uncertainty；
   - coordinates；
   - rate constants；
   - barriers；
   - resource and performance metrics。
5. 列表必须检查：
   - 根类型；
   - 非空性；
   - 元素类型；
   - 有限值；
   - 长度兼容；
   - 唯一性（需要时）；
   - shape。
6. mapping 必须检查键的类型和唯一语义；不得以 `or {}` 把明确提供的非空畸形值静默当默认配置。
7. CSV/JSON/JSONL/YAML 必须处理：
   - 缺表头；
   - 缺列；
   - 多余字段；
   - 空行；
   - 重复身份；
   - 编码错误；
   - 畸形文档；
   - 路径逃逸。
8. 对直接 Python API 调用和 CLI 两条路径都测试，防止仅 schema 路径严格、直接调用宽松。

============================================================
七、Phase 3：数值稳定性和求解器审计
============================================================

逐项检查：

1. 指数：使用 log-space，显式处理 overflow/underflow。
2. 求和：在抵消敏感或长序列使用 math.fsum、pairwise 或等价稳定算法。
3. 范数/RSS：使用 hypot、scaled norm 或稳定库实现，避免先平方溢出。
4. 差值：明确绝对/相对误差、参考值接近零时的语义。
5. 统计：
   - median、quartile、MAD、modified z-score；
   - 样本数不足；
   - 全相同值；
   - 非有限值；
   - outlier 阈值；
   - 稳定排序和确定性。
6. 线性代数：
   - 避免显式求逆；
   - 检查矩阵 shape 和有限值；
   - 评估条件数；
   - 使用 lstsq/solve/SVD/QR 的合适边界；
   - 截距是否惩罚；
   - primal/dual 选择；
   - 正则项是否正确加入。
7. 收敛：
   - 必须有足够完整 tail；
   - 排序方向明确；
   - 重复控制值处理明确；
   - 阈值必须有限且非负；
   - 不得把缺数据判为收敛。
8. 不确定度：
   - 明确独立/相关假设；
   - RSS、线性相加和分开报告语义；
   - 不得生成无依据的单一综合不确定度。
9. 热力学和动力学：
   - forward/reverse closure；
   - TST/Eyring；
   - molecularity 和速率单位；
   - 标准态说明；
   - 对数速率区间。

============================================================
八、Phase 4：算法、内存和 I/O 复杂度审计
============================================================

1. 找出：
   - O(N²)、O(N³) 路径；
   - 全量 read_text/read_bytes；
   - 全文件正则；
   - 重复解析；
   - 重复哈希；
   - 多次排序；
   - Python 内层数值循环；
   - 不必要的矩阵、identity、完整副本和序列化。
2. 对每个候选写明当前复杂度和目标复杂度。
3. 优先采用：
   - 单遍流式读取；
   - bounded-memory tail/window；
   - mmap（仅适合随机定位且证明有益时）；
   - NumPy/BLAS/LAPACK 向量化；
   - chunking；
   - heap/top-k；
   - 内容寻址缓存；
   - 避免重复 canonical JSON；
   - 原子输出和事务式发布。
4. 不得为微小文件或非热点引入复杂缓存。
5. 输出操作必须：
   - 先在同一文件系统 staging；
   - 完整生成并校验；
   - 再原子发布；
   - 发布失败应回滚已有正式输出；
   - 不留下半成品或临时文件。
6. 对解析器重点审查：
   - Gaussian 大日志；
   - VASP OUTCAR/vasprun；
   - QE 输出；
   - CP2K 输出；
   - late-failure-wins 语义；
   - 最后有效值；
   - block parsing；
   - regex catastrophic backtracking。
7. 对几何和轨迹重点审查：
   - atom mapping；
   - pair distances；
   - RMSD；
   - neighbor lists；
   - trajectory frames；
   - periodic minimum-image；
   - O(N²) 内存爆炸。

============================================================
九、Phase 5：性能证据和缩放数学
============================================================

1. 性能证据入口必须拒绝：
   - NaN/Inf wall time；
   - 非正 wall time；
   - 小数伪装 repeat/rank/thread/node；
   - 空构建指纹；
   - 不一致硬件身份；
   - 缺失 artifact hash；
   - 失败 parser；
   - 不足重复；
   - 非有限科学观测量。
2. 统计必须保留全部成功和失败运行，不得只选最快一次。
3. 默认使用稳健统计，明确 median、MAD、IQR 和 outlier 标记；不得静默删除离群值。
4. speedup 只在以下条件同时满足时计算：
   - reference median 和 candidate median 有限且大于零；
   - 重复数达标；
   - 构建和硬件身份一致；
   - artifact 验证通过；
   - 科学等价性 PASS。
5. 强缩放：
   - 基准 GPU 数明确；
   - GPU 数和 rank 布局明确；
   - efficiency 公式正确；
   - 跨拓扑结果不得直接比较；
   - 单 GPU 基准缺失时不得生成强缩放结论。
6. profiler adapter 必须拒绝畸形、负值或非有限时间/内存/利用率。
7. 任何速度比必须标记测量环境、重复数、统计量和证据等级。

============================================================
十、Phase 6：并行、HPC 和异构硬件边界
============================================================

1. 检查节点、socket、NUMA、core、thread、MPI rank、GPU 数量和绑定的一致性。
2. 检查：
   - oversubscription；
   - ranks per GPU；
   - GPU visibility；
   - CPU affinity；
   - OpenMP 线程；
   - scheduler allocation；
   - memory per node/device；
   - scratch 和并行文件系统；
   - interconnect 和 collectives。
3. CPU-only、NVIDIA/CUDA、AMD/HIP、Intel/SYCL 和 Apple/Metal 路径必须显式区分。
4. 不得把硬件可用性推断为引擎构建支持；必须读取或提供 engine build capability。
5. 不得把 CUDA-X、ROCm、oneAPI、cuTENSOR 或 cuEquivariance 当作任何 DFT 引擎的通用 drop-in 开关。
6. cuEquivariance 只可用于确认的等变 ML 工作负载，例如 MACE/NequIP/e3nn 路径；不得用于 Kohn–Sham DFT 的虚假加速声明。
7. cuTENSOR 只在存在明确张量收缩热点、数据布局和数值等价性证据时评估。
8. 边缘设备仅可运行经过验证的 surrogate/inference；必须有 uncertainty/OOD gate 和远程 DFT fallback，不得取代科学验证。

============================================================
十一、Phase 7：原生代码和 GPU 实现准入门槛
============================================================

只有同时满足以下条件，才可新增 C++、OpenMP、Kokkos、CUDA、HIP、SYCL 或 native extension：

1. profile 证明该路径是端到端热点，而不是占比很低的辅助函数；
2. 给出代表性数据规模和测量方法；
3. Python/native 数据转换成本已计入；
4. 有纯 CPU/reference 实现；
5. 有严格数值等价测试；
6. 有异常、空输入、极端值和资源不足测试；
7. 有未安装编译器/运行时时的安全降级；
8. 构建矩阵不破坏 Python 3.10/3.12/3.13 和 Windows 核心支持；
9. 不增加无法审计的二进制或下载执行路径；
10. 实测端到端收益显著且可复现。

若条件不满足，必须记录为 PROFILE_GATED / NOT_IMPLEMENTED，不得为了“有 GPU”而添加无证据代码。

============================================================
十二、Phase 8：测试和验收要求
============================================================

每个修复至少覆盖其中适用项：

1. 正常值；
2. 独立参考值；
3. 边界值；
4. 极大/极小值；
5. NaN/Inf；
6. bool、字符串、小数伪装整数；
7. 空输入、缺字段、错 shape；
8. 重复身份和重复标签；
9. malformed JSON/YAML/CSV；
10. 失败中途输出清理；
11. 旧文件保留和原子替换；
12. 顺序确定性；
13. primal/dual、scalar/vectorized、streaming/full reference 等价；
14. property-based 或 fuzz 测试（对纯函数和 schema 边界适用时）；
15. 大规模但稳定、非计时依赖的复杂度测试。

禁止以脆弱 wall-clock 阈值作为普通 CI 的唯一性能验收。可采用：

- 禁止调用旧标量函数；
- 断言不使用 read_text/read_bytes；
- 断言不分配 identity/full matrix；
- 统计处理元素数；
- 内存上界或 chunk 次数；
- 独立 benchmark 脚本和非阻断测量报告。

每阶段验收：

- 所有既有测试通过；
- 新测试通过；
- 测试总数不得减少；
- statement coverage 不低于阶段起始基线；
- branch coverage 不低于阶段起始基线；
- 六个信任核心不得回退；
- Ruff、mypy、strict mypy、Bandit、repo audit、CodeQL、dependency audits、SBOM 全部通过。

若任一门失败：立即停止进入下一阶段，读取真实日志，最小修复，重新运行同一最新 HEAD 的质量门。

============================================================
十三、Phase 9：真实 benchmark 协议
============================================================

只有有真实硬件权限时执行。对每个引擎和候选：

1. 固定科学输入和方法指纹；
2. 固定 engine version/build；
3. 记录编译选项和 linked libraries；
4. 记录 CPU/GPU/节点/互连/驱动/运行时；
5. 预热策略一致；
6. CPU reference 与 candidate 至少满足策略规定的成功重复数；
7. 保留所有失败和异常运行；
8. 采集 wall time、CPU time、SCF iterations、host/device memory、I/O 和能耗（可用时）；
9. 科学等价检查至少覆盖 energy、force、stress 和任务特定 properties；
10. 报告 median、range、IQR/MAD、outlier 标记；
11. 计算 CPU-to-candidate speedup；
12. 多 GPU 时计算 strong-scaling speedup 和 efficiency；
13. 不跨不兼容 topology 混合统计；
14. 生成内容寻址证据包、校验和和审核状态。

真实硬件不可用时：

- 不伪造结果；
- 输出可执行 benchmark matrix、job scripts、采集模板和阻断项；
- 标记 REAL_BENCHMARK_NOT_AVAILABLE；
- 公共能力等级保持不变。

============================================================
十四、强制交付物
============================================================

至少生成或更新：

1. `docs/TSAODFT_FORMULA_UNIT_REFERENCE_STATE_LEDGER.md`
2. `docs/TSAODFT_NUMERICAL_RISK_REGISTER.md`
3. `docs/TSAODFT_PERFORMANCE_PROFILE_AND_ACCELERATION_MATRIX.md`
4. `docs/TSAODFT_FULL_NUMERICAL_AND_ACCELERATION_FINAL_REPORT.md`

最终报告必须包含：

- 起始 HEAD 和最终 HEAD；
- 每阶段提交；
- 变更文件清单；
- 公式和单位修复；
- 数值稳定性修复；
- 复杂度和内存/I/O 改善；
- 性能证据修复；
- profile 结果；
- 已实现和未实现的原生/GPU 边界；
- 测试数、套件数、失败数；
- statement/branch coverage 前后对比；
- 六个信任核心覆盖率；
- Python 3.10/3.12/3.13；
- Ruff/mypy/strict mypy/Bandit/repo audit/CodeQL/dependency audit/SBOM；
- 真实 benchmark 的硬件、构建和证据等级；
- 所有未验证声明和剩余阻断项；
- 明确的 NO_FABRICATION 结论。

============================================================
十五、最终状态格式
============================================================

完成后必须输出类似：

FULL_EXECUTABLE_CODE_INVENTORY: COMPLETE
FORMULA_AND_DIMENSIONAL_AUDIT: COMPLETE / PARTIAL_WITH_BLOCKERS
EXACT_NUMERIC_TYPE_CONTRACTS: PASS
NONFINITE_VALUE_GATES: PASS
NUMERICAL_STABILITY_AUDIT: PASS
ALGORITHMIC_COMPLEXITY_REVIEW: COMPLETE
STREAMING_AND_VECTORIZATION: IMPLEMENTED_FOR_PROVEN_HOTSPOTS
PERFORMANCE_EVIDENCE_TRUST_BOUNDARY: PASS
NATIVE_ACCELERATION: IMPLEMENTED_WITH_EVIDENCE / PROFILE_GATED
REAL_CPU_BENCHMARK: AVAILABLE / NOT_AVAILABLE
REAL_GPU_BENCHMARK: AVAILABLE / NOT_AVAILABLE
REAL_DFT_ENGINE_BENCHMARK: AVAILABLE / NOT_AVAILABLE
SCIENTIFIC_EQUIVALENCE: PASS / NOT_EVALUATED
FINAL_HEAD_CI: PASS
COVERAGE_REGRESSION: NO
PUBLIC_CAPABILITY_LEVEL: UNCHANGED / REVIEWED_PROMOTION
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
TEST_DELETION: NO
FABRICATED_PERFORMANCE_CLAIM: NO

现在立即执行以上协议。不要只复述 Prompt，不要停在建议阶段。先读取最新 main、冻结基线并开始 Phase 0；每个阶段通过自己的永久 CI 后自动进入下一阶段。真实硬件不可用时继续完成全部静态、数理、测试、控制平面、benchmark 设计和证据准备工作，但不得伪造任何真实速度结果。
```

---

## 使用说明

在新的 Codex 或 ChatGPT 工作窗口中，直接粘贴上述代码块即可。若仓库已经完成部分阶段，执行者必须从最新 `main` 和现有报告判断断点，禁止重复初始化或回退已验证成果。
