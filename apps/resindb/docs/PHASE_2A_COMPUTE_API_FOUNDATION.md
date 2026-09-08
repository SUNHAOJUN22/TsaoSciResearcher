# ResinDB Pro Phase 2A：Compute API 基础层

## 1. 阶段定位

本阶段在不修改现有 React 页面、科学 Worker、树脂数据和算法输出的前提下，建立统一科学计算入口。当前只启用 TypeScript 参考后端，WASM、WebGPU 和 Edge/CUDA 后端仅保留能力标识与路由扩展位。

## 2. 已实施内容

新增 `src/compute/`：

- `types.ts`：后端、精度、优先级、任务、数值矩阵和证据合同。
- `capabilityProbe.ts`：CPU 并发、设备内存、WASM、SIMD、线程条件、WebGPU 和边缘服务能力探测。
- `taskProtocol.ts`：任务 ID、外部取消、超时和中止竞态处理。
- `kernelRegistry.ts`：算法内核注册、版本标识、重复注册阻断和缺失内核错误。
- `computeEvidence.ts`：输入形状、算法版本、后端、精度、耗时、能力快照和回退状态收据。
- `backendRouter.ts`：`edge → webgpu → wasm → typescript` 自动选择顺序，以及显式后端回退政策。
- `backends/typescriptBackend.ts`：保留科学正确性的 TypeScript CPU 参考后端。
- `computeEngine.ts`：统一 `register()` 与 `run()` 接口。
- `index.ts`：稳定导出边界。

## 3. 调用合同

```ts
import { computeEngine } from '@/compute';

computeEngine.register({
  id: 'example-kernel',
  version: '1.0.0',
  supportedBackends: ['typescript'],
  supportedPrecisions: ['f64'],
  execute: (input: Float64Array) => input.reduce((sum, value) => sum + value, 0),
});

const result = await computeEngine.run<Float64Array, number>({
  kernel: 'example-kernel',
  backend: 'auto',
  precision: 'f64',
  input: new Float64Array([1, 2, 3]),
});
```

成功结果同时返回 `output` 和 `evidence`。显式指定的后端不可用时默认报错；只有 `allowFallback: true` 才允许回退并在证据中记录。

## 4. 科学与安全边界

- 本阶段没有迁移或改写任何现有科学算法。
- TypeScript 后端继续作为未来 WASM、WebGPU 和 CUDA 的数值参考实现。
- FP32 与 FP64 必须由内核显式声明支持范围。
- 任务超时会主动拒绝调用，即使内核没有读取 `AbortSignal`。
- Edge 服务默认视为不可用，必须由可信连接探测显式开启。
- WebGPU 能力存在不代表某个科学内核允许使用 GPU，最终选择还受内核支持声明约束。

## 5. 测试覆盖

`tests/unit/computeEngine.test.ts` 验证：

1. TypeScript 内核执行与完整证据收据。
2. TypedArray、矩阵和嵌套数组输入形状。
3. 显式后端回退政策。
4. 不允许回退时的阻断。
5. 外部取消传播。
6. 忽略信号内核的强制超时。
7. 能力探测的确定性输入。
8. 重复内核注册阻断。

阶段一工具链测试同时新增了运输残留动态注入测试，防止 `.github/.resindb-*delta/patch/transport*` 目录再次漏过 CI。

## 6. 本阶段退出条件

- `npm run validate:docs` 通过。
- `npm run validate:source` 通过。
- `npm run lint` 通过。
- `npm run typecheck` 通过。
- `npm run test:unit` 和完整 `npm test` 通过。
- 覆盖率、生产构建、HTTP/UI smoke 和依赖审计不回退。
- 精确树 GitHub Actions 状态为成功。

## 7. 后续阶段

Phase 2B 将在本合同之上建设 Lazy Worker Pool、任务队列、进度协议、空闲回收和 Transferable 数据传输。现有 Worker 在完成逐个适配前继续保持原实现，不进行一次性大规模替换。
