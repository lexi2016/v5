# V5 执行复盘：问题如何变成可验证改进

2026-10-13｜范围：原模块开发、GitHub 交付、P0 集成与 Mac 验收衔接。

## 结论与证据边界

主要问题是把“模块可运行交付”拆成多轮核收、读源码、单文件修补和接续整合。局部动作有记录，最终链仍有断点。不能全部归因工具或模型，也不能把明确禁止提交的轮次算作开发者拒不提交。

以下依据实际读取的原 Chat 消息、固定 GitHub 反馈及关键 producer/reader 源码。源码和提示词差异可直接确认；Mac 结果来自固定回执，本次复盘未重跑。并行效率和优先级影响属于基于证据的判断，不虚构耗时、费用或责任比例。改进操作见 [WORKFLOW.md](WORKFLOW.md)，现有开发不等待复盘完成。

## 11 项问题、后果与纠正

### 1. 临时限制取代完整交付目标〔确证〕

M03 20:04 的任务明确“只输出一个完整源码、不要求 GitHub、测试随后”，20:09 又限定“只修接口、不扩三件”；回复按此只交源码。P0 也有明确仅核收、不开发的轮次。后果是任务被主动收窄后又要重新催完整交付。

**纠正/验证：** 开发与核收分开；新任务明确旧临时限制结束，终点是完整交付或真实阻塞。

[M03 提示词与回复](https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8?messageId=41c177f7-ff04-4849-a5d0-940eae2fdb39)；[P0 核收轮次](https://chatgpt.com/c/6acc9a79-4364-83ee-8b6d-e9fb51798e5b?messageId=cc3411af-7704-41a0-8c1a-18598b40d769)。

### 2. 最小单元变成不能产生结果的片段〔确证〕

M03 两次提交仅新增 45 行字典检查及 34 行测试，没有 producer、保存或冷读；M14 两文件候选接受调用者字典，没有原 reader、API 或页面。后果是需要再次补写核心接线。

**纠正/验证：** 以可运行调用链而非文件数划定最小增量；入口必须实际调用原 producer/reader，并有可核结果。

[M03 固定反馈](https://github.com/lexi2016/v5/commit/528af98f28de0105f5d2229007cc93e345210311)；[M14 固定反馈](https://github.com/lexi2016/v5/commit/8869a79d97b9b1eb2769b7aadf466d34b0e957c4)。

### 3. 源码位置与版本没有成为唯一入口〔确证〕

M03 19:40 查根 V5 路径得到 404，遂判定源码缺失；19:46 使用实际候选目录即可读到完整 R14。旧 START_HERE 又将判断带回 R13。

**纠正/验证：** 固定当前 HEAD、实际源码根、运行目标根和最新反馈；修改前像与装配目的地对应，单路径失败先查树。

[路径误判与纠正](https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8?messageId=a1db2990-09aa-4b35-a0d2-cb23ee74ce7f)。

### 4. 尚未执行的前置步骤被当成外部阻塞〔确证〕

M02 20:13 收到完整源码/GitHub任务后，仍以“尚未拿到目标树，下一次先读取”结束。此前仅输出完整大文件的限制，又使回复退回片段。没有实际工具错误就不能断定权限故障，也不能称仍在后台开发。

**纠正/验证：** 自行完成可用工具支持的查树、分段读取和工具发现；BLOCKED 必须有具体动作、目标与原始错误。

[M02 停止点](https://chatgpt.com/c/6aca47c7-0bd4-83e8-ab3b-3d4c2cee272a?messageId=3bb37794-a85c-498b-9f61-a115fb0b2bab)。

### 5. 先写推测接口，后核真实合同〔确证〕

M03 使用不存在的 quote_fetch、transport_options，漏必需 captured_at；M14 修正版曾把原 reader 返回的完整 artifact 当作另有 artifact 外壳。代码长度不能证明可调用，错误 shape 还可能造成假空结果。

**纠正/验证：** 动笔前核调用链必要签名、返回形状、marker 与身份字段；正例实际经过原接口。

[M03 原签名](https://github.com/lexi2016/v5/blob/528af98f28de0105f5d2229007cc93e345210311/handoffs/M03/source/collector_owner/ops/us_market_digest.py#L479-L492)；[M14 原 reader 返回](https://github.com/lexi2016/v5/blob/c7b815c065da83bd2db2b3023be4607ce9f194ec/V5/src/v5_shadow/rebound_owner.py#L490-L532)；[M14 当轮输出](https://chatgpt.com/c/6aca4e2a-ea0c-83e8-a4fa-dc01a13867bf?messageId=6913cc39-0563-4a71-a034-ce490578865d)。

### 6. 测试证明自写替身，而非目标链〔确证〕

M03 四字段 READY 被当正例，原合同要求 22 个顶层字段及 24 行一致性。M14 只有三个拒绝测试，没有持久化正例，import 路径也与交付位置不符。旧链通过记录不能覆盖这些新文件。

**纠正/验证：** 先做原 producer→原保存→冷 reader→消费入口的正例，再测本次风险；每个 PASS 绑定版本、命令及实际覆盖范围。

[M03 测试缺口](https://github.com/lexi2016/v5/commit/528af98f28de0105f5d2229007cc93e345210311)；[M14 测试缺口](https://github.com/lexi2016/v5/commit/8869a79d97b9b1eb2769b7aadf466d34b0e957c4)。

### 7. 创建 commit 与原分支完整交付混淆〔确证〕

M14 ba347 已创建，但反馈核对时原开发分支仍指向父提交。M03 新文件未加入旧完整 manifest。拉分支或按旧清单装配会漏代码。

**纠正/验证：** 核远端原分支可达 commit，并核完整清单、依赖和装配说明；HEAD 变化继承，不 force。

[M14 分支核验](https://github.com/lexi2016/v5/blob/8869a79d97b9b1eb2769b7aadf466d34b0e957c4/handoffs/M14/feedback/saved-reader-delivery-20261013/README.md)。

### 8. 局部保护缺少合法升级路径〔事实加判断〕

M14 早期源码候选没有同步 manifest/capsule/PIN/AST，原 Chat 后续确认完整闭包未生成。若一方面要求修源码，另一方面所有轮次都禁止必要身份变更，就会留下无法被 loader 接受的候选。

**纠正/验证：** 在 V5 中将必要源码与精确新身份作为同一闭包交付；保留旧版本，旧/新版本分别严格验证。无需降低安全、PIT 或来源要求。

[M14 闭包缺口确认](https://chatgpt.com/c/6aca4e2a-ea0c-83e8-a4fa-dc01a13867bf?messageId=a9fcae6c-4828-4190-af6a-2010d7f2d69b)。

### 9. 有数据、有页面、有测试被当成每日完整闭环〔确证〕

M02 SDK 两板各 698 成功，整体 collector 仍因 stock_owner NaN 失败；保存和页面成功仍为 SOURCE_IDENTITY_ONLY，PIT/历史资格 false。c7b 隔离页面通过，也不代表现役 opt-in/daily 已开启。

**纠正/验证：** 采集、计算、保存、冷读、页面、自然触发分别报告，最终核同 run/generation。

[M02 回执](https://github.com/lexi2016/v5/blob/7eac09efd3ffcb0e48d58b8d10e7b92a525c41df/handoffs/P0/feedback/mac-m02-saved-publication-20261013/README.md)；[c7b 回执](https://github.com/lexi2016/v5/blob/dd2962f869ed04562707f202aa11d0cd342ccba8/handoffs/P0/feedback/mac-manager-c7b-isolated-20261013/README.md)。

### 10. 共享文件单 writer 被扩大为全工程串行〔执行判断〕

已读历史可见多个原 Chat 结束在等下一轮；这不足以量化全工程并发率，但说明“已发任务”不等于持续执行。共享 P0 需要单 writer，不意味着独立模块分支互相等待。

**纠正/验证：** 原 Chat 并行开发，P0 串行合共享文件，Mac 串行装配/现役变更。状态明确区分已投递、执行中、已结束、待合入，不以后台开发笼统覆盖。

### 11. 汇报和核收多，最终断点仍在〔事实加判断〕

P0 核收 M06 有限自然成功时，总链仍记录 manager_request 缺失。核收有助保留状态，但不能替代修复。改变模型设置、重复工具动作和再次列计划，都没有证明目标更接近完成。

**纠正/验证：** 优先独立数据源、request/template、保存发布、默认页面断点；只报告新增能力、实际失败、必要决策和完成。无需重测未变的已通过项。

[P0 总链缺口记录](https://chatgpt.com/c/6acc9a79-4364-83ee-8b6d-e9fb51798e5b?messageId=cc3411af-7704-41a0-8c1a-18598b40d769)。

## 不能被改进流程掩盖的事实

- 当时记录的 18/14/14/0/0 分别表示代码接入覆盖、真实输入或保存读回覆盖、数据状态页面覆盖、全系统每日自然验证、完整验收；这些不是统一的完成百分比。
- M06 有限自然成功保留，但不能据此确认 V5 完全独立每日采集计算或全系统同 run。
- c7b 最初 11 PASS/1 FAIL 历史保留；后续只重跑 navigation 8/8。既定隔离范围已覆盖，不等于“全部 12 项重跑”，也不等于部署。
- 错过原时间窗口不能回填自然成功；可以现在完成受控候选和隔离测试，真实自然证据在合法窗口另行取得。历史不足等数据缺口不能靠放宽 PIT 或资格来清零。
- 新规范的效果须看实际完整交付、可运行链和同 run 证据；把 prompt 改得更强硬或更长，本身不算改进完成。
