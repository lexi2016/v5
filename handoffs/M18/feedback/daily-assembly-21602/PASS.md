# 21602 daily assembly 原样隔离测试

固定GitHub源码：21602c9e16732ae6cd869b26a630ce3764f725a4；用户提供parent d921ee5c705ea7fb78ea854c301effbf20c33478。分支 dev/m18-daily-assembly-20261012。
本地独立worktree m18-daily-assembly-21602-candidate，基线6900d8982b2542e67a37fa4da5608bbbf94d5abf，仅替换 V5/src/v5_shadow/daily_manager_assembly.py。
11504字节、478行，SHA256 5073fd3f774673502603f0d6e0df123c813cb4a46ea37e77201d3a9aa9b9fd2c，Git blob 63e5a84215962bd74703ef80d39f5db54fe1373c。
794个原基线文件未变；两组测试文件字节未变；未二次源码审查，未本地修产品。

实际命令（工作目录 <workspace>）：
```sh
../../2026-10-11/task/m13-isolated/venv/bin/python -I -B m18-daily-assembly-21602-evidence/run_tests.py test_daily_manager_assembly
../../2026-10-11/task/m13-isolated/venv/bin/python -I -B m18-daily-assembly-21602-evidence/run_tests.py test_daily_candidate_contracts
```
原套件：UTC 2026-10-12T01:27:13.233088+00:00 至 01:27:13.304145+00:00，8 PASS，exit 0。
定向合同：UTC 2026-10-12T01:27:13.899783+00:00 至 01:27:13.959592+00:00，8 PASS，exit 0。
旧eccac84失败不重跑、不覆盖；无新失败，因此未提交新GitHub失败反馈。

## 原套件逐项日志
```text
test_closed_execution_window_can_read_existing_ledger_without_claim (test_daily_manager_assembly.DailyManagerAssemblyTests.test_closed_execution_window_can_read_existing_ledger_without_claim) ... ok
test_missing_real_revision_inputs_do_not_invoke_model_or_owner (test_daily_manager_assembly.DailyManagerAssemblyTests.test_missing_real_revision_inputs_do_not_invoke_model_or_owner) ... ok
test_new_defaults_are_explicit_hk_slots_not_legacy_claim (test_daily_manager_assembly.DailyManagerAssemblyTests.test_new_defaults_are_explicit_hk_slots_not_legacy_claim) ... ok
test_rebound_reference_and_new_revision_binding_assembled (test_daily_manager_assembly.DailyManagerAssemblyTests.test_rebound_reference_and_new_revision_binding_assembled) ... ok
test_revision_capsule_is_exact_fixed_assembly (test_daily_manager_assembly.DailyManagerAssemblyTests.test_revision_capsule_is_exact_fixed_assembly) ... ok
test_sealed_real_cutoff_reused_not_new_plan_every_tick (test_daily_manager_assembly.DailyManagerAssemblyTests.test_sealed_real_cutoff_reused_not_new_plan_every_tick) ... ok
test_stale_template_us_and_observation_not_silently_reused (test_daily_manager_assembly.DailyManagerAssemblyTests.test_stale_template_us_and_observation_not_silently_reused) ... ok
test_us_exact_run_bytes_copied_and_changed_pointer_rejected (test_daily_manager_assembly.DailyManagerAssemblyTests.test_us_exact_run_bytes_copied_and_changed_pointer_rejected) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.024s

OK
```

## 此前八项合同逐项日志
```text
test_01_fixed_announcement_preserved (test_daily_candidate_contracts.AssemblyContracts.test_01_fixed_announcement_preserved) ... ok
test_02_native_master_archives_deepcopy (test_daily_candidate_contracts.AssemblyContracts.test_02_native_master_archives_deepcopy) ... ok
test_03_rebound_research_reference_preserved (test_daily_candidate_contracts.AssemblyContracts.test_03_rebound_research_reference_preserved) ... ok
test_04_four_argument_signature (test_daily_candidate_contracts.AssemblyContracts.test_04_four_argument_signature) ... ok
test_05_conflicting_ann_binding_rejected (test_daily_candidate_contracts.AssemblyContracts.test_05_conflicting_ann_binding_rejected) ... ok
test_06_wrong_identity_rejected (test_daily_candidate_contracts.AssemblyContracts.test_06_wrong_identity_rejected) ... ok
test_07_changed_source_rejected_and_cutoff_stable (test_daily_candidate_contracts.AssemblyContracts.test_07_changed_source_rejected_and_cutoff_stable) ... ok
test_08_no_qualification_promotion (test_daily_candidate_contracts.AssemblyContracts.test_08_no_qualification_promotion) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.028s

OK
```

## 接续范围及阻塞

此步通过后可接续：以这份固定装配源码和6900固定依赖进行隔离预览集成；应先绑定已经完成真实验收的manager产物与v2归档身份、准备独立发布generation，再核对GET及普通页面显示。此次尚未执行该接续，也未改变旧54779预览。
当前旧preview仍绑定aa15b8ed25ec41e6893b72575cedcda8；新30MB run46596b03c2ab4e29b1219fd2e5eb698f尚未发布到它。旧预览独立公告解析503、超跌SCREEN_AUTHORITY_ROOT_NOT_BOUND/目标资格未确认仍保留，不能凭本装配测试清除。已有v2离线归档验证通过不等于API/页面已集成。
真实producer/manager未重跑，无调度安装、交易、凭据或权限变更；不宣称全部M18/P0、全三路或自然日通过。

