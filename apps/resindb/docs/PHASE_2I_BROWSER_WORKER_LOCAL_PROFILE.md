# ResinDB Pro Phase 2I：浏览器 Worker 本机校准与 Profile 生命周期

## 1. 阶段定位

本阶段承接 Phase 2H 的固定环境 benchmark 与保守自动后端策略，把版本化 benchmark/profile 合同真正接入浏览器设备本地运行环境。

阶段目标：

1. 在专用浏览器 Worker 中完成 TypeScript/WASM FP64 等价与性能校准；
2. 生成只属于当前浏览器 Worker 环境的设备本地 profile；
3. 使用独立 IndexedDB 存储 profile；
4. 在每次 K-Means `auto` 运行前读取 profile；
5. 在 K-Means Worker 内再次校验环境指纹、版本和有效期；
6. 没有可信 profile 或任何本地设施失败时，保守使用 TypeScript；
7. 为用户提供运行、取消、查看与清除本机校准的可见界面。

本阶段继续遵守：

- 仅远程 `main`；
- FP64 正式计算；
- TypeScript FP64 是权威参考；
- WASM 初始化或运行失败时安全回退；
- 不改变 Seeded RNG、K-Means++、空簇重置、Silhouette 或候选 K 选择；
- 本机 profile 不上传外部服务；
- 共享 CI 不执行完整设备校准，也不生成可控制用户运行时的 profile；
- 不宣传未经目标设备验证的固定加速倍数。

## 2. 浏览器 Worker Benchmark

新增：

```text
src/compute/kmeansBrowserBenchmark.ts
src/workers/kmeansBenchmarkWorker.ts
```

浏览器 benchmark 使用当前产品实际嵌入的 FP64 WASM assignment/update 内核和同顺序 TypeScript 参考后端。

Worker 支持：

```text
RUN_KMEANS_BROWSER_BENCHMARK
→ PROGRESS
→ KMEANS_BENCHMARK_COMPLETE
```

执行发生在独立 Worker，不阻塞 React 主线程，并复用现有 Worker Manager 的：

- 任务优先级；
- 进度；
- 取消；
- 超时；
- Worker 复用与销毁；
- 错误边界。

默认完整校准超时为 120 秒。用户取消或超时不会影响正常 K-Means；下一次聚类仍可使用 TypeScript。

## 3. 测量合同

浏览器 benchmark 固定：

- seed；
- 样本数 `N`；
- 维度 `D`；
- 簇数 `K`；
- 预热次数；
- 重复次数；
- 每次重复的内核调用数；
- TypeScript/WASM 交替执行顺序。

每个 case 在计时前和每个重复后均逐项比较：

- assignments；
- centroid sums；
- counts；
- changed assignment count。

任何差异会使校准失败，不保存 profile。

计时使用 Worker 内的：

```text
performance.now()
```

报告保存：

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
- 绝对中位数差；
- 等价状态；
- 交叉点分析；
- SHA-256 report digest。

## 4. 浏览器环境指纹

benchmark 与实际 K-Means profile-aware Worker 均调用同一环境构造器：

```text
createKMeansBenchmarkEnvironment()
```

在 Worker 中，环境 runtime 为：

```text
browser-worker
```

指纹包含：

- Worker user agent/runtime version；
- platform；
- architecture（浏览器不可得时为 unknown）；
- logical cores；
- WASM；
- WASM SIMD 能力；
- WASM threads 能力。

环境身份经过稳定哈希生成。profile 只能在完全匹配的 Worker 环境使用。

主线程不会自己推断 Worker profile 是否可控制后端；真正决策仍在 K-Means Worker 内完成。

## 5. Device-local Profile

校准完成后生成：

```text
source: device-local-benchmark
eligibleForRuntimeAutoSelection: true
```

profile 包含：

- schema version；
- auto policy version；
- kernel/version；
- FP64 protocol version；
- generatedAt；
- expiresAt；
- Worker environment fingerprint；
- status；
- crossover workload；
- improvement/IQR/consecutive-win 规则；
- benchmark report digest。

profile 状态仍可能是：

```text
wasm-beneficial
typescript-preferred
insufficient-evidence
```

“校准完成”不等于 WASM 必然被选中。若证据不足，profile 会被接受但 `auto` 仍使用 TypeScript。

## 6. 独立 IndexedDB 生命周期

新增：

```text
src/compute/kmeansBackendProfileStore.ts
```

数据库：

```text
resindb-kmeans-backend-profile-v1
```

该数据库与树脂产品数据库分离，避免性能配置污染科学数据与产品目录 schema。

生命周期：

```text
benchmark complete
→ validate
→ save
→ load before auto K-Means
→ validate again inside Worker
→ expire/invalidate/clear
```

读取时检查：

- profile 存在；
- schema/policy/kernel/protocol 兼容；
- 来源为设备本地 benchmark；
- eligible 标志；
- stored Worker environment；
- generatedAt/expiresAt；
- 最大有效期；
- status 与 crossover 一致；
- digest 存在。

过期或损坏 profile 自动失效并尝试删除。

IndexedDB 不可用、读取失败、写入失败或清除失败均显式返回错误，但不会阻止普通 K-Means 使用 TypeScript。

不使用 Cookie，不上传 profile，不写入不可控全局变量。

## 7. 实际 K-Means 接入

新增适配 Worker：

```text
src/workers/kmeansProfileAwareWorker.ts
```

选择适配层而非复制 K-Means Worker，原因是：

- 原 K-Means 数学代码已经通过完整科学门；
- 复制 500 余行会造成双实现漂移；
- profile 策略属于后端路由，不应混入聚类公式；
- 包装层可在调用原 Worker 前决策，在结果返回时补写真实 evidence。

流程：

```text
useKMeansWorker
→ load local profile for auto request
→ profile-aware Worker
→ recreate current Worker environment fingerprint
→ validate/decide backend
→ original K-Means Worker with explicit selected backend
→ restore requestedBackend=auto in evidence
→ return actual backend and decision reason
```

显式用户选择优先级保持不变：

```text
typescript → TypeScript
wasm       → WASM (subject to fallback option)
auto       → device-local profile policy
```

若 profile 缺失、失效、环境不匹配、过期或证据不足：

```text
auto → TypeScript
```

若兼容 profile 标记 `wasm-beneficial` 且当前 `N×D×maxK` 达到交叉点：

```text
auto → WASM
```

WASM 初始化/运行失败后仍按 Phase 2G 的会话级回退策略切换 TypeScript。

## 8. React Hook 生命周期

新增：

```text
src/hooks/workers/useKMeansBackendCalibration.ts
```

Hook 负责：

- 页面加载时读取 profile；
- 显示 missing/valid/invalid/unavailable/error；
- 启动 full browser benchmark；
- 显示 Worker 进度；
- 用户取消；
- benchmark 成功后保存；
- 写入失败提示；
- 显式清除；
- 清除后刷新状态。

`useKMeansWorker` 在每次 `auto` 计算前重新读取 profile，因此新校准或清除结果会在下一次聚类立即生效，不依赖页面刷新或全局单例状态缓存。

## 9. 用户界面

新增：

```text
src/components/charts/KMeansBackendCalibrationPanel.tsx
```

面板挂载于实际使用 K-Means 的 Canvas Scatter 场景。

显示：

- 当前 profile 状态；
- profile 生成时间；
- 过期时间；
- crossover workload；
- 校准进度；
- benchmark/storage 错误；
- “运行校准”；
- “取消”；
- “清除配置”。

隐私说明明确：

```text
校准在浏览器 Worker 中运行；配置仅保存在本机 IndexedDB，不会上传。
```

界面不显示共享 CI 倍数，也不把 `wasm-beneficial` 等同于产品性能承诺。

## 10. 测试门禁

新增测试覆盖：

1. profile 保存、读取和清除；
2. 过期 profile 自动失效并删除；
3. IndexedDB 读取失败不暴露 profile；
4. 写入和清除失败返回错误；
5. browser Worker benchmark 三个 smoke case 的逐数组等价；
6. benchmark report/profile schema 与 SHA-256 digest；
7. profile-aware Worker 在兼容本地 profile 下选择 WASM；
8. 无 profile 时 `auto` 保守选择 TypeScript；
9. 原 K-Means 显式 TypeScript/WASM 与科学结果保持不变；
10. 全部既有回归、覆盖率和构建门不得退化。

## 11. Chromium UI 证据

新增独立 Chromium 场景：

```text
scripts/ui-kmeans-calibration-smoke.mjs
```

场景执行：

1. 登录测试会话；
2. 打开科研可视化；
3. 切换 Canvas Scatter；
4. 等待校准面板；
5. 展开面板；
6. 验证 IndexedDB/不上传隐私说明；
7. 验证运行和清除控件；
8. 验证初始无 profile 时清除按钮禁用；
9. 捕获截图；
10. 写入现有 UI manifest。

共享 CI 不点击“运行校准”。因此：

- 不生成 CI 浏览器 profile；
- 不把 GitHub Runner 数据写入运行时；
- 不增加计时阈值门；
- 只验证真实产品 UI、Worker/IndexedDB 边界和用户控制存在。

截图：

```text
artifacts/ui-kmeans-device-calibration.png
```

## 12. 已修复的工程问题

实施过程中发现两项非科学代码问题：

1. benchmark report 对象被 TypeScript 扩宽为普通 string，已通过 `as const satisfies` 锁定字面量合同；
2. profile-aware Worker 的顶层动态 import 触发 Worker code splitting，与 Vite IIFE Worker 输出冲突，已改为静态副作用导入，保持单 chunk。

两项均未通过放宽 TypeScript 或构建门处理。

## 13. 仍保留的边界

- profile 当前只存储一份活动 K-Means assignment profile；
- 浏览器校准仅针对当前标量 FP64 WASM 内核；
- 浏览器更新、CPU/核心数变化、policy/kernel/protocol 版本变化会使旧 profile 失效；
- 浏览器可能限制高精度时钟，离散度过大时应返回 `insufficient-evidence`；
- profile 不在设备间同步；
- 无法访问 IndexedDB 的隐私模式中，聚类仍工作，但 `auto` 保持 TypeScript；
- 后续若增加 SIMD/线程内核，必须使用新的 kernel/profile 版本和独立等价门；
- 其他科学模型尚未接入设备本地 benchmark profile。
