# ResinDB Pro 数理程式与性能审计：第四轮（2026-08-02）

## 1. 范围与原则

- 仓库：`SUNHAOJUN22/ResinDB-Pro-by-SunHJ`
- 本轮基线：`decbc6053d641413f1c3cc19371ab2ee4959c7fc`
- 审查重点：Spearman、Gaussian Copula 的平均秩计算与 Monte Carlo 一维 Gaussian KDE。
- 原则：不改变并列秩定义、完整案例策略、normal-score 伪观测、相关系数、随机序列、KDE 带宽、输出网格和科学解释边界。

本轮是在前三轮非线性拟合、Copula 网格、Prony/Mahalanobis、Gaussian Process、Bayes/MOO 与 Similarity 优化之后开展的增量深审。

## 2. Spearman 排名与相关矩阵

Spearman 仍定义为平均秩后的 Pearson 相关；并列值获得其占据名次的算术平均，常量特征相关性继续按现有契约返回 0，而不是错误返回 1。

原实现存在两类可消除开销：

1. 每个特征排名时为每个观测创建 `{ value, index }` 对象；
2. 每个特征对、每个观测都重复计算 `rank - rankMean`。

本轮新增共享 `fillAverageRanks`：

- 值使用 `Float64Array`；
- 排序使用调用方复用的索引数组；
- 不再分配逐观测排名对象；
- 每个特征的秩只中心化一次；
- 特征对循环直接计算中心秩点积。

复杂度仍为排名 `O(kn log n)` 加相关矩阵 `O(k²n)`，但从高频的 `O(k²n)` 循环中移除了两次中心化减法，并降低了排名阶段的对象分配和 GC 压力。

代表性本地夹具为 8,000 个观测、24 个特征。旧实现约 70.6 ms，新实现约 38.2 ms，相关矩阵最大绝对差为 0。该时间仅代表当前 Node 环境，不作为跨设备固定倍数承诺。

## 3. Gaussian Copula 平均秩

Copula 保持以下定义不变：

- 完整有限二元观测；
- 平均秩；
- 伪观测 `(averageRank - 0.5) / n`；
- 逆标准正态 normal scores；
- normal-score Pearson 相关系数；
- Gaussian Copula 密度公式与 `rho` 钳制边界。

本轮改为：

- `x`、`y`、秩和排序副本使用 `Float64Array`；
- 两个变量依次复用同一索引排序工作区；
- 排名阶段逐观测对象分配为 0；
- 保留上一轮网格轴逆正态分位数预计算。

大规模独立排名基准中，100,000 个观测的平均秩阶段约由 26.39 ms 降至 15.92 ms，输出秩完全一致。

## 4. Monte Carlo 一维 Gaussian KDE

估计器仍为精确直接 Gaussian KDE：

`f(x) = [1 / (n h sqrt(2π))] * Σ exp(-(x-x_i)² / (2h²))`

没有引入分箱、核截断、FFT、近似最近邻或样本抽样。每个有效模拟结果仍参与全部 101 个网格点的核评价。

原实现把以下固定运算放在最内层：

- `(x - x_i) / h` 的带宽除法；
- 每次核贡献除以 `sqrt(2π)`。

本轮将以下不变量提升到核循环之外：

- `-0.5 / h²`；
- `1 / (n h sqrt(2π))`；
- 输出数组长度预分配。

最大 1,000,000 次 Monte Carlo 迭代且全部样本有效时，KDE 包含 101,000,000 次核评价。本轮从这些评价中消除了重复带宽除法和 Gaussian 归一化除法。

代表性本地夹具为 200,000 个样本、101 个网格点。旧实现约 253.8 ms，新实现约 204.7 ms；最大相对差约 `2.81e-14`，来自代数等价表达式的浮点运算重排。

## 5. 可审计元数据

版本更新：

- Spearman：`average-rank-pearson-complete-cases-2.1.0`
- Copula：`gaussian-copula-normal-scores-2.1.0`
- Monte Carlo：`monte-carlo-formula-numeric-dictionary-3.1.0`

新增或明确记录：

- `rankStorage`
- `rankOrdering`
- `pairwiseCentering`
- `centeredRankValues`
- `rankingScratchIndices`
- `rankValueObjectsAllocated`
- `sortedValueStorage`
- `kdeKernelStrategy`
- `kdeKernelEvaluations`
- `kdeBandwidthDivisionHoisted`
- `kdeGaussianNormalizationHoisted`

这些字段使性能实现能够由测试与导出记录核验，而非仅依赖说明文字。

## 6. PR 26 exact-tree 验证

PR 26 最新代码树已经通过：

- 文档、源码卫生、治理数据与科研 UI 语义；
- ESLint 与 TypeScript；
- K-Means 后端基准烟测；
- 52 个测试文件、254 项测试全部通过；
- 隔离单元测试；
- 隔离科学与 Worker 测试；
- 235 个生产 TypeScript 文件的完整覆盖率范围；
- 生产构建与外部数据证明；
- HTTP 生产烟测；
- 完整 Chromium 交互烟测；
- 生产依赖和完整依赖审计，漏洞总数均为 0。

构建指标：入口 gzip 173,207 B / 350,000 B；ECharts 原始包 850,460 B / 900,000 B。

该 PR 唯一失败项为“远端仅允许 main”，原因是验证期间临时 PR 分支必然存在。合并后必须删除临时分支，并对最终单一 `main` 文件树执行自证式 exact-tree 终审。

## 7. 保留边界

- Spearman 仍需要为每个特征保存中心秩向量，因此内存为 `O(kn)`；在计算完整相关矩阵时这是避免重复排名所需的精确存储。
- Copula 仍需对两个边际排序，复杂度为 `O(n log n)`；本轮减少对象分配，不改变精确排序。
- Monte Carlo KDE 仍为 `O(nm)` 精确直接估计；若未来需要对百万样本进一步数量级加速，必须明确引入近似方法并建立独立误差合同，不能静默替换。
- Monte Carlo 结果仍完整排序并返回，用于现有分位数与界面契约；本轮未以选择算法改变结果顺序。

## 8. 结论

第四轮优化针对三处可证实热点：共享平均秩工作区、Spearman 中心秩预计算，以及 Monte Carlo 精确 KDE 不变量提升。统计模型、随机性、单位、输出网格和科学边界保持不变。最终接受状态以清理后单一 `main` 的完整自证式 exact-tree 终审为准。
