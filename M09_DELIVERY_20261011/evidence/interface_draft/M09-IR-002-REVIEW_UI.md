# M09-IR-002 · 原 ReviewView 的 A 股预览展示接口

**状态：DRAFT / SHARED_FRONTEND_OWNER_IMPLEMENTATION_REQUIRED。** 本文件请求原页面的小范围类型和显示扩展。没有修改前端共享源码，没有创建替代页面，没有活动浏览器渲染或部署结果。依赖 M09-IR-001 的精确日期只读组合接口。

## 1. 前像、来源与已核入口

附件 SOURCE_SUMMARY.json 指明：活动 release hk-dated-name-20261011-r2；ReviewView 导入 ../components/review/AshareReviewPanel.vue 并将 current.market_reviews.A 传给 review prop；该面板只直接导入 Vue 和 ../../contracts/review。三个完整直接依赖已经补齐。不要继续把 AshareReviewPanel 源码列为缺失。

| 活动前端相对路径 | 字节 | 原字节 SHA-256 |
| --- | ---: | --- |
| apps/web/src/App.vue | 133644 | d87285a8a1de1611ca83add16d70101979ea469d2c7fb093dc1f9ca5961baef0 |
| apps/web/src/api/review.ts | 1436 | fc2c7551fe386a9b01375d6d82d7f633990bba169f48e9b918386e31baa6dd7d |
| apps/web/src/views/ReviewView.vue | 3441 | cb1f4f19d9b8100d0caf86a5563990a90b627fdb72699b9ccbe499b1e9542c71 |
| apps/web/src/components/review/AshareReviewPanel.vue | 25639 | f9deaf8d15a3273d3237458b083b847a72f6dcda86824d37731103c13d6672bf |
| apps/web/src/contracts/review.ts | 10012 | 079adf7971e346a8da5d40c49bc3c1fdfb2307aaf6ed70df5ed4d9312699c507 |

完整附件路径、计算出的 Git blob SHA-1 和来源身份见同目录 M09_INTERFACE_BEFORE_IMAGES.json。上述是 Mac 源码附件身份；对应源码 commit **UNKNOWN**。用户报告的 lexi2016/v5@782bfc9ae91ff9cfe897afffc52aad43b7c1b78c 是集成交付身份，不能替代这些前像。集成者应用前必须重核实际前端构建基线及原字节 SHA；不照搬整文件。

已核普通入口为 App.vue 的 loadCloseReview("A")；loadReview(T) 发 GET /api/v3/review?date=T。ReviewView 只调整 A/HK/research 的区块顺序。App.vue 同日已有 payload 且 refresh=false 时直接复用，显式“刷新快照”才使用 refresh=true 重新 GET。

## 2. 现有显示阻断与小范围请求

AshareReviewPanel 的 modelReady 精确判断为：

    model.value.status === "INDEPENDENT_CLOSE_REVIEW_READY"

必须保留此原模型状态。不能把 model.status 改为 PARTIAL、把 HTTP 200 当作模型就绪、或凭 record 验读成功强制 modelReady=true。M09 业务状态、模型数值状态、原 close_chain 状态和证据质量分别显示。

当前 richReady 在 review_surface.tier 为 V3_RICH_READY 或 V3_RICH_PARTIAL 时为 true；富表面分支和原生模型分支互斥。上涨/下跌/平盘、原生板块、个股角色在另一分支的 modelReady shell 内。仅给 M09 加一个“富复盘”tier 会隐藏这些用户要求的内容，而且伪造来源归属。

请求前端 owner：

1. 保留现有原生模型壳和其 counts、board_rows、anchor_role_rows 的字段/顺序。M09 原生输出默认走其适合的 compact/native 路径，不改写为 Review Core 富复盘。若 owner 调整显示条件，只对 M09 让就绪原生模型仍可见，非 M09 的 rich 行为保持不变。
2. 在 A 面板新增一个较小的 M09 状态、证据缺口及来源区块。区块位于原生结果附近，并能在 MISSING/CANNOT_CONFIRM 且模型未形成时单独显示。只依据 A.m09_publication 和原 A/model/chain 缺口，不能请求另一来源填空。
3. 在原生模型中补显示 scenario_tree 三个原分支的名称、probability、open_trigger、invalidation。扩充 TypeScript 类型，保留所有原值和顺序。
4. MISSING 提示适配到当前页面；ReviewView 现有只检查 NOT_MATERIALIZED 的提示不足以表示显式 M09 缺失。避免在 M09 无结果时残留上一日期数值。
5. 不新增路由、独立服务器、第二套日期选择器、运行按钮、轮询、自动重算或计算型 API。

## 3. 数据到画面映射

| 画面字段 | 数据来源 | 显示要求 |
| --- | --- | --- |
| 所选交易日 | envelope.trade_date / A.trade_date | 与请求 T 一致；历史日显式显示原日 |
| M09 读取状态 | m09_publication.read_status | MISSING、CANNOT_CONFIRM 或真实有效状态，不能翻译成正式成功 |
| 业务完成度 | A.status / m09_publication.business_status | 保留真实部分/缺失状态 |
| 原生模型状态 | model_review.status | INDEPENDENT_CLOSE_REVIEW_READY 才展示对应模型壳 |
| 上涨/下跌/平盘 | model_review.market_summary | 精确保留申报集合内计数；0 显示为 0，缺失显示“未确认”，不以 0 填空，不称全市场覆盖 |
| 行业/板块 | model_review.board_rows | 原排序、角色、中位涨幅、上涨占比、反证和触发条件 |
| 个股角色 | model_review.anchor_role_rows | 原排序、理由、失效条件；WATCH_ONLY 不升级成正式核心 |
| 模型情景 | model_review.scenario_tree | stronger、inline、weaker 原分支、原概率与条件 |
| 原来源角色 | A.source_role | 保留 V3_5_NATIVE_CLOSE_MODEL 等原值，另加 M09 来源标签即可 |
| 原模型时点 | model_review.as_of | 原 T 15:30+08:00；明确这是模型字段，不称源可用时间或严格15:00证据 |
| 数据/执行分类 | m09_publication.data_kind / execution_kind | 按合法配对分别说明；REAL 可用于 DAILY_RESEARCH 或 HISTORICAL_REPLAY，不能自动标为自然运行 |
| 覆盖范围与成员 | m09_publication.scope / membership | DECLARED_UNIVERSE_ONLY；保留 record.membership；只确认申报范围，不称全市场成员已核 |
| 独立证明状态 | m09_publication.natural_verified / source_provenance_independently_verified | 两者 false 均可见；分别说明自然触发/来源缺独立证明，不因读回 VERIFIED 升级 |
| 计算时间 | m09_publication.computed_at | 保留实际提交计算时间；复用成功不替换为后来触发时间 |
| 最新尝试 | m09_publication.latest_attempt / latest_attempt_status | 单独显示实际status、槽、尝试/运行身份、时间和原因；不覆盖正在展示的成功run、SHA、业务状态或计算时间 |
| 发布读取恢复信息 | m09_publication.publication_recovery | 可选独立元数据；显示core提供的事实，served SHA仍指实际选中代；不称已修改head或已执行回滚 |
| 源材料时间与缺口 | m09_publication.provenance / evidence_status | 未知即显示未知；不能从 mtime 推算 available_at |
| 摘要链 | m09_publication 的各类摘要和 model_run_id | 用各自标签；细节可折叠但可复制完整值，不统称一个“SHA” |
| 研究边界 | M09 safety、原 model.safety、原 cannot_confirm | strict_1500_pit_verified=false、LLM disabled、未学习/未泛化、WATCH_ONLY/SHADOW_ONLY 等继续可见 |

必须分别保留 review.cannot_confirm、model_review.cannot_confirm、close_chain.cannot_confirm，以及从 record.cannot_confirm 深拷贝的 m09_publication.record_cannot_confirm。记录层三项 FULL_MARKET_MEMBERSHIP_NOT_VERIFIED、STRICT_1500_PIT_NOT_VERIFIED、NATURAL_TRIGGER_NOT_INDEPENDENTLY_VERIFIED 必须可见。聚合显示可以按层分组，不能覆盖原数组或用“模型已形成”消除 CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED。视频链节点 READY 不证明模型已语义消费视频。

natural_verified=false 表示没有独立证明自然触发，不等于从未出现触发事件；实际 slot/attempt/执行起止时间仍来自独立回执。该标志不能从数据分类 REAL、模型计算成功或某个最新回执推导为 true。

latest_attempt 可来自终态回执，或 started 记录存在但无完成回执的 UNKNOWN 观察；其状态键为 status。latest_attempt_status 与 read_status、business_status 分开展示。例如“当前展示16:05已核结果；17:10最近尝试失败”可同时成立，且尝试run/generation可以不同于被服务成功。UNKNOWN显示为结果未确认，不能替换成失败或自动重试。None时 latest_attempt 和 latest_attempt_status 均为 null，显示没有可用尝试记录；不得把旧成功的run/时间填入尝试字段。即使A没有可服务结果，已有尝试说明仍可单独显示。

主 committed reader 返回 None 后，adapter才另外读取同日尝试元数据，且不再次读取head。若此元数据读取失败，UI保持MISSING，显示M09_LATEST_ATTEMPT_READ_FAILED，两个attempt字段null；此时应显示“尝试状态读取未确认”，不能误说没有发生过尝试或显示成功。

publication_recovery是core在缺完成回执的当前head下，经校验选择同根同日predecessor时提供的可选说明，adapter仅深拷贝。它不是页面执行回滚、修复head或改写数据的回执。UI以served identity展示实际选中代，单独保留恢复说明和最新尝试；不拿未完成head或latest_attempt中的SHA替换served SHA。没有该对象时不制造恢复状态，其内部字段随core固定schema，不由前端推演。

R3 SOURCE_SUMMARY.json 已核两个精确路径的 transcript_stockdict/stock_mentions.json 均缺失；此缺失已取得证据，不是等待第三次补件。它不证明其他全部视频材料不存在，也不补足缺失的来源 available_at/PIT。显示范围应与实际 record 的缺口一致。

## 4. 类型与文案合同草案

下面是增量类型方向，供 owner 与最终 M09 adapter 对齐；不是共享 contracts/review.ts 的完整覆盖。A.m09_publication 身份字段平铺；顶层同名字段仅供 API 归属复核，原面板直接消费 A prop 即可。

    type M09ExecutionClassification =
      | { data_kind: "SYNTHETIC"; execution_kind: "ENGINEERING" }
      | { data_kind: "RECORDED_INPUT_REPLAY"; execution_kind: "HISTORICAL_REPLAY" }
      | { data_kind: "REAL"; execution_kind: "DAILY_RESEARCH" | "HISTORICAL_REPLAY" };

    type M09LatestAttempt = Readonly<Record<string, unknown>> & Readonly<{
      status: "SUCCEEDED" | "FAILED" | "UNKNOWN";
      trade_date?: string;
      slot?: string;
      trigger?: Readonly<Record<string, unknown>>;
      run_id?: string | null;
      record_sha256?: string;
      generation_sha256?: string;
      started_at?: string;
      finished_at?: string;
      reason?: string;
    }>;

    type M09EvidenceBase = Readonly<{
      schema_version: "v5.m09.read_evidence.v1";
      trade_date: string;
      strict_1500_pit_verified: false;
      reason_codes: readonly string[];
      latest_attempt: M09LatestAttempt | null;
      latest_attempt_status: M09LatestAttempt["status"] | null;
      publication_recovery?: Readonly<Record<string, unknown>> | null;
      safety: Readonly<Record<string, unknown>>;
    }>;

    type M09ReadEvidence = M09EvidenceBase & (
      Readonly<M09ExecutionClassification & {
        read_status: "VERIFIED";
        model_run_id: string;
        canonical_review_sha256: string;
        raw_review_sha256: string;
        source_sha256: string;
        record_sha256: string;
        generation_sha256: string;
        business_status: string;
        computed_at: string;
        provenance: Readonly<Record<string, unknown>>;
        evidence_status: Readonly<Record<string, unknown>>;
        membership: Readonly<Record<string, unknown>>;
        scope: "DECLARED_UNIVERSE_ONLY";
        natural_verified: false;
        source_provenance_independently_verified: false;
        scenario_probabilities_status: "FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED";
        record_cannot_confirm: readonly string[];
        review_cannot_confirm: readonly string[];
        model_cannot_confirm: readonly string[];
        close_chain_cannot_confirm: readonly string[];
      }>
      | Readonly<{
        read_status: "MISSING" | "CANNOT_CONFIRM";
        business_status: "CANNOT_CONFIRM";
        model_run_id: null;
        canonical_review_sha256: null;
        raw_review_sha256: null;
        source_sha256: null;
        record_sha256: null;
        generation_sha256: null;
      }>
    );

    type CloseScenario = Readonly<{
      probability?: number;
      open_trigger?: readonly string[];
      invalidation?: readonly string[];
    }>;

    // Add optional m09_publication to AShareReview.
    // Add optional scenario_tree to AShareCloseModel:
    // Readonly<{ stronger?: CloseScenario; inline?: CloseScenario; weaker?: CloseScenario }>

AShareReview.m09_publication 本身保持可选，以兼容既有非 M09 响应；读取 VERIFIED 分支前先按 read_status 收窄类型。 publication_recovery采用可选mapping/null，内部schema由core固定；它不收窄或覆盖read_status/business_status及任何served identity字段。 latest_attempt/latest_attempt_status 是两个 M09 分支共用的新增字段，无可用尝试时两者均为 null；非 M09 旧响应可以完全没有 m09_publication。对象存在时 latest_attempt_status 直接等于 latest_attempt.status（SUCCEEDED / FAILED / UNKNOWN）；不从 read_status 推算，也不补造状态。上面的配对联合避免允许 SYNTHETIC/HISTORICAL_REPLAY、RECORDED_INPUT_REPLAY/DAILY_RESEARCH 或 REAL/ENGINEERING 等非法交叉组合；后端仍须独立校验。MISSING/CANNOT_CONFIRM 不要求计算分类、成员或计算时间字段，UI 不填造缺失值。最终 provenance/evidence_status/membership 的内部结构以候选契约为准，不能因 UI 不认识就丢弃元数据。渲染采用普通文本，不将来源字符串当 HTML。MISSING/CANNOT_CONFIRM fixture 的模型 run 和各类摘要为 null；不制造空字符串伪摘要。VERIFIED 是读回完整性状态，不能翻译为业务或自然运行成功。

原算法固定分支如下；显示为百分比只改变格式：

| 原分支 | 原概率 | 建议显示 |
| --- | ---: | --- |
| stronger | 0.12 | 偏强情景 · 12% |
| inline | 0.28 | 基准情景 · 28% |
| weaker | 0.60 | 偏弱情景 · 60% |

必须相邻说明“原算法固定情景权重，未经概率校准，仅用于研究”。不得标成实测胜率、已校准预测、置信度或正式买入建议。不得将这些值重新拟合、归一化、排序，或根据后来视频变更历史产品。原条件和失效文本逐项显示。

可用状态文案：

- “M09 A股复盘预览 · 所选交易日 T”；保留原 source_role 原值作为来源详情。
- “模型计算已形成；业务证据仍有缺口”；仅在两部分事实同时成立时显示。
- “该交易日没有已提交的 M09 结果”；对应 MISSING，不是生成中。
- “该交易日结果校验未通过”；对应 CANNOT_CONFIRM，并显示原因。
- “历史输入回放”或“工程样本”；由分类字段决定，不能套用自然当日成功标题。
- “严格15:00 PIT：未确认”；保持 false 所表达的事实。
- “统计范围：申报集合；全市场成员未独立确认”；对应 DECLARED_UNIVERSE_ONLY 和记录层缺口。
- “自然触发、来源材料：独立证明未确认”；分别对应 natural_verified=false 与 source_provenance_independently_verified=false。
- “最近尝试失败/结果未确认；继续展示上一份已核结果”；仅在对应 FAILED/UNKNOWN 与可服务成功均有证据时显示，并分别列出两者身份。

## 5. 导航、缓存和研究 POST

保留 App.vue 的 closeReviewRequestVersion、requestedDate、assertExactResponseDate 及 selectedDate 比较。日期 A 的晚响应不得覆盖用户后来选中的 B。保留浏览器 URL/history 的 a-review/review/research-review 定位和页面已有日期准入；M09 不能套用另一市场或未来目标日合同。

同日重复点击 A/HK 标签可按当前实现复用同一 envelope；用户显式刷新必须重新 GET，因此能够读到后来提交的新一代。缓存是显示层行为，不能以缓存命中记作新计算回执。服务端应对普通快照采用明确缓存语义，例如 no-store，或返回足够验证代身份的元数据；不以“每次点击重算”解决陈旧显示。

ReviewView 的 generateSelectedDate 当前只由 DailyResearchReviewPanel 的 @generate 调用，内部 POST /api/v3/review/generate 后 GET。它是已有研究生成动作，与 A 预览独立。本请求不新增或扩大该 POST 的用途。A 导航、刷新、前进/后退和“读回最新提交”都不能连到该方法。

## 6. 双方验收请求

| 用例 | M09 提供 | 前端/API owner 验证 | 执行状态 |
| --- | --- | --- | --- |
| 原生模型 READY、业务 PARTIAL | 原字段完整 fixture | counts/行业/角色可见；业务缺口可见；未打富复盘/正式标签 | NOT_RUN |
| 0 与缺失值 | 0、null/缺失的精确 fixture | 0 不丢失，未知不填 0；无旧日残影 | NOT_RUN |
| 三分支模型 | 原算法情景 | 12%/28%/60%、原条件、原顺序、未校准说明齐全 | NOT_RUN |
| 模型未就绪 / M09 MISSING | 无模型元数据 fixture | 明确原因；无 modelReady 强制、无隐式计算 | NOT_RUN |
| 非 M09 rich A | 既有 rich fixture | 原显示逻辑保持；本扩展不降级或改变原来源 | NOT_RUN |
| 先读T1再切T2、T1较晚返回 | 两日可控 GET | 精确日守卫工作；history 往返行为正确 | NOT_RUN |
| 同日点击与显式刷新 | 请求计数 | 标签切换按原缓存；显式刷新 GET；A 路径 POST/计算计数均为 0 | NOT_RUN |
| 研究手动生成 | 独立研究 stub | 仅显式研究动作 POST；M09 不接管该能力 | NOT_RUN |
| 历史分类与时点 | REAL/HISTORICAL_REPLAY 与 RECORDED_INPUT_REPLAY/HISTORICAL_REPLAY | 原数据分类保持；日期/来源未知/计算时间/as_of 各自显示，不称自然16:05/17:10成功 | NOT_RUN |
| 记录层范围与缺口 | membership、scope、record_cannot_confirm、false 独立证明标志 | 申报集合限定、三项记录层缺口可见；原模型/链缺口仍保留 | NOT_RUN |
| 可选元数据与分类联合 | 非M09、不可用M09、四种合法配对 | 类型/显示兼容；缺失字段不填造；非法配对不获 VERIFIED | NOT_RUN |
| 后槽失败或中断 | 已核成功 + 独立FAILED/UNKNOWN latest_attempt | 旧模型/served SHA继续显示，尝试失败/未知同时可见；不混run/时间、不自动重算 | NOT_RUN |
| 无成功但有尝试 / 无尝试 | MISSING与尝试对象或None | 有据的尝试状态独立显示；不虚构模型、终态或重试 | NOT_RUN |
| 缺失结果且尝试读失败 | MISSING + M09_LATEST_ATTEMPT_READ_FAILED | 显示尝试读取未确认，null字段不填造；无成功/自动重试 | NOT_RUN |
| 同日predecessor只读恢复 | 已核所选代 + publication_recovery | 选中代的模型/SHA显示正确，恢复说明独立；无“head已修复/已回滚”虚假成功标签 | NOT_RUN |
| HK 与其他区块 | 组合前后 envelope | HK/research/intraday 的数据与既有显示相等 | NOT_RUN |
| M09 回滚后刷新 | 两代 API 响应 | 展示已核旧 generation；摘要标签与实际读代一致 | NOT_RUN |

**当前只核验源码事实与附件字节；前端构建、组件测试、可访问性/布局检查、Mac 浏览器实测、活动 API 集成和现场回滚均 NOT_RUN。** 模块适配器测试即使成功，也不能代替此处渲染证据。owner 回传固定 commit、精确 diff、构建/测试命令及结果、按 T/run/record/generation 对齐的页面证据，M09 再补集成验收状态。
