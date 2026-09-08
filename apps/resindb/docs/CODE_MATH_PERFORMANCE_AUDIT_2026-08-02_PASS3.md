# ResinDB Pro 数理程式与性能审计：第三轮（2026-08-02）

## 1. 范围与基线

- 仓库：`SUNHAOJUN22/ResinDB-Pro-by-SunHJ`
- 本轮基线：`0f05effa5874bdcc259e0258cf1e16784ddfb749`
- 已合并代码提交：`9cf0e9d0bce738c4044729ff719d778fd6ca2cf2`
- 审查重点：Gaussian Process 公共内核、Bayesian Optimization、Multi-objective Optimization、Similarity Worker，以及与其关联的数值、内存和可复现性契约。
- 原则：不改变核函数、概率模型、随机序列、归一化定义、余弦相似度、Pareto 判定、单位或结果语义；优化必须由自动化测试和完整 exact-tree CI 约束。

本轮是在前两轮解析雅可比、Copula 网格、分布函数、Prony/FISTA 和 Mahalanobis 缓冲区优化之后进行的增量深审，不重复已完成工作。

## 2. Gaussian Process 内核审查

### 2.1 数理定义

RBF 核保持为：

`k(x, x') = exp(-||x-x'||² / (2l²))`

协方差矩阵仍在对角线上加入配置噪声，并通过 Cholesky 分解求解。预测均值、前向代入以及后验方差下限定义均未改变。

### 2.2 已实施优化

文件：`src/compute/gaussianProcess.ts`

- 在因子分解对象中缓存 `1 / (2l²)`，候选预测不再重复计算固定 RBF 比例。
- 新增 `predictGaussianProcessRbfInto`，允许调用方提供并复用 `GaussianProcessPrediction` 对象。
- 原 `predictGaussianProcessRbf` 保持兼容，仍可返回独立对象。
- `solveGaussianProcessAlpha` 增加可选前向代入工作区，默认调用方式保持兼容。
- Cholesky 抖动重试复用同一个下三角矩阵缓冲区，不再为每次尝试重新分配矩阵。
- 输入维度、有限值、工作区长度和方差下限校验继续保留。

## 3. Bayes 与 MOO 高频候选预测

### 3.1 Bayesian Optimization

文件：`src/workers/bayesWorker.ts`

- 候选上限为 20,000。
- 整个 Worker 执行只创建并复用一个预测结果对象。
- GP 前向求解复用既有 scratch 缓冲区。
- EI 公式、正态 CDF/PDF 近似、流式 Top-5 保留和种子随机序列保持不变。
- `1/sqrt(2π)` 提升为模块常量，消除高频 PDF 调用中的固定平方根计算。

预测结果对象的分配由约 `candidateCount + historicalCount` 降为固定 1 个；最大候选配置下，至少消除约 20,000 个短生命周期对象。

### 3.2 Multi-objective Optimization

文件：`src/workers/mooWorker.ts`

- 候选上限为 50,000。
- 首目标 GP 预测复用一个结果对象；共享核向量继续用于其他目标均值计算。
- 多目标 alpha 求解共享同一前向工作缓冲区。
- 二目标排序扫描、三目标以上增量非支配前沿、reservoir sampling 和可复现随机契约保持不变。

预测结果对象的分配由约 `candidateCount` 降为固定 1 个；最大候选配置下消除约 50,000 个短生命周期预测对象。

## 4. Similarity Worker 内存与边对象

文件：`src/workers/similarityWorker.ts`

### 4.1 数理定义保持不变

- 缺失值仍以对应特征有限值均值填补。
- 标准差仍使用样本标准差分母 `n-1`。
- 各产品向量仍先进行 Z-score，再归一化为单位向量。
- 相似度仍为余弦内积，并钳制到 `[-1, 1]`。
- `maxEdges` 仍通过最小堆保留最强边，等值边的原有保留规则未改变。

### 4.2 已实施优化

- 原始值、均值填补、Z-score 和单位向量在同一个 `Float64Array` 中原位完成。
- 主矩阵缓冲区由两个 `productCount × featureCount` 的 Float64 矩阵降为一个，主矩阵内存减少 50%。
- 当 `maxEdges` 已填满时，先比较当前堆根阈值；只有可能进入最强边集合的候选才创建边对象。
- 对无上限模式仍保留所有阈值以上边，行为不变。

回归夹具包含 40 个产品、780 个产品对、`maxEdges=10`。优化前会为 780 条阈值以上边创建对象；优化后只创建 10 个边对象，并返回同样的 10 条最强边。

## 5. 版本与可审计元数据

- Bayes：`bayesian-optimization-rbf-ei-2.1.0`
- MOO：`multiobjective-rbf-gp-2.1.0`
- Similarity：`zscore-cosine-flat-f64-2.1.0`

性能元数据新增：

- `predictionStorage: reused-object`
- `solveWorkspace: shared-forward-buffer`
- `kernelExponentScaleCached: true`
- `matrixAllocationPolicy: single-in-place-float64`
- `matrixBufferCount: 1`
- `edgeObjectsAllocated`
- `boundedEdgeAllocationPolicy: retained-only-after-heap-threshold`

这些字段用于让性能实现能够被测试和导出记录验证，而不是依赖口头说明。

## 6. 验证结果

PR 23 对代码精确树执行的永久 CI 已确认以下门槛通过：

- 文档、源码卫生、治理数据与科研 UI 语义；
- ESLint 与 TypeScript；
- K-Means 后端基准烟测；
- 完整回归测试；
- 隔离单元测试；
- 隔离科学与 Worker 测试；
- 全生产源码覆盖率；
- 生产构建与外部数据证明；
- HTTP 生产烟测；
- 完整 Chromium 交互烟测；
- 生产依赖与完整依赖审计。

该 PR 唯一失败项为“远端仅允许 main”检查，因为验证时临时 PR 分支必然存在。代码合并后通过一次性清理流程删除临时分支，并在单一 `main` 状态下再次执行最终 exact-tree CI。

## 7. 保留边界与后续非阻断项

- GP 预测仍逐点执行有限值验证；若未来需要进一步压缩极大候选循环的校验成本，应设计明确的内部可信批量 API，而不应直接删除公共安全检查。
- MOO 三目标以上的增量非支配前沿在最坏情况下仍可能接近二次复杂度；更换数据结构会改变较多代码和排序细节，应单独建立大规模基准与等价性证明。
- Bayes 的 EI 仍使用现有 erf 近似；本轮没有在缺乏必要性的情况下更换统计近似。
- Similarity 仍为全产品对计算，复杂度为 `O(n²d)`；本轮降低内存与对象分配，没有以近似最近邻替代精确相似度。

## 8. 结论

第三轮优化消除了 Bayes/MOO 高频 GP 预测中的结果对象分配和重复固定比例计算，并将相似度主矩阵内存减半，同时显著减少有界边图中的废弃对象创建。所有模型公式、随机性、单位和科学解释边界保持不变。最终接受状态以清理后单一 `main` 的完整 exact-tree CI 为准。
