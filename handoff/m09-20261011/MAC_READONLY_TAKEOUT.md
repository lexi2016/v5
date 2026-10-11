> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 Mac 精确只读取件单

这是一项现有 Mac 环境的只读发现/取件工作，不运行 producer、collector、scheduler、pytest，不安装依赖、不改变配置，不碰 V4 写入，不复制秘密。先复用既有任务已验证的 checkout、Python、运行配置和入口；下文大写变量是待从现场证据赋值的工作变量，不是猜定的路径。

## 1. 必要输入：panel 与日期 T

固定原件：`handoff/v4-running-source-20261005/canonical/ops/build_a_share_close_review.py`。

- 入口：`build_review_from_panel(data_root, trade_date, *, panel_pointer, run_id=None, video_acceptance=None, video_capture=None, stockdict_pointer=None, ocr_alignment_pointer=None, video_gap_pointer=None, replace_previous_sha=None)`。
- CLI 搜索符号：`ops.build_a_share_close_review`、`a_share_close_review`、`--panel-pointer`、`panel_pointer`、`--data-root`、`business_date`。
- 冻结工作负载：`V5/vendor/daily_schedule_baseline/contracts/runtime_workloads.json` 中 `workload_id=a_share_close_review`；命令参数来自 `{data_root}`、`{business_date}`、`{panel_pointer}`；owner `v35_dispatcher.a_share_close_review`、slots `1605,1710`。这是定义，不是运行证明。
- 只在已核 checkout 中查配置与调用位置。例如：

```sh
# REPO 必须是既有任务核实的 checkout；这些命令只读，不扩展到整个用户目录。
git -C "$REPO" rev-parse --show-toplevel
git -C "$REPO" rev-parse HEAD
git -C "$REPO" status --short
rg -n --glob '*.py' --glob '*.json' --glob '*.toml' --glob '*.plist' \
  --glob '!**/.git/**' --glob '!**/.env*' --glob '!**/*secret*' --glob '!**/*credential*' \
  'a_share_close_review|ops\.build_a_share_close_review|panel_pointer|--panel-pointer' \
  "$REPO/ops" "$REPO/infrastructure" "$REPO/contracts" "$REPO/V5"
```

候选目录若不存在，应报告，不扩大盲搜范围。真正活动配置以进程/启动服务绑定为证，历史 handoff 命中不计活动绑定。

原 `_panel_path` 把 pointer 的 UTF-8-SIG 内容去首尾空白后当路径，并要求 `is_file()`。相对 pointer 目标依赖运行 cwd，应精确记录 cwd；不要自行改成“相对 pointer 所在目录”。交回：

- `panel_pointer_path`、`pointer_bytes` 或不含秘密的原件、`pointer_sha256`、`pointer_target_text`、`effective_cwd`、`resolved_panel_path`、是否 regular file / symlink。
- panel 原件或得到许可的只读可消费副本，`panel_bytes`、`panel_sha256`、文件元数据、取件前后 SHA 一致证据。mtime 单独列，不作采集时点。
- panel Arrow schema。固定 producer 请求 8 列：`trade_date, ts_code, name, pct_chg, amount, bar_close_pos, tdx_industry_code, tdx_industry_name`；按 `ds.field('trade_date') == T` 精确筛选。检查 T 是真实 `YYYYMMDD`，字段类型与查询兼容。
- T 行数、唯一 ts_code 数、重复代码/非 A 后缀/缺列/空行业/非数值/NaN/负 amount/越界 bar_close_pos 统计，以及每项是否阻断；不要先静默清洗再宣称完整。
- T 的完整声明成员清单原件与 SHA、来源、版本和是否可证明全市场。不能用结果 Top10、M07阶段列表或模型输出反推 membership。
- T 对应交易日历文件及 SHA、actual capture/acquired/available timestamps 与证据出处、时区。M09 是 T 当日复盘；不预填 20261012，也不照抄 M13 的 source9/target12。历史 T 可用于真实输入回放，必须标 replay，不能冒称自然当日执行。

## 2. 同日已有 M07 / M12 证据（可缺，不倒要未来产物）

只消费已提交、当时已可用的输入，不重新跑 M07/M12。每个工件交：所属模块、producer/run、trade_date、状态、artifact/ref、文件或对象 SHA、available_at、来源回执、该值是否独立验证。不存在或时点未核如实写 MISSING/UNKNOWN，价格复盘仍可作为 PARTIAL 候选继续。

原 producer 接受五个可选 JSON：

- `video_acceptance`：原 chain 实际读取 `trade_date`、`checks.same_day_video_count`、`today_bv_status`、`status`、`asr_status`；同日锁定条件为 `TODAY_BV_LOCKED` 且数量 > 0。
- `video_capture`：`trade_date`、`status`、`videos`；ASR 状态可能是 `ASR_READY` / `ASR_REVIEW_REQUIRED`。
- `stockdict_pointer`：同日且 `status=CURRENT_ASR_STOCKDICT_READY_EXACT_ONLY`。
- `ocr_alignment_pointer`：同日且 `status=VIDEO_TABLE_ASR_NEWS_ALIGNMENT_READY`、`row_count>0`。
- `video_gap_pointer`：同日且 `status=VIDEO_GAP_AUDIT_READY`、`gap_row_count>0`。

上述旧结构不自带可靠 available_at 保证；若外层已提交证据无真实时间，不得用 mtime 或 slot 补填。晚到工件只可进入其 available_at <= cutoff 的后槽；晚于 17:10 的材料不进入当天这两个槽的历史结果。

源中已见的只读定位线索（不是现场存在证明，路径均相对已核 data_root）：

- `close_review_sources/{T}/bilibili/selector_pointer.txt` 是视频 runner 的 selector 线索，未证明等于收盘 producer 的活动 panel_pointer，不能混用。
- `close_review_sources/{T}/bilibili/transcript_stockdict/current_asr_pointer.json`
- `close_review_sources/{T}/bilibili/transcript_stockdict/stock_mentions.json`
- `close_review_sources/{T}/bilibili/video_ocr_alignment/alignment_pointer.json`
- `close_review_sources/{T}/bilibili/video_gap/video_gap_audit.json`
- `close_review_sources/{T}/bilibili/video_session.json`
- 视频共享层只允许点查已知非秘密绑定：`REVIEW_CORE_PACKAGE_ROOT` / `V35_REVIEW_CORE_PACKAGE_ROOT`、`REVIEW_CORE_DATA_ROOT` / `V35_REVIEW_CORE_RUNTIME_ROOT`、`V35_REVIEW_EVIDENCE_STRICT`。不得倾倒全部进程环境变量。
- 需要确认共享投影解析时，读取活动 `ops/_run_v35_close_review_node_parts/source_binding.py` 及其实际调用合同；不要把整条视频生产链拉进 M09。

## 3. 存储与公开读面：取合同，输出由实现生成

原 store 固定相对结构已经知道，无须用户猜：

- `{store_root}/a_share_reviews/{T}.json`
- `{store_root}/a_share_reviews/receipts/{T}.json`
- `{store_root}/a_share_reviews/manifest.json`
- `{store_root}/a_share_reviews/.import.lock`
- 替换回执：`{store_root}/a_share_reviews/supersessions/{T}/{expected_sha256}.json`

只读取活动 root 来源/绑定、`AShareReviewStore` / `SafeRoot` 当前源码 SHA、owner/权限事实与是否和 V4 同根。旧 `replace_review` 保存 supersession 摘要但覆盖同日 payload，不能仅靠它声称保留前槽完整成功；候选应在 V5 私有不可变 run/generation 隔离保存两个版本。

V5 公共只读接口契约：`module_api._config` 要求 `schema_version,module_id,release_id,data_root,routes`，root 标记 `.v5-module-root` 内容为 `v5.module-root.v1:<module_id>\n`。对象为 `objects/{sha}.json`，generation 为 `generations/{sha}.json`，活动头 `active.json`，比较交换入口 `module_artifacts.publish_generation(..., expected_generation=...)`。需要现场核真正 M09 module_id、root、release、routes、generation 和唯一发布 owner，不能先造配置或 marker。

原 API 片段给出 `prefix=/api/v3`、`GET /review?date=T`，A 数据来自 `AShareReviewStore.read_review(T)` 或 strict Review Core 分支，响应包有 `market_reviews.A` / `.HK`。必须取活动 facade、`create_review_router` 调用、`review_core_a_share_bundle_required` 分支与绑定摘要；若 strict 分支生效，仅写 legacy store 不会证明原页面消费成功。

搜索符号：`create_review_router`、`AShareReviewStore`、`review_core_a_share_bundle_required`、`load_review_core_a_share_review`、`ReviewView`、`/api/v3/review`、`generation_bindings_path`、`data_root`、`review_root`。活动进程端口/URL从既有服务配置或监听表确认，不能直接使用旧注释/常量端口。原 `run_v35_close_review_slot.py` 的 docstring 8872 与实际常量 8873 已不一致；两者都不是当前入口证明。

需要的交回物：活动 API/UI 源码相对路径+SHA、实际进程/启动配置的去秘密摘要、请求入口与路由→模块/根/版本关系、原页面消费字段位置。可以返回已有响应作诊断，但未生成的 M09 当日 review、receipt、manifest、API 响应、UI 截图不是前置输入。

## 4. 运行环境与两槽

交回现有 Python executable/version、锁文件/依赖声明路径+SHA和 pandas/pyarrow/pytest 已安装版本（只读元数据，不装/升级）。V5 固定 pyproject 声明 Python >=3.14、pandas >=2.3,<3、pyarrow >=21,<25，pytest 未钉版本。取 Mac 当前值，不能把声明当已满足。

现有活动 scheduler/launch agent/dispatcher 对 `a_share_close_review` 的参数展开、两槽定义、日历、时区、实际可用回执位置/身份规则。视频 runner 的 20:25—21:15 NODE_SLOTS 是 M12 线索，不是 A 16:05/17:10 的触发证明。禁止运行 slot 或创建回执来补证。

## 最小交回格式

将结果按 `required_input / optional_input / runtime_binding / implementation_output_not_required` 分类；每项包含 `status, value_or_file, bytes, sha256, source_path, source_symbol, observed_at, trade_date_if_applicable, time_semantics, blocker_scope`。源中已知字段与现场实际值分开。必要数据缺失可阻断真实运行层，绑定缺失只阻断对应部署/API/UI层；继续已有源码能完成的编码与工程验证。
