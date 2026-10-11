# M09 R2：在现有开发分支完成实体修复

继续同一 M09，不新建模块或另起空壳。使用真实 GitHub 连接读取私有 `lexi2016/v5` 的 `v5/m09-handoff-20261011`；先核当前 HEAD、提交祖先和本目录 `FILES_SHA256.json`。完整 R1 是 `d0f9905940584777abbcae248850ebc487cade63`，本反馈提交为它的后继；保留已有全部源码、前后像和证据。后续修复可直接提交同一开发分支，不 force、不覆盖并发，不 merge main。

先完整阅读 `source_reviews/MERGED_REVIEW_M09_R1_MAC_AND_R2_REPAIR.md`、`source_reviews/PROMPT_M09_R2_REPAIR_20261011.txt` 和 `mac_evidence/`。下面的 GitHub 方式替代原文所有附件/ZIP交付要求，其技术要求仍有效。不能仅回复计划、接口请求或重新给 ZIP。

## 一、重复 attempt 回执漏洞

R1 `a_close_daily.py:738–742` 只核 request_sha 就返回既存 receipt。独立 Mac 六个合成夹具先真实 FAILED，再保留 request_sha 篡改 schema、日期、trigger、安全字段、伪 SUCCEEDED/run/generation 或删除必需字段，全部被接受。原输入、原 receipt、篡改、实际返回、request、started、结果及脚本均可直接读。

统一验证持久化 schema、精确日期/slot/trigger/request/started、时间类型及顺序、安全真 bool 和 status-specific 字段。SUCCEEDED 要验证真实 calculation/run/record/generation 与可信提交见证；单换现有 _attempt_receipt 不充分。坏回执 fail closed，不跑 producer、不切代、不覆盖坏证据或有效旧成功。合法 FAILED/UNKNOWN 保持正确幂等语义；17:10 合法 reuse 可引用 16:05 创建的 generation，不能错误强制每个 reuse trigger 等于 generation.commit_trigger，不能循环校验。

保留原 125+6 断言，补六类 RED→GREEN，以及坏 started/slot/cutoff、伪或缺失产物、跨 run/跨日和前槽成功保旧等负测。

## 二、历史研究与自然/PIT准入分开

20261009 未清洗原件已真实解码 5126 行，2 个 bar_close_pos 缺失，137 空 name，240 空 industry code，240 空 industry name。两个历史 admission 各九类原因、617 个空文本字段（不是617只股票）、两次 FAILED/无成功 generation 都已有原始证据。不要等待未来日期或把这归为环境没跑。

按原总任务和冻结原源码，逐项区分错误身份/完整性/越界硬拒绝、自然/前瞻/PIT阻断、历史研究可显示缺口。先在隔离目录用未清洗原件实际跑原 producer/store/独立 reader，保留完整新结果或具体原错误。依实际合同给最小历史研究路径，诚实标记 HISTORICAL_REPLAY、PARTIAL/CANNOT_CONFIRM、未知来源时点和受影响指标，不能全页永久 MISSING 代替可计算性判断，也不能猜放宽。禁止清洗原件、补0补名称、复制旧 REPLAY 当新计算、改原算法、用 mtime/现在/模型15:30伪造 available_at。原模型自己的固定变换不应误标为新清洗。80MB 原 receipt 按安全原件绑定与合同处理，不制造 READY 摘要，也不简单提高上限求通过。研究成功不得被 NATURAL/正式消费者复用晋升，不得生成当时 16:05/17:10 已可用的伪证。

## 三、共享接口要交实体实现

普通 API：`apps/api/v35_api/app.py`、`review_router.py` 和必要的 `domains/review_evidence_layers.py`。服务端受信私有 root 绑定；HTTP 不可提供 root；保留 HK 和共享 path owner；M09 选择后不能被旧 strict A 或后置 evidence loader 混源，GET 只读且精确日期。

原页面：`apps/web/src/views/ReviewView.vue`、`components/review/AshareReviewPanel.vue`、`contracts/review.ts`，确需再改 `App.vue`/`api/review.ts`。保留原 native 模型、涨跌平、行业、个股角色、三情景固定概率和 WATCH_ONLY；展示研究分类、缺口、served 与 latest_attempt 分离，空值不补0。提供真实组件挂载、请求、切日、慢响应、返回和刷新测试，不能 stub 掉关键消费者。

Dispatcher：已有 `daily_close_plan.py`、`daily_dispatch.py`、`run_ledger.py`、`composition.py`，按 a_share 日历触发 16:05/17:10 两份回执、同计算可复用、不让日 logical key 吞后槽、不增第三槽、不改 HK 规则或全局 allowlist/root。仅交可运行隔离候选和测试，不启用自然调度。若共享 owner 另行应用，仍交精确文件映射的 integration_candidate/before 与 after、真实正反 diff、SHA、适用前像和测试，不能再只写接口请求。活动前像 source commit 未知保持未知，不冒称最新现役。

## 四、GitHub实体交付

完整 R2 源码、tests、integration 候选、R1 前像及新增路径 ABSENT 证明、R1→R2 正反 patch、真实 apply 往返日志、逐文件 SHA256/Git blob、实际命令及完整 stdout/stderr/exit、RED→GREEN、单模块回滚说明，全部作为可读文件提交该分支。先核远端 HEAD，基于最新合规继承链继续；遇并发先检查，不 force。回复仓库、分支、最终固定 commit、可直接读取入口、已验证与 NOT_RUN 的精确清单，不以 ZIP 交付。

支持 Mac 125/125 零 skip + 原独审6/6仅属于 d0f R1，新版必须重验，不能借旧通过数。当前环境可跑立即跑；缺依赖或无法操作 Mac 时记录真实错误与准确 NOT_RUN，同时交完整实体代码，交由既有授权 Mac 流程独验。原算法、业务完成度、现场接线、自然运行分层报告。

只在独立 V5 候选范围工作；不动现役 V4，不改冻结算法/固定概率/研究与PIT边界，不采集、不交易、不部署、不启用自然调度、不扩大安全权限或凭据访问。
