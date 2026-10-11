# M03 下一次返修：保留最新reader，交完整累积代码

本文件是原SOURCE、R9/R12历史静态审查、完整R11字节和最新R13字节的派生任务。不是实现代码或运行证据。

## 先核真实前像
使用本固定commit的source63份原件/48owner和三个隔离候选目录。R13确为最新reader切片；不能把R9称最新，不能直接把R13完整after覆盖R11。
R11 `us_source_daily.py` SHA`464faaf371bd5eb6e3cea899842131173544292e0452e6c39063e121925ed4d8`；R13对应SHA`78cff69c77097aa45507596becf78b762498ca966a18438101340c15a9a14334`。原manifest的文字R11-after不能代替前像哈希。

## 保留进步、禁止回退
- R13真正多行child脚本，可解析；使用原load_owner、admit_output、ResearchPeripheralStore.read_exact，finally verify/audit后才输出成功JSON。父端真实subprocess.run，sys.executable/-I/-B、明确路径、非零stdout/stderr诊断、JSON/payload dict或None检查。不要重新引入R12的`;try:`或先输出再验证。
- 保留R11的USSourceRequest/parse_utc/source_paths/collector_argv/run_cold_collector/select_capture/create_binding/persist_binding等现有类/helper；采用完整累积文件或独立reader模块的准确接口，不交破坏性替换切片。
- R9历史上已有源不采集、失败exit/0后仍缺源不保存、capture唯一匹配、日期/cutoff、完整binding版本身份及冲突检查的意图必须在完整入口中实际保留，不能把历史helper存在当当前总链已恢复。

## 本次需真正完成的源码
1. 完整`run_us_source`默认接线：原frozen collector独立cold child，原reader另起fresh child；固定受控v5_src/owner_root，原PIN/verify/audit/transport/显式采集门禁不删。真实采集不在本轮离线测试范围。
2. 用原initialize_output/admit_output进行私有数据根准入，不把data放在代码BASE/owner_root内部或祖先，不先resolve后掩盖symlink。保留不同capture/source/snapshot/binding根的身份及双向隔离。
3. 从明确source稳定取得原payload/receipt/manifest三件，复制到准入的独立snapshot，拒绝复制期间变更；原store reader与三件物理SHA必须验证同一个snapshot。不能从任意store取payload、另一个root算SHA。
4. 保留原trade/session/phase、capture唯一选择、capture_session_date、UTC时区/cutoff/原窗口、late/historical例外、source_response_sha256及market_snapshot合同。缺源、原拒绝、有效空、PRE_OPEN NOT_DUE不能混成成功；不改原日历/DST/provider。
5. 使用原SafeRoot/owned IO/跨进程锁语义形成真正原子no-replace binding提交，补新根准备、FileExistsError同值重验复用/冲突及finally清理。仅os.link存在不代表完整持久化合同；保留旧成功。
6. 独立磁盘读回完整binding身份、请求/日期、snapshot三件SHA与原reader结果。已有对象复用也要重验其引用原件，不能仅json.loads或对象相等。
7. 完整处理timeout、非零、坏JSON/类型、原诊断，不能吞成缺源。清楚定义各层payload/None/异常结果与类型边界。

## 真实离线测试，不等同自然业务通过
复用`source/V5/tests/test_cloud_us_collector.py`原152–203离线RSS/quote→原producer→原ResearchPeripheralStore源码模式。owner_root直接用已物化48件，新的定向fixture避免旧test setUp的git assembler；不改冻结owner。原源码和标准库已在，不以缺git checkout拖延完整代码。
- fixture禁真实socket/Direct，原Proxy合成响应/clock只在测试接缝，不进入生产默认runner。
- 在新标记私有根生成真实格式三件，实际调用默认reader fresh child；核返回与三件前后字节不变。
- receipt/manifest/payload篡改、坏marker/错根/非零/timeout/坏JSON必须实际拒绝；不只查callable/函数名/脚本AST。
- 完整入口补已有源复用、collector非0、0后仍缺源、错session/phase、同日多capture、换源、复制中变更、并发no-replace、失败保旧成功及读回引用篡改用例。
- 执行状态如实区分：UNIMPLEMENTED是没写代码，NOT_RUN是代码有但未运行；存在性/AST检查不是reader/业务测试。真实网络provider、Mac、页面和自然接续未验时继续NOT_RUN。

## 完整GitHub交付
在本模块分支交完整before/after、全部测试、真实前像和后像SHA256/Git blob/原来源映射、标准相对路径正向及真正反向diff、隔离apply/rollback说明。各版原错误patch不复用；原fixture/日志没有跑过不造PASS。实际执行才记录原命令/解释器/退出值与允许范围脱敏日志。
只写M03工程范围，保留原算法/owner/PIN/guard，shared scheduler/API/UI交INTEGRATION_REQUEST，不碰V4/main/其他模块，不交易或扩大权限。固定候选commit交独审和现有Mac隔离验收，本次源码交接不算功能落地。
