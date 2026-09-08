# ResinDB Pro Phase 2H：K-Means 固定环境 Benchmark 与保守自动后端策略

## 1. 阶段定位

本阶段承接 Phase 2G 的 FP64 K-Means WebAssembly assignment/update 内核，解决“WebAssembly 可用”与“当前规模值得使用 WebAssembly”被混为一谈的问题。

阶段目标：

1. 建立可重复、机器可读的 TypeScript/WASM benchmark runner；
2. 在每次计时前先证明两后端输出等价；
3. 输出环境指纹、原始重复值、稳健统计量和规模交叉点分析；
4. 建立版本化、设备限定、可过期的 benchmark profile；
5. 让 `auto` 后端决策只接受兼容的设备本地 profile；
6. 禁止共享 CI 的一次计时结果成为所有浏览器的硬编码阈值。

本阶段继续遵守：

- 仅远程 `main`；
- FP64 正式计算；
- TypeScript FP64 为权威参考；
- WASM 初始化或运行失败时安全回退；
- 不改变 Seeded RNG、K-Means++、空簇重置、Silhouette 或候选 K 选择；
- 不以共享 CI 毫秒阈值作为 pass/fail 门；
- 不在 README 或商业材料宣称未经目标设备验证的固定加速倍数。

## 2. Benchmark 命令

新增：

```bash
npm run benchmark:kmeans:smoke
npm run benchmark:kmeans
```

`benchmark:kmeans:smoke` 用于 CI 中的小型确定性验证；`benchmark:kmeans` 用于固定设备上的完整显式测量。

Runner：

```text
scripts/run-kmeans-backend-benchmark.mjs
```

Runner 不复制一份未知 WASM 文件，而是直接读取当前仓库 `src/compute/wasm/kmeansAssignmentWasm.ts` 中嵌入的实际字节，并同时读取：

```text
native/wasm/kmeansAssignmentKernel.c
```

报告记录 WASM 二进制与 C 源码 SHA-256，保证测量对象与产品运行对象一致。

## 3. 测量方法

每个 case 固定：

- 数据生成 seed；
- 样本数 `N`；
- 维度 `D`；
- 簇数 `K`；
- 预热次数；
- 内核迭代次数；
- 重复次数。

每次正式计时前，先分别运行 TypeScript 和 WASM，并逐项比较：

- assignments；
- centroid sums；
- counts；
- changed assignment count。

任何不一致立即失败，不产生可接受的性能报告。

正式测量交替执行顺序：

```text
TypeScript → WASM
WASM → TypeScript
```

以降低固定先后顺序造成的热状态偏差。

报告同时保存：

- 全部原始重复值；
- minimum；
- Q1；
- median；
- Q3；
- maximum；
- IQR；
- MAD；
- relative IQR；
- median per call；
- TypeScript/WASM 中位数比；
- 绝对中位数差。

## 4. 机器可读合同

新增配置与 Schema：

```text
src/compute/kmeansBackendPolicyConfig.json
schemas/kmeans-backend-benchmark-report.schema.json
schemas/kmeans-backend-profile.schema.json
```

版本：

```text
benchmark policy: kmeans-backend-benchmark-policy-1.0.0
benchmark report: kmeans-backend-benchmark-report-1.0.0
runtime profile: kmeans-backend-profile-1.0.0
auto policy: kmeans-auto-backend-policy-1.0.0
```

CI evidence artifact 中新增：

```text
artifacts/kmeans-backend-benchmark.json
artifacts/kmeans-backend-benchmark.md
artifacts/kmeans-backend-profile.json
artifacts/kmeans-backend-environment.json
```

## 5. 环境指纹

环境指纹包含：

- runtime 与版本；
- operating system；
- architecture；
- logical cores；
- CPU model；
- V8 version；
- WASM 能力；
- SIMD 能力；
- 线程能力。

环境身份经过稳定 FNV-1a 哈希生成：

```text
kmeans-env-xxxxxxxx
```

profile 环境指纹与当前设备不一致时自动失效。

## 6. 交叉点规则

当前规则：

```text
minimum improvement ratio = 1.15
maximum relative IQR = 0.25
required consecutive wins = 2
```

单个 case 只有同时满足以下条件才可视为 WASM 稳定获益：

1. 数值等价 PASS；
2. `TypeScript median / WASM median ≥ 1.15`；
3. TypeScript relative IQR 不超过 0.25；
4. WASM relative IQR 不超过 0.25。

只有连续两个及以上规模满足条件，才标记：

```text
wasm-beneficial
```

若不能形成稳定连续区间，则返回：

```text
insufficient-evidence
```

不会用一个异常快的 case 强行生成交叉点。

## 7. 第一轮固定环境证据

第一轮精确树：

```text
3ca8480e852ca143fbf822cbb3e6cdd80677fe72
```

环境：

```text
Node v22.16.0
Linux x64
4 logical cores
Intel Xeon Platinum 8370C
WASM available
SIMD available but not used
WASM threads not used
```

三个 smoke case 均完成逐数组等价验证：

| Case | N×K×D | TypeScript median/call | WASM median/call | TS/WASM |
|---|---:|---:|---:|---:|
| 64×4×3 | 768 | 0.005377 ms | 0.004063 ms | 1.324 |
| 512×8×5 | 20,480 | 0.046008 ms | 0.023437 ms | 1.963 |
| 4096×12×8 | 393,216 | 1.013339 ms | 0.379664 ms | 2.669 |

该 Node Runner 上的规则分析为：

```text
status: wasm-beneficial
candidate crossover: N×K×D = 768
```

但该 profile 同时明确记录：

```text
source: shared-ci-benchmark
eligibleForRuntimeAutoSelection: false
```

因此上述交叉点只说明该固定 Node/Xeon 环境，不是浏览器、桌面电脑或其他 CPU 的通用阈值。

## 8. 保守自动后端策略

新增：

```text
src/compute/kmeansBackendPolicy.ts
```

显式选择优先级最高：

- `typescript`：始终选择 TypeScript；
- `wasm`：严格请求 WASM，是否回退继续由 `allowFallback` 控制；
- `auto`：进入 profile 决策。

`auto` 只接受同时满足以下条件的 profile：

1. profile、policy、kernel、protocol 版本完全兼容；
2. `source = device-local-benchmark`；
3. `eligibleForRuntimeAutoSelection = true`；
4. 环境指纹与当前设备一致；
5. 未过期；
6. 生命周期不超过 30 天；
7. benchmark digest 存在；
8. 交叉点与状态字段合法。

无 profile、共享 CI profile、过期 profile、环境变化、版本不匹配或证据不足时：

```text
auto → typescript
```

只有兼容的设备本地 profile 明确为 `wasm-beneficial`，并且当前工作量达到该 profile 的交叉点时：

```text
auto → wasm
```

决策证据记录：

- policy version；
- requested backend；
- selected backend；
- reason；
- `N×K×D` 工作量；
- WASM 能力；
- 环境指纹；
- profile 是否接受；
- 拒绝原因；
- profile 状态；
- crossover workload。

## 9. CI 与正式证据

CI 新增：

```text
Deterministic K-Means backend benchmark smoke
```

该步骤的硬门只有：

- runner 可执行；
- WASM 字节可实例化；
- 所有 case 数值等价；
- 报告合同与 digest 可生成。

以下内容仅作信息，不会使共享 CI 红灯：

- TypeScript/WASM 毫秒数；
- speed ratio；
- crossover 状态；
- `wasm-beneficial` 或 `insufficient-evidence`。

benchmark 现已进入：

- validation receipt；
- HTML dashboard；
- Markdown release report；
- PDF validation report；
- 完整 CI evidence artifact。

## 10. 仍未关闭的边界

1. 当前 CI benchmark 是 Node WASM，不是 Chromium Worker benchmark；
2. 当前产品没有自动运行浏览器本地完整 benchmark 的 UI；
3. 浏览器 profile 的安全本地存储、重新测量触发和用户清除入口尚未实现；
4. 第一轮 smoke case 不能替代完整规模扫描；
5. SIMD 虽然在 Runner 上可用，但当前内核没有使用 SIMD；
6. 当前不能宣称所有设备在 `N×K×D=768` 后都应启用 WASM；
7. 具体商业性能声明仍需目标硬件、目标浏览器、预热、多轮重复和完整 benchmark 证据。

## 11. 下一阶段

下一阶段优先级：

1. Chromium Worker 固定环境 benchmark；
2. 浏览器本地 profile 生成、验证、过期和清除流程；
3. 根据浏览器实测交叉点接入 K-Means Worker payload；
4. 完整 benchmark 多运行环境对比；
5. 第二个 FP64 WASM 内核候选：Gaussian Process 批量均值预测或 KDE 乘加核心；
6. 任何 SIMD、线程或近似算法必须建立独立等价与回退门。
