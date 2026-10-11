# M15候选R1独立静态审核

## 结论

**退回补齐；不能作为“原M15完整修好代码”交付或进入Mac业务验收。**

候选确实基于给定M15文件前像，只增加两行 `ledger_run_id` 非空字符串检查。该小改动在M15允许范围内，放在调用有副作用的owner之前合理，未发现它新增跨模块写入或改变原映射算法。**不足之处是任务要求的M15入口、消费兼容、精确保存读回和交付包没有完成，且原样runtime.patch不能在固定源包根应用。** 这不是因为没有真实数据或因为NOT_RUN；下文把静态可证的代码/交付缺口与未执行验证分开。

本次仅读取ZIP、源码、任务书，校验字节/SHA/manifest、AST语法和 `git apply --check`。未导入/运行产品，未执行pytest，未访问Mac、采集、交易、GitHub写入、预览或部署；未改产品代码。报告中的测试结果为候选自带日志，未经本审核重跑。

## 1. 候选与前像身份

- 任务：本地 `v5-chat-module15-20261010/PROMPT_FOR_CHAT.md`、`START_HERE.md`、`MAC_ACCEPTANCE.md`。
- 固定目标基线：`f7cb731c384ee6890a87d16c19a5b5a621779477`。
- 源ZIP：`V5_MODULE15_SOURCE_20261010.zip`，322278 bytes，SHA-256 `5140895769b51fd225544e1cd4a243a13b0e7ed4944b40f951393b6751baa940`。
- 候选ZIP：`V5_M15_CANDIDATE_ledger_guard.zip`，4568 bytes，SHA-256 `114a17f4dd8dae9563150a85f5287d701c949bd778efe0c9036fba950c845f51`。
- ZIP的10项为6个文件、4个目录，不是10个代码文件。
- 唯一产品文件：`V5/src/v5_shadow/daily_us_owner.py`。
- before：`6523a4926f452f59f94b5649e28cf4caf6c79417a223f8c57577bace9750bc3c`，与固定源ZIP该文件一致。
- after：`89fa9680fd36294c941ce5a42adbdaa802ccbce03f87dd8c3da229cd98689c3c`，与候选文件一致。
- 静态逐字差异：仅在候选24—26行的函数开头新增 `if not isinstance(ledger_run_id, str) or not ledger_run_id:` 和 `raise ValueError('US_OWNER_LEDGER_ID_INVALID')`；其他字节保持。
- before/after均可由标准库AST解析；这只证明语法可解析，不证明产品运行或测试通过。
- 原M15 source manifest的39项实际文件长度/SHA全部匹配。canonical descriptor SHA为 `97129b2c480879fbc8dc12e7ee5170928e86a9cc24a1b9c689eb3fbb830a3682`，与 `us_mapping_daily.py:28` 的PIN一致。候选没有改变vendor或descriptor，此次guard本身不需要改该vendor PIN；`bind_us_owner`已经在17—20行将自身字节纳入code identity。

以下行号除注明候选外均对应上述固定源ZIP。简称：

- `S/` = `V5/src/v5_shadow/`
- `U/` = `V5/vendor/us_mapping_baseline/`
- `M/` = `V5/vendor/manager_plan_baseline/v4/manager_research/`
- `R3/` = `references/R3/handoff/manager-daily-r3-repair-20261009/after/api_current/v4/manager_research/`

## 2. 真实接线与已存在能力

### 2.1 本M15真实调用不是R3 kwargs调用

实际链条：

1. `S/daily_dispatch.py:37—40` claim后调用 `bindings[lane]['invoke'](job['owner_request'], claim['run_id'])`。
2. `S/daily_us_owner.py:19`绑定 `run_us_owner`；候选 `daily_us_owner.py:27`调用 `run_us_mapping(request)`。
3. `S/us_mapping_daily.py:32—33`请求只接 `target_date, now, us_data_root, us_files, manager_output_root`。
4. `S/us_mapping_daily.py:155—181`加载原mapping/bridge/store，建立原三文件reader与M15输出store。
5. `S/us_mapping_daily.py:182`实际调用 `mapping.persist_daily_run(service, target, now=started)`。
6. 对应 `U/v4/manager_research/us_mapping_research.py:280` 原接口恰为 `persist_daily_run(service, target_trade_date, *, now)`。

因此**不存在已证实的“当前M15传timeout_seconds/execution_context导致TypeError”**。R3的 `persist_daily_run(..., timeout_seconds=None, execution_context=None)` 在 `R3/us_mapping_research.py:958—960`，是条件donor，不能因为参考包里有它就无条件替换完整owner。若为恢复合同选用R3，才需要核其budget、dispatch、publication intent、依赖与新增精确I/O；签名shim/吞TypeError不成立。

### 2.2 原三文件、session和安全能力已在

`S/us_mapping_daily.py:62—81`约束精确三文件名和session路径，84—102按声明SHA读原字节，141—165按原日历/时区/cutoff复核实际session，168—182将研究cutoff与实际生成时钟分开，190—198及230—233复核输入和实现身份。原bridge还保留session/phase/PIT/来源和安全验证。**不要求重写reader、日历或M03采集。**

### 2.3 原四键和材料算法都已存在，但入口归属不同

- `U/v4/manager_research/us_mapping_research.py:140—149`从真实reviewed卡片构造daily keys；152—181验证关系registry可用时间；184—277为既有四键daily build。
- 固定种子真实内容：HK.06166对应LITE/COHR、`PRODUCT_PEER`；HK.06088对应AVGO、`DIRECT_NAMED_COMPONENT_SUPPLY`；HK.00763对应CIEN、`OPTICAL_TRANSPORT_PEER`。HK.06869、HK.01729是无daily键宽主题卡。无需扩种子，更不能把peer改成供应链。
- 原材料算法在M18物理闭包中存在：`M/issuer_us_relations.py:193`的 `material_us_relations(cards, start, cutoff)`；`M/research_evidence.py:528—538`的 `collect_attention_evidence(...)`，550行调用前者、575—576行调用 `us_mappings` 与 `us_mapping_diagnostics`；`M/research_attention.py:537—556`的 `build_research_attention(...)`调用证据入口。
- `M/research_evidence.py:352—374`是行业/主题join，376—402是显式US个股join。`M/issuer_us_relations.py:59—67,108—174,193—237`已有主体/span、native身份、来源SHA、真实取得/PIT与standing contract处理。
- `S/current_us_research.py:60—81`已有三个范围的coverage传递，114—146显式dynamic编排经过M18；`S/manager_plan.py:411`也已绑定native master。**不应返修历史上“永远未绑定native root”的旧问题，也不能把这条跨模块dynamic路径当本候选已交M15独立材料入口或普通auto/API/页面完成。**

## 3. 静态可证的返修项

### R1-01 / P1：M15材料入口与可消费产品仍未交付

证据：候选只改guard；`S/us_mapping_daily.py:32—33`无材料、native引用/输入合同，`_worker:155—198`只调用种子daily；输出不提供独立材料行业/材料个股结果。39项U闭包不含上述M材料函数。候选也没有专属新入口、SOURCE_TARGET_MAP或跨模块请求来说明怎么调用现有算法。

这不是要求重新发明材料算法；是**已有原算法尚未通过M15固定接口接线**。真实材料未提供可记NOT_RUN，但入口/合同/代码本身应先交。

最少返修：

1. 在允许的M15适配器或M15专属新增文件中给出稳定入口，绑定同一US session/cutoff和M02 native主表参考日、目标/资格日，读取M04已验证正文/span/来源/真实取得引用。
2. 复用上述原函数；如做私有闭包，只带实际需要的固定原依赖，逐文件给donor、byte identity、manifest/PIN差异。不要跨改共享M18 vendor，也不要复制完整经理系统。
3. 交出种子daily、材料行业、材料个股三个独立结果/拒绝/未评估视图；材料缺件不覆盖已评估种子，种子成功也不能代替材料评估。原M04取得时点缺失不得补历史时间。
4. 给M18稳定DTO或只读入口和按原workspace保存的请求；经理store、普通API、页面属M18联调，可列缺口，不阻塞独立M15候选。

### R1-02 / P1：原store已接受的精确旧receipt仍被M15 bridge拒绝

证据：`U/v4/manager_research/us_market_bridge.py:75—76`先调用原store exact-read；89—95的第二轮字节绑定仍要求 `receipt_from_bytes == self.store._receipt(payload_from_bytes, payload_sha)`。原store的窄兼容已在 `U/infrastructure/_research_peripheral_store_parts/publish_read.py:80—99`；两个字段常量已在 `U/infrastructure/research_peripheral_store.py:77—80`。所以恰缺 `market_snapshot_captured_at` 与 `market_snapshot_source_response_sha256` 的合法旧receipt通过store后，又在bridge:95变成 `US_MARKET_LINEAGE_BYTES_INVALID`/CANNOT_CONFIRM。

最少返修：只将M15消费桥接该条件替换为同一store的 `_receipt_matches(payload_from_bytes, payload_sha, receipt_from_bytes)` 判定，保留payload映射相等、manifest绑定、原receipt字节SHA和后续session/phase/cutoff/安全门。更新该U文件对应manifest entry及 `S/us_mapping_daily.py` PIN；source store与旧receipt不改。M18同名bridge需要同修时仅列跨模块请求。

所需定向用例：完整新形状、恰缺两字段旧形状成功；只缺一项、多缺、改值、额外字段、payload/manifest/原字节SHA篡改拒绝。不能拿完整新形状测试覆盖旧receipt回归。

### R1-03 / P1：精确run读回、失败保留成功与结果未知恢复仍未完成

证据：

- `U/.../us_mapping_research.py:57—78`的 `_read_saved(store,date)`从latest定位run。
- 同文件280—302的persist不分成功/失败状态写 `latest.json`（298行），然后299行仍经latest读回。
- `S/us_mapping_daily.py:182—187`保存后再次调用 `read_workspace_mapping(service,target)`，该入口在U文件81—84仍使用latest。
- 因而A保存后B推进latest，A会误读B并失败；现有“比较发现不匹配”是安全拒绝，但**不是指定A的独立exact-read**。合法输入得出PARTIAL/CANNOT_CONFIRM等非成功结果时，旧persist也会让它推进原成功latest。历史成功run文件未删除，不等于成功指针未被覆盖。
- guard只把ledger ID放进返回引用（候选40行），没有把该attempt绑定到持久化的daily输入/执行身份；`S/daily_dispatch.py:43—46`遇到异常保留OUTCOME_UNKNOWN，`S/run_ledger.py:89—91`避免盲重试，这个安全边界已有，但候选没有提供owner按原attempt查结果的恢复闭环。

最少返修：

1. 按本次daily run_id和artifact SHA读取 `us_mapping_research/<date>/runs/<run_id>.json`，验证schema/date/run/hash/安全字段；latest单列观察，不能作为本次artifact定位器。固定R3 donor的 `_read_exact_run(store,date,run_id,expected_sha=None,*,read_budget=None)` 在419—434行可作为已有语义依据。按实际选用版本保留必要依赖，不只摘签名。
2. 成功A、失败B时，B保留自身不可变产物/诊断，成功A仍可由成功引用读取；不要用失败指针覆盖成功作为唯一可消费结果。
3. 未知结果必须能按原ledger attempt/trigger找到对应持久化run或明确仍未知；继续保持不自动重试。若采用R3机制，列出M15内精确新增dispatch/intent路径与完整闭包，`S/us_mapping_io.py:80—86`当前只白名单runs/latest，不能放成任意I/O。跨模块service/router接线交M18。

必要独验场景：A写入、B推进latest、A仍exact读A；A成功后B失败A仍保留；同attempt结果未知先查原run；错SHA/date/run/安全字段拒绝。无需改M03生产者或共享调度。

### R1-04 / P1：runtime.patch原样不可应用，reverse交付含糊

候选runtime.patch前四行：

```diff
diff --git a/tmp/V5_before_m15/src/v5_shadow/daily_us_owner.py b/V5/src/v5_shadow/daily_us_owner.py
index cb6252d..4b0507c 100644
--- a/tmp/V5_before_m15/src/v5_shadow/daily_us_owner.py
+++ b/V5/src/v5_shadow/daily_us_owner.py
```

实际只读检查（不是产品运行，也没有应用补丁）：

```text
cwd = /workspace/shared/review_m15_r1/source
command = git apply --check /workspace/shared/review_m15_r1/candidate/V5_M15_AFTER/runtime.patch
exit = 1
error: tmp/V5_before_m15/src/v5_shadow/daily_us_owner.py: No such file or directory

cwd = /workspace/shared/review_m15_r1/candidate/V5_M15_AFTER
command = git apply --check reverse.patch
exit = 1
error: tmp/V5_before_m15/src/v5_shadow/daily_us_owner.py: No such file or directory

same cwd
command = git apply --reverse --check reverse.patch
exit = 0
```

runtime.patch与reverse.patch完全相同，SHA均为 `17077237c3415c6891c9851c3ae237313e89374149fcd0d207688d398e6f676b`。因此不能宣称reverse完全不能用：显式 `-R` 检查可过；但是包没有写出此回退约定，且forward header确实有错误源路径。

最少返修：以同一仓库相对路径 `a/V5/src/...` 与 `b/V5/src/...` 重生正向补丁及真正反向补丁，或明确唯一 `git apply -R` 回退约定；在完整固定before/after树分别做只读检查与临时隔离根应用/回退字节校验。别让Mac集成者猜strip层级、创建虚构 `/tmp/V5_before_m15` 或手工改补丁。before SHA正确但包内没有before完整文件，须补齐。

### R1-05 / P2：恢复评估与历史可用性应分开报告

`S/us_mapping_daily.py:166—182`正确保留实际started/generated_at，同时冻结研究cutoff。`S/us_mapping_scope.py:16—24`又要求 `daily.generated_at <= market.research_cutoff` 才让ready成立；25—50在不满足时把本次scope行和评估计数设None。对cutoff之后执行的历史恢复，这是确定的静态路径。原测试 `test_us_mapping_scope.py:45—47`已明确验证迟到产物不能假装在cutoff前存在，故**不能直接删除这道历史PIT门或回填generated_at**。

本次daily产物本身仍保留status/matches；问题是尚无“现在对固定历史输入完成了哪一范围评估”的独立诊断出口，不能拿历史不可用来一并抹掉当前恢复评估，也不能把当前恢复冒充历史当时可见。

最少返修：保留原历史available/PIT结论，另显式输出恢复评估的执行kind、实际生成时点和种子路径结果/范围计数；材料/资格另行说明未知。此项是任务输出合同补齐，不要求重写原关系算法或改变历史页。

### R1-06 / P2：交付与测试证据还不足以独立落地

现有6文件仅有一个after源码、两份同字节patch、两行SHA manifest、TEST_REPORT.md、test.log。缺任务要求的START_HERE、SOURCE_TARGET_MAP.csv、before完整文件、MAC_APPLY_AND_ACCEPTANCE.md、CROSS_MODULE_REQUESTS.md、M15新增/修改测试源码，以及执行cwd/解释器/依赖/exit记录。

日志逐字末行为 `11 passed, 10 errors in 0.16s`；10项均在 `V5/tests/test_us_mapping_daily.py:17` setup阶段报 `V5_US_MAPPING_REQUEST_PATH_REQUIRED_NO_SKIP`，业务断言未进入。日志SHA `3c25bdb5842f228c723839685e87b35bb467f80e4abe33ce0181cb4aca317500`。

准确分类：

- 这是候选报告的11项通过、10项缺输入导致的setup ERROR/BLOCKED；不是21项通过，也不是已证实10个业务代码回归。
- 该日志没有进程exit记录；不根据pytest惯例伪造exit。
- 固定源的4项daily_us_owner测试使用mock，7项scope测试合成数据；没有guard非法ID并且owner未被调用的新增测试。候选没有补该测试。
- 真实原件/材料重放、Mac业务验收、自然接续和回滚均尚未证明，可明确NOT_RUN；**NOT_RUN本身不是本报告退回代码的理由**。

最少返修：把上述包材料与对应delta测试源码补齐，保留现有失败日志。真实输入缺失则给最小输入合同而非造三文件/回填时钟；已知源码已有，不应要求用户重新发整仓。后续Mac应核逐文件前像并在独立M15根执行，不猜安装路径或覆盖现役。

## 4. 可直接回传Chat的最小返修单

1. 保留guard及原四键/材料算法；补guard非法输入无owner副作用测试。
2. 在M15 bridge调用原 `_receipt_matches`，同步唯一受影响的U manifest entry及PIN，交完整正反例。
3. 对现有daily owner补本次run/SHA exact-read、成功保持与未知attempt可核恢复；只按实际需要采用R3，不声称当前已有kwargs错配。
4. 给M15自己的材料入口和三路径输出，复用原 `material_us_relations → collect_attention_evidence/us_mappings/us_mapping_diagnostics → research_attention`；列实际最小闭包和M02/M04缺件合同。不得跨改共享M18。
5. 修正恢复评估与历史可用性诊断的分工，保留实际生成时钟、源session/截止、目标/参考/资格日与未知，不扩大种子。
6. 重打完整可应用文件包：before/after、标准相对路径patch、SHA、映射表、改动范围、测试源码/日志、Mac隔离应用回退说明和跨模块请求。不要以另一份泛化计划代替代码。

## 5. 验收边界

- 可确认：候选身份、唯一2行delta、before/after SHA、原39项静态manifest/PIN一致、实际调用链、上述静态合同缺口及补丁路径失败。
- 不能确认：候选真实运行正确、Mac前像/产物、M03真实采集/自然slot、M02/M04真实材料和资格、M18普通auto/API/页面或完整M15业务验收。
- 当前不需要：新开模块、重写已存在关系算法、扩四键凑覆盖、重修M03可信加载、修改source store/receipt、跨改M18/前端/调度、生产切换或放宽权限。
- M18集成尚未完成本身不阻止独立M15候选；**本候选的直接阻塞是范围内代码与完整交付尚未补齐，先返Chat修复，再由Mac独立验收。**
