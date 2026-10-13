# M06 真实输入只读准入与晚间配置草稿

固定基线 5eddebf5c6ecf530ece3fdb31a054b56bf2f1d57 + 已验 guard 8a5d45c4b99fabeab55333052ea99cb547213f16。2026-10-13 04:42–04:44 UTC（北京时间12:42–12:44），只读准入函数/哈希核对；没有重跑89/85/15测试，没有调用 prepare_input_delivery、prepare_daily_candidate、owner、模型或调度。

## 实际输入

历史 D20261012→target20261013：原2026 HK证券日历解析正确。dispatcher成功→envelope→lane原始522680字节/SHA→panel authority及panel parquet SHA通过；model bundle 33062913字节、name96765字节的原声明SHA通过；signal日master READY、manifest及artifact SHA通过。只证明原始字节和这些合同字段，不证明模型已重新加载验证。

整个delivery adapter仍 NOT_READY：原 store latest 已含20261013 HK_CONNECT_D1_TOP100_0_2池；其 manifest 缺 production_allowed、buy_gate_updated、orders_sent 三字段，_capture_inputs对该既有池调用 _safety(required=True) 时抛 M06_DELIVERY_SAFETY。对应receipt三字段符合，manifest canonical hash和artifact SHA均匹配。没有补写原字段、删latest、过滤既有池或修改产品绕过。此外，固定 GENERATE_IF_ABSENT 在目标池存在时会被原worker明确拒绝为 M06_GENERATION_REQUIRES_ABSENT_POOL；不能把历史已存在池当成新生成场景。

今日 D20261013→target20261014：原HK证券日历为FULL_TRADING_DAY、nextsession14。当前 panel_latest 仍为12日；13日1720 HK成功dispatcher回执不存在，lane hk-20261013.json不存在，13日master entry不存在。完整adapter当前首先报 M06_DELIVERY_PANEL_DATE。属尚未收盘交付，不改历史日期充当今日数据。没有制作快照、delivery、冻结job、ledger claim；completed_at为null。

## 新V5策略与配置

本次明确的新策略：full/half均17:30–18:30 Asia/Shanghai，每300秒检查，完整预算1200秒，owner_contract_cutoff为target日09:00+08。后者只是原owner兼容上界；实际硬deadline仍D18:30，PIT沿原回执，不能延长执行。_candidate_policy、原calendar和配置/pin验证通过。18:10是1200秒预算的最晚理论准入点；18:15返回预算不足，18:30返回错过窗口不补跑。快照/inspection等耗时会使可准入时刻更早。

登记单进程timeout在新草稿明确设600秒，因此满足代码budget>=2*timeout的下界。先前手工生成配置是1800秒，不能直接沿用：1800会要求预算至少3600而与1200冲突。本草稿没有把新600冒充此前手工配置值，也没有承诺1200足够任何真实输入耗时。

已有HK02 launcher路径含祖先目录符号链接，第一次配置校验exit1 SYMLINK_REJECTED；后按现有解释器真实venv目录固定launch leaf、binary、pyvenv.cfg与readlink SHA，未改权限/解释器，第二次只读校验exit0。这是精确路径配置修正，未改产品或放松no-symlink规则。

另一个未解决定位约束：dispatch_receipt_relative只支持日期字段，不支持随机run-id发现。原回执路径为DATE/1720/UUID.dispatch-receipt.json；今日UUID尚不存在。禁用草稿保留明确 UNRESOLVED_EXACT_RECEIPT 哨兵，不伪造READY，也不能直接启用日常无人值守。需以后原回执出现时精确验证并绑定实际相对路径；若需要自动发现，须原作者提供并验收明确的桥接定位方案，当前代码不做此工作。

## 路径边界和下一步影响

独立状态根含 snapshots、deliveries、bundles、p0-ledger、m06-output，互不嵌套，marker正确；全部属于本任务。原 store/assets/dispatcher/lane 四根只作为迁移桥接只读来源。合同要求registration store/asset初始等于原输入根，成功封存后才把owner实际输入切到自有snapshot/store、snapshot/assets。因此无法声称最终已不依赖V4输入交付；不能把registration先改成不存在的snapshot路径以满足独立表象。

可执行的disabled草稿为 private-m06-evening-bridge-20261013/daily.disabled.draft.local.json；rollback.disabled.local.json为相同三开关false的回退副本。operator-policy.json单独记录300秒外部触发策略，没有安装/渲染launchd。仅运行daily_tick读取该disabled草稿会返回DISABLED。

以后启用的准确影响：允许adapter只读原链并复制已声明字节到自有不可变快照，以实际封存时间写delivery；随后冻结精确job，cold-inspect，最多一次原owner/model执行，独立ledger及输出，独立readback/CAS推进自有current-success。现役APIbinding不会自动改。未知/中断不可通过清理状态强制重试。此轮未授权/未执行这些步骤。

回退：当前无运行可停，保留三开关false及所有证据即可；未来若启用，先禁用触发和三开关，仅在身份核实后停止自有进程，保留snapshot/ledger/current-success不删不改。V4配置、现役M12/M04/M06/M17绑定和旧池均未触碰。
