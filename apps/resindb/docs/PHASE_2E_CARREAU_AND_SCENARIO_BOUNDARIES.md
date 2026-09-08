# ResinDB Pro Phase 2E：Carreau 受约束拟合与老化情景边界

## 1. 阶段定位

本阶段继续上一轮数理程序全面审计，关闭两个明确保留的高风险边界：

1. Carreau–Yasuda Worker 采用粗网格加固定学习率梯度、缺少收敛诊断且 `a` 仅取 1 或 2；
2. Material Trend Forecaster 使用规则生成的历史路径，却将结果呈现为观测历史、预测置信区间、T50 寿命和安全分类。

本阶段不引入未经等价验证的 FP32、WASM、WebGPU 或 CUDA 内核，也不宣称未经同机 benchmark 证明的加速倍数。

## 2. 通用有界非线性最小二乘

新增 `src/compute/nonlinearLeastSquares.ts`：

- 有限上下界通过 logistic 参数变换强制满足；
- 中心有限差分构造雅可比；
- Levenberg–Marquardt 阻尼控制；
- 每个增广线性步调用现有 Householder QR / Jacobi-SVD 最小二乘；
- 禁止显式构造或求逆 `JᵀJ`；
- 支持梯度、步长、目标函数变化、最大迭代和阻尼上限终止；
- 返回函数求值数、迭代数、终止原因、阻尼、梯度无穷范数及雅可比秩/条件数诊断。

## 3. Carreau–Yasuda 拟合

Carreau Worker 现在采用模型：

```text
η(γ̇) = η₀ [1 + (λγ̇)^a]^((n-1)/a)
```

并明确记录 `η∞ = 0` 假设。具体实现：

- 只接受完整、有限、正剪切速率与正黏度；
- 至少需要 5 个观测；
- 在 log 黏度域拟合，减弱跨数量级数据对目标函数的支配；
- `η₀`、`λ`、`n`、`a` 均为连续受约束参数；
- 81 个确定性粗初值计算目标，选择最优 8 个进行有界 LM；
- 使用稳定的 softplus 计算转变项，避免 `(λγ̇)^a` 直接溢出；
- 返回线性尺度与 log 尺度 `R²`、log RMSE、收敛状态、函数求值、参数边界和可辨识性诊断；
- 不将雅可比诊断包装为参数置信区间，结果明确标记为 `identifiability diagnostics only`。

合成无噪声 Carreau–Yasuda 数据用于参数恢复门禁；`a` 不再被限制为 1 或 2。

## 4. 老化模块科学边界

原模块输入是多个牌号的横截面属性，历史路径由规则和确定性扰动生成，因此其本质不是观测时序预测。本阶段保留 `RUN_FORECAST` / `FORECAST_RESULT` 兼容消息，但统一定义为：

```text
rule-based scenario projection, not a validated forecast
```

主要修正：

- 基线明确为选定牌号的横截面均值；
- 负月份路径明确为规则生成的 synthetic baseline path；
- Q10 风格热损失规则不再称为 Arrhenius 拟合；
- `holt-winters` 旧 ID 仅作兼容别名，真实算法标记为无季节项 Holt linear trend；
- 线性投影预测标准误杠杆项修正为 `(m-x̄)²/Sxx`；
- 极端热应力造成的月损失率设置明确上限，防止 `1-loss ≤ 0` 的数值崩溃；
- 所有随机扰动使用版本化 Seeded RNG；
- T50 改称 scenario T50 crossing；
- 结果带改称 heuristic scenario band，不再声称 95% confidence interval；
- retention band 仅用于筛查，不再称安全认证、稳定性认证或失效预测；
- 输出完整 assumptions、规则名称、有效应力、月损失率、是否触发上限、seed 和投影参数。

## 5. 前端同步

`MaterialTrendForecaster` 已同步改名与呈现：

- `Material Aging Scenario Projection`；
- `Synthetic baseline path` 与 `Scenario projection`；
- `Heuristic scenario band`；
- `Holt Linear Trend (No Seasonality)`；
- 页面顶部和结果区均显示“非观测历史、非置信区间、非材料认证、非验证寿命预测”的边界。

所有旧的 `Observed Baseline History`、`95% confidence interval`、`Expected T50 Half-Life`、`STABILITY CLASSIFICATION` 和 Arrhenius 误标均已删除。

## 6. 测试门禁

新增测试覆盖：

1. 通用有界 LM 对合成指数模型的参数恢复；
2. 无效参数边界与欠定系统阻断；
3. 合成 Carreau–Yasuda 四参数恢复；
4. 连续 `a` 优化与高 log `R²`；
5. 极端 180 °C 热情景仍保持有限输出，月损失率触发 25% 模型边界；
6. 同输入情景结果完全可复现；
7. 输出明确为 rule-based scenario projection；
8. `holt-winters` 旧 ID 正确映射为 Holt linear no seasonality。

原有完整回归、科学 Worker、覆盖率、生产构建、浏览器 UI、依赖审计和单一 `main` 分支门禁不得回退。

## 7. 仍保留的后续边界

- Carreau 当前为 `η∞ = 0` 四参数模型；如需五参数 Cross/Carreau–Yasuda 或温度联合拟合，应建立独立模型和选择门禁；
- 参数协方差、profile likelihood、bootstrap 置信区间尚未实现，不得从雅可比条件数直接推断置信区间；
- 老化模块若要升级为验证预测，必须接入真实时序或加速老化数据、训练/验证划分、外推评价和单位一致性证据；
- 原生/WASM 加速必须首先选择固定 FP64 参考内核，并通过逐点容差、退化输入和跨后端证据门。
