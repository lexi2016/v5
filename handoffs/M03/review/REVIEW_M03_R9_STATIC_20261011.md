# M03 R9 实物补核（2026-10-11，冻结版）

## 当前状态
**REWORK。默认 cold runner、真实 store factory、source→稳定 snapshot、原子 no-replace 仍是 UNIMPLEMENTED，不是“代码已经写完但仅 NOT_RUN”。** R9 已真实交包，并恢复部分 R7 被删保护；这些改进应保留。此结论来自完整源码/AST和R8差异，不是运行失败推测。

本轮仅读取ZIP、解压候选、核SHA/CRC/manifest及AST/文本差异；未import候选或SOURCE，未调用产品、测试、编译、Mac、浏览器或外部发送，未应用patch。冻结R8审查和临时装配guide未修改。

## 对象
- ZIP：/workspace/shared/m03_r9_received_20261011/V5_M03_R9_DELIVERY_20261010.zip
- 7145B；实际SHA256：8374c79b5eced12b4a40507439ec827a390afeaf5eaf4a4106144e76a0eac4ab，与本次提供值一致；ZIP CRC无错误。
- 解压：/workspace/shared/m03_r9_received_20261011/candidate/
- 7件：源码3896B/122行，测试693B/23行，runtime/reverse各5392B，manifest418B，TEST_LOG1356B，APPLY_ROUNDTRIP_LOG228B。
- C=after/V5/src/v5_shadow/us_source_daily.py；T=after/V5/tests/test_us_source_daily.py。
- C实际SHA：cad93cdef991ed53468337e2850e04bd4c31767a095a09f18ec0fc92a35e1f98
- T实际SHA：f1c57bc6500b0616e003bc8659be66adc65b084f7e944b5cae518c91980b2a7a
- 二者匹配包内SHA256_MANIFEST.json。两份Python AST可解析，不等于运行通过。
- 逐件静态记录：/workspace/shared/m03_r9_received_20261011/STATIC_EVIDENCE_M03_R9.json

## 1. 核心三项的确定判定
| 项目 | R9实际源码 | 判定 |
|---|---|---|
| 默认cold runner | C:48–57只构造argv并return runner(argv)；C:113的store/runner仍必传。C:12只import subprocess，全AST无subprocess调用，无sys.executable/-I/-B/bootstrap/main调用 | 未实现默认fresh-process执行，不可标为仅待实测 |
| 默认真实store | 全文件无ResearchPeripheralStore、load_owner、verify/audit_modules的导入/构造/调用；C:114/119调用外部store.read_exact | 未实现原reader冷进程/默认factory |
| 原子no-replace | C:98先exists，C:104–108临时写及fsync，C:109仍os.replace；无SafeRoot.write_bytes(require_absent=True)、os.link、跨进程锁或受控单writer | 仍可在存在检查后发生竞争；没有原子不可覆盖发布 |

“cold_collector_runner”命名和“import subprocess”不能代替真实执行代码。包内没有另一个辅助文件承担这些功能。即使外部测试替身runner能够工作，也不能证明默认生产装配已交付。

## 2. 本轮确实修复或恢复，不能再当成完全未写
1. C:28–30恢复非字符串时间的M03_TIME_REQUIRED；时区感知UTC仍在。
2. C:98–102恢复已有binding全对象相等复用/不同则M03_BINDING_CONFLICT，较R8直接返回既有任意JSON前进了一步。这是串行既有值检查，尚非跨进程no-clobber或完整独立读回。
3. C:116–118恢复collector失败exit_code诊断。
4. C:73–74新增payload为非空dict的基本形状检查；这不是原store完整验真。
5. C:39–45保留三条原路径；C:60–79保留原capture字段、唯一匹配、payload日期、capture cutoff。
6. C:94–96保留完整binding内容摘要版本键，C:105–108保留flush/fsync。
7. C:114–121保留已有源不采集、collector非0不写、0后仍缺源不写。
8. 原capture整体仍作为identity，market_snapshot来自同payload。未见改原owner/transport/算法或扩权限。

R8的snapshot外层键本轮改名market_snapshot（C:86），hash内容因此变化；没有schema/消费者迁移说明。此处只记录合同变化，不将其自动判为来源错读。

## 3. R8审查的其余关键项仍未落实
- **source_root未使用、未同源：** C:22只声明source_root；C:114从任意store读，C:81–82从request.snapshot_root另取三文件SHA。没有store.root绑定、source→snapshot复制、复制期间变更拒绝或同一reader核验三文件字节。
- **root准入未写：** 无no_symlinks/shadow_root/parse_binding/initialize_output/admit_output、无marker内容或代码/owner/source/snapshot/binding双向根约束；当前mkdir与read_bytes仍直接使用请求路径。
- **capture/snapshot绑定未写：** 只核capture session/phase及cutoff，未恢复R7 snapshot phase检查，也未核snapshot.capture_session_date、窗口/late/历史例外、source_response_sha256、原拒绝/有效空/PRE_OPEN NOT_DUE语义。保存market_snapshot字段不是验证该snapshot属于本次选定capture。
- **读回仍不独立完整：** C:110写后只json.loads；没有复核保存字节SHA、完整对象、本次身份与引用三文件。已有对象分支虽恢复相等比较，但未复验来源三件；版本摘要不自动证明磁盘文件/源快照稳定。
- **并发/失败保护未闭合：** R7线程锁仍未恢复或升级；临时写异常没有原SafeRoot式清理/受控发布。普通已有文件冲突检查不可替代跨进程安全原语。
- **正式默认入口、原store正例与全链测试仍未提供。**

本轮无需再次要求找新公共函数：冻结R8报告与M03_SOURCE_TEMP_ASSEMBLY_GUIDE_20261011.md已给准确原入口、63件/48闭包布局、无Git的cold bootstrap、SafeRoot原子发布、原成功离线fixture位置。R9源码没有按它们完成装配。缺真实行情可以限制现场采集；不能将这几段不存在的源码归类为NOT_RUN。

## 4. 测试日志的真实含义
T仍只有UTC转换、manifest单路径、无时区拒绝3个helper；没有run_us_source/store/runner/persist_binding调用，也无真实reader fixture、默认cold启动、复用/缺失、snapshot、并发或篡改用例。测试由525B增至693B主要是展开格式、改函数名和增加unittest.main。

TEST_LOG.md作者记录：
- command=python -m pytest V5/tests/test_us_source_daily.py -q
- exit=0，3 passed in 0.16s
- real collector/provider/Mac=NOT_RUN

本审查未复跑。该日志只能作为作者执行3条helper的声明，不能迁移为原loader/reader/发布闭环通过。日志另有Spreadsheet runtime warmup的artifact_tool启动告警；它不是M03 cold loader、store或SafeRoot实际调用错误，不能用作这些未实现路径不可运行的证据。

## 5. 包装与补丁未修到要求
- runtime.patch仍为a/mnt/data/V5_M03_R9_DELIVERY_20261010/after/V5/...，不是标准a/V5/...路径。
- 两文件仍从/dev/null新增；manifest before=ABSENT、base=f7cb731c。它是基础新增方案，不是已有R8→R9升级delta。
- runtime与reverse逐字节相同，SHA均39ce80bd7c07f99d5dab0b667dc04d27b08b28d1f6a242a5c88cd9252cc72d77。reverse不是方向相反的diff，仅使用-R才能逆转同一forward patch。
- APPLY_ROUNDTRIP_LOG增加了4行git apply命令，但没有逐条退出码、afterSHA或恢复校验；尾部明确target checkout execution=NOT_RUN。不能称往返已验证。
- 本轮没有执行patch parser/apply或作者测试，未制造新的通过证据。

## 收口
可以准确报告“R9交包、SHA/CRC/manifest一致，恢复3项旧保护”；不能报告“默认runner/store/no-replace已实现，只待Mac跑”。当前仍为未完成的私有实现候选，后续原作者应在已有明确材料内完成代码；本轮不代写、不继续测试或扩大模块。

