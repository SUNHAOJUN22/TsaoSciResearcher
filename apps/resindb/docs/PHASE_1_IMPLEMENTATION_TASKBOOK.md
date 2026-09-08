# ResinDB Pro 阶段一实施任务书

## 1. 基本信息

- **阶段名称：** 工具链统一与跨平台兼容基线
- **适用版本：** ResinDB Pro 3.2.0
- **目标分支：** `main`
- **执行方式：** 直接提交 `main`；禁止创建临时开发分支和 PR
- **技术基线：** Node.js 22 LTS、npm 10+、React、TypeScript、Vite
- **上位方案：** 《ResinDB Pro 原生计算与边缘加速改进方案 V1.0》

## 2. 阶段目标

本阶段不改变树脂数据、科学算法、页面交互和图表表现，只统一开发与验证工具链，为后续 Compute API、C++/WASM 和边缘计算建设提供稳定基线。

必须完成：

1. 将三个 Python 辅助脚本迁移为 Node.js ESM。
2. 删除仓库和 CI 对 Python 的强制依赖。
3. 保持 22 张 README 科研 SVG 的文件名、字节内容和 SHA-256 不变。
4. 保持源码卫生规则、README 链接检查、数据合同和临时残留检查不降级。
5. 建立可恢复、可更新、可审计的确定性视觉资产包。
6. 在 Windows、macOS、Linux 可使用同一组 npm 命令。
7. 保持永久 CI 只读并只接受 `main`。

## 3. 范围

### 3.1 纳入范围

- `scripts/generate-readme-visuals.py`
- `scripts/validate-repository-docs.py`
- `scripts/validate-source-hygiene.py`
- `package.json`
- `.github/workflows/ci.yml`
- `README.md`
- `docs/README_VISUAL_DESIGN_SYSTEM.md`
- `docs/VALIDATION.md`
- 阶段一工具链回归测试

### 3.2 不纳入范围

- C++/CMake 工程
- WebAssembly 编译
- WebGPU Kernel
- CUDA 边缘服务
- Worker Pool 重构
- 科学算法数值迁移
- UI 大规模重构

上述内容分别进入后续阶段，不得在本阶段夹带实施。

## 4. 工作分解结构

### WBS-1：基线审计

- 统计 Python 文件和调用位置。
- 记录 22 张 SVG 的 SHA-256、大小和清单。
- 检查 package scripts、README、设计文档和 CI 中的 Python 引用。
- 保存迁移前验证结果。

### WBS-2：视觉工具迁移

新增：

- `scripts/readme-visuals.bundle.json`
- `scripts/bundle-readme-visuals.mjs`
- `scripts/generate-readme-visuals.mjs`

要求：

- 资产包使用 gzip + Base64 保存 canonical SVG 字节。
- 每个文件记录 SHA-256 和未压缩字节数。
- `visuals:generate` 可恢复被删除或损坏的 SVG。
- `visuals:check` 必须逐字节验证 22 张图。
- `visuals:bundle` 只用于经过审核的有意图像更新。
- 不依赖网络、浏览器、字体下载或第三方 npm 包。

### WBS-3：文档验证迁移

新增 `scripts/validate-repository-docs.mjs`，必须覆盖：

- README 本地链接存在性。
- package、README、验证合同版本一致性。
- 22 张图清单和 README 单次引用。
- SVG accessibility/design metadata。
- 视觉资产包哈希一致性。
- 数据治理根目录合同。
- 永久 CI 只读要求。
- 临时工作流、触发器和迁移载荷清零。
- `scripts/` 下无 Python 文件。
- CI 不调用 Python。

### WBS-4：源码卫生迁移

新增 `scripts/validate-source-hygiene.mjs`，保留并验证以下禁止项：

- `@ts-ignore` / `@ts-nocheck`
- `eslint-disable`
- `dangerouslySetInnerHTML`
- `eval()`
- `new Function()`
- `TODO` / `FIXME` / `HACK`

扫描范围保持 `src/**/*.{ts,tsx,js,jsx,mjs}`，发现问题必须输出文件、行号、规则和原文。

### WBS-5：命令与文档统一

package scripts 统一为：

```text
visuals:bundle   → node scripts/bundle-readme-visuals.mjs
visuals:generate → node scripts/generate-readme-visuals.mjs
visuals:check    → node scripts/generate-readme-visuals.mjs --check
validate:docs    → node scripts/validate-repository-docs.mjs
validate:source  → node scripts/validate-source-hygiene.mjs
```

同步更新 README、视觉设计系统和验证合同，删除 Python 环境要求。

### WBS-6：测试与验收

至少验证：

1. 资产包包含且只包含 22 张图。
2. 资产包 SHA-256 与提交的 SVG 一致。
3. 删除临时目录中的图后可以重新生成。
4. 篡改 SVG 后 `visuals:check` 必须失败。
5. 源码卫生扫描文件数不为零。
6. 文档检查能识别 Python 残留和临时迁移文件。
7. 原有完整回归、科学 Worker、覆盖率、构建、HTTP、UI 和依赖审计全部保持通过。

## 5. 接口和兼容性要求

- CLI 返回码：成功 `0`，失败非 `0`。
- 所有路径通过 `import.meta.url` 和 Node `path` 解析，不依赖当前 shell 类型。
- 统一使用 UTF-8。
- 不使用 Bash 专属逻辑实现核心功能。
- 不修改 SVG 字节、换行或 XML metadata。
- Node 版本遵循 `.nvmrc` 和 `package.json#engines`。

## 6. 交付物

- 本实施任务书。
- 三个 Node.js 替代工具。
- 一个确定性视觉资产包。
- 更新后的 npm scripts。
- 更新后的 README、视觉设计合同和验证合同。
- 删除三个 Python 文件。
- 完整验证日志和 CI 工件。

## 7. 验收命令

```bash
npm ci
npm run visuals:check
npm run validate:docs
npm run validate:source
npm run validate:data
npm run lint
npm run typecheck
npm run test
npm run test:unit
npm run test:science
npm run test:coverage
npm run build
npm run smoke
npm run test:ui
npm run audit:prod
npm run audit:all
```

## 8. 退出条件

阶段一只有同时满足以下条件才可关闭：

- `scripts/` 下不存在 `.py` 文件。
- README 和 CI 不再要求 Python。
- 22 张 SVG 的 SHA-256 与迁移前一致。
- Node 生成、检查和文档验证全部通过。
- 原有功能和科学计算测试无回归。
- `main` 是唯一远程分支。
- 永久 CI 对正式 `main` 提交全绿。

## 9. 风险与回退

- **视觉资产损坏：** 以 bundle SHA-256 和原 SVG 哈希双重阻断。
- **跨平台路径差异：** 禁止硬编码 `/` 和 shell 专属路径。
- **验证规则缩水：** Node 版本逐条映射原 Python 规则，并增加 Python 残留检查。
- **发布失败：** 不移动 `main`；保留已验证父提交和本地冻结 commit。
- **功能回归：** 任何原有质量门失败均停止交付，不允许跳过测试。
