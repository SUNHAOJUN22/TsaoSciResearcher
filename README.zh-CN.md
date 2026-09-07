# TsaoDFT Skill 中文说明

本仓库的**规范中文 README 已统一维护在 [`README.md`](README.md)**，避免两个中文文件长期漂移。本文件只保留中文导航、代码质量边界和验收边界。

<p align="center"><img src="assets/ai/hero/tsao-dft-hero.svg" alt="TsaoDFT AI-assisted conceptual hero" width="100%"></p>

> 上图和主 README 中的模块场景图属于 AI 生成或 AI 辅助概念图，只用于平台与研究场景表达，不是轨道、ESP、能带、自由能、机理或实验数据。

## 维护与去重策略

- `scripts/` 只保留可重复执行的构建、验证、分析和发布工具；已经完成使命、会原地改写仓库的单次迁移脚本不得长期留在生产树中。
- legacy CLI 可以作为兼容适配层存在，但最终状态、有限数判断、数量种类和形状必须服从规范 parser contract，不能维护第二套相互漂移的验收语义。
- Python 字节码、覆盖率数据库、临时构建目录和一次性修复工作流不得进入版本库。

文件身份计算复用 `engine_scan_core.sha256_file`，规范 parser 保留同名薄适配入口。`chunk_size` 必须是非 Boolean 的正整数；实际单次读取最多 1 MiB。非法大小在打开工件前拒绝，避免非空文件因零缓冲被误标成空内容摘要。有效缓冲大小不改变文件摘要；此项是内存上界与正确性保证，不是未经测量的速度提升声明。

*The parser delegates artifact hashing to the shared scan core. Positive, non-Boolean chunk sizes preserve the exact digest, with each read capped at 1 MiB; invalid sizes are rejected before opening the source. No measured throughput gain or external DFT qualification is implied.*

## 资格与科学边界

仓库 CI、parser contract、覆盖率和 legacy-smoke 通过，只能证明软件合同在被测提交上成立。它不等于 Gaussian、VASP、Quantum ESPRESSO 或 CP2K 已在真实许可/算力环境执行，也不等于计算结果获得独立科学验收。

真实外部执行在缺少可验证的输入、程序/赝势版本、环境、输出摘要、签名回执和独立复核时，必须保持：

```text
EXTERNAL_DFT_EXECUTION_NOT_VERIFIED
```

请直接阅读：

- [`README.md`](README.md)：完整中文说明、DFT 能力、安装、验证和图像治理；
- [`README_EN.md`](README_EN.md)：English documentation；
- [`README_ACCEPTANCE.md`](README_ACCEPTANCE.md)：软件资格与科学验收边界；
- [`docs/AI_IMAGE_GOVERNANCE.md`](docs/AI_IMAGE_GOVERNANCE.md)：AI 图像证据边界；
- [`docs/ENGINE_SUPPORT_MATRIX.md`](docs/ENGINE_SUPPORT_MATRIX.md)：引擎支持等级。
