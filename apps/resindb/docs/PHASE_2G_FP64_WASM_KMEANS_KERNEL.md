# ResinDB Pro Phase 2G：首个 FP64 WASM 等价内核

## 1. 阶段定位

本阶段在 Phase 2F 的 `row-major-float64-1.0.0` 连续内存合同上建立首个可实际调用的 WebAssembly 科学计算内核。目标不是把全部 K-Means 重写为不透明二进制，而是选择边界清晰、调用频繁且可逐数组核验的 Lloyd assignment/update 核心，保留 TypeScript FP64 权威参考和完整安全回退。

本阶段继续遵守：

- 仅远程 `main`；
- FP64 正式计算；
- 不使用 `fast-math`、FP32、SIMD 或线程制造表面速度；
- 不改变 Seeded RNG、K-Means++、空簇重置、Silhouette 或候选 K 选择；
- 不使用共享 CI 机器的毫秒阈值作为唯一验收；
- 不在 README 或商业材料宣称未经同机 benchmark 证明的倍数。

## 2. 内核选择

审计比较了四个候选：

1. K-Means assignment/update；
2. RSM 网格求值；
3. Gaussian Process 批量预测；
4. KDE 乘加核心。

首个内核选择 K-Means assignment/update，理由：

- Lloyd 迭代中重复执行 `N × K × D` 距离计算；
- 输入已经是 row-major `Float64Array`；
- 数学操作只包含确定顺序的减法、乘法、加法、比较和累加；
- ties 规则可固定为最先出现的簇；
- K-Means++、随机空簇重置和 Silhouette 可继续留在 TypeScript，避免改变随机轨迹；
- 输出可用 assignments、centroid sums、counts 和 changed count 逐数组比较。

RSM QR/SVD、GP 方差预测和 KDE 仍保留为后续独立内核，不能因为首个 WASM 成功就推断这些模型已经获得原生加速。

## 3. 公共后端会话

新增：

- `src/compute/kmeansAssignment.ts`；
- `src/compute/wasm/kmeansAssignmentWasm.ts`；
- `native/wasm/kmeansAssignmentKernel.c`。

公共会话支持：

```text
auto | typescript | wasm
```

行为：

- `typescript`：始终使用 FP64 TypeScript 参考循环；
- `wasm`：严格请求 WASM；`allowFallback=false` 时不可用或失败即报错；
- `auto`：能力存在时优先使用 WASM，否则保持 TypeScript；
- 初始化失败、内存增长失败、运行 trap、输出簇索引非法、计数不一致或和向量非有限时，可按策略回退 TypeScript；
- 回退发生后，同一会话后续调用继续使用 TypeScript，避免反复触发同一失败。

## 4. WASM FP64 内核

内核标识：

```text
kernel: kmeans-assignment-update
kernelVersion: 1.0.0
wasmBinaryVersion: kmeans-assignment-wasm-f64-1.0.0
precision: f64
protocol: row-major-float64-1.0.0
```

输入和输出：

- 输入矩阵：row-major FP64；
- 输入质心：row-major FP64；
- 输入/输出 assignments：`Int32Array`；
- 输出 centroid sums：FP64；
- 输出 counts：`Uint32Array`；
- 返回 changed assignment count。

矩阵在会话创建时复制到 WASM 线性内存一次。每次 Lloyd 迭代只交换质心、分配、和与计数，不重复复制完整样本矩阵。

当前内核为标量 FP64：

- `wasmSimdUsed=false`；
- `wasmThreadsUsed=false`；
- 能力证据仍记录 SIMD 和线程是否可用，但“可用”不等同于“已使用”。

## 5. 可重建源码与二进制

权威 C 源码：

```text
native/wasm/kmeansAssignmentKernel.c
```

本阶段嵌入二进制 SHA-256：

```text
a2b3e7cf1106e09682a6229f43af8cf32973487ae918db35962046406839d6b6
```

对应仓库 C 源码 SHA-256：

```text
14cf5e56caed1c534b94893a32377082a18f52194da2b00227f7b354b8d17c27
```

参考构建命令：

```bash
clang --target=wasm32 -Oz -nostdlib -fno-builtin \
  -Wl,--no-entry \
  -Wl,--export=assign_accumulate \
  -Wl,--export=__heap_base \
  -Wl,--export-memory \
  -Wl,--initial-memory=131072 \
  -Wl,--max-memory=268435456 \
  -Wl,--strip-all \
  -o kmeansAssignmentKernel.wasm \
  native/wasm/kmeansAssignmentKernel.c
```

该构建没有启用 `-ffast-math`、SIMD 或线程。嵌入字节使产品运行不依赖客户端 clang，也不进行运行时外部二进制下载。

## 6. K-Means Worker 集成

K-Means Worker 新增可选字段：

```text
backend: auto | typescript | wasm
allowFallback: boolean
```

旧对象消息和 Phase 2F FP64 Transferable 消息继续支持。默认产品路径为 `auto`。

WASM 仅替换 Lloyd assignment/update：

```text
样本到质心距离
→ 最邻近簇
→ assignments
→ centroid sums
→ counts
→ changed count
```

以下逻辑保持 TypeScript：

- 均值插补与标准化；
- Seeded K-Means++；
- 空簇的 Seeded 重置；
- 完整/抽样 Silhouette；
- 候选 K 比较；
- 最终 UI 对象构造。

因此后端切换不改变随机数消耗顺序。

## 7. 运行证据

`performance.assignmentKernel` 返回：

- kernel 与版本；
- WASM 二进制版本；
- FP64 协议版本；
- requested backend；
- actual backend；
- fallback 是否发生及原因；
- 内核调用次数；
- WASM 线性内存字节数；
- SIMD/线程能力与实际使用状态。

原有字段继续保留：

- 输入传输方式；
- 数值输入字节数；
- 矩阵与 assignment 存储类型；
- Lloyd 迭代数；
- 距离求值次数。

## 8. 数值和故障门禁

新增测试覆盖：

1. TypeScript 与 WASM assignments 完全一致；
2. centroid sums、counts 和 changed count 完全一致；
3. 完整 Worker 在同 seed 下簇分配、最佳 K、质心、Silhouette、模型选择和复现证据一致；
4. 显式 TypeScript 后端仍可用；
5. WASM 初始化失败时安全回退；
6. WASM 运行失败后不保留部分输出，改用 TypeScript 重新完成当前迭代；
7. `allowFallback=false` 时严格失败；
8. WebAssembly 能力不存在时严格请求被阻断；
9. NaN、正无穷和负无穷样本矩阵被会话边界拒绝；
10. 非有限质心在任一后端执行前被拒绝。

## 9. 性能证据边界

本阶段的确定性收益包括：

- Lloyd 核心进入 WASM 线性内存；
- 样本矩阵每会话只复制一次；
- TypeScript 与 WASM 共用同一 row-major FP64 合同；
- 后端和回退均可追踪；
- Worker Pool、Transferable 与 WASM 形成端到端路径。

但以下说法仍禁止：

- “WASM 固定加速若干倍”；
- “SIMD 加速”；
- “多线程加速”；
- “全部 K-Means 已在 WASM 中运行”；
- “所有科学模型均已原生加速”。

具体倍数必须在固定浏览器、固定 CPU、固定数据集、预热、多轮重复和结果等价条件下测量，并报告中位数、离散度和交叉点规模。

## 10. 下一阶段

后续优先级：

1. 增加固定环境 benchmark runner 与机器可读报告；
2. 根据规模交叉点决定是否默认启用 WASM，而非仅按能力启用；
3. 评估 K-Means SIMD 版本，但必须保留标量 FP64 参考；
4. 选择第二个内核：GP 批量均值预测或 KDE 乘加核心；
5. RSM QR/SVD 原生化必须单独建立秩亏、条件数和残差等价门；
6. 任何近似算法必须显式命名，并与精确参考报告误差或召回率。
