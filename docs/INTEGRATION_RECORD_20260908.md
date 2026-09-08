# astra-pro-1 合并记录

唯一代码维护目标：`SUNHAOJUN22/TsaoSciResearcher`，产品名 TsaoScience。

## 已生成的合并

合并提交 `78cfb7ea57bdc4f0da81ba9708f68937e56c8e64`，树 `5192af0efb981f7897adb89f70a52fcf55c0f0a9`。Researcher 原主线作为祖先，另外六库的固定源提交作为合并父提交；各源库历史在同一 Git 对象图中可追溯。工作树不使用 submodule。

`migration/source-map.json` 映射 3,295 个原文件。`migration/patches.json` 记录 16 个已修改原文件的前后摘要。原有许可与受控分类保留。

## 真实构建记录

迁移构建：`https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/runs/34198695715`。

构建在固定源码上应用经摘要验证的代码变更，执行源文件完整性检查、59 项新集成测试和 84 项选定原有回归（另有 17 个子测试）、DFT 原有四个严格类型检查目标，以及 ResinDB 的安装、外发治理检查、TypeScript、完整 Vitest 测试与生产构建。实际 TypeScript 代码的五项发送快照检查和十组 Python/TypeScript 摘要向量也通过。

迁移构建的环境 SHA 是迁移脚本提交，不应冒充后生成的最终源码提交。最终提交及后续修改仍需在根永久 CI 中重新执行。本文件保留该区别，不把这次迁移运行当成任意后来提交的证据。

## 唯一维护入口与退役

六个来源仓库只保留历史回滚与迁移指引；不再作为独立开发或发布来源。完成切换前必须核查统一主线、相应测试和源库并发修改。平台上的 archive/delete 标志与代码级退役不同，不由一份 Markdown 声明自动生效。

## 验证范围

以上是所列软件测试，不是七库全部历史资格检查的重新执行，不代表真实 Aspen、DFT 引擎、外部 AI、实验、工艺认证或科学批准。完整原测试和方法资料保留在组件中。未执行能力按对应运行状态继续保持待验证。
