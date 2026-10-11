# M09 R1 合并审查与R2返修要求

更新：2026-10-11 11:38 UTC。基于固定R1 d0f9905940584777abbcae248850ebc487cade63及独立Mac反馈。此报告编写阶段只读已有源码/日志，没有另运行测试或改业务代码。后附11:28静态全文作为有时间戳的审查底稿；其中当时的Mac/parquet NOT_RUN已被本节真实证据更新。

## 最新结论

保留R1全部实际成果。支持版本的Mac隔离环境已完成125/125、零skip（四个pyarrow案例实际执行）及原独审6/6；两槽与generation演示通过；原未清洗20261009 parquet已真实解码。重复attempt返回校验漏洞由原静态发现升级为六类真实复现。普通API、原ReviewView和dispatcher尚未接线，仍不能部署或认定自然验收通过。

Mac支持环境为既有 /Users/lexi/Documents/Codex/2026-10-11/task/m13-isolated/venv/bin/python，Python3.14.6、pandas2.3.3、pyarrow24.0.0、pytest9.1.1。没有安装依赖或更改全局环境。这一结果不能冒充原现役pandas3.0.5/pyarrow25.0.1超声明范围环境的兼容认证。TMPDIR已设为新无symlink工作区，本次没有前次静态提醒的临时路径误判。

## 反馈包与独立核验

- M09_MAC_INDEPENDENT_FEEDBACK_20261011.zip：145272B，SHA256 2b03a827150a9b7ce2232bbbc808831a1d1e42d1fc7f6d46e5e1675433f7af6f。
- Library libfile_01628ba1c4e081919510ba03fbac7bb4。
- 本次下载核CRC173成员、MANIFEST172项bytes/SHA全合。
- a_close_daily.fixed_candidate.py SHA23b4200ffb29e83041b761927c6f285ff84d6b92a3cf8b2fc3e527a9d8ae1d9c，与完整R1一致。原after、before、runtime/反向patch往返和测试前后树保持一致。
- 主套件 verification/original-suite125.stderr.log：Ran125，OK，.exit=0；unittest自身32.980s，外围计时33.716s，两种时长不可混称。
- 原独审 verification/independent-six.stderr.log：Ran6，OK，.exit=0；内部3.679s，外围3.763s。
- 真实诊断、generation walkthrough各.exit=0。pyarrow的sysctl缓存/NEON权限警告原样保留，真实解码测试仍成功；不以它要求扩安全权限。

## 阻断1：重复attempt漏洞已真实复现

固定源码a_close_daily.py:738–742保持相同request_sha就返回existing；六个独立私有SYNTHETIC夹具先以错误input_manifest_sha真实得到FAILED（SOURCE_SHA_MISMATCH:input.json），随后只保留request_sha，分别改：

1. schema_version=INVALID_SCHEMA
2. trade_date=20261008
3. trigger.attempt_id=other-attempt
4. safety.orders_sent=true
5. status=SUCCEEDED、run_id=fabricated-run、generation_sha256=a*64
6. 删除schema_version/trade_date/trigger/safety/status

negative_original_artifacts/RESULTS.json六项均为tampered_receipt_returned_unchanged=true、error=null。verification/duplicate-receipt-negative.exit=1刻意表示应拒绝而未拒绝。每件原receipt、篡改receipt、实际返回、request、started及异常原文均留在包中。没有真实订单、真实producer成功、head或外部副作用。不能扩大结论为独立公开generation reader已被攻破。

返修必须统一持久化回执校验：schema、精确T/slot/trigger/request/started绑定、时点类型及顺序、安全字面bool、status-specific字段。SUCCEEDED须独立验证实际存在的calculation/run/record/generation及其可信提交见证，不能仅有格式正确的SHA。单纯换成现有_attempt_receipt也不够，它没有检验SUCCEEDED所有实体链，仍需补齐。

要保留合法两槽复用：17:10成功receipt引用16:05创建的generation时，generation.commit_trigger本来属于首槽，不得要求所有reuse回执trigger等于创建trigger；同时不能循环调用校验或把伪成功洗成合法。保留合法FAILED/UNKNOWN重试的原语义，不以缺run/generation误拒全部非成功回执。坏回执拒绝且不运行producer、不激活新代、不覆盖原回执或有效旧成功。

新增负测除原六类外，应覆盖坏started/request/cutoff/slot、伪/丢失record或generation、跨run/跨日、坏旧输入/产品，以及前槽有效成功时后续坏receipt仍不能污染served身份。完整125+6仍要保留，不能删除/放宽断言来绿。

## 真实20261009已解码，拒绝原因可精确核验

real_historical_diagnostic/decoded_original_statistics.json实际5126行/5126唯一；日期/后缀/成员顺序与集合匹配，cleaning_applied=false。2个bar_close_pos缺失；137空name、240空industry code、240空industry name。原件及复制原件前后SHA不变。

admission_1605.json与admission_1710.json均panel_decoded=true、row_count5126、admitted=false；各issue计数：

- SOURCE_IDENTITY_MISSING：1
- SOURCE_TIME_INVALID_OR_UNKNOWN：1，CONTRACT_TIME_INVALID
- MEMBERSHIP_IDENTITY_MISSING：1
- MEMBERSHIP_TIME_INVALID_OR_UNKNOWN：1，CONTRACT_TIME_INVALID
- SOURCE_AUTHORITY_NOT_READY：1，status PARTIAL、authority_status REBUILD_REQUIRED
- SOURCE_COVERAGE_INCOMPLETE：1，0.8858620689655172
- SOURCE_RECEIPT_NOT_BOUND：1，OWNED_FILE_TOO_LARGE（原receipt80017050B超过16MiB）
- PANEL_TEXT_MISSING：617，137+240+240个字段缺失，不能误称617只股票
- PANEL_NUMBER_INVALID：2

两个attempt均FAILED，run_id=null、previous_success_generation_sha256=null、publication_recovery_status=UNCHANGED，无可服务成功generation。两个cutoff为2026-10-09T16:05/17:10+08:00，实际执行2026-10-11T11:34UTC，是历史回放。六种可选stage/video角色另为MISSING，不能捏造补齐。

以上是R1实际拒绝事实，并不预判九类原因都必须永久阻断历史研究展示。重试安全漏洞修复与真实历史研究可用性要分开处理；不等待未来10/12。不能清洗原件、缩造READY回执、猜available_at或用mtime/模型15:30冒充PIT；前瞻与自然两槽准入继续严格。

新增原代码证据：冻结domains/a_share_close_model.py:36–62只对ts_code/pct_chg/amount缺失做原有dropna；bar_close_pos仅列为必需列，后续模型没有计算引用。:53把空行业名变为NA，:65–66只在行业聚合中排除，不从市场广度数据丢掉这些行；:97–119按仍保留的行计算涨跌平。空name不会被丢弃，但:25–33的ST近似涨跌停判定会受名称未知影响，不能宣称相关统计无不确定性。原producer:55–161保留原model/review/store完整链。任务书TASK_M09:13要求真实历史复盘可用；:20允许RECORDED_INPUT_REPLAY；:30禁止静默过滤后把剩余称全市场。原内部变换不能被误说成新清洗，原件仍须字节不动。

请原Chat依据这些代码和总任务逐项建立九类问题的范围矩阵：硬完整性/错误身份/越界必须拒绝；自然/前瞻/PIT缺口不得晋升；历史研究可显示的缺项与受影响指标必须按原行为给证据。先在隔离目录用未清洗5126原始行运行原producer/store/独立reader，保存实际结果或原错误，再给最小实现：若原研究合同支持可计算部分，就在明确HISTORICAL_REPLAY/研究资格及缺口元数据下保存和展示真实复盘，不因可显示缺项把整页永久MISSING；若原链实际拒绝，精确说明字段/位置，保留可合法读取事实与缺口。不得复制旧REPLAY产物当新计算或擅改算法来求成功。

历史研究分支不得生成“16:05/17:10当时输入已可用”的成功证明；可有实际历史执行成功且自然/PIT未证，须在输入/计算/run/generation/回执/API/UI各层准确分离，并且不能被NATURAL或正式消费者复用晋升。80MB回执应按原件绑定与历史合同处理，不仅为了通过简单提高JSON上限；如可安全保留原件SHA/引用与真实可解析字段，明确其PARTIAL与未知，绝不制造READY摘要替身。具体分支/元数据方案由原源码和实际运行证据决定，不由本报告先猜放宽。

mac_real_input_check.py还把acceptance_class写死UNCERTIFIED_RUNTIME_DIAGNOSTIC，即使本次支持依赖满足声明；后续可准确区分声明版本满足与自然/PIT未验证，不改本次原日志标签。

## 阻断2：原API/UI/dispatcher需要实际代码候选

R1只有a_close_daily_api.py中的读取与纯合并，三份INTERFACE_REQUESTS尚为owner请求；25新增中没有活动router/页面/dispatcher接线。R2需依照已齐原字节前像交实际最小完整after与测试。若共享owner必须独立合并，则另交精确映射的integration_candidate/before与after、真实正反diff、SHA和适用基线，不再仅复述文档。

API：apps/api/v35_api/app.py、review_router.py以及必要的domains/review_evidence_layers.py。服务端受信配置绑定M09私有reader；HTTP不能提供root。保持未绑定旧行为、HK逻辑和共享path owner；选择M09后不得被旧strict A分支或后置evidence loader混源。缺失/损坏保持精确日MISSING/CANNOT_CONFIRM，无计算型GET。

UI：apps/web/src/views/ReviewView.vue、components/review/AshareReviewPanel.vue、contracts/review.ts；如真实请求/缓存路径需要，再精确改App.vue或api/review.ts。保留原native model显示、涨跌平/行业/个股角色/WATCH_ONLY及三情景原概率；显示M09证据、缺口和最新attempt与served成功分离，空值不补0。真实组件挂载/请求/切日、慢响应、返回/刷新测试，不能stub关键消费者代替集成。

调度：已有V5/src/v5_shadow/daily_close_plan.py、daily_dispatch.py、run_ledger.py、composition.py及确需的最小配置绑定。A用a_share日历，1605/1710各自触发receipt、同计算可复用；不让每日logical key吞后槽、不增加第三槽、不改HK既有规则、不全局开放lane/module/root。先做可运行接线代码和隔离测试，不启用自然调度。优先直接router注入单一M09可见性门，无需凭空扩大generic transport；确需wrapper须分别保留transport和M09身份、单模块CAS回滚。

原active附件source commit未知的事实保留；对已核原字节制作候选，不冒充其等于最新活动发布。统一集成者应用前另核真实前像。所有修改仅独立V5开发候选，不写现役V4，不改原冻结算法、固定概率或PIT/资格，不采集、不交易、不扩大凭据/权限。

## R2实体交付要求

完整更新after、原R1前像以及新增路径ABSENT证明；R1→R2正反patch与真实apply往返；代码/测试/集成候选逐件SHA与全包SHA；实际命令/完整日志/exit、新负测RED→GREEN。支持Mac125+6只属于d0f R1，新版本必须重新验证，不能套用旧数。当前环境可跑立即跑，缺依赖明确NOT_RUN且交完整代码，不以无法操作Mac或未来数据为不能实现借口。原算法/业务完成度/现场接线/自然运行分层报告。

---

# 附录：11:28只读静态审查全文（保留历史时间状态）


# M09 R1 独立只读收件与静态审查

日期：2026-10-11 11:28 UTC。范围仅已交付文件、源码、既有日志和GitHub只读身份。未执行候选业务、未重跑测试、未操作Mac、未发原Chat消息、未改仓库或部署。

## 结论

M09已获得可进入独立隔离验收的完整实体候选。默认入口是真实冻结producer/store调用，不是外部注入空壳。没有发现必须停止所有隔离Mac测试的源码空缺。当前不能作为部署或完整验收完成：活动API/UI/dispatcher接线尚未实现、真实parquet和Mac环境兼容未验证；重复attempt回执返回分支有确定静态校验缺口，应在发布前补负测并处理。

## 身份与完整性（本轮独立核验）

- 用户完整prompt：de12f6f3-05d7-4890-abf6-0c3a49699f21，10:26:04.463582Z。
- 最终答复：8bcae10b-6be2-54ce-812f-531413993b77，11:24:05.737586Z–11:24:51.743141Z。
- 原Chat：https://chatgpt.com/c/6acb63a0-57a4-83ee-8f96-e5c6936b6405?messageId=8bcae10b-6be2-54ce-812f-531413993b77
- 新ZIP：M09_A_CLOSE_CANDIDATE_20261011_d0f990594058.zip，17,258,686 bytes；SHA256 e39bbd8dad4a603a4412aa01b0d5ffdaeb4259271fdb284c576e9628b03964ad；872成员，CRC全通过。
- Library：libfile_b84dfb775a6c8191bf1a8f8df423cae5。
- GitHub实际commit：d0f9905940584777abbcae248850ebc487cade63；parent 782bfc9ae91ff9cfe897afffc52aad43b7c1b78c；tree 2e9f7ac6b9cca37a84ddbc02d0872440aa9c0a32。
- 已只读取远端完整树：1063项、870 blob、truncated=false；870项与下载文件的Git blob/bytes/mode逐项一致。870文件本地SHA256/bytes/Git blob全合。
- 内交付清单759项，排除清单自身；无缺项、无额外项、无哈希错。
- original/SOURCE_MANIFEST.json的F=f7cb731c384ee6890a87d16c19a5b5a621779477，共52份原件与before逐字节、SHA256、Git blob一致。
- before52份全部与after相同；after77份=52保留+25新增；仓库根对应源码与after完全相同。
- forward/reverse是不同的真实补丁。已有check/apply及52→77→52日志存在；本轮未重复apply。

## 发布前确定缺口

### 1. 重复attempt的既有receipt未经完整校验直接返回

文件after/V5/src/v5_shadow/a_close_daily.py:738–742。

run_a_close_daily读取attempts/<trigger_sha>/receipt.json后，只比较request_sha256，随后return existing。它未调用同文件593–613已有的_attempt_receipt，因而绕过schema_version、trade_date、trigger、trigger_sha256、status、safety和started绑定校验。若该文件残缺或改掉这些字段，只保留匹配request_sha256，重复请求即可原样返回该对象。正常GET路径仍会使用_attempt_receipt并拒绝不合法数据，因此这不是已经证明GET可服务坏generation，而是执行/重试返回合同不一致。

建议：至少将重复返回经由_attempt_receipt验证并绑定当前请求；对于SUCCEEDED如何表达“历史已执行回执”和“目前可读成功”需保持清晰。补残缺schema/错日期/错trigger/错safety/非法status负测，断言旧产品、head和回执不被重写。此结论来自直接分支阅读，未运行复现，不计为已测失败。

### 2. 活动API/UI/dispatcher仅有接线请求，没有实现

25个新增文件全部为V5私有源码/tests/vendor/合同与文档。原52份包括module_api/api_gateway/composition/daily_dispatch等均未修改。after没有ReviewView.vue、AshareReviewPanel.vue或contracts/review.ts的新实现。当前a_close_daily_api.py:254提供读取、:295提供纯A合并，尚无活动应用调用。

INTERFACE_REQUESTS三件明确标记DRAFT / SHARED_OWNER_IMPLEMENTATION_REQUIRED。普通API必须在strict A选择前绑定M09 reader，并阻止后置旧evidence loader重新混源；UI必须实际显示m09_publication/失败attempt与served generation分离；dispatcher必须真正绑定16:05/17:10。当前这些都是未实现的集成任务，不是仅缺截图。

## Mac执行前注意

### 3. 测试临时路径存在可避免的Mac准入风险

DailyBehaviorTests:63–69、Parquet类:470及source/independent tests直接使用tempfile.TemporaryDirectory并把原路径交给严格no-symlink代码。daily:74–83与sources:62–73会拒绝任一祖先symlink。

如果Mac当时tempfile.gettempdir()为/var/folders/...且/var是symlink，测试会在真实业务前因路径准入失败。尚未读取当前Mac的实际tempdir，所以应记为条件性运行风险，不是已证Mac失败。推荐新验收session下建立0700的tmp目录，并在所有新Python进程开始前设TMPDIR到该真实无symlink绝对路径；不改生产安全规则、不resolve输入绕开校验。

### 4. 原日志包装器少记环境变量

tools/run_logged.py及evidence/run_logged.py记录M09_ORIGINAL_ROOT而测试实际读取M09_ORIGINAL_SOURCE_ROOT；也未记录TMPDIR。命令本身可运行，但新Mac证据应额外保存M09_ORIGINAL_SOURCE_ROOT、TMPDIR、PYTHONNOUSERSITE与全部路径，不把旧元数据的null误作未提供原件。

## 已确认真正实现的链与边界

- 默认路径：run_a_close_daily:724，准入后:809调用_build；_build:456–475启动当前解释器-I -B worker，固定文件，无公开producer/guard替换参数。worker校验私有run路径及implementation后调用build_from_admitted_panel。
- frozen sources:369–410校验16份固定F原字节和独立namespace，调用原producer.build_review_from_panel(:398)，原producer:152–160构造AShareReviewStore并import_review，再由新构造原store独立read_review验证。
- 原pyarrow.dataset读入替换为明确的admitted-frame适配；真正parquet解码属于daily:224–255。已有算法对照因此仅证明准入frame上的原完整链等价，不证明原parquet reader等价。
- 两槽：trigger包含slot，计算身份:775–781不含slot，但包含完整输入/实际可见evidence/配置/实现。相同输入可用同run，:854–857仍分别保存回执。晚到证据:368–370在前槽TOO_LATE、后槽AVAILABLE，计算身份变化后新run。
- 缺口：缺视频/阶段为MISSING/UNKNOWN/INVALID，不伪造；实际业务record始终PARTIAL，strict1500/natural/provenance独验均false。坏行、空名/行业、数值缺失和来源不足拒绝，不清洗后晋升。
- 保存：新run独立store，record绑定calculation、原始输入、producer pointer、store三件raw SHA和review身份。generation绑定成功trigger/request见证后才可读。
- 失败/硬中断：GET只读选择同日已核predecessor；下次写者在日期锁内恢复。后续FAILED/UNKNOWN和正在服务成功分开。
- 回滚：同日predecessor链+CAS，切M09 head，保留run/input/receipt；无共享root/V4修改。

## 既有测试证据（仅阅读，未重跑）

- logs/final_candidate_regression.stderr.log末尾：Ran 125 tests，OK(skipped=4)。121通过，四个pyarrow相关skip。
- evidence/independent_review/independent_final_all_green.stderr.log：Ran 6 tests，OK。
- 两组原完整工程对象对照1239/1301字段及容器项，另原跨日异常一致。输入是合成工程frame。
- Linux Python3.12.14/pandas2.2.3，缺pyarrow/pytest；不满足固定声明。原pytest套件BLOCKED。
- Mac已知Python3.14.6/pandas3.0.5/pyarrow25.0.1仍需本次固定候选实测，不改声明范围或环境。
- 真实20261009输入仅执行两槽预期拒绝，未真实parquet解码；row_count=null。80,017,050B原receipt超过16MiB上限亦如实拒绝。

## 后续顺序

先准备隔离Mac会话和TMPDIR、核固定字节与现有解释器；跑已交付125项及独审6项、generation walkthrough、未清洗真实parquet预期拒绝。保留四个parquet测试本次实际是否执行的结果。重复attempt校验缺口应列成新负测/修正项。活动API/UI/dispatcher、自然触发和发布回滚要在共享owner真实接线后分别验收，不能与本轮工程测试合并为“上线完成”。

