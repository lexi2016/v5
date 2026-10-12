# M01 当前候选：默认双 roots 入口已实现

2026-10-12：本轮在 R15 完整核心上修复真实默认创建/读取入口，保留 r15 schema 和原 owner。新候选在 [candidate_source_entrypoints_20261012/REPORT.md](candidate_source_entrypoints_20261012/REPORT.md)，完整 [after](candidate_source_entrypoints_20261012/after/)、[前后 SHA](candidate_source_entrypoints_20261012/BEFORE_AFTER_SHA256.json)、[正向 patch](candidate_source_entrypoints_20261012/runtime.patch)、[反向 patch](candidate_source_entrypoints_20261012/reverse.patch) 和 [Mac 验收步骤](candidate_source_entrypoints_20261012/MAC_APPLY_AND_ACCEPTANCE.md) 均已交付。

本轮云测试：36 PASS、8 项真实 Parquet fixture 因缺现有 pyarrow 而明确 NOT_RUN/SKIP；不算 Mac、真实业务或生产通过。两份 patch 已实际往返，原 SOURCE 71 件字节核合。原 source/reference/review/历史材料完整保留。下面为上一轮交接记录，状态仅对应其注明候选。

# M01 A行情与公式面板来源：GitHub工程与返修入口

当前独立私有仓库为 lexi2016/v5，本模块开发分支为 dev/m01-github-handoff-20261011。本次只是现有工程材料交接，不是实现、测试或部署通过。

## 阅读顺序

1. [完整原返修任务](TASK_ORIGINAL_1141.txt)：保留R15正确核心，完成真实默认双入口与原依赖装配、严格source/root准入、完整测试和真正正反patch。
2. [R17独立静态审查](reviews/REVIEW_M01_R17_STATIC.md) 与 [R15差分审查](reviews/REVIEW_M01_R15_DELTA_20261011.md)、[R15/R17真实差分](reviews/R15_vs_R17.diff)。
3. [原完整SOURCE](source/)：71件原文件，包含63件固定仓库源码/测试/契约和8件交接/来源文档。[原来源清单](source/SOURCE_MANIFEST.json)保留固定commit/path/blob/SHA身份。
4. [R15参考前像](reference_r15/) 与 [R17未通过候选](candidate_r17_rejected/)。两个版本分别保留，不把R17直接覆盖成通过版。
5. [历史R6 Mac工程反馈](historical_r6_mac/)：现成REVIEW_RECEIPT、REPORT和合成boundary harness；仅对应R6，不能代表R15/R17已通过。
6. [发布逐文件清单](PUBLISH_MANIFEST.json)：本次每个工件的字节数、SHA256和Git blob。

## 最新工作方式与安全边界

所有本模块后续代码、测试、审查反馈和固定交付commit通过这个独立GitHub开发分支完成；旧文档里的ZIP主流程是历史记录，本入口优先。没有工具权限时提供真实错误，不虚构commit或测试。

仅修改原M01许可的实现与测试，复用原SafeRoot、formula generation reader和共享composition。原SOURCE中的共享/采集/其他owner文件都是只读对照，不允许整包覆盖V4、main、其他模块或共享整合分支。必要共享接线改动应独立提请求，交唯一整合者核当前前像。

V5/等路径是原donor或候选内部路径命名空间；提交新实现时交准确REPO_PATH_MAP，不猜测最终运行根。不得执行交易、采集真实业务数据、读取新凭据、扩大系统安全权限或自行部署。由既有Mac任务对经过修复的固定候选独立验收。

## 明确状态

R17原包6753B，SHA256 91c79646be97c97d6a4b55430fe40e211ae8cd2708ed43ab762f6bacd5e37e05。它尚未通过：默认生产装配未实现、bounded reader/严格校验存在回退、两个patch同向；仅有两个日期测试，实际测试NOT_RUN。R15也不是通过版。本次没有执行产品测试或Mac部署。

当前不纳入真实history-gap输入合同及历史Mac原始日志整包。已有历史R6反馈保留原字节；两组成功和缺陷复现不能当最新候选或真实来源运行通过。源码完整交接与业务完整验收分开记录。

继续唯一原M01会话：https://chatgpt.com/c/6aca4d01-136c-83ec-83fd-2cac19e42e50 。不得另建平行M01。
