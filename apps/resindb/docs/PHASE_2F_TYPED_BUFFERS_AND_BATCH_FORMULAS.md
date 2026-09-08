# ResinDB Pro Phase 2F：TypedArray 数据通道与批量公式执行

## 1. 阶段定位

本阶段继续数理程序全面审计与计算加速，目标是消除 Worker 边界和高频公式求值中的结构化克隆、嵌套数组与短寿命对象开销。范围包括：

1. 公共 row-major FP64 数值矩阵合同；
2. RSM 与 K-Means 的 Transferable 输入路径；
3. K-Means 连续内存计算核心；
4. Monte Carlo 与 Sobol/Jansen 的可复用数值公式执行器；
5. 旧对象消息、旧性能字段及现有 UI 合同兼容。

本阶段不引入未经等价验证的 FP32、WASM、WebGPU 或 CUDA，也不使用不稳定的计时阈值作为 CI 门禁。

## 2. Row-major FP64 公共合同

新增 `src/compute/numericBuffers.ts`，固定协议：

```text
row-major-float64-1.0.0
```

矩阵合同包含：

- `rows`；
- `columns`；
- 连续 `Float64Array values`；
- 行优先索引 `row * columns + column`；
- 协议版本、尺寸、长度、列数、最小行数和有限值校验。

该布局同时适用于 TypeScript Worker、未来 C++/WASM 线性内存和原生边缘服务，避免不同后端分别定义输入格式。

## 3. RSM Transferable 输入

`useRsmWorker` 现在将 `{x1,x2,y}[]` 转换为三列 FP64 矩阵，并通过 `postMessage(..., { transfer })` 转移底层 `ArrayBuffer`。

RSM Worker 同时支持：

- 旧 `data: {x1,x2,y}[]` 克隆路径；
- 新 `matrix: RowMajorFloat64Matrix` 转移路径。

两条路径进入相同 QR/SVD 拟合、驻点和网格代码。结果新增性能证据：

- `inputTransport`；
- `numericInputBytes`；
- `validRows`；
- `gridPoints`。

因此旧调用不会失效，新产品路径不再深度克隆数值对象数组。

## 4. K-Means 连续内存核心

K-Means 产品 Hook 现在发送：

- `ids: string[]`；
- `keys: string[]`；
- row-major `Float64Array` 数值矩阵；
- 底层 `ArrayBuffer` Transferable。

Worker 继续接受旧对象消息，但内部统一转换为连续内存。主要工作区：

- 样本矩阵：`Float64Array`；
- 特征均值和标准差：`Float64Array`；
- 质心：`Float64Array`；
- 最近距离：`Float64Array`；
- 簇分配：`Int32Array`；
- 簇计数：`Uint32Array`；
- Silhouette 临时距离与计数：可复用 typed buffers。

主要改进：

- 归一化在转移后的输入缓冲区上原地执行；
- 每个候选 K 不再建立 `number[][]` 样本矩阵；
- Lloyd 迭代复用质心累积和计数缓冲区；
- K-Means++ 距离缓存复用；
- Silhouette 不再为每个样本创建数组；
- 最终结果才将最佳质心转换为 UI 兼容的 `number[][]`。

结果新增：

- 输入传输路径；
- 数值输入字节数；
- 矩阵和分配存储类型；
- 总 Lloyd 迭代数；
- 距离求值次数。

现有确定性 Seeded RNG、均值插补、完整/抽样 Silhouette 策略和输出字段保持兼容。

## 5. 批量公式执行

原 `FormulaEngine.compileGraph()` 每次调用均从 Product 枚举属性、创建数值字典并创建结果对象。Monte Carlo 和 Sobol/Jansen 即使复用 Product，仍会在每次模型求值产生这些开销。

本阶段新增：

```text
createPropertyDictionary(product)
compilePropertyGraph(formulas)
```

`compilePropertyGraph` 接受可复用数值属性字典和可选结果对象：

- 不重复枚举 Product 属性；
- 不重复创建公式结果对象；
- 仍按拓扑顺序写入派生公式名称；
- 非有限公式结果仍归零；
- Product 执行路径继续由同一编译计划提供。

Monte Carlo 与 Sobol/Jansen 现在：

- 固定复用数值属性字典；
- 固定复用公式结果对象；
- 仅更新随机或混合变量；
- 对基础属性与公式同名的碰撞进行显式恢复；
- 保留旧 `workObjectReused` 证据字段，并新增更精确的字典/结果复用字段。

随机序列、模型求值次数、Jansen 估计器和输出排序均未改变。

## 6. 等价与边界门禁

新增测试覆盖：

1. row-major FP64 协议、字节数、版本和异常尺寸；
2. RSM 旧对象输入与 FP64 输入的系数、驻点、网格和诊断完全一致；
3. K-Means 在同 seed 下两种输入路径的簇分配、K、质心、Silhouette 和复现证据一致；
4. 公式 Product 执行与数值字典执行一致；
5. 结果对象可复用；
6. 基础属性与公式同名时，显式恢复后无跨样本污染；
7. 原有 Monte Carlo、Sobol/Jansen、K-Means、RSM、UI 和完整回归不得退化。

## 7. 性能证据口径

本阶段记录确定性结构指标，不在共享 CI 机器上设定毫秒阈值：

- Transferable 是否启用；
- 数值输入字节数；
- 连续内存类型；
- 距离求值次数；
- Lloyd 迭代数；
- 公式字典与结果对象是否复用。

具体“加速若干倍”必须在固定浏览器、固定 CPU、固定数据集、预热后重复测量，并同时验证输出等价后才能进入 README 或商业材料。

## 8. 下一阶段边界

### 8.1 首个 FP64 WASM 内核

优先候选：

1. K-Means assignment/update；
2. RSM 设计矩阵和网格求值；
3. Gaussian Process 批量均值预测；
4. KDE 乘加核心。

每个 WASM 内核必须：

- 复用 `row-major-float64-1.0.0`；
- 保留 TypeScript FP64 参考后端；
- 建立逐点绝对/相对容差；
- 覆盖 NaN、秩亏、零方差、空簇和边界数据；
- 记录后端、版本、精度、输入形状和耗时；
- 在 WASM 不可用时安全回退。

### 8.2 大规模算法

- K-Means：MiniBatch 或分块 assignment；
- Similarity：精确 top-k 或 ANN，并报告召回率；
- Gaussian Process：诱导点或随机特征参考模式；
- Monte Carlo/Sobol：公式 AST 到紧凑数值寄存器计划，减少字符串键查找。

以上优化不得通过隐藏近似或删除科学证据获得表面速度。
