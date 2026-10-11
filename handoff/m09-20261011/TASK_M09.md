> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 A 收盘复盘独立交付任务书

版本：2026-10-11 本地材料版。目的仓库：独立私有 `lexi2016/v5`，仓库/分支/提交是否已建立由发布回执证明。原始 donor 出处为 `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`，仅作不可变来源。禁止把 M09 新文件或候选写回 v4。

本轮材料准备不代表已编码、测试、部署或自然运行。旧 ZIP handoff 的旧目的仓库和窄任务描述不能覆盖本任务书；固定源码及其 manifest 原字节保留。

## 1. 已批准目标

复用 V4 原确定性算法，以真实 A 股交易日 T 的 panel 数据形成 V5 A 收盘复盘；在 V5 私有根保存，独立读回，接入现有普通 API 和原 ReviewView 的 V5 预览绑定，展示涨/跌/平、行业、角色、模型情景及证据缺口。保留 V4 服务、数据和系统；不交易、不下单、不改 BUY 门，不扩系统安全权限或凭据访问。

保留上海时区 16:05 和 17:10 两槽。完整输入、算法、配置身份相同可复用成功计算，但两个触发都要独立回执。后槽有已可用新材料时新建 run；后槽失败不丢前槽成功。阶段/视频不足时如实 PARTIAL/CANNOT_CONFIRM，不能把模型数值成功冒充整链完整。单模块发布/回滚，其他模块与另一市场无改动。

## 2. 日期与证据硬边界

- T 是本次收盘复盘的真实 A 股交易日；panel 的 `trade_date`、模型 `review_date`、review `trade_date`、输入引用以及 API 请求日必须一致。`next_day_trigger_tree` 是原复盘产品字段，不把整个复盘改成未来目标日。
- 不套用 M13/M18 的跨日选择器合同，不预填某个未来日期。若用既有历史日验证，明确 `RECORDED_INPUT_REPLAY` 或等价的历史运行分类；不能借当前触发时间冒称自然当日数据。
- 来源 `acquired_at / captured_at / available_at`，模型历史 `as_of=15:30`，严格 15:00 PIT，触发 slot，实际执行起止时间是不同概念。旧标签、文件 mtime、模型输出都不能制造缺失的来源时间。
- cutoff 取已确认的该槽业务规则；只准入 `available_at <= cutoff` 的同日材料，来源时点未知须保留未知或拒绝对应准入。17:10 后才到的视频不能回填16:05/17:10旧 run，也不能静默发明第三槽。
- panel_pointer/parquet、同日成员与来源时点是必要的真实运行输入。尚未生成的 review/store/API/UI 是实现输出，不能先索要输出再实现。已有输出仅可选作诊断/对照。

## 3. 固定源码事实与入口

1. 原生产链：`ops.build_a_share_close_review.build_review_from_panel` → `domains.a_share_close_model.build_close_model` → `domains.close_review_chain.build_close_review_chain` → `domains.a_share_review.build_a_share_review` → `AShareReviewStore.import_review / replace_review`。原正式 reader 为 `AShareReviewStore.read_review(T)`。
2. 本包含该 producer 的 12 个内部静态 import 依赖，AST 只读审计未发现该入口未附的内部 import；外部 pandas/pyarrow、实际解释器与 Mac OS 行为尚未核。不能把静态闭包已齐冒称运行已验，也不要反过来假称 writer 源码全部缺失。
3. 现有 V5 `a_close_review.py` 只准 `SYNTHETIC / RECORDED_INPUT_REPLAY`，固定 capsule 三文件；保留此回放边界。真实 daily 入口是新 `a_close_daily.py`，不把回放放宽或改名为生产。
4. 原模型会按日与 A 后缀筛选、把部分数字转换并 dropna。daily 准入必须在调用前验证完整声明成员和数值质量，不能经静默过滤后把剩余行称全市场；不修改模型内部算法来掩盖输入问题。
5. 原 store 同日路径固定。`replace_review` 会改同日 payload，supersession 保存前后摘要而非完整旧 payload。因此保前槽必须有 V5 私有不可变 run/generation 或等价已核隔离；不能仅调用 replace 并宣称旧成功完整保留。
6. 原 API 历史片段 `GET /api/v3/review?date=T` 可能按 strict Review Core 分支绕过 legacy store。现场确认活动分支后由统一集成者接通；不能以写文件成功推定原页已消费。

## 4. 实现范围与原件/after 边界

原 ZIP、`original/`、donor、旧 vendor 和旧来源 manifest 不修改。新候选在 `after/` 下，保留仓库相对路径 `V5/...`，不能自行删掉一级 V5 或把源码复制进现役 V4。新仓库若选择不同布局，先给逐路径映射及新的固定基线，禁止隐式重定位。

M09 独占候选：

- `V5/src/v5_shadow/a_close_daily.py`（固定 F 不存在，应用时重核）
- `V5/tests/test_a_close_daily.py`（同上）
- `V5/docs/M09_A_CLOSE_HANDOFF.md`（同上）
- 仅必要兼容差异的 `V5/src/v5_shadow/a_close_review.py` 与 `V5/tests/test_a_close_review.py`，不得破坏回放拒绝/研究/PIT标志。

复用 producer/store 若需要新冻结闭包：提交精确 donor→新目标映射、新文件完整字节、来源 commit/path/blob/SHA、全部内部依赖及 manifest 候选，由统一集成者收录到 M09 专属命名空间；不修改或伪造现有三文件 capsule 的来源，避免裸 `domains/contracts/infrastructure` 与活动应用冲突。该收录是完成既定 M09 的依赖交付，不是理由只交计划停止。

共享 API/gateway、artifact publisher、run ledger、dispatcher、日历、前端、M10/HK 和其他模块由唯一集成者单写。M09 Chat 给函数级接口请求、前像SHA、schema/调用样例与双方测试，不能交跨模块整文件覆盖。集成者完成后回传固定基线，M09 对此 rebase 最小差异。不得新增18套服务器/页面/调度。

## 5. 应实现的完整闭环

A. 准入：校验 T 日历、真实 panel_pointer 与不可变 parquet 快照、8列类型、行数/成员唯一性/全声明集合、来源时点与SHA；记录声明范围，不把已声明集合等同全市场资格。源文件、pointer 与SHA在计算期间变化应失败，不能悄悄采新值。

B. 调用原算法与原正式产品构造：保留原上涨/下跌/平盘、行业/角色顺序、分值、理由、情景树和常量概率，保留 disabled LLM、WATCH_ONLY、PIT/学习/泛化/视频未消费等研究边界。视频链就绪不等于模型已语义消费视频，不能清除原 `CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED`。输出完整 review/model/close_chain，不只输出模型 JSON。

C. 身份与两槽：区分计算 identity（所有实际参与计算的不可变输入、依赖/代码/配置）与触发 identity（T、slot、job、attempt、实际触发类型/时间）。相同计算可共享成功 artifact，但16:05/17:10都要receipt；cutoff或材料影响输出时纳入identity并建立新run，不能同日 logical key 吞后槽。

D. 私有保存：原 writer 在核实的 V5 私有候选 run 根工作，先独立 `read_review(T)` 验证 payload/receipt/manifest；旧成功和失败 attempt 分离保存。新 generation 仅在完整校验后CAS切换。写到半途/验读失败/CAS冲突应保持原可服务成功版本并返回真实错误。

E. 普通 API/原页：只读兼容层消费已提交结果；证明 T、model run_id、payload/source/record/generation摘要链一致。不同层不同摘要必须注明类型，不能要求“所有SHA字符串相等”：`source_sha256`、canonical payload SHA、原件 raw SHA、API record SHA、generation SHA各有含义。API刷新、返回、日期切换、重复点击不得触发计算/采集；旧日成功可显示但要注明日期/过期。

F. 独立回滚：只切回 M09 经核上一 generation/binding，不删除新旧objects/runs，不覆盖 HK/A共用响应的另一市场，不改 V4。验读回滚后响应、原页、另一市场和V4摘要并留回执。

## 6. 工程开始与依赖处理

读 `ASSEMBLY.md` 可从现成附件解压、核对并开始编码，GitHub connector 不可用不构成源码阻断。先列模块局部短计划与失败用例，不等待全18模块再审一次大计划。按 Superpowers 对相关工作使用 systematic-debugging、test-driven-development、verification-before-completion；已有用户逐项批准的目标和约束不重复审批。

工程 fixture 只用于边界/幂等/并发等可控验证。真实输入和API绑定尚未取齐时继续不依赖它们的实现，逐层写BLOCKED/NOT_RUN，不能伪造真实行情或测试结果。详见精确 `MAC_READONLY_TAKEOUT.md` 与 `DELIVERY_CONTRACT.md`。
