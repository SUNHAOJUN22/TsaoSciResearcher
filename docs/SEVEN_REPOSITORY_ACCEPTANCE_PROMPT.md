# 七仓并行修复与六小时持续软件验收 Prompt

本指令用于直接执行代码修复、文档重写、真实测试及 GitHub 交付。工作对象为 SUNHAOJUN22 的七个仓库：AspenOps-Agent、TsaoSciComputation、TSAO-PROCESSING-SKILL、ResinDB-Pro-by-SunHJ、TsaoDFT_skill、TsaoSciResearcher、OpenDeepMind_skill。以当前远端 main 为基线，不能把过去的审计结论或本地测试结果当作当前版本已完成的证据。

## 1. 角色与执行授权

你是交付负责人，使用实际可用的子代理并行工作。七个逻辑工作包同时规划；并发实例数量遵守运行环境的真实上限，不虚构“已经启动大量代理”。每个子代理在同一时间只负责一个仓库，不跨仓争写。为七个仓库分别维护任务、提交检查点和测试证据；当前环境允许主控加三个子代理同时运行，三个执行槽完成一个仓库后再接手下一仓。主控负责跨仓接口、独立复核、版本冻结和发布。GitHub 验收矩阵可独立启动七个仓库作业。

用户已要求实际修改这七个 GitHub 仓库、重写双语 README、嵌入对应语言的 AI 设计图并自动测试。对必要的可逆修复和正常提交继续执行，不把常规实现选择变成重复审批。不要发送邮件或外部消息。不要加入无关功能，不改变许可证，不把测试夹具伪装成实验。

先读取各仓 AGENTS.md、项目声明、依赖锁、CI、公开入口和源码结构。保存开始时间、远端 SHA、树身份、分支清单和工作区状态。所有仓库只有 main 时不新建长期分支。存在额外分支时，先检查提交差异、是否已经合入及冲突；合并有效修改并验证，只有确认内容完整保留后才清理冗余分支。不得强制推送或覆盖未知更新。发布前重新读取 main，使用 expected SHA 防止覆盖并发提交。

## 2. 修复的共同要求

从实际 CLI、公开 API、前端组件、Worker、存储适配器和执行计划追踪数据。严格函数必须被真实入口调用。不要仅新增一个带新版本号、无人调用的合同模块。

必须检查：

- 数值输入、单位换算、求和、乘除和序列化全链的有限性；拒绝 NaN、Infinity、布尔冒充数值、超大整数溢出、非零下溢及无效范围。
- 物理量的值、单位、维度、形状、测试条件、不确定度、来源和版本一致性；禁止猜测缺失单位或静默用零替换未知。
- 状态转换与证据强度一致；FAIL、HOLD、UNKNOWN、NOT_EVALUATED 不得被缺失字段、空数组或 truthy 字符串升级成 PASS。
- 原始工件、输入快照、运行回执、审批记录之间的引用和摘要绑定；一个格式正确的 SHA 字符串不是实际文件核验。
- 真实命令的 argv、工作目录、输入文件、标准输入和产物依赖；计划生成与执行授权应绑定同一规范化对象。
- 测试通过不能代替外部求解器资格、科学模型验证、工程批准或材料放行。

每个确认缺陷先构造能在原入口复现的反例，再修生产代码，最后同时运行反例、正常路径及既有门禁。测试以行为合同为准，不为迎合实现删掉负例、弱化断言、降低覆盖率或跳过失败模块。旧测试若依赖错误科学语义，应明确记录为何更新其预期。

## 3. 各仓修复清单

### AspenOps-Agent

将优化目标和约束绑定到实际输出单位；未知来源单位不能直接贴标签。统一百分数、分数与温度等工程参数归一化。校验反应元素、质量与明确离子电荷守恒，并对无法确认的数据保留明确状态。为采样加入有限范围和计算预算；Pareto 接口拒绝非有限目标、保持严格支配。JUnit 解析不得将非法失败计数当零、把损坏报告显示成通过。保持原有覆盖率门槛及 Mock／真实 Aspen 资格区分。

### TsaoSciComputation

让 confidence、planner 和状态机消费实际科学接受合同，禁止靠非空 evidence 字符串得到工程就绪。修复 HandoffRecord 的有限性、单位、不确定度和深层不可变性。ScientificQuantity 的单位必须与维度、形状一致。通用 parser 正确识别否定、状态赋值与终止条件。按引擎定义真实 argv，至少正确区分 GROMACS grompp/mdrun 及 QE 输入参数；未实现的执行接口保持 PLAN_ONLY 或相应外部待验证状态。

### TSAO-PROCESSING-SKILL

统一设备、控制、需求、HSE、软件与总状态；任一实质失败不能被总状态掩盖。衡算全链检查中间溢出及下溢，避免 NaN 比较产生误差零。空流程仅可作为明确的 METADATA_ONLY，不得宣称守恒或工程通过。POE 软件结果严格核验字段和状态，证据工件检查真实字节与 SHA；拒绝重复身份、互相矛盾的 status/result、占位摘要及无来源接受声明。更新源码清单与分发工件，保留外部资格边界。

### ResinDB-Pro-by-SunHJ

追踪导入、编辑、批量编辑、create/batchCreate、REST、Worker、表格和图形真实链路。严格解析完整数字，禁止 parseFloat 接受数字后缀。编辑保存保留科学元数据，批量更新使显示值和 canonical value 同步；存储适配器保留治理身份。TOPSIS 不复活无效数量，空有效集不显示假排名，正比例缩放权重保持排名不变；Mahalanobis 不将缺失值补零。公式引擎执行维度代数、无量纲函数和有效输出单位检查。

中文模式与英文模式分别检查文本、按钮、tooltip、弹窗、错误、图例、导出和引导页。材料原始名称可保留来源文字，界面标签必须符合语言模式。修复缺字、替换字符、UTF-8 乱码、字体加载、数学渲染、Canvas/SVG 尺寸和空图。实际浏览器检查导入、公式、数据表、科学图、语言切换、移动尺寸与导出；不得只用源码字符串扫描证明 UI 正确。雷达图不得一边声明面积无绝对含义、一边输出“全能型绝对均衡分”。

### TsaoDFT_skill

让 Eyring CLI 真正使用标准态、参考势垒、反应级数与浓度因子，不能只更改单位标签。QE/VASP/CP2K parser 有界读取并按最后作业隔离版本、能量、收敛与终止信号；保留行、字节和文件摘要。拒绝非有限输出和单位转换溢出。公开 Quantity 接口核验维度及形状。ML 训练完成只表示 training_completed；没有合格数据和独立验证时保持 UNQUALIFIED，数据集输入绑定实际 SHA、划分与来源。

### TsaoSciResearcher

实际 project verify 核验审批台账和状态迁移语义；receipt 核验输入版本、engine、command、产物及摘要。evidence-traceability 不能将占位文本当双向追溯；修复中英因果声明漏检。兼容接口拒绝 truthy 字符串；数值换算避免错误等号。更新派生 README facts、inventory 与受控校验结果。由此仓协调七仓固定版本的六小时软件回归。

### OpenDeepMind_skill

核对评分摘要与逐项断言计数、比率及通过条件；空断言、红色阻断、模块泄漏或错误 TRIZ 启用不能通过。根据运行元数据计算机械可检验指标，总通过率与成对比较共用判定。重复与孤立工件阻断完整性，极大 repetition 在路径构造前拒绝。JSON 有大小、深度、有限数和 Unicode 边界。v16/v17 命题类型与 D/O/L/C/A/E/V/U 规范一致，严格布尔、唯一槽位和归一化分数；完整工件不得自行授予 publication_ready。将未被既有 unittest 发现的有效测试纳入发现机制。保留模块隔离、显式 TRIZ 和留出集边界。

## 4. README 与图像交付

每仓重写独立中文和英文 README，入口互链。文档依据最终源码说明：定位、真实能力、限制、安装、快速运行、输入输出、目录、数学条件、使用策略、测试、排错、许可和引用。公式逐一定义符号、单位、有效范围、边界和代码位置；分清实际实现的数值计算与方法论建模模板。使用 GitHub 可渲染的 Markdown、美元符号数学分隔符和简洁 Mermaid。

每仓提供中文 vision-zh.png 与英文 vision-en.png，保存于 docs/assets，并嵌入相应语言 README。使用内置 imagegen 生成有艺术设计、科学主题和少量概念公式的愿景插图；检查主标题、中文字形和公式，必要时重生成。不要把精确数据图交给生成模型，不伪造图表数据、认证或已实现功能。概念图注明其性质；准确数学内容保留正文。检查 README 所有图片，不仅检查新图：本地路径、大小写、字体、SVG foreignObject、外部依赖、缺字、乱码和可读性。

交付是修改好的仓库及 README，不单独把一堆图片当作完成结果。

## 5. 基线门禁与复核

在隔离、按锁文件安装的环境运行原有完整门禁，包括编译、类型、lint、测试、覆盖率、构建、安装、包内资源和派生内容一致性。使用所需 Node/Python 版本。工具缺失属于环境问题，应解决后重跑，不能写成产品通过。外部许可证或真实硬件缺失则准确标记外部待验证，不能伪造执行。

记录每项真实命令、版本、退出码、耗时及日志。解释原有 skip 的原因，新增 skip 必须有真实条件，不得把失败改为 skip。由不同代理复核至少一个关键数学或证据路径，修复复核发现后再运行相关回归。检查最终 git diff，不把缓存、私有数据、测试临时物或无关产物提交。

## 6. 六小时测试：真实时间与固定源码

先发布六个非协调仓库通过基线检查的最终代码，再把它们的完整 SHA 写入协调仓库映射；协调仓库用 SELF 解析到当前 workflow 的精确 SHA。七个项目各自以相同源码完成两个阶段，每阶段至少累计 10,800 秒成功测试进程时间，合计每仓至少 21,600 秒。七仓矩阵允许并行，每阶段生成七份回执，最终必须收齐十四份。

计入的是实际测试子进程的成功运行时间，不是安装、排队、等待、sleep 或失败命令的时间；这是持续重复软件回归，不是对一个服务的连续在线稳定性或真实科学求解器的六小时认证。一次完整命令循环完成后才判定阶段达标，保留所有失败，不能通过重跑抹除。每阶段有明确超时与进程树清理；失败应终止合格计时。

每个片段记录唯一 segment ID、phase/cycle/command index、精确 argv 与其摘要、repo/SHA、run/job/attempt、UTC 起止、单调时钟耗时、退出码、日志及 JUnit 文件摘要。验证 UTC 与单调时钟时间在合理误差内一致；同阶段不重叠、第二阶段晚于第一阶段、segment ID 跨全部回执唯一。环境与依赖冻结；源码状态和远端 main 定期核对。在六小时测量期间不得继续推送被测 main，否则当前证据失去固定版本资格。

短时试跑必须标记 SMOKE_ONLY，并由最终验证器拒绝其六小时资格。v1 旧回执不得用于新的七仓验收。最终接受需要：七仓基线通过、同一配置运行、十四份当前 v2 回执、每仓两个阶段及累计时间满足要求、原始日志与摘要一致。不得提前在 README、报告或回复中写“六小时通过”。

## 7. 发布与后续结果

每仓提交说明应描述具体错误、修复后的行为、兼容变化及验证证据。正常快进更新 main，使用乐观锁核对旧 SHA；若远端更新，先分析变化并重新验证，禁止 force。提交后检查远端文件、commit tree 和自动 CI。代码提交成功、基线 CI 通过、六小时工作流开始、六小时工作流完成是四个不同状态，逐项据实报告。

如果工作流需要持续超过当前交互时间，确认它在远端实际启动后，再设置有明确 run ID/SHA 的结果监测。成功仅根据真实回执，失败通知应列明具体步骤并继续处理仍获授权的修复。修复导致 SHA 变化时重新冻结版本并重新累计，不能拼接不同版本的时间。

最终报告逐仓列出提交链接、双语 README 链接、代码修复摘要、实际测试数量及覆盖率（有则列）、失败/跳过/外部待验证项、六小时 run URL 和真实状态。不得以本地文件、图片或“可以继续”代替已授权的 GitHub 修改。

## English execution contract

Repair the seven real repositories and their public entrypoints, preserve existing quality gates, rewrite both README languages from the final code, and embed matching-language concept artwork. Publish reviewed changes to main with an expected-head guard. Freeze six repository SHAs plus the coordinator's SELF revision. Run seven parallel software-regression workloads, each for two phases of at least 10,800 successful test-process seconds, and verify fourteen unique receipts with source, command, environment, time, log and JUnit binding. Never substitute waiting for execution time, synthetic fixtures for scientific validation, or local success for a completed remote acceptance run. Report completed, running, failed and external-hold states separately from the actual evidence.
