# V5 全量前端与相关Python实际验收

固定HEAD：91f1dbe18e9da1d6abbdb974c600c8196a9b796e。2026-10-18本轮，独立worktree repo-91f1dbe，Node24.19.0/Python3.14.8；沿用既有依赖，无产品tracked源码修改。

## 真实结果
- typecheck PASS，exit0。
- 首轮全量Vitest：471 PASS /14 FAIL /6 SKIP，5失败文件，exit1，26.53s。
- 用仓库原make_synthetic_recovery_fixture.py生成明确SYNTHETIC_EMPTY_OWNER_NOT_BUSINESS_EVIDENCE样本，仅绑定V5_SYNTHETIC_CURRENT_RECOVERY_RESPONSE；对应3项定向PASS。
- 随后完整重跑Vitest：474 PASS /11 FAIL /6 SKIP，4失败/55通过/2跳过文件，exit1，17.81s。不得报告全量通过。
- Python unittest：52测试PASS，exit0，83.117s：M17 reader13、M17 API9、module API14、manager currentRecovery16。
- 既有本固定HEAD历史结果：p0 164/164 PASS、M09 4/4 PASS；本轮未重复。

## 11项失败逐组归因
1. frontend/src/api/managerWorkspace.currentRecovery.spec.ts:5–6：3失败。未绑定V5_REAL_CURRENT_RECOVERY_RESPONSE，默认../evidence/manager-read-publication.json不存在。ENOENT发生在原始回执读取，尚未进入真实回执合同验收。
2. frontend/src/manager-selection/cloudActualReadback.spec.ts:8–9：1失败。V5_CLOUD_WORKSPACE_RESPONSE_REQUIRED，未提供实际云端workspace响应。
3. frontend/src/manager-selection/__tests__/actualResearchSelectionProjection.spec.ts:10–15：1失败。ORIGINAL_OCT2_RESEARCH_SELECTION_PROJECTION_REQUIRED；需要OCT2_RESEARCH_SELECTION_PROJECTION原始gzip投影，测试要求689-row owner投影。其fixture依赖原owner observations也需要一起补全。
4. frontend/src/manager-selection/__tests__/researchSelectionLedger.spec.ts（6失败），共同根因在__tests__/fixtures/issue8R2.fixture.ts:6–8：缺原issue8R2.ownerObservations.json，V5_ISSUE8R2_OBSERVATIONS未绑定。虽然外围envelope有synthetic标识，原owner observations仍必须原件，不能重新造数。

以上11项当前证据支持“测试交付/输入依赖缺失”，不是已经证明业务断言错误；也不构成这些功能通过。最小下一步是明确原件来源、授权可读位置、SHA与绑定，然后保留原断言复测。不得用合成Recovery、空JSON、静默skip或删除测试充数。

## SKIP和NOT_RUN
- 6个主动skip：managerWorkspace.module01.http.spec.ts三项缺真实HTTP材料；tests/cloud-page-check.spec.ts三项缺loopback/fixture/evidence opt-in。后者本来是jsdom+HTTP，不是浏览器截图。
- 额外runtime组初次unittest只执行1个example测试，同时test_p0_runtime_safety import报ModuleNotFoundError:pytest，exit1；test_p0_runtime_lifecycle及test_m18_v2_module_api_binding的pytest函数未被unittest收集，不算通过。
- 当前冻结V5环境不包含pytest（只读探测pytest_available=False）。尝试补装测试工具被审批拒绝，理由为用户禁止软件安装；未改权限或换渠道绕过。此组BLOCKED/NOT_RUN，需要单独授权官方pytest测试依赖或既有合适环境。CI工作流自身在第44/119行另装pytest==9.1.1，不能据此假定本机已有。
- daily_manager_reconcile：对固定HEAD源码内容及tracked文件名检索无匹配。NOT_FOUND；该命名实现测试NOT_RUN。需给准确文件/commit/附件映射，不猜测等价实现。
- 本轮build/HTTP/真实浏览器/自然调度/真实采集NOT_RUN。浏览器旧阻塞为sandbox网络命名空间隔离、升级启动bwrap基础设施失败、官方终端输入失败及错误页URL策略拒绝；没有重试或绕过。

## 命令与证据
命令由repo-91f1dbe执行；Python变量为已安装repo/V5/.venv/bin/python的绝对路径。
1. cd frontend && timeout 120 npm run typecheck
2. cd frontend && PYTHON="$PY" timeout 300 npm test -- --reporter=verbose
3. timeout 120 "$PY" -B V5/tools/cloud_preview/make_synthetic_recovery_fixture.py --out <logs>/explicit-synthetic-recovery.json
4. cd frontend && PYTHON="$PY" V5_SYNTHETIC_CURRENT_RECOVERY_RESPONSE=<logs>/explicit-synthetic-recovery.json timeout 300 npm test -- --reporter=verbose
5. PYTHONPATH=V5/src:V5/tests timeout 180 "$PY" -B -m unittest -v test_m17_readonly test_m17_readonly_api test_module_api test_m18_v2_module_api_binding test_manager_current_recovery
注意5中M18 pytest函数0收集，52只来自上述4个unittest类；不冒称M18已覆盖。首轮相对解释器路径有sys.prefix警告，原日志保留，52项exit0。

原始日志在logs-91f1dbe-full/：frontend.log、frontend-with-synthetic.log、typecheck.log、python.log、python-runtime.log、synthetic-generate.log、synthetic-recovery-retest.log及各.exit；environment.txt和daily-manager-reconcile-search.log。本轮原测试未上传/外发；本次用户授权仅发布此文档及下列脱敏日志。
