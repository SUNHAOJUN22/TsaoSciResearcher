# ResinDB Pro Phase 2B：Lazy Worker Pool 与统一任务通道

## 1. 阶段定位

本阶段在 Phase 2A Compute API 合同之上统一浏览器 Worker 的生命周期和任务调度。目标是不改写现有科学算法输出，通过公共 `useWorkerManager` 让全部现有科学 Hook 自动获得懒创建、统一排队、并发上限、取消、超时、进度和空闲回收能力。

## 2. 已实施内容

新增 `src/compute/` 基础设施：

- `workerPool.ts`：全局优先级队列、按内核键复用 Worker、动态并发上限、运行中取消、超时终止和空闲销毁。
- `workerProtocol.ts`：统一 `PROGRESS` 消息、进度归一化、Worker 错误提取和任务发送选项。
- `transferables.ts`：递归收集并去重 `ArrayBuffer`、TypedArray 和浏览器可传输对象，不把 `SharedArrayBuffer` 误作 Transferable。

更新 `useWorkerManager`：

- React Hook 挂载时不再创建 Worker。
- 第一次 `postMessage()` 时才向共享池提交任务。
- 默认以成功消息类型作为稳定池键，使同类 Worker 可跨 Hook 实例复用。
- 新任务会安全取消同一 Hook 的旧任务，避免响应串线。
- 返回 `progress`、`activeTaskId` 和 `cancel()`。
- `postMessage()` 支持显式 Transferable 列表、优先级、外部 `AbortSignal`、超时和进度回调。
- 组件卸载时终止其活动任务；空闲 Worker 由共享池延迟销毁。

## 3. 调度政策

默认最大并发根据设备逻辑核心数计算：

```ts
Math.max(1, Math.min(4, navigator.hardwareConcurrency - 1))
```

任务优先级顺序：

```text
interactive → scientific → background
```

同一优先级保持 FIFO。页面进入后台时有效并发自动降为 1；页面恢复可见后继续泵送队列。默认空闲回收时间为 30 秒。

## 4. 进度协议

Worker 可发送：

```ts
{
  type: 'PROGRESS',
  payload: {
    ratio: 0.4,
    completed: 400,
    total: 1000,
    phase: 'sampling',
    message: 'optional'
  }
}
```

`ratio` 会被限制到 `[0, 1]`。缺少 `ratio` 时，可由有限的 `completed / total` 推导。Monte Carlo、Sobol 和 K-Means 已接入分阶段进度消息；最终科学结果结构保持不变。

## 5. Transferable 数据通道

调用方必须显式选择要转移所有权的缓冲区，防止无意分离仍在 UI 使用的 TypedArray：

```ts
const values = new Float64Array([1, 2, 3]);
postMessage(
  { type: 'RUN', values },
  { transfer: [values.buffer], priority: 'scientific' },
);
```

也可以使用 `collectTransferables()` 从受控的嵌套输入中收集并去重缓冲区。当前阶段建立通道和测试，不强制把仍使用对象数组的旧算法一次性改为 TypedArray。

## 6. 科学与兼容性边界

- 不改变现有 Worker 的成功消息和结果 payload。
- 不把所有任务强制并行；全局并发由设备资源和页面状态约束。
- 取消运行中任务采用终止 Worker 的确定性方式，避免无法中断的数值循环继续占用 CPU。
- 显式 Transferable 会分离发送端 `ArrayBuffer`，调用方必须确认发送后不再读取原缓冲区。
- 本阶段只增加 Monte Carlo、Sobol 和 K-Means 进度，不改变其随机算法和数值方法；可复现 RNG 与算法优化属于后续阶段。

## 7. 测试覆盖

`tests/unit/workerPool.test.ts` 验证：

1. Worker 按需创建、同键复用和空闲销毁。
2. 交互、科学和后台优先级队列。
3. Transferable 去重和真实 `postMessage` 传递。
4. 进度消息归一化。
5. 活动任务取消与 Worker 终止。
6. 无响应 Worker 的强制超时。
7. 池键释放对排队和运行任务的关闭。
8. 循环嵌套对象的 Transferable 安全收集。

`tests/unit/useWorkerManager.test.tsx` 验证公共 Hook 的懒创建、进度、结果、任务 ID、Transferable、卸载和任务替换行为。

## 8. 阶段退出条件

- 全部现有 Worker Hook 不再在组件挂载时预创建 Worker。
- `npm run lint`、`npm run typecheck`、完整测试、科学 Worker 测试和全源码覆盖率通过。
- 生产构建、HTTP/UI smoke、依赖审计和单一 `main` 分支证明通过。
- 精确树 GitHub Actions 生成新的完整证据包并返回成功状态。

## 9. 后续阶段

下一阶段应进入 Phase 2C：Seeded RNG、随机算法版本化、Monte Carlo/K-Means 可复现回归、Sobol 命名与采样边界纠正，以及 RSM QR/SVD 数值参考求解器。
