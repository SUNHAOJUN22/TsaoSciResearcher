# ResinDB Pro Phase 2J：设备 Profile 审计、迁移与第二内核候选评估

## 1. 阶段定位

Phase 2J 承接 Phase 2I 的浏览器 Worker 本机 K-Means 校准与 IndexedDB profile 生命周期，完成：

1. profile 只读审计视图和隐私安全 JSON 导出；
2. audit JSON 导入后的重新校验，但永不激活运行时 profile；
3. 浏览器、架构、核心数与 WASM 能力变化时的保守失效策略；
4. 本地 K-Means backend decision history；
5. 四个第二 FP64 WASM 内核候选的代码级评估；
6. 明确撤回越过本阶段授权范围的 KDE WASM 中间实现。

本阶段继续遵守：

- 仅远程 `main`；
- 不建立 branch 或 PR；
- FP64 正式计算；
- TypeScript FP64 为权威参考；
- K-Means WASM 失败时安全回退；
- 不上传 profile、audit 或 decision history；
- 不保存原始材料数据、聚类输入或用户身份；
- 第二内核仅评估，不进入生产运行路径。

## 2. 审计文档合同

新增和更新：

```text
src/compute/kmeansProfileAudit.ts
schemas/kmeans-profile-audit.schema.json
```

审计文档版本：

```text
kmeans-profile-audit-1.0.0
```

只读审计文档包含：

- profile schema 和 policy version；
- kernel 和 kernel version；
- FP64 protocol version；
- profile 生成和失效时间；
- 浏览器 Worker 环境指纹；
- benchmark report SHA-256；
- profile decision status；
- crossover workload；
- profile 加载与验证状态；
- 当前 `auto` decision；
- migration event 和 migration history；
- 最多 50 条隐私安全 decision history；
- audit 自身 SHA-256。

审计环境默认不导出完整 User-Agent、CPU 型号、网络地址、平台字符串、架构或逻辑核心数，只保留：

```text
fingerprint
runtime category
WASM capability
SIMD capability
WASM thread capability
```

完整计算环境仍留在设备本地 profile 数据库中，用于迁移校验，不进入默认 audit export。

## 3. 导出隐私边界

审计文档固定声明：

```text
scope: device-local-non-product-metadata
notice: not-a-cross-device-performance-conclusion
importPolicy: audit-import-never-activates-runtime-profile
```

固定排除：

```text
product-data
clustering-inputs
raw-benchmark-samples
user-identity
network-addresses
```

导出文件不是可移植性能 profile，也不能直接控制其他设备的 `auto` 后端选择。

## 4. Audit JSON 只读导入

新增：

```text
validateKMeansProfileAuditImport(...)
```

人工导入后必须重新验证：

1. audit schema version；
2. SHA-256 digest；
3. import policy；
4. profile schema 和 auto policy version；
5. kernel、kernel version 和 protocol；
6. profile 来源必须为 `device-local-benchmark`；
7. shared CI profile 必须拒绝；
8. generated/expires 时间；
9. profile 是否过期；
10. 当前浏览器 Worker environment fingerprint；
11. WASM/SIMD/thread capability 是否匹配。

即使全部验证通过，结果仍固定为：

```text
auditOnly: true
canActivateRuntimeProfile: false
```

导入路径不会调用 `kmeansBackendProfileStore.save()`，不会写入 active profile，也不会改变 K-Means `auto` decision。

## 5. 浏览器环境变化与迁移策略

迁移策略版本：

```text
kmeans-profile-migration-policy-1.0.0
```

以下变化必须使 profile 失效并要求重新校准：

- runtime kind；
- browser/runtime version；
- platform；
- architecture；
- logical core count；
- WASM capability；
- SIMD capability；
- WASM thread capability；
- profile schema/policy/kernel/protocol 不兼容；
- profile 过期或字段损坏。

唯一允许的自动迁移是：所有计算环境字段完全一致，仅稳定 fingerprint 算法产生了不同键值。此时只允许 re-key，并记录 migration event。

任何迁移写入失败时，profile 不会返回给 `auto`；K-Means 保守使用 TypeScript。

## 6. K-Means decision history

新增：

```text
src/compute/kmeansDecisionHistoryStore.ts
```

数据库：

```text
resindb-kmeans-decision-history-v1
```

最多保留 50 条，仅记录：

- timestamp；
- requested backend；
- policy selected backend；
- actual backend；
- decision reason；
- profile accepted/rejected；
- rejection reason；
- fallback used/reason；
- workload operations；
- environment fingerprint。

明确不记录：

- material grade；
- property name/value；
- product object；
- sample matrix；
- formula；
- user identity；
- network information。

IndexedDB 不可用或写入失败不会阻止 K-Means 返回结果。

## 7. UI

K-Means 校准面板的审计详情现在直接显示：

- validation state；
- profile schema；
- kernel/version；
- protocol；
- generated/expires；
- environment fingerprint；
- benchmark digest；
- profile status；
- crossover workload；
- decision history count；
- current auto decision/reason；
- audit SHA-256。

提供：

```text
Copy summary
Export JSON
Import audit JSON
```

导入后的 UI 文案必须明确：只读查看，不能激活运行时 profile。

## 8. 第二 FP64 WASM 内核候选

正式报告：

```text
docs/SECOND_WASM_KERNEL_CANDIDATE_REPORT.md
```

候选：

1. KDE separable row accumulation；
2. Gaussian-process batch prediction；
3. RSM QR/SVD；
4. Sobol/Jansen sampling and hybrid evaluation。

结论：

```text
status: insufficient-evidence
preferredFutureCandidate: kde-separable-row-accumulation
productionMigrationAuthorized: false
```

KDE 排名第一，原因是连续 FP64 缓冲区、无随机序列、无秩/条件数决策、逐数组等价边界清晰。但仍缺少目标浏览器交叉点、device-local backend profile、memory/trap/cancellation UAT 和独立验收，因此本阶段不得迁移。

## 9. 范围纠正

Phase 2J 中间树曾加入 KDE WASM C/TS 实现并接入生产 Worker。该实现超出用户“仅审计、不立即迁移”的明确授权，已通过前向提交完整删除：

- 删除 KDE WASM C source；
- 删除嵌入 binary wrapper；
- 删除 backend session；
- 删除 WASM 等价测试；
- 恢复 Phase 2I TypeScript KDE Worker 和性能合同；
- 从公共 compute exports 移除 KDE WASM。

保留的是候选分析结论，不是生产代码。

## 10. Chromium 启动稳健性

新增：

```text
scripts/run-ui-smoke-suite.mjs
```

仅当主 Chromium smoke 明确失败于：

```text
Timed out waiting for http://127.0.0.1:9224/json/version
```

才使用完全相同的 UI smoke 重试一次。页面断言、控制台错误、截图、数据、审计字段或交互失败不会重试掩盖，仍立即阻断。

## 11. Phase 2J 完成边界

```text
PROFILE_AUDIT_VIEW = IMPLEMENTED
PROFILE_AUDIT_EXPORT = IMPLEMENTED
PROFILE_AUDIT_IMPORT = READ_ONLY_VALIDATED
CROSS_DEVICE_RUNTIME_ACTIVATION = PROHIBITED
ENVIRONMENT_MIGRATION_POLICY = IMPLEMENTED
DECISION_HISTORY = DEVICE_LOCAL_PRIVACY_SAFE
SECOND_WASM_CANDIDATE_REPORT = COMPLETE
SECOND_WASM_PRODUCTION_KERNEL = NOT_IMPLEMENTED
```
