# M16 经理候选公开资料任务：离线源码与测试

此ZIP提供普通Chat可直接阅读的源码原文，不依赖私有GitHub可访问。先读handoff/PROMPT_FOR_CHAT.md，再按handoff/SOURCE_MAP.md阅读fixed-f7cb731c中的同路径文件。Chat负责实际代码候选；嘻嘻负责真实Mac独验、共享集成与单窗口发布。

## 版本和范围

- fixed-f7cb731c：固定f7cb731c384ee6890a87d16c19a5b5a621779477的132份模块donor、测试、必要直接依赖及只读共享集成参考；原文件字节不改。
- reference-plans：24c6d60d总计划、d1bf0346迁移计划两份原文。模块编号与P4按总计划；早期编号换算看任务文档。
- handoff：本模块四份完整任务/源码映射/验收文档。共享源码即使在包中，也仍只读；模块写根按这些文档。
- SOURCE_MANIFEST.json：134份仓库原文件的commit/path/blob/SHA256/bytes/包内路径。全部重算Git blob匹配；链接用于复核，不是唯一输入。

V5/src/v5_shadow/manager_jobs.py在固定树不存在，是本Chat拟新增目标。不要把包内原V4源码路径当V5部署目标，也不要因不存在daily wrapper重写原算法。没有确认的f7cb之后新修复未猜入本包；如后续取得，应分donor目录核前像后最小集成，不能整包覆盖。

## 明确限制

已附原ManagerResearchJobService/store/provider及原manager_research源码目录（含原PDF vendor），生命周期/事务/路由原测试和共享UI参考。V5现有manager_plan_baseline没有service.py，本包没有伪造该文件。共享UI/router/其他业务方法为只读对照，不授权本Chat跨写。

这是供实现和契约审查的精确源码subset，不是完整仓库、完整已安装运行环境或部署包。测试引用的外部依赖、真实原件、活动配置、provider、完整现役绑定仍由Mac核；不安装新软件、不读取秘密、不扩安全范围。缺运行绑定只影响依赖它的真实执行，不得只返回缺件而不交可静态完成的代码与契约测试。

本包没有从Mac读取业务数据、媒体或凭据；只取固定仓库source/tests/contracts文档。未导入产品模块、运行测试、发采集请求或部署。包内fixture代码是原测试材料，不是自然来源或真实业务通过证据。五项状态：代码接入、真实数据通过、页面可用、自动接续、完整验收；工程测试另记。

## 包内原测试

- handoff/v4-running-source-20261005/canonical/tests/optimization/test_manager_transactions.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_contract_hardening.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_lifecycle_hardening.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_catalyst_service.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_decision_recovery_contract.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_event_source.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_pdf_parser.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_reader.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_router_contract.py
- handoff/v4-running-source-20261005/canonical/tests/test_manager_research_service.py
