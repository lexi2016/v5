# M05 A股预选池：GitHub 源码交接

状态：SOURCE 已核身份；最新候选为 **R9 / REQUEST_CHANGES**。本提交只发表既有源码、准确前像与静态审查，未修产品代码、未运行产品测试、未部署。

- 仓库：用户自己的私有 `lexi2016/v5`
- 本模块开发分支：`dev/m05-github-handoff-20261011`
- 原 Chat：https://chatgpt.com/c/6aca4eef-525c-83e8-abb9-d8423024bf90
- 本交接从 main `2489ea1e04a26a9e2f318f498ac3f5f8c970fe48` 继承。请以调度提供的本次固定 commit 为阅读基线；不要依赖可移动 HEAD 来声称已读固定版本。

## 阅读顺序

1. [准确返修任务](STATIC_TASK.md)
2. [R9 逐行静态缺口及完整 R8↔R9 差异](review/R9_STATIC_GAPS.json)
3. [完整原来源清单](source/SOURCE_MANIFEST.json)与[40 件 owner 身份](source/V5/contracts/a_preselection_source_manifest.json)
4. [原 assembler/只读隔离 worker](source/V5/src/v5_shadow/a_preselection.py)、[真实 store](source/V5/vendor/a_preselection_baseline/infrastructure/preselection_pool_store.py)、[真实 gate context](source/V5/vendor/a_preselection_baseline/infrastructure/scope_gate.py)
5. [原 fixture](source/V5/tests/test_a_preselection.py)、[当前 R9 daily](candidate_r9_latest_rejected/V5/src/v5_shadow/a_preselection_daily.py)、[准确 R8 前像](candidate_r8_historical_rejected/V5/src/v5_shadow/a_preselection_daily.py)
6. [发表范围与逐件身份](PUBLICATION_SCOPE.json)

## 本次真实范围

82 件：67 件原 source 正文、1 件原 SOURCE_MANIFEST、R8/R9 各 5 件原候选文件、1 件逐行静态审查、3 件新交接文档。原清单 69 条保持原字节；其中 2 件历史运行审查/receipt 的正文未发表，原因和身份在范围表，不可声称 69 件正文全部装配。40 件 owner 全部保留，canonical SHA 仍为 `d0fddbcaa1d5eb22f50edd5d651976b8bc2643122bc951b31733448dea8e23e4`。

SOURCE 可支持原 A 六 lane 的冻结 owner、wrapper 与离线 fixture；canonical publisher/consumer 文件只是装配合同参考，非完整 V4 checkout。其他延迟 research/HK 分支不构成此模块的运行闭包，不应为凑闭包导入无关模块。

## 必须更新的判断

R9 确实已改为 `_require_write_gate_context`、`_write_gate_context is context` 和真实类校验，也增加了 strict store factory；不能继续把 R8 的公有属性错误套在 R9 上。R9 尚未接通冻结 writer 导入和默认 context/factory 调用，缺真实 fixture、最终同锁批次身份及 consumer 接线。

R9 正反 patch 原件保留。它们仅少最后一个 LF；内存补 LF 后与完整 R8↔R9 两文件 diff 相等。原样 patch 解析失败，不能直接使用；此次未修改 patch 或应用产品补丁。

所有源码工作通过本 GitHub 分支进行，交完整可读源码、固定 commit、准确 diff 和真实测试状态。旧资料中的 ZIP 主流程及禁止本模块开发分支提交措辞已被当前 GitHub 工作指令替代；GitHub 读取失败应报真实工具错误和路径，不能换回 ZIP 作为默认入口。不得改 V4、main、其他模块或合并。运行候选需另记，Mac 独立验收后方可判断部署。
