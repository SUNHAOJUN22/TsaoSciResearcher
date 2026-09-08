# ResinDB Pro 代码、数理程式与性能审计（2026-08-01）

## 1. 审计范围与基线

- 仓库：`SUNHAOJUN22/ResinDB-Pro-by-SunHJ`
- 基线提交：`0fd88ccf868e9478ef4bf3318ee1c6eb56a5d4af`
- 本轮审计代码头：`79f4563901403a6a8a2faa4aa922ee12dad1ed95`
- 审计对象：生产源码、数值计算内核、Web Workers、科研图表运行时、单元/科学测试、TypeScript、构建预算及 Chromium 证据脚本。
- 原则：保持现有模型定义、单位、输出契约和科学边界；任何优化必须保留数值等价或由测试明确锁定。

本轮不是仅依据函数名进行静态浏览。已逐项核查线性/非线性最小二乘、Carreau–Yasuda、WLF、Arrhenius、Kissinger、Weibull、Prony/NNLS、Gaussian Copula、KDE、Mahalanobis、Sobol/Monte Carlo、分布函数及随机数基础设施，并检查其调用链、边界条件、复杂度、临时分配和浏览器 Worker 执行方式。

## 2. 已确认的数理实现

### 2.1 最小二乘与矩阵计算

- `src/compute/leastSquares.ts` 使用列缩放、Householder QR 和 SVD/伪逆回退，避免直接求逆正规方程。
- 秩、条件数和残差诊断被保留；病态问题通过条件阈值显式处理。
- `src/compute/nonlinearLeastSquares.ts` 使用有界参数的 logistic 变换和阻尼最小二乘，约束链式法则现已覆盖解析雅可比路径。

### 2.2 流变模型

- Carreau–Yasuda 零无穷剪切黏度假设、对数黏度残差和多起点有界拟合保持不变。
- 解析导数已逐式校核：`eta0`、`lambda`、`n`、`a` 四个参数的物理参数雅可比与中心差分在代表性点上一致至浮点误差范围。
- WLF 线性化和温度平移因子符号关系正确；当前实现明确属于垂直平移未建模的简化契约。

### 2.3 热分析与动力学

- Arrhenius 的 `ln(k)` 对 `1/T` 回归及活化能换算正确。
- Kissinger 的 `ln(beta/Tp^2)` 对 `1/Tp` 斜率关系正确；现有输出属于指定动力学假设下的估计。

### 2.4 可靠性、松弛与统计模型

- Weibull 使用 Bernard 中位秩和二参数线性化估计；该方法不是最大似然估计，代码元数据未将其伪装为 MLE。
- Prony 模型使用广义 Maxwell 基、非负最小二乘/正则化与 Abaqus 归一化输出，参数含义一致。
- Gaussian Copula 的 normal-score 相关系数和密度公式正确。
- 二维 KDE 使用乘积 Gaussian 核与二维 Scott 带宽规则，边界假设明确。
- Mahalanobis 使用正则化协方差、Cholesky 距离和卡方阈值近似，避免显式矩阵逆。
- Sobol 模块采用种子可复现的伪随机正态采样；元数据正确说明其不是低差异 Sobol 序列。

## 3. 已实施的代码与性能改进

### 3.1 通用有界非线性最小二乘

文件：`src/compute/nonlinearLeastSquares.ts`

- 增加可选 `evaluateJacobian` 接口，优先使用解析雅可比。
- 保留中心差分作为完全兼容的回退路径。
- 对有界 logistic 变换实施链式法则。
- 复用物理参数、变换导数、扰动参数、候选参数和残差工作缓冲区，减少循环内短生命周期分配。
- 对解析雅可比的非有限值进行硬失败，防止静默污染拟合。
- 结果新增 `jacobianMethod`，使解析/差分路径可追踪。

代表性双参数指数单元夹具中，残差函数调用由 31 次降至 7 次，结果和目标函数保持等价，即残差调用减少约 77.4%，调用次数约为原来的 22.6%。实际速度收益随观测数量和残差函数成本变化。

### 3.2 Carreau–Yasuda 拟合

文件：`src/workers/carreauWorker.ts`

- 提供四参数解析雅可比，消除每轮中心差分所需的额外残差计算。
- 预计算剪切速率和黏度对数。
- 复用 `logEta0`、`logLambda`、`1/a` 等公共量。
- 使用稳定的 sigmoid/softplus 分支，避免极端转变参数下不必要的溢出。
- 诊断中记录 `jacobianMethod: analytic`。

文件：`src/hooks/math/useCarreau.ts`

- 将前端触发门槛从 3 个观测值统一为求解器真实要求的 5 个正有限观测值，消除无效 Worker 调用和可预见错误。

### 3.3 Gaussian Copula 密度网格

文件：`src/workers/copulaWorker.ts`

- 将网格轴概率和逆标准正态分位数从双层密度循环中移出并预计算。
- 默认 `gridSize=50` 时，逆正态函数调用由 2,450 次降至 49 次，减少 50 倍。
- 最大 `gridSize=200` 时，调用由 39,800 次降至 199 次，减少 200 倍。
- 密度公式、网格点数量、排序结果和输出契约保持不变；新旧公式的代表性数值比较仅有机器精度量级差异。

### 3.4 分布函数基础设施

文件：`src/compute/distributions.ts`

- 将 Acklam 逆正态近似的四组系数提升为模块级只读常量，避免每次调用重复分配数组。
- 上尾分支改用 `Math.log1p(-p)`，改善接近 1 的概率输入下的数值稳定性。
- 输入域和卡方 Wilson–Hilferty 近似契约保持不变。

### 3.5 图表运行包与 UI 证据

文件：`src/lib/echarts.ts`

- 删除全仓未使用的 `SVGRenderer` 注册；生产图表继续统一使用 Canvas 渲染器。
- 由构建预算和 Chromium 烟测负责防止误删功能。

文件：`src/components/charts/scientificFigurePolicy.ts`

- 连续轴 tooltip 默认启用 `axisPointer.snap`，同时保留显式覆盖。
- 将 tooltip 过渡时间设为 0，提升科研证据脚本的确定性。

文件：`scripts/ui-phase2l-scientific-smoke.mjs`

- 修复浏览器证据脚本在 Canvas 位于视口外时发送无效鼠标坐标的问题。
- 探测前将目标 Canvas 居中、重新读取可见交集，并仅在视口内进行多点探测。
- 该修复位于测试工具，不向生产图表生命周期加入自动滚动或抢焦点行为。

## 4. 测试与验证门槛

本审计文档所在 PR 必须通过仓库永久 `CI` 工作流的 exact-tree 验证后才可合并。门槛包括：

1. `npm ci` 精确依赖安装；
2. 单元测试、科学测试和 Worker 矩阵；
3. TypeScript 类型检查；
4. 生产构建与 bundle budget；
5. 源码/文档/数据契约与依赖审计；
6. Chromium 主烟测、K-Means 校准烟测和 Phase 2L 科研图表证据；
7. PDF、覆盖率、构建指标及浏览器证据产物。

基线和中间提交已证明数值测试、TypeScript、构建和科学模块通过；中间失败均定位到旧 tooltip 证据脚本的视口坐标问题，而非数学结果退化。最终结论以本 PR 最新头提交的 CI 状态和产物为准。

## 5. 保留的科学边界与后续非阻断项

以下项目不是本轮新增错误，且未在缺乏科学依据时擅自改变模型：

- WLF 当前不估计垂直平移/密度修正。
- Weibull 当前为 Bernard rank 二参数线性化估计，不是 MLE，也不包含位置参数。
- Sobol 模块当前名称对应敏感度方法，但采样器为可复现伪随机数，不是低差异 Sobol 序列。
- Mahalanobis 小样本阈值依赖 Wilson–Hilferty 卡方近似。
- 通用 LM 仍会为 `solveLeastSquares` 的二维数组接口构造设计矩阵；进一步降低分配需要改造线性代数 API，宜单独基准验证。
- 解析雅可比诊断代表最后一次实际计算的雅可比；若未来需要严格的最终参数协方差，应在收敛后重新评价雅可比并建立专门不确定度模型。

这些边界均应继续在 UI、导出元数据和科研说明中明确，不得用更强的统计或物理结论替代。

## 6. 结论

本轮修正集中于可证实的热点：减少非线性拟合的残差重复计算、消除 Copula 网格中的重复逆分位数计算、降低基础分布函数的临时分配、移除未使用图表渲染器，并修复阻断 CI 的浏览器证据坐标缺陷。模型定义、单位和科学边界保持不变。是否达到最终可接受状态，由本报告对应 PR 的完整 exact-tree CI 结果决定。
