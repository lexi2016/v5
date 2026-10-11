# M09-IR-001 · 普通 Review API 的 A 股只读组合接口

**状态：DRAFT / SHARED_OWNER_IMPLEMENTATION_REQUIRED。** 本文件是函数级接口请求及验收合同，不是活动应用补丁、集成成功回执或部署授权。M09 仅交付模块候选和本请求。共享 API、gateway、应用绑定由唯一集成者修改；不得把候选写入现役 V4。

## 1. 目标与固定证据

在 V5 预览绑定下，现有 GET /api/v3/review?date=T 消费 M09 已提交的精确 T 日复盘；A 股子树与其兼容投影来自同一代提交。HK、研究复盘、盘中研究和全局安全标志保持原值。GET、刷新、重复点击、日期切换均不触发计算、采集或 POST。

附带源码所对应的活动 release 为 **hk-dated-name-20261011-r2**。其活动源码 commit **UNKNOWN**；不能把下列 V5 交付 commit 赋给 Mac 源码：

- 用户报告的当前集成基线：lexi2016/v5，分支 v5/m09-handoff-20261011，commit 782bfc9ae91ff9cfe897afffc52aad43b7c1b78c。本请求未远端重核该基线。
- 不可变 donor：lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477；其来源身份不因交付仓库变化而改写。
- 本文前像为实际附件原字节本地复算，完整路径及机器可读身份见同目录 M09_INTERFACE_BEFORE_IMAGES.json。

| 活动源码相对路径 | 字节 | 原字节 SHA-256 |
| --- | ---: | --- |
| apps/api/v35_api/review_router.py | 42184 | ef6e870077fecd1e025ec1a0741ec3f766b76ef914b60661e4f32937acc9e28d |
| apps/api/v35_api/app.py | 327501 | ba40457e4fc6d4f60155c55e4202ac82e870467598d49ea36bcbc2aab5c70eb3 |
| domains/review_evidence_layers.py | 24730 | 96886aa56318968625bfb57e484fde39ba267388591234fe7ed9e3f2939d77a7 |

活动绑定附件 actual_api_binding.json 与 runtime_bindings.json 记录：API 的 data_root 在 com.lexi.v4.local/state/data，producer 在 com.lexi.v35.local/state/data；二者不是一个根。所采 T=20261009 响应为 A.status=PARTIAL_STAGE_EVIDENCE、source_role=V3_5_STAGE_EVIDENCE_PARTIAL，且 API 根没有精确 T 的 Review Core current。该响应说明活动读路由的现状，不证明 M09 已接入，也不证明源数据可作自然当日成功。

## 2. 已核函数行为及修改位置

1. create_review_router(...) 的 GET review(date) 先独立计算 HK，然后选择 A。review_core_a_share_bundle_required(data_root, T) 仅在解析后的 review_bundle/T/current.json 是文件时返回 true；不能将某个 Review Core 目录存在概括为 strict=true。
2. strict A 分支从 load_review_core_a_share_review 读取；否则从 AShareReviewStore(data_root).read_review(T) 读取，且 legacy 分支拒绝 source_role 不是 V3_5_NATIVE_CLOSE_MODEL 的 review，再尝试同日阶段部分证据。
3. 创建 envelope 后，现代码又调用 load_review_evidence_layers(data_root,T,A)。该函数会先重新读取 Review Core，而非无条件信任传入 A。因此，仅在末尾覆盖 market_reviews.A 会留下来自另一来源的 A 证据或 READY 富表面。
4. review_core_bundle 的根字段在 A 分支生成；review_evidence_layers 的实现只处理 A 的日线/模型/视频。它们是可明确识别的 A 所属顶层字段，不能和 HK、research_review、intraday_research 混为一组。
5. app.py 的 create_app(...) 在 include_router(create_review_router(store.root,...)) 中传入当前共享根。为 V5 预览加入独立受信任 reader 绑定，不修改 store.root 或现役 V4 的环境根。

## 3. 请求的接口

仅请求共享 owner 在应用构造与 router 构造处增加可选、关键字形式的 **a_close_reader**。它是服务端启动时绑定的 callable；默认 None 保留既有行为。HTTP 用户不能传任意 root、文件路径、源码模块、shell 命令或 latest 指针。

M09 候选边界位于 V5/src/v5_shadow/a_close_daily_api.py：

    project_committed_review(committed, requested_date) -> dict
    read_a_close_preview(root, requested_date) -> dict
    merge_a_close_preview(existing_envelope, preview) -> dict

底层独立读回边界：

    read_a_close_daily(root, T, generation_sha256=None)
        -> {"review": ..., "record": ..., "generation": ..., "identity": ...,
            "latest_attempt": optional_attempt_or_none,
            "publication_recovery": optional_metadata_or_none} | None

    read_a_close_latest_attempt(root, T) -> dict | None

共享 owner 可绑定等价于 lambda T: read_a_close_preview(approved_private_root,T) 的闭包。此例仅说明调用形态；根必须先由可信的私有 V5 配置核验，不能默认为 API 旧 data_root。被显式选中的 M09 reader 无结果时返回 M09 缺失对象；不切回 V4、其他日期或另一 A 来源。

latest_attempt 是精确 T 的独立尝试观察，来自终态回执，或在已有 started 记录而没有完成回执时表现为 status=UNKNOWN，或为 None。它与不可变 review/record/generation/identity 并列，不属于被服务成功的计算身份。A.m09_publication 增加 latest_attempt 的深拷贝和独立 latest_attempt_status；没有可用尝试时两字段均为 null，有对象时 latest_attempt_status 直接取其 status（SUCCEEDED / FAILED / UNKNOWN）。最新尝试可以引用不同于当前可服务成功的 run/generation，不要求其 SHA 与 served identity 相等，但仍必须属于请求日 T。

read_a_close_preview 仅在主 committed reader 返回 None 时调用同根 read_a_close_latest_attempt(root,T)，为 MISSING 对象附加尝试说明；它不为该查询第二次读取 head。主 reader 已返回完整对象时使用其并列元数据，主读取失败也不通过另一个 head/来源绕过。若 None 后的尝试元数据读取失败，A 仍为 MISSING，latest_attempt/latest_attempt_status 保持 null，并明确记录 M09_LATEST_ATTEMPT_READ_FAILED；不能制造成功。无完成回执的 UNKNOWN 不是 FAILED 或已成功；只读接口不得补写回执、自动重试、修复或切代。

core 可返回并列的可选 publication_recovery 元数据：当当前 head 缺少完成回执而需选择经独立校验的同日 predecessor 时，adapter 深拷贝该说明，保持其与 served identity/status 分离。此处是同一 M09 私有根、精确 T、经核 predecessor 链内的只读恢复选择，不是允许旧日期、其他根、legacy store 或任意历史对象回退。对外 generation_sha256、record_sha256、model_run_id 必须始终指向实际选中并验读的代，不能用未获完成回执的 head 摘要冒充。GET 不修复/切换 head，不写任何数据。publication_recovery 的对象内部 schema 以 core 固定合同为准，本请求仅约定 mapping 或 null，不发明字段。

下列伪代码表达分支位置；不是整文件替换：

    hk_payload = existing_hk_read_exactly_as_before(T)
    selected_m09 = a_close_reader is not None

    if selected_m09:
        preview = a_close_reader(T)  # committed read only; no writer/import/compute
        base = review_envelope(T, a_review=None, hk_review=hk_payload or {})
        envelope = merge_a_close_preview(base, preview)
        # Do not call strict/legacy A loading or load_review_evidence_layers here.
    else:
        envelope = existing_strict_or_legacy_A_composition(T, hk_payload)
        # Preserve the original strict predicate, errors and A evidence handling.

    attach_existing_intraday_research_and_research_review(envelope,T)
    attach_existing_HK_reference_snapshot(envelope,hk_payload)
    return envelope

此顺序避免先被旧 strict A 验证阻断再尝试 M09，也避免 M09 提交成功后被后续旧 evidence loader 混入其他来源。若复用现有 helper 的 A schema 校验，必须确认该 helper 接受 M09 外层业务状态；不得为通过旧验证而改写原 model.status。使用已有合法空 A 组合后调用纯合并适配器是可审查方案。

## 4. 合并范围与状态语义

merge_a_close_preview 应 deepcopy 输入，不改变传入对象。允许变化的范围限定如下：

| 范围 | 处理 |
| --- | --- |
| market_reviews.A | 替换为同一 T、同一提交的 M09 预览对象 |
| 已存在的 fupan_review_v3 | 对齐 A 的原生兼容别名，移除不属于当前 A 的旧富表面归属 |
| 顶层 review_core_bundle | M09 选中时移除旧 A 归属 |
| 顶层 review_evidence_layers | M09 选中时移除旧 A 归属；不伪造原 schema 的 READY 替身 |
| 顶层 m09_publication | 等于 A.m09_publication 的独立拷贝 |
| market_reviews.HK 和其他顶层字段 | 深度相等；包括 research_review、intraday_research、reference_snapshot、production_allowed、buy_gate_updated、orders_sent |

fupan_review_v3 已知原生别名包括 first_screen_big_picture←big_picture、next_day_trigger_tree_v2←next_day_trigger_tree、human_video_gap_scorecard←quality_gate、replay_model_v1←model_review，以及 headline、market_regime、risk_tone、mainlines、core_stocks、observation_pool、cannot_confirm。不能留下旧 A 的 Review Core run/SHA、rich tier 或旧模型。不得从 WATCH_ONLY 观察池制造正式 core_stocks。

| 情况 | A 外层/读状态 | 行为 |
| --- | --- | --- |
| 未绑定 M09 | 原行为 | strict/legacy A 路径不变 |
| M09 已绑定，T 无已提交结果 | MISSING | 同日缺失对象；无旧根或 latest 回退 |
| 所选提交存在但日期、摘要、schema、读回或安全边界不合格 | CANNOT_CONFIRM | 明确理由；不得降级成“缺失”并读其他来源 |
| current缺完成回执、存在经核同日predecessor | 所选有效提交的业务状态 | publication_recovery单独说明只读选择；served SHA指实际代，head不写改 |
| 有效提交 | record.business_status | 保留真实业务缺口；成功验读不自动升级整链完整 |
| model_review 已形成 | 保留原 INDEPENDENT_CLOSE_REVIEW_READY | 独立于 A 业务状态和 close_chain.status |
| 历史成功被请求 | 请求 T 的真实分类和时点 | 保留实际 data_kind 与 HISTORICAL_REPLAY；REAL 原始数据也可作历史回放，不称自然当日成功 |

HTTP 200 表示成功返回可读的业务对象，不代表业务 READY。若共享 owner 使用 HTTP 409/503 表示校验失败/暂不可用，响应正文仍须明确 CANNOT_CONFIRM、T 和具体理由，并验证原页面的错误处理；不能把任何非 200 偷换为成功。推荐让“正常同日无结果”仍是可渲染 MISSING 对象。

## 5. 摘要与时间合同

A.m09_publication 使用 v5.m09.read_evidence.v1 命名空间，身份字段直接平铺：trade_date、model_run_id、canonical_review_sha256、raw_review_sha256、source_sha256、record_sha256、generation_sha256。附 read_status、data_kind、execution_kind、business_status、computed_at、provenance、evidence_status、membership、scope、natural_verified、source_provenance_independently_verified、strict_1500_pit_verified、scenario_probabilities_status、safety，以及 reason_codes、分层缺口列表、latest_attempt、独立 latest_attempt_status 和可选 publication_recovery。有效读状态为 VERIFIED，仅证明本次读回校验；MISSING/CANNOT_CONFIRM 的身份摘要和 model_run_id 为 null。scenario_probabilities_status 为 FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED。最终接入时仍需对照固定候选契约，共享 owner 不猜算缺失摘要。

| 字段 | 所证明的对象 |
| --- | --- |
| source_sha256 | 原 producer 的来源摘要；不可重新定义为全依赖摘要 |
| canonical_review_sha256 | 原完整 review 的规范 JSON 摘要，加入 API 元数据之前 |
| raw_review_sha256 | 原 store review 文件实际原字节摘要 |
| record_sha256 | v5.m09.record.v1 规范 JSON 摘要 |
| generation_sha256 | v5.m09.generation.v1 规范 JSON 摘要 |

规范 JSON 是 UTF-8、ensure_ascii=False、sort_keys=True、紧凑逗号/冒号、allow_nan=False，无末尾 LF。不同对象的摘要不要求字符串相等。m09_publication 加入后，整个 API A 子树的摘要通常不同于 canonical_review_sha256；原 review 的验证发生在投影前，不能对添加字段后的 A 直接误用该比较。

latest_attempt 的变化只改变读时元数据，不重算或覆盖原 record/generation 摘要、model_run_id、computed_at 或 business_status。即使17:10最新尝试 FAILED/UNKNOWN，16:05完整成功仍可被读为 read_status=VERIFIED；两者分别标注。pinned generation 固定被服务成功的对象链，不承诺把独立 latest_attempt 观察也冻结到该代；不得把两个来源读时点称为一次跨对象原子快照。

record 的 data_kind 说明源数据分类，execution_kind 说明本次计算分类。合法配对如下；不能仅凭 REAL 推断自然运行，也不能将真实历史来源改写为工程合成。

| record.data_kind | 允许的 record.execution_kind |
| --- | --- |
| SYNTHETIC | ENGINEERING |
| RECORDED_INPUT_REPLAY | HISTORICAL_REPLAY |
| REAL | DAILY_RESEARCH 或 HISTORICAL_REPLAY |

有效 m09_publication 还须保留 record 的 business_status、computed_at、provenance、evidence_status、membership 和安全标志。scope 固定为 DECLARED_UNIVERSE_ONLY，natural_verified=false，source_provenance_independently_verified=false；membership 深拷贝自 record.membership，不把“已声明集合完整”升级为“全市场成员已独立确认”。原生 counts/行业/角色均须在该声明范围下解释。

record_cannot_confirm 深拷贝自 record.cannot_confirm，独立于原 review/model/chain 缺口；当前必须保留 FULL_MARKET_MEMBERSHIP_NOT_VERIFIED、STRICT_1500_PIT_NOT_VERIFIED、NATURAL_TRIGGER_NOT_INDEPENDENTLY_VERIFIED。不得只转发原 review.cannot_confirm 而丢失这些新增记录层边界。natural_verified=false 表示缺少独立的自然触发证明，不宣称“从未触发”；真实 slot/attempt/起止时间由独立触发回执记录。source_provenance_independently_verified=false 同样不能因 reader 验 SHA 成功而变成 true。

generation 记录 trade_date、run_id、record_sha256、previous_generation_sha256 和其实际 published_at。T、原 model.review_date、原 review.trade_date、record/generation 日和请求日必须一致。next_day_trigger_tree 仍是复盘产品字段，不改变 T。

原模型 as_of=T 15:30+08:00 原样显示。源 acquired_at/captured_at/available_at、槽 cutoff、实际触发/执行时间和 computed_at 各有含义。不得把最新触发回执时间映射成复用计算的完成时间；不得从模型 as_of 或文件 mtime 推断严格 15:00 PIT。strict_1500_pit_verified 保持 false。

## 6. 双方验收请求

| 用例 | M09 侧应提供 | 共享 owner 侧应核 | 当前集成执行状态 |
| --- | --- | --- | --- |
| 有效 T、原 model 已就绪但整链部分 | committed fixture、真实摘要链、独立读回 | GET 展示 native model 且 A 仍为真实业务状态 | NOT_RUN |
| M09 已绑定，旧 strict current 同时存在 | 有效 M09 提交 | strict/legacy A reader 与旧 evidence loader 调用计数均为 0；HK 调用不变 | NOT_RUN |
| M09 缺失、旧 A 存在 | MISSING fixture | 无旧根/旧日/latest 回退，T 保留 | NOT_RUN |
| 错日/坏 record/坏 generation/不安全标志 | 每类失败 fixture | CANNOT_CONFIRM；无混源、无计算、无指针变化 | NOT_RUN |
| 并发切代 | 两个有效 generation | 一次读得完整旧代或新代，不出现半代；标出的 digest 为实际所读代 | NOT_RUN |
| 分类配对 | 四种合法配对与不合法配对 fixture | REAL/HISTORICAL_REPLAY 可读；非法交叉组合 CANNOT_CONFIRM；原 replay 边界不变 | NOT_RUN |
| 记录层缺口与范围 | record 的 membership/三项缺口/false 标志 | metadata 无损复制；仅声明集合，缺独立自然/来源证明不被 VERIFIED 掩盖 | NOT_RUN |
| 后槽失败/中断且前槽成功 | 前槽有效提交 + 后槽 FAILED/UNKNOWN 回执观察 | read_status 与 served SHA 保留成功；latest_attempt/status独立显示；不得强制两个run相等 | NOT_RUN |
| 无成功但有尝试 / 无尝试 | None提交 + FAILED/UNKNOWN 或 None | A仍缺失/未确认；尝试有据才展示；GET不补回执、不重试 | NOT_RUN |
| None后的尝试读失败 | 主reader返回None，latest reader抛错 | MISSING + M09_LATEST_ATTEMPT_READ_FAILED；两个attempt字段null；主head读取一次 | NOT_RUN |
| 未完成发布的只读恢复 | 无完成回执的head + 经核同日predecessor | served identity指实际predecessor；publication_recovery独立复制；GET零写入 | NOT_RUN |
| 恢复链无可核成功 / 日期根错误 | 不合格predecessor/跨日或外根fixture | 不返回未核成功、不改head、不跨日/跨根/legacy回退 | NOT_RUN |
| A-only 合并 | 多个 HK/research/未知字段的 envelope | 仅允许列表变化；HK 和所有保留字段 canonical subtree SHA 不变；输入对象未变 | NOT_RUN |
| 缓存、刷新、切日、后退 | 已提交两日与缺失日 | GET-only；重复点击不启动 owner；较晚到达的旧日响应不能覆盖当前日 | NOT_RUN |
| 回滚 | 经核上一代 | T/代链可读，A 回到旧代，HK/研究/V4 保存前后摘要相同 | NOT_RUN |

本请求只完成附件源码阅读及本地原字节摘要复算。Mac API 冒烟、原页渲染、真实交易日自然触发、V4 文件/服务现场前后对比均 **NOT_RUN**。现成活动响应是输入证据，不能填作本候选的执行 PASS。

## 7. 集成者回传

实施前重核实际集成仓库、完整 commit、目标文件原字节 SHA/字节数；与本前像不同则停止套用片段并定位最小差异。回传最终函数 diff、服务器 reader 绑定、私有根身份、T/模型 run/record/generation 摘要链、未绑定回归、HK 保留比较及部署前后回执。M09 随后对该固定基线 rebase 模块最小差异。任何 V4 写入、部署、调度启用都不由本请求授权。
