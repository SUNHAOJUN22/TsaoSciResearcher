# ResinDB Pro Phase 2D：数理程序全面审计与 CPU 加速

## 1. 阶段定位

本阶段对科学计算 Worker、公共数值内核、随机源、矩阵求解、模型选择和大规模候选计算进行系统审计。目标不是通过放宽误差、减少测试或改变科学含义获得表面速度，而是在保留结果合同、增加证据字段和建立等价门的前提下，降低算法复杂度、内存峰值和垃圾回收开销。

审计对象包括 Arrhenius、Bayes、Carreau、Copula、Feature Importance、Forecasting、KDE、Kinetics、K-Means、Mahalanobis、Monte Carlo、MOO、Pareto、Prony、RSM、Similarity、Sobol/Jansen sensitivity、SPC、Spearman、Weibull 和 WLF，以及 `src/compute/` 中的随机、最小二乘、Cholesky、Gaussian Process、Pareto、分布近似、Worker Pool 和 Transferable 合同。

## 2. 审计原则

1. 禁止把显式矩阵求逆作为回归或距离计算的默认路径。
2. 随机算法必须固定 seed、算法名称、算法版本和模型版本。
3. 加速实现必须保留参考公式或建立数值等价测试。
4. 不以 FP32 替代正式 FP64 科学计算，除非内核明确声明容差。
5. 大规模任务必须限制不必要的候选保存、全排序和全矩阵物化。
6. 缺失值不得静默等同于真实零值；必须记录删除或插补策略。
7. 退化样本、秩亏、零方差、无重叠区间和非有限结果必须显式失败或记录诊断。
8. 未经基准测试不得在 README 宣称具体倍数。

## 3. 已关闭的数理与性能问题

| 模块 | 原问题 | 当前处理 | 数理/复杂度结果 |
|---|---|---|---|
| RSM | 计算 `(XᵀX)⁻¹Xᵀy` | 列缩放、Householder QR、Jacobi-SVD 伪逆回退 | 避免法方程条件数平方；返回秩、条件数、残差和奇异值 |
| Feature Importance | 标准化岭回归仍显式求逆 | 以增广设计矩阵表达岭惩罚，调用 QR/SVD 最小二乘 | 不再求逆；截距不惩罚；返回求解诊断 |
| Mahalanobis | 求协方差逆矩阵 | 正则化协方差 + Cholesky 分解后逐向量求解 | 避免逆矩阵；阈值使用 Wilson–Hilferty + Acklam 正态分位近似 |
| Gaussian Process | Bayes 与 MOO 重复实现矩阵代码 | 共享 flat `Float64Array` RBF/Cholesky 内核和可复用 scratch | 每次任务只分解一次；多个目标共享协方差分解 |
| Bayes | 保存并排序全部候选，只返回前 5 | 流式 top-k，只保留 5 个最佳 EI 候选 | 候选存储由 `O(C)` 降为 `O(5)`；取消全排序 |
| MOO | 默认 10,000 候选后两两支配，约 `O(C²T)` | 二目标精确排序扫描；多目标增量非支配前沿；确定性 reservoir 输出 | 二目标前沿提取降为 `O(C log C)`；输出缓存有界 |
| Pareto Worker | 多处重复支配逻辑 | 共享 Pareto 内核 | 二目标使用正确分组排序扫描；多目标使用增量前沿 |
| K-Means | 每个候选 K 计算完整 Silhouette `O(KN²D)` | 小样本完整；大样本确定性抽样 Silhouette | 大样本模型选择约为 `O(KSND)`，`S << N`；记录抽样规模 |
| K-Means 缺失值 | 缺失值直接填 0 | 按特征有限均值插补并记录数量 | 避免把未知测量解释为物理零值 |
| Monte Carlo | 每次迭代复制 Product 与全部 properties | 复用工作 Product/Property 对象，预计算随机属性，使用 `Float64Array` 结果缓冲 | 大幅减少对象分配和 GC；随机序列与公式不变 |
| Sobol/Jansen sensitivity | A/B 使用嵌套数组；每次求值复制对象；物化每维 hybrid 输出 | flat `Float64Array` A/B，复用工作对象，hybrid 输出流式累计 | 内存为 `2ND + 2N` 数值；模型求值仍严格为 `N(D+2)` |
| Sobol 科学命名 | 容易被误称为 Sobol 序列采样 | 明确为 Saltelli A/B 独立伪随机正态设计、Jansen 1999 估计器 | 明确 `usesLowDiscrepancySobolSequence: false` |
| Similarity | 嵌套矩阵与重复归一化；边集合可能无界 | flat 单位向量；一次点积；可选最强 `maxEdges` 有界堆 | 精确计算仍为 `O(N²D)`；可将结果内存限制为 `O(maxEdges)` |
| KDE | 每个样本和二维网格点重复计算联合指数 | 利用乘积高斯核可分离性，预计算 X 核并按行计算 Y 权重 | 指数函数次数由 `NG²` 降为 `2NG`，密度公式逐点等价 |
| Prony | 最多 100,000 次投影梯度且循环分配 | flat 设计矩阵、岭正则、非负 FISTA、收敛诊断 | 迭代上限降低；加速梯度；保持非负广义 Maxwell 系数 |
| WLF/TTS | 401 个平移网格 × 每点线性扫描参考曲线 | 粗细两级网格 + 二分线性插值 | 每曲线约 142 次目标评估；插值由 `O(P)` 降为 `O(log P)` |
| Copula | 方法与边界不清晰 | 平均秩伪观测、正态分数 Gaussian copula、共享逆正态近似 | 明确 ties、伪观测和模型版本 |
| Spearman | 常量特征对角线错误写为 1；`Infinity` 可进入 | 完整有限样本、平均秩；常量特征行列返回 0 并列入诊断 | 不再把未定义相关性伪装成完美相关 |
| Arrhenius | 截距容易误称速率前因子 | 明确为 log-lifetime Arrhenius OLS | `Ea = mR`，截距标记为寿命模型截距 |
| Kissinger | 峰温拟合被直接当作普适动力学 | 明确峰温线性化与一阶等温外推假设 | 返回方法、单位和外推边界 |
| Weibull | 估计器身份不清 | Bernard 中位秩两参数 OLS，明确非 MLE | 使用 `log(-log(1-p))` 和 5% 失效分位 |
| SPC | 总体/样本标准差及 PPM 假设不清 | `n-1` 样本标准差；PPM 标记为拟合正态假设 | Cp/Cpk 与尾部概率口径闭环 |
| Worker 调度 | Hook 挂载即创建多个 Worker | Lazy Worker Pool、优先级、取消、超时和空闲回收 | 控制并发和 Worker 总库存；长任务可取消 |

## 4. 复杂度与内存基线

### 4.1 Bayes

- GP 建模：`O(N³)` 分解，单次完成。
- 候选预测：当前精确方差为 `O(CN²)`；均值为 `O(CN)`。
- 候选存储：由 `O(C)` 降为固定 `O(5)`。
- 后续大样本方向：诱导点 GP、随机特征或分批 GPU 预测，必须与当前精确后端比较。

### 4.2 MOO

- 多目标共用一次 `O(N³)` GP 分解。
- 每目标只求一次 alpha。
- 二目标 Pareto：`O(C log C)`。
- 三个及以上目标：`O(CFT)`，其中 `F` 为当前前沿规模，通常远小于 `C`，最坏情况仍可能退化。
- 展示候选使用 reservoir sampling，内存不随 `C` 线性无限增长。

### 4.3 K-Means

- 聚类：约 `O(KIND)`，`I` 为迭代数。
- 完整 Silhouette：`O(KN²D)`。
- 大样本抽样 Silhouette：`O(KSND)`，默认 `S ≤ 1000`。
- 后续方向：MiniBatch K-Means、距离块计算和 WebGPU assignment。

### 4.4 Similarity

- 精确全部两两相似性不可避免为 `O(N²D)`。
- flat 单位向量减少对象和除法开销。
- `maxEdges` 只限制结果内存，不减少全部配对计算。
- 真正突破复杂度需引入 top-k/ANN，并建立召回率与精确参考比较。

### 4.5 KDE

乘积高斯核满足：

```text
exp[-0.5(dx² + dy²)] = exp(-0.5dx²) · exp(-0.5dy²)
```

因此预计算每个样本在全部 X 网格上的核值，并逐 Y 行计算权重。乘加次数仍为 `NG²`，但最昂贵的指数函数次数由 `NG²` 降为 `2NG`。

## 5. 仍未关闭的科学边界

### 5.1 Carreau 拟合：P1

当前仍采用粗网格初始化和固定学习率梯度微调。主要风险：

- 参数高度相关，固定步长可能振荡或停在边界；
- 没有梯度范数、目标函数变化和参数协方差诊断；
- `a` 只在 1 与 2 中选择，模型边界没有显式说明；
- `R²` 不能单独证明非线性拟合可靠。

建议下一阶段建立受约束参数变换和 Levenberg–Marquardt/信赖域参考求解器，并用合成真值、残差、AIC、参数恢复和多初值测试验收。未经该门禁，不应仅为速度替换现有拟合器。

### 5.2 Forecasting：P0 科学标签边界

当前输入是多个产品的横截面属性，而历史轨迹由环境应力规则和确定性扰动生成。因此其本质是“情景投影”，不是由观测时间序列训练的预测模型。另需注意：

- `holt-winters` 当前没有季节项，数学上属于 Holt 线性趋势；
- 线性、指数和 Holt 路径的区间含义并不统一；
- 热、UV、水解和循环应力系数属于情景假设，不是由数据估计的动力学参数；
- 安全等级文案不能被解释为材料认证或寿命验证。

后续必须选择其一：重命名为 scenario projection 并显示假设账本；或接入真实时序/老化数据、训练验证分割和外推证据。完成前不得用该模块生成验证性科研结论。

### 5.3 多目标高维前沿：P2

增量前沿在所有候选都互不支配时仍会退化。后续可引入非支配排序、分块支配、ε-dominance 或 GPU 并行，但必须明确是精确还是近似前沿。

## 6. 等价与回归门禁

新增或扩展测试覆盖：

1. 共享 Gaussian Process 在训练点的数值恢复与 scratch 重用。
2. Bayes 同 seed 完全一致，候选只保留 top-k。
3. MOO 同 seed 完全一致，二目标结果内部不存在支配关系，reservoir 输出有界。
4. K-Means 大样本自动使用确定性抽样 Silhouette。
5. Similarity 在 `maxEdges` 下保留最强边并报告截断。
6. Monte Carlo 复用工作对象和 typed result buffer。
7. Sobol/Jansen flat matrix 与 hybrid streaming，模型求值数不变。
8. KDE 可分离实现逐网格点等于直接二维高斯公式。
9. Feature Importance、Mahalanobis、Prony 返回求解器与版本诊断。
10. Spearman 常量特征不再输出虚假的对角线 1。
11. WLF 粗细搜索的目标评估数和参考曲线对齐结果。

## 7. 性能声明规则

本阶段只记录可由代码结构直接证明的变化，例如：

- 候选保存 `O(C) → O(k)`；
- 二目标 Pareto `O(C²) → O(C log C)`；
- K-Means Silhouette `O(KN²D) → O(KSND)`；
- KDE 指数函数次数 `NG² → 2NG`；
- WLF 插值 `O(P) → O(log P)`；
- 显式求逆被 QR/SVD/Cholesky 求解替代。

实际耗时倍数必须由固定数据集、固定设备、固定浏览器和预热策略下的 benchmark 确认，不能由理论复杂度直接推断。

## 8. 阶段退出条件

- `npm run validate:docs`、`validate:source` 和 `validate:data` 通过。
- ESLint 与 TypeScript 通过。
- 完整回归、独立单元和科学 Worker 测试通过。
- 全生产源码覆盖率不低于既有门限。
- 构建、HTTP smoke、Chromium UI、依赖审计和单一 `main` 分支证明通过。
- 精确树 CI 生成 Markdown、HTML、PDF 和机器可读收据。
- 不在 README 宣传未经 benchmark 验证的加速倍数。

## 9. 下一执行基线

下一阶段建议拆为两个独立工作包：

1. **Phase 2E-Numerics**：Carreau 受约束 LM/信赖域、Forecasting 科学边界重构、WLF 垂直移位/密度修正可选合同。
2. **Phase 3-WASM Baseline**：RSM、Mahalanobis、KDE、K-Means assignment 首批 C++/WASM 内核，使用当前 TypeScript FP64 结果作为强制等价参考。
