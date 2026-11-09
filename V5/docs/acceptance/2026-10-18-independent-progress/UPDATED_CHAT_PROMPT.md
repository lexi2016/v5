# 给原Chat的最新返修/交付Prompt（交付稿，未向外部Chat发送）

请以固定91f1dbe18e9da1d6abbdb974c600c8196a9b796e为本轮验收基线，保持现有V5分支和V4隔离。不重写已过日期竞争、M17错误分类、默认run、M09缓存修复，不执行采集/交易/凭据/权限变更。

独立实际结果：typecheck PASS；p0此前同HEAD164/164 PASS；M09此前4/4 PASS；本轮相关Python unittest52/52 PASS。全量Vitest初跑471PASS/14FAIL/6SKIP；用仓库原生成器仅补明确synthetic Recovery样本后，全量重跑474PASS/11FAIL/6SKIP，exit1。不是全量通过，不能把合成样本当真实结果。

现在需补的是原始测试证据交付/绑定，不是凭缺文件重写业务：
1. managerWorkspace.currentRecovery.spec.ts:5–6，3项ENOENT：提供V5_REAL_CURRENT_RECOVERY_RESPONSE，原manager-read-publication.json，保留测试run/SHA严格断言。
2. cloudActualReadback.spec.ts:8–9，1项V5_CLOUD_WORKSPACE_RESPONSE_REQUIRED：交实际workspace原响应及run身份。
3. actualResearchSelectionProjection.spec.ts:10–15，1项ORIGINAL_OCT2_RESEARCH_SELECTION_PROJECTION_REQUIRED：交原OCT2_RESEARCH_SELECTION_PROJECTION gzip、原SHA与689-row来源。
4. researchSelectionLedger.spec.ts六项均因fixtures/issue8R2.fixture.ts:6–8缺原ownerObservations；交V5_ISSUE8R2_OBSERVATIONS原件。外围synthetic envelope不能授权虚构内部owner数据。

请为每个原件列来源commit/路径、内容SHA、授权读取/传递方式和环境变量；无原件就明确BLOCKED，不造空文件、不用synthetic替代、不静默skip、不删断言。原件就绪后复测4文件与全量npm test，并交原日志/退出码及新固定SHA。当前11失败只证明输入缺失，尚不能断言业务逻辑错或功能通过。

额外6 skip也要诚实列出：module01实际HTTP三项、cloud-page-check jsdom+HTTP三项未配置；后者不算浏览器。Python runtime/M18函数型回归需pytest，冻结环境未安装且本轮安装被拒，保持NOT_RUN，先取得授权或使用已有合适环境；不得更改安全设置。不要把unittest未收集函数当通过。

附件提到daily_manager_reconcile，但固定HEAD内容和tracked文件名均无此标识。请给准确文件路径/commit与需求映射；当前NOT_FOUND/NOT_RUN，禁止编造已有实现或声称验收。

最终交付包括：本轮具体改动（若只是材料则明确无产品改动）、固定完整SHA、测试命令/环境/退出码/原始日志、失败逐项原因、未解项和最小下一步。真实采集、自然调度、业务数据、浏览器仍分别验收。本次已授权将进展文档及必要脱敏测试日志提交当前V5开发分支；未授权向外部Chat发送本提示。
