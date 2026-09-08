# ResinDB Pro Phase 2C：随机可复现与数值参考求解器

## 1. 阶段定位

本阶段建立正式科学计算的可复现随机基线，并替换 RSM 中不稳定的显式法方程求逆。范围只覆盖随机源、Monte Carlo、K-Means、方差型敏感性分析和 RSM 求解器；不引入 WASM、WebGPU、CUDA 或 UI 大规模改造。

## 2. Seeded RNG 合同

新增 `src/compute/random.ts`：

- 固定算法：`xoshiro128**`。
- 固定算法版本：`1.0.0`。
- 字符串和有限数值 seed。
- 稳定对象序列化和 FNV-1a 派生 seed。
- `[0, 1)` 均匀分布、开区间均匀分布和 Box-Muller 正态分布。
- 可选截断正态拒绝采样边界。
- 固定序列测试向量阻止算法实现静默漂移。

相同算法版本、相同 seed 和相同输入必须得到完全相同的伪随机序列。自动 seed 由完整逻辑输入稳定派生，结果中必须返回实际使用的 seed、seed 来源、算法和版本。

## 3. Monte Carlo

Monte Carlo Worker 现在：

- 不再调用 `Math.random()`。
- 接受可选显式 seed；未提供时由公式、产品、方差和迭代数派生。
- 以绝对基值计算标准差，避免负基值产生负标准差。
- 验证方差百分比和迭代数边界。
- 对零方差结果使用有限带宽 KDE，防止步长为零。
- 返回 seed、随机算法、Box-Muller 版本、模型版本、请求样本数和有效样本数。

## 4. K-Means

K-Means Worker 现在：

- k-means++ 初始化和空簇重置均使用版本化 Seeded RNG。
- 相同 seed、数据、特征和 `maxK` 必须得到相同的簇分配、最佳 K 和质心。
- 输出实际 seed、随机算法版本、模型版本和最终 Silhouette 分数。
- 修复单簇路径未返回质心的问题。
- 保持当前完整 Silhouette 选择逻辑；其规模优化仍属于后续算法优化阶段。

## 5. Sobol 科学边界

现有 Worker 名称和 `SOBOL_COMPLETE` 消息为兼容性保留，但结果明确记录真实方法：

- 目标量：方差型 Sobol 一阶和总效应指数。
- 估计器：Jansen 1999。
- 采样设计：Saltelli A/B 独立伪随机正态矩阵。
- 当前没有使用 Sobol 低差异序列。
- `totalEffect - firstOrder` 只是聚合高阶余量，不是成对交互分解。
- 模型求值次数严格记录为 `N × (D + 2)`。
- 可选物理边界采用截断正态拒绝采样，不以简单截断制造边界点质量。
- 没有提供边界时，结果明确标记为无界独立正态输入。

因此文档和证据不得把当前采样设计描述为“Sobol 序列采样”。

## 6. RSM QR/SVD 求解器

新增 `src/compute/leastSquares.ts`：

- 列尺度归一化。
- 一侧 Jacobi SVD 用于秩和条件数诊断。
- 满秩且条件数可接受时使用 Householder QR。
- 秩亏、欠定或病态系统自动使用 Jacobi-SVD 伪逆。
- 禁止计算 `(XᵀX)⁻¹`。
- 返回 solver、行列数、数值秩、条件数、条件数状态、残差范数、容差和奇异值。
- 秩亏系统以 `conditionNumber: null` 和 `conditionNumberStatus: "infinite"` 表示无穷条件数，保证 JSON 证据不失真。

RSM 结果增加模型版本和完整求解诊断，原有 `beta`、驻点和网格字段保持兼容。

## 7. 测试门禁

新增测试覆盖：

1. `xoshiro128**` 固定序列与版本。
2. 稳定派生 seed。
3. 截断正态可复现和边界不越界。
4. 满秩二次曲面的 QR 系数恢复。
5. 秩亏设计的 SVD 伪逆回退。
6. Monte Carlo 同 seed 完全一致。
7. K-Means 同 seed 完全一致。
8. Saltelli/Jansen 真实采样元数据和模型求值数。
9. RSM Worker 的 QR 诊断与 SVD 回退。

所有原有测试、科学 Worker、覆盖率、构建、浏览器验证和依赖审计不得回退。

## 8. 后续阶段

Phase 2D 建议进入 TypedArray 数值数据合同和首批算法适配：优先 RSM 与 K-Means，建立 Worker Transferable、TypeScript 参考内核和后续 WASM 内核之间的数值等价门禁。
