# M09 R2 GitHub 返修入口

本目录是 M09 原模块的可直接读取反馈，不是新模块，不是 R2 实现完成。开发仓库为独立私有 `lexi2016/v5`，唯一工作分支为 `v5/m09-handoff-20261011`。继续修复并提交到这一分支；不要改 main、V4 或其他模块分支，不要 force push。

## 先读这里

1. [当前 GitHub 交付任务](PROMPT_M09_R2_GITHUB.md)
2. [完整合并审查](source_reviews/MERGED_REVIEW_M09_R1_MAC_AND_R2_REPAIR.md)
3. [独立 Mac 验证摘要](mac_evidence/verification/SUMMARY.md)
4. [六类篡改回执的原始结果](mac_evidence/negative_original_artifacts/RESULTS.json) 与 [实际失败输出](mac_evidence/verification/duplicate-receipt-negative.stdout.log)
5. [复现脚本](mac_evidence/duplicate_receipt_probe.py)、[全部原始日志与命令](mac_evidence/verification/)、[两个历史槽原始诊断](mac_evidence/real_historical_diagnostic/)
6. [逐文件校验清单](FILES_SHA256.json) 与 [来源核验](SOURCE_VERIFICATION.json)

## 代码与证据身份

- 完整 R1 候选：`d0f9905940584777abbcae248850ebc487cade63`，tree `2e9f7ac6b9cca37a84ddbc02d0872440aa9c0a32`，唯一 parent `782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`。
- 本次发布前重新读取远端完整 tree：1063 项、870 blob、未截断；870 份本地候选与远端 Git blob/字节数逐一相符。
- 本次开始时开发分支仍指向 `782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`，虽然 d0f 完整候选对象已存在。此次提交以 d0f 为直接 parent，仅新增本反馈目录，再用预期旧 HEAD 和非强推快进开发分支，把完整候选与反馈一同落到正确分支。没有声称原分支此前已经指向 d0f。
- 根目录 `V5/` 及 `M09_DELIVERY_20261011/` 仍是完整 R1 源码与交付树。本目录的 `mac_evidence/a_close_daily.fixed_candidate.py` 是被测 R1 原样快照，不是补丁或已修复 R2。
- `mac_evidence/` 原样保留已解包的 173 份文件，原 MANIFEST 的 172 个文件全部通过 bytes/SHA256。Mac 原证据 ZIP 身份仅用于追溯：145272 bytes，SHA256 `2b03a827150a9b7ce2232bbbc808831a1d1e42d1fc7f6d46e5e1675433f7af6f`。阅读和后续交付均直接用 GitHub 目录，无需 ZIP 附件。

## 三类事实必须分开

- 支持环境既有 Python 3.14.6 / pandas 2.3.3 / pyarrow 24.0.0：R1 主套件 125/125 零 skip，原独审 6/6，generation 演示和正反 patch 往返通过。这不等于原 pandas 3.0.5 / pyarrow 25.0.1 环境已认证，也不是 R2 测试结果。
- 新独立负测六种篡改全部被重复 attempt 分支原样接受，probe exit 1 表示应拒绝却未拒绝。不是环境失败，不得与上面的通过项合成“全部验收成功”；没有真实订单或公开 generation reader 已被攻破的证据。
- 20261009 原件真实解码 5126 行；16:05 与 17:10 的历史 attempt 均拒绝且无成功 generation。历史研究可计算性要按原算法和合同实证处理；NATURAL、前瞻和 PIT 准入继续严格，不得拿历史计算成功冒充当时可用证明。

## 下一步与交付方式

实际实现 R2：修复回执校验、按原合同验证并提供真实历史研究路径、补齐普通 API / 原页面 / dispatcher 的实体接线候选和测试。完整内容见任务和审查。所有成果、前后像、真实补丁、命令、日志、校验清单提交同一 GitHub 分支；回复最终固定 commit 与目录入口。用户最新要求优先于历史材料中的 ZIP/附件交付措辞。

`source_reviews/` 保留原报告字节和时间状态，其中“附件”“最终 ZIP”等仅是历史交付文字；当前不再以 ZIP 交付。复现及验证脚本中的绝对 Mac 路径是原执行上下文，重跑时应使用新隔离目录和实际已授权解释器，不要在历史证据目录内覆写证据。

本反馈发布未执行产品测试、未改产品代码、未操作 Mac 或浏览器、未部署、未启用自然调度、未交易，也未读取或扩大凭据/系统权限。
