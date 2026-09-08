# 验证范围

本轮根测试覆盖共同 JSON 和摘要合同、物理量、任务图、执行授权、原算法调用、并发证据账本、结果篡改检查与关键反例。TypeScript 测试直接执行修改后的实际源码，在替身网络对象上检查审计摘要与发送字节，并检查 Python/TypeScript 共同向量。

`tools/qualify.py` 是本轮集成回归入口。它不伪装成原七个仓库所有完整软件、性能、专用系统和真实求解器资格检查。完整原测试文件仍然保留。未执行的阶段标为未执行；失败阶段使该回执失败；不能从仓库内历史 coverage/report 文件自动继承 PASS。

必须在最终源码提交上读取根 CI。回执记录真实 GITHUB_SHA、运行 ID、重试次数、各阶段退出码和耗时，不手填测试数量或覆盖率。临时运行输出放入独立验证目录，不覆盖来源基线。

本轮没有运行真实 Aspen、Gaussian、VASP、QE、CP2K，也没有调用外部 AI 提供商，没有获得新的科学、工业或公开分发批准。


## astra-pro-2 extended profile

Use `python tools/qualify.py --profile extended`. The manifest is the STAGES and EXTENDED_STAGES code in that executable, not a historical count in this document. The report includes per-stage JUnit counts and its explicitly limited scope. Each invocation uses a unique evidence directory. Root CI adds final software acceptance only after Linux/Windows integration, original strict DFT types and frontend checks finish. Imported result verification is separate from these code tests and does not authenticate measurements.

See INTEGRATION_A2.md for shared-code ownership, runtime versus catalog semantics and the source-history retirement boundary.
