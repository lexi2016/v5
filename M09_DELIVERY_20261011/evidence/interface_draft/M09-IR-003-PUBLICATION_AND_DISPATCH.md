# M09-IR-003 · 私有发布、独立回滚与两槽调度接口

**状态：DRAFT / SHARED_OWNER_IMPLEMENTATION_REQUIRED。** 此请求定义 M09 与共享 artifact、module API、gateway、ledger、dispatcher、composition owner 的边界。本轮不修改共享源文件，不写 V4，不创建调度或部署。M09 新 daily 候选与原 replay 入口分别保留自己的准入规则。

## 1. 共享文件前像

以下为固定包 before/V5/src/v5_shadow/ 下原字节本地复算。它们不是本轮从活动 V5 服务采集的执行证明。不可变 donor 为 lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477；用户报告的目标集成基线为 lexi2016/v5，v5/m09-handoff-20261011，782bfc9ae91ff9cfe897afffc52aad43b7c1b78c。owner 必须在该实际基线重新核对，不能把旧包前像视作最新分支已匹配。

| 文件 | 字节 | 原字节 SHA-256 |
| --- | ---: | --- |
| module_artifacts.py | 7936 | 07c1ab119367abbdb73363ca4f4d0af2d05e3bbef5e02be911a77a6a31f02e17 |
| module_api.py | 15282 | 8ce7e4ce59a724629cdc25e407e1b66f2d2aed79e7ae6779b6c3145de020b6ca |
| api_gateway.py | 16003 | 9bdb76f8cbbdd020ba414f183fc8e8af9ad5306baf6ccc7f9458d45c660cc225 |
| run_ledger.py | 6105 | 2258adcf6f1f61640e9ee2bb36cae5daa06670293f4227fc431289c858077dfd |
| daily_dispatch.py | 3438 | a7d0a9bfe672fd670ee3c7504a0b25c1a0365498c0520b71d16e38bc93cae240 |
| composition.py | 5297 | 258462c4ee53a3ee7acc4f8e0e0f35b4b20994f9ec4dd6ee48f37a6a68c981b0 |
| daily_close_plan.py | 5807 | f51af9be40a32de88ea55672fffb7b7c74570c9d1ae6053b488b51a4d89bf3f6 |
| digests.py | 425 | 134b1a13b7ff677afef6f556e2a750d94cc54a396cbdcff111c5d67e645280e5 |

完整路径和机器前像见 M09_INTERFACE_BEFORE_IMAGES.json。活动 Mac API 的源 commit UNKNOWN；不要借上述 V5/donor commit 补写。

## 2. 可直接复用与必须请求 owner 扩展的边界

| 文件/函数 | 已核行为 | 请求 |
| --- | --- | --- |
| module_artifacts.publish_generation(config,records,expected_generation=...) | 私有标记根、不可变 objects/generations、按预期旧代比较、完整验读后激活；保留旧对象 | 可原样复用；不为 M09 重写 publisher 或增加任意路径权限 |
| module_artifacts.activate_generation(config,generation,expected_generation=...) | 验证所指对象，比较当前代后切换 | 可原样用于符合其 schema 的共享 transport 代回滚；不等同 M09 自有代 |
| module_api.read_response(config,root,path,query) | 返回 (record,record_digest)；内部选择 active generation，但未把所选 generation 交给调用者 | 请求兼容的新增 pinned/identity reader；旧返回签名保持 |
| module_api._validate_record | transport data_kind 只接受 SYNTHETIC / RECORDED_INPUT_REPLAY / OWNER_RESULT | M09 REAL 属于内层 M09 record，不能无审查把共享或旧 replay 准入整体放宽 |
| api_gateway.validate_config / dispatch | route path 唯一 owner，不能按响应子树分别路由 A 与 HK | GET /api/v3/review 留给共享 composition owner；不得整体改派给 M09 |
| run_ledger.identity_key / claim_run / finish_run | LANES 没有 M09；成功 identity 会直接 REUSED_SUCCESS；严格 receipt keys | 显式接纳 M09 的实际 lane 映射，且保证每槽触发回执独立，不用每日 logical key 吞后槽 |
| daily_dispatch.dispatch_due | LANES 只有 announcement/us_mapping/rebound，且所有 lane 目前硬编码 hk_securities 日历 | 由可信 lane policy 为 A 指定 a_share 日历，不改变现有 HK lane 的规则 |
| composition.render_effective_config / switch_module | 执行和切换限 rebound_shadow | 请求受限 M09 分支及最小绑定切换；不得删除 allowlist 或笼统开放所有模块 |
| daily_close_plan.plan_close_day | 已有 A 的 a_share_close_review owner、市场 A、BUSINESS_DATE、独立 job_key；明确不执行 | 复用计划事实，保持 1605/1710；计划 DUE 不写成运行成功 |

## 3. M09 计算产物与共享 transport 不是同一种 schema

M09 独立读回返回 review、record、generation、identity，以及并列的可选 latest_attempt 和 publication_recovery。M09 record.schema_version=v5.m09.record.v1；M09 generation.schema_version=v5.m09.generation.v1。后者包含 trade_date、run_id、record_sha256、previous_generation_sha256。

共享 module_artifacts 接受的是 v5.module_response.v1 records，生成 v5.module_generation.v1（module_id、release_id、records key→digest 映射），并用 v5.module_active.v1 指针激活。这些是另一层对象，不能互相当作 payload 或摘要。若采用共享 transport，需在内层完整保留 M09 记录和身份；共享 record/generation digest 使用 transport_record_sha256、transport_generation_sha256 等明确标签，不覆盖 m09_publication 中的 M09 身份。

共享 wrapper 示例仅展示已有 schema 的适配；module_id/path/query 由唯一 owner 固定配置：

    {
      "schema_version": "v5.module_response.v1",
      "module_id": "<owner-approved-module-id>",
      "release_id": "<fixed-v5-release>",
      "path": "<owner-approved-internal-read-key>",
      "query": {"date": "YYYYMMDD"},
      "payload": { "<actual M09 A fields or shared-owner envelope fields>": "<values>" },
      "payload_sha256": "<canonical JSON SHA of exactly payload>",
      "source_input_sha256": "<explicitly documented immutable input identity>",
      "data_kind": "OWNER_RESULT",
      "generated_at": "<actual wrapper creation time with timezone>",
      "status_code": 200
    }

这是 schema 草图，尖括号字符串不是可发布 fixture。OWNER_RESULT 表示经 owner 输出的 transport 记录，不证明真实来源、自然执行、PIT 或业务完整。内层必须仍显示其 REAL / RECORDED_INPUT_REPLAY / SYNTHETIC、execution_kind、business_status 和研究边界。不得把 original a_close_review.py 的 replay 边界放宽为生产。

内层分类配对必须校验：SYNTHETIC 只对应 ENGINEERING；RECORDED_INPUT_REPLAY 只对应 HISTORICAL_REPLAY；REAL 可对应 DAILY_RESEARCH 或 HISTORICAL_REPLAY。REAL 是来源分类，不能独自证明当前槽自然执行。历史执行可使用真实原件，不能把其 data_kind 强改为 SYNTHETIC 或用当下包装时间冒充原计算时间。

有效 M09 投影还须从 record 保留 membership、scope=DECLARED_UNIVERSE_ONLY、natural_verified=false、source_provenance_independently_verified=false 和 record_cannot_confirm（深拷贝自 record.cannot_confirm）。当前记录层缺口包括 FULL_MARKET_MEMBERSHIP_NOT_VERIFIED、STRICT_1500_PIT_NOT_VERIFIED、NATURAL_TRIGGER_NOT_INDEPENDENTLY_VERIFIED。共享 wrapper 的完整性验证、OWNER_RESULT、发布成功或 transport SHA 均不能清除这些内层证据边界。

若 envelope 由共享 owner 物化，其完整 A/H 响应仍由共享 owner 发布与服务；M09 只能交付自己的 A 子对象和摘要。无需为 M09 新建独立公开页面/API/服务器。**优先方案是向现有共享 router 注入 M09 reader；此方案不需要新增模块服务器或 generic publisher 阶段。** 共享 transport wrapper 仅是 owner 需要该通道时的可选适配，须单独固定身份与 schema。M09 私有 store 的实际根标记以其模块实现和后续固定绑定为准；不可推定它采用 generic publisher 的 .v5-module-root 标记。

## 4. pinned reader 请求

当前 module_api 先读取 active，再验 generation 和 object；因对象不可变，该流程可以保持一次选择的一致性。但它只返回 record digest。不能在响应准备好后再次读取 active.json，把新代 SHA 错标到旧 record 上。

请求新增等价于下列只读接口，同时保持现有 read_response 返回约定：

    read_response_with_identity(
        config, root_fd, path, query, *, generation_sha256=None
    ) -> {
        "record": verified_record,
        "record_sha256": verified_record_digest,
        "generation_sha256": generation_actually_selected
    }

未传 generation 时，只选择一次 head，返回那次选中的代；传入已固定 generation 时，验读该不可变代，不跟随后来 active。处于 legacy 无 generation 模式时必须明确返回 None/模式身份，不能捏造代 SHA。模块的 mark/config/module_id/release_id、path/query、payload、raw object digest 校验保留。只读过程不得创建、修复或切换指针。

M09 的 read_a_close_daily(root,T,generation_sha256=...) 已有自身 pinned 读取边界；其身份直接用于 a_close_daily_api 的 m09_publication。若共享 owner 选直接注入方案，无需为了取该 M09 摘要而扩展所有 module API。若选共享 transport，新增 reader 必须证明 transport 代和其中绑定的 M09 代各自准确。

独立 read_a_close_latest_attempt(root,T) 提供精确日的最新终态回执，或存在started但无完成回执时的status=UNKNOWN观察，或None。adapter将其深拷贝为m09_publication.latest_attempt并给出独立latest_attempt_status；无对象时两字段均为null，有对象时状态直接取其status（SUCCEEDED / FAILED / UNKNOWN）。它可以指向另一run/generation，不能加入已完成record/generation的内容、覆盖原computed_at，或被当作新的提交证据。pinned generation仅钉住所服务成功，latest_attempt是另一次只读观察。若owner物化整个transport envelope，其中尝试状态只是物化时观察；需独立刷新尝试信息时使用只读边界，不回写原计算记录来更新状态。

adapter只有在主committed reader返回None时调用该独立latest-attempt reader，不第二次读head；主reader返回完整对象时直接用其并列元数据。None后的元数据读错误保留MISSING，两个attempt字段null，并记录M09_LATEST_ATTEMPT_READ_FAILED；不发起生成、修复或其他来源读取。

core可以并列返回publication_recovery，用于缺完成回执的当前head下，对同一私有根、同日predecessor链进行校验后选择可服务代。adapter仅深拷贝mapping/null，不自行推演或补写其schema。generation_sha256等身份始终对应实际选中的经核代，publication_recovery与latest_attempt都不能覆盖该身份或业务/读状态。此只读恢复是有验证边界的同日链内选择；禁止的旧日期、外根、legacy或任意历史对象回退仍不允许。GET不改变head、不补写receipt、不激活generation；它与第7节显式CAS回滚操作是不同动作。

## 5. 发布和失败顺序

在未来获准的 V5 集成中，建议 owner 按下列顺序执行并记录每一步结果：

1. 固定 repository/commit、模块 manifest、配置摘要、私有根标记和已有可服务 M09 generation/binding。采集 HK 及其他模块配置/响应摘要、现役 V4 指定路径的原字节前像；记录缺失文件状态，不创建它们。
2. M09 先准入精确 T 和不可变来源。原 producer/store 只在新的私有 run 根写入，禁止同日覆盖式 replace_review 作为保存两槽历史的唯一手段。
3. 创建新的独立原 store reader，验证 payload/receipt/manifest、日期、原 source SHA、规范 review SHA及原字节 review SHA。读取不完整或校验失败的 attempt 不能进入可服务代。
4. 写入并独立验证 M09 不可变 record/generation。规范 JSON 摘要按 UTF-8、sort_keys=True、ensure_ascii=False、紧凑分隔、allow_nan=False、无末尾 LF计算；旧 runs/objects/generations 保留。
5. 通过 expected previous generation 做比较后切换。CAS 冲突、写入中断、验读失败应保留已核旧代；实际结果未知时先只读核对，不自动重新算或盲目覆盖。
6. 若使用共享 transport，将已验证且固定 M09 generation 的子对象交由共享 owner 组合、发布；其 publisher 使用自己捕获的 expected_generation。一次普通 GET 的响应与标注的 M09/transport 身份相符后，才形成 API 验读回执。
7. 使用原 ReviewView 的显式 GET 刷新，核对 T、model_run_id、各类摘要、模型展示与缺口；单独确认 HK、研究及 V4 保存前像未变。页面检查不回写原模型或 close_chain 的 UI_ACCEPTANCE_PENDING。

两个不同 publisher/head 之间没有现成分布式事务。owner 必须固定哪个 head/binding 决定服务可见性，并让服务绑定不可变 M09 generation，或采用直接读取完整已提交 M09 head 的单一可见性门。不能先后切两个 mutable head 并宣称原子成功。若第二阶段失败，应明确仍服务哪一代及其原因；不删除完整但尚未使用的对象。

## 6. 两槽与身份合同

计划 owner 名为 a_share_close_review，市场 A；M09 是任务编号。共享 lane 的最终字符串由 owner 固定并显式映射，避免另起一个与计划脱节的名字。上海时区仅保留 **16:05 与17:10** 两槽；旧 close_chain 中的15:55/20:30等显示节点不是额外调度授权。

| 身份 | 包含内容/含义 | 不可混用 |
| --- | --- | --- |
| 计划 logical_run_key | module_id、market、T 的日逻辑键 | 不是已执行 run，不足以判定计算复用 |
| 计划 job_key | 上述字段及 slot | 区分1605/1710的计划机会，不证明触发发生 |
| 计算 identity | 所有实际参与计算的不可变输入、来源内容、代码/闭包、配置、日历，以及会影响结果的 cutoff/上下文 | 同 identity 可复用成功模型，但不吞掉独立触发 |
| 触发 identity | T、slot、job、attempt、实际 trigger_kind、触发/执行起止时间 | 不是模型完成时间，不足以证明输入合格 |
| 发布 identity | M09 run/record/generation 摘要链 | 不等于触发 key或 transport generation |

当前 ledger 的成功短路发生在 dispatcher 调用 owner 之前。接入时必须让1605与1710进入不同的触发记录，或显式记录后槽 REUSED_SUCCESS 触发回执再引用原计算。可将稳定 job/slot 作为受信任 owner_request 的一部分并纳入共享 claim identity，同时由 M09 负责独立计算 identity；不要仅用 T 的 logical_run_key 锁死整天。重复 scheduler 轮询不应被伪造为新的自然触发。

owner_request 应提供经过批准的槽 cutoff、精确 T、稳定 job身份和实际 trigger 信息；不能把机器现在时间当作源材料 available_at，也不能用历史回放补齐一个自然触发事件。真实来源可用时间未知须保持未知或拒绝对应准入。

相同计算输入/代码/配置可在17:10复用16:05已验证结果，但两个触发必须各自有 receipt。若后槽有在其 cutoff 前已可用、实际参与产品的新材料，建立新计算身份和新 run。新材料改变 cutoff准入/产品时必须体现在 identity；17:10之后的材料不能回填任何旧槽，也不能静默创建第三槽。后槽失败要保留前槽已提交成功，并另留失败 attempt，API 所服务旧代与后槽失败回执分别标记。

最新尝试的status独立于所服务成功的read_status/business_status。后槽FAILED/UNKNOWN时，API仍可展示前槽已核完整代，并在latest_attempt列出后槽实际attempt、slot、run、时间和原因。不同run/generation是允许状态，不得为消除差异而覆盖旧成功。没有完成receipt时保持UNKNOWN；GET和刷新不得写补偿回执、把未知判为失败、或自行启动重试。无成功generation时仍可显示同日尝试观察，但不产生可服务成功身份。

允许工程计算/存储“SUCCEEDED”与业务 PARTIAL/CANNOT_CONFIRM 同时存在；receipt 中 product_reference 应绑定 T、model_run_id、M09 record/generation、业务状态及计算/触发分类。不能用 ledger 终态替代业务状态。现 ledger natural_verified=False 不得仅因新增 lane 而改为 true。M09 record/投影中的 natural_verified=false 同样表示缺少独立自然证明，不表示“从未发生触发”；源材料独立证明由 source_provenance_independently_verified=false 单独表达。实际触发槽、attempt、起止时间和原样触发分类留在独立回执，不能直接覆盖 record.execution_kind 或 computed_at。自然触发需要实际受控环境的独立证据。

## 7. 单模块回滚顺序

1. 读取并记录当前 M09 generation/binding，确认它等于本次要回退的预期新代；固定经核的上一代完整对象及所需版本绑定。
2. 先对上一代进行 pinned 独立验读，核查 T、模型 run、record、generation 和安全标志。坏旧代不能因“以前成功过”直接激活。
3. 只以 CAS 切换 M09 的 serving generation/binding；若有 transport 层，按已固定可见性方案回切相应 M09 transport 代。不得整体重置共享 composition、gateway 或另一市场。
4. GET 精确 T 并显式刷新原页，记录实际返回的旧代身份、业务状态和缺口；新旧 objects/runs 和失败 attempts 全部保留。
5. 比较 HK 子树 canonical SHA、其他模块绑定/响应摘要及 V4 原字节文件 SHA与事先采集值。若改变，记录具体范围并停止扩大操作，不把其归为 M09 正常回滚。

V4 文件保持比较必须基于真实现场采集；本轮附件只能作为已知输入。至少包含活动 API/前端源及用户核准的数据/回执/manifest/指针路径的“存在性+原字节SHA+字节数”。比较 API JSON 子树用规范 JSON摘要，比较原件文件用 raw bytes摘要，两者不要混称“字节不变”。活动文件或 PID/服务状态尚未现场复核时保持 NOT_RUN。

## 8. 双方验收与回传

| 场景 | M09 侧责任 | 共享 owner 侧责任 | 当前集成执行状态 |
| --- | --- | --- | --- |
| 私有根/错误根/符号链接 | 拒绝不合格根 fixture | 绑定只接受批准根，V4前像不变 | NOT_RUN |
| 原 store独立验读失败 | 失败 fixture/attempt | 不发布、不换旧代；真实错误回执 | NOT_RUN |
| publisher写中断/CAS竞争 | 不可变对象及冲突 fixture | 原代仍可读；冲突不覆盖；失败不删对象 | NOT_RUN |
| 并发发布与 pinned read | 两完整 M09代 | 返回实际所选代；不得事后重读head错标 | NOT_RUN |
| 两槽同一计算 | 可复用成功 | 两独立触发receipt，计算一次；时间身份不混用 | NOT_RUN |
| 后槽新增可用材料 | 新identity/新run | 第二代成功才可见；前代保留 | NOT_RUN |
| 后槽失败 | 失败attempt + 前槽成功 | 第一槽成功持续可读；latest_attempt/status显示后槽FAILED；两个run/代分别核对 | NOT_RUN |
| 后槽中断无receipt | started记录 + 前槽成功 | 最新尝试UNKNOWN；served SHA不变；GET不补写回执、不自动重试 | NOT_RUN |
| 无成功/无尝试 | None提交、同日尝试或None | 缺失A与尝试观察独立；不得制造generation或终态 | NOT_RUN |
| None后的latest元数据读取失败 | None提交 + reader错误 | MISSING保留、M09_LATEST_ATTEMPT_READ_FAILED、null状态；head不二次读取 | NOT_RUN |
| 无回执current的只读恢复 | 经核同日predecessor + recovery metadata | 实际所选代身份准确，metadata单独透传；原head/文件raw SHA不变 | NOT_RUN |
| predecessor不合格或跨日/外根 | 无可核成功链 | 不返回未核成功，无legacy/跨根/跨日回退，无GET修复或重试 | NOT_RUN |
| A开市/HK休市及反向 | A日历准入 | A用a_share，HK规则不变；不得全lane统一HK判断 | NOT_RUN |
| UNKNOWN/非交易日/历史手工回放 | 明确拒绝或回放分类 | 无自然成功、无第三槽、无自动补跑 | NOT_RUN |
| transport映射 | 内层真实分类/摘要及四种合法配对 | REAL可作HISTORICAL_REPLAY；OWNER_RESULT不改业务事实；旧replay拒绝边界保留 | NOT_RUN |
| 记录层证明边界 | membership/三项record缺口/false独立证明标志 | 申报集合限定保留；发布/ledger成功不改自然/来源证明状态 | NOT_RUN |
| gateway全路径owner | A-only子对象 | /api/v3/review仍共享组合，HK未被M09接管 | NOT_RUN |
| 独立回滚 | 上一代可读链 | 仅M09变更，HK/其他模块/V4前后摘要相同 | NOT_RUN |

本请求已完成静态源码审阅和附件原字节前像复算。Mac 文件系统/锁语义、活动 ledger/dispatcher、两槽自然运行、真实 API/浏览器、部署及现场回滚全部 **NOT_RUN**。集成者回传固定基线、函数级 diff、lane/calendar映射、完整 private binding、每项实际命令/回执和前后摘要后，再更新对应验收状态。共享扩展不由 M09 私自实施，部署与调度启用另须已有明确授权。
