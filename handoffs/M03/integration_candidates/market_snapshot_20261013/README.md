# M03 独立行情来源完整候选

范围：统一计划 `386d5ce67a6a9914a96162cd47528290b8e7d75f` A2。候选基线为 M03 分支 `528af98f28de0105f5d2229007cc93e345210311`。只新增本 `integration_candidates` 目录，不覆盖历史候选、原冻结 owner、P0、现役 V4 或任何数据根。

## 本候选真正执行的链

`V5/run_market_source.py` → R14 `run_us_source` 默认独立 owner child → `run_cold_collector` 的明确 market-only 分支 → 新 `us_market_capture.main` fresh child → 原 `load_owner`/descriptor/PIN/module audit → 原 guarded transport → 原 Chat adapter → 原 `build_us_market_snapshot` 完整公开入口 → 原 `_base_payload`/`_annotate_payload` → 原 `ResearchPeripheralStore.publish` → R14 另进程原 `read_exact` → 稳定三件复制到独立 snapshot → 原 `create_binding/persist_binding` 及独立磁盘重验。

原 frozen producer 的 24 主题/33 唯一代理股票、同 session 报价处理、算术、provider 证据及完整 store 验证保持原样。没有新行情算法、动态下载 owner 或回退 V4 活动代码。

### 原 Chat 与本次补装的贡献

- `original_chat/market_snapshot_adapter_4c9f0aa2.py` 是本次收到的原 Chat 源码原字节，raw SHA256：`e4140a3c29bbe31d1d8ca512c5bd9c5e73190e7ef2aaf7f19bc2df0bdafc07a1`。
- active `V5/src/v5_shadow/market_snapshot_adapter.py` 复用它的请求类型、原公开 producer 调用和身份核对。本次仅补受控 module audit、session/cutoff 前置检查、原完整 snapshot validator，并保留原合法非 READY 结果供上层明确拒绝；没有把非 READY 改成 READY。
- `us_source_daily.py` 复用完整 R14，总链、cold reader、三件物理 SHA、不可替换 snapshot/binding 和失败保旧不重写。本次仅增加 `market_snapshot_only` 布尔请求字段与 collector 分支。
- 本次补装提供 `us_market_capture.py`、独立启动入口、完整随包闭包、定向测试与交付清单。旧默认 RSS+quote 调用仍可用；新独立启动入口固定选择 quote-only。
- 原 owner 48 文件逐字保留。原 descriptor raw SHA256/PIN：`34f45318dd89132a496ac0edf98147455b41d9ea926198d83ce1bd8810c20d8b`；owner 原来源 commit：`164c010c7eaa1659db9bfed0ff5f123c7a39eefc`。

## 新闻与行情身份不可混用

独立行情不抓 RSS。原 envelope 的 `status=READY_EMPTY` 只描述零新闻条目；`item_count/raw_item_count=0`，details/overview/items/feed_receipts 均空，source_url 为真实 quote 请求 URL。

- `cannot_confirm` 保留 `NEWS_NOT_REQUESTED_QUOTE_ONLY_CAPTURE`。
- capture 明标 `rss_status=NOT_REQUESTED`、`quote_capture_status=ATTEMPTED`。
- 行情成功必须独立满足 `market_snapshot.status=READY`，完整 quotes/24 rows 和原 22 字段及语义校验。新闻零条不意味着行情为空或未抓取。
- 报价失败/旧 session/HTTP 拒绝等保留原 CANNOT_CONFIRM 快照和原因；原 store 保存可审计三件，R14 返回 `SOURCE_REJECTED`，不创建成功 binding。
- 既有合法来源仍按 R14 原 reader 复用。`market_snapshot_only` 控制新采集选择，不把旧正常 RSS+quote 来源强改为 quote-only。

M15 应继续通过原 `ResearchPeripheralStore` 读取同三件的 `market_snapshot`，不得用顶层新闻 item_count 判定行情是否就绪。M15/P0 页面接线不在本候选内。

## 实际时钟和授权边界

启动请求没有 captured_at、now、provider、fetch callback 或 transport override 字段。采集子进程仅从原 `owner._capture_now()` 取得一次实际时刻，先检查 cutoff、原交易日认证和 `build_capture_metadata` 的纽约收盘窗口，再请求 quotes。captured_at 绝不取 cutoff 或回填旧日。

自然 POST_CLOSE、原 DST/日历和显式 controlled-late 规则均沿原 helper。late 元数据原样进入 snapshot/capture；不会冒充自然触发。测试中的 clock/Proxy 只在测试子进程 bootstrap 注入，不是 CLI 或生产请求选项。

原 `allow_network_capture` 默认 false；未授权缺源返回 SOURCE_MISSING。新采集必须显式 true、指定 capture_root 并满足实际时钟/原门禁。本次所有测试均禁真实 socket，未执行真实网络采集。

## 自包含启动与依赖

- POSIX Python 3.12；实际验证解释器见 TEST_REPORT.md。使用 Python 标准库（含 fcntl、zoneinfo），本候选无需安装 pandas/pyarrow 或新依赖。
- 系统需已有 `America/New_York` 时区数据。原 2026 calendar JSON、全部 frozen owner、wrapper、descriptor、vendor/test 源码均随包，不需要 V4 工作目录或旧 Git 对象。
- 先从固定 commit 完整取本候选目录，核 `RELEASE.json` 与 `python -I -B verify_release.py`。manifest 每项 SHA256 是文件原字节，不是 Git commit，也不是业务产物 SHA。
- 从任意其他工作目录均可启动：`python -I -B "$CANDIDATE/V5/run_market_source.py" --help`。无需设置任意 PYTHONPATH。help 不导入 owner、不建数据根。
- 执行：`python -I -B "$CANDIDATE/V5/run_market_source.py" --request "$LOCAL_REQUEST"`。
- 退出码：0=VALIDATED_SOURCE_BINDING；3=显式业务非成功（如 SOURCE_MISSING/NOT_DUE/SOURCE_REJECTED/COLLECTOR_FAILED）；2=异常/请求或完整性拒绝。进程零退出不能替代读取其原业务状态。
- 这是单次 CLI，不安装/启用调度器、不启动 API 或常驻服务，不占现有端口。

`LOCAL_REQUEST` 是仅本地保存的 JSON，字段使用原 `USSourceRequest` 合同：

```json
{
  "trade_date": "YYYYMMDD",
  "capture_phase": "POST_CLOSE",
  "session": "YYYYMMDD",
  "cutoff": "timezone-aware actual business cutoff",
  "source_root": "local absolute authorized source root or absent path",
  "snapshot_root": "local absolute new immutable snapshot root",
  "binding_root": "local absolute private binding root",
  "owner_root": "absolute CANDIDATE/collector_owner",
  "v5_src": "absolute CANDIDATE/V5/src",
  "allow_network_capture": false,
  "capture_root": null,
  "allow_late_post_close": false,
  "development_dates_file": null,
  "market_snapshot_only": true
}
```

这是字段模板，须本地填真实日期、cutoff 和已授权路径，不能按占位值运行。原新采集 CLI 合同要求 trade_date=session；已有来源读取仍用其真实独立身份。新独立路径只做 POST_CLOSE，历史/backfill 保留旧明确入口，不自动退回旧路径。

所有 source/capture/snapshot/binding/owner/code 根必须为绝对、无 symlink、相互不嵌套；建议数据根完全置于候选包之外。已有未标记根拒绝，不追补 marker。R14 仅对不存在的新私有根调用原 initializer。

每个 capture_root/snapshot_root 只容纳一个完整三件 generation；不得把它当滚动日库。成功三件：

- `research/peripherals/{trade_date}/external_finance.json`
- `receipts/research/peripherals/{trade_date}/external_finance.json`
- `research/peripherals/manifest.json`

receipt 中 canonical payload/snapshot/source-response 身份由原 store 生成；binding 的 source_sha256 则是复制后、实际冷读的三个文件 raw SHA256。这两类 SHA 含义不可互换。

## 冷读、失败恢复与回退

- 只读快照：原 `v5_shadow.us_source_daily.read_cold_snapshot(req)`；新进程中读取同请求 JSON 并调用，绝不触发采集。
- 原完整 binding 的幂等重验：`run_us_source` 使用同一完整请求和已有 binding，先读 binding 并独立核引用，成功即复用，不重 owner producer。请求字段变化意味着不同 binding 身份，不可悄悄删改字段。
- collector 已保存三件但回执丢失：下一次明确请求先由原 reader 核 capture_root，符合相同日期/session/cutoff/quote-only scope 才复用三件，零 quote 调用；不重采，不把恢复算自然运行。
- 三件缺一、坏 hash、未知 source、坏 marker/owner、不同日期挤入同 capture_root 均 fail closed。不把损坏转换成 SOURCE_MISSING，不自动修件或覆盖。
- 已保存拒绝来源不会在同根重试网络。若确需下一次授权实际采集，必须新 generation 根、真实时点及原窗口重新准入；不能覆旧成功或伪造无效果标记。
- 进程退出/超时或响应丢失不证明无副作用。先冷读三件与已有 binding，再决定是否允许后续受控调用。此候选不创建、删除或重置 P0 ledger/claim。
- 回退是停止使用本候选并切回之前固定代码与其原根；本交付不对旧代码/根/指针做迁移或覆盖，无需在旧 owner 上反向打补丁。保留本次证据，不能删掉失败证据来放行。

## 定向离线验证

从候选目录执行：

```sh
M03_FIXED_SOURCE="$CANDIDATE" python -B "$CANDIDATE/V5/tests/run_m03_offline_suite.py"
```

这个原 R14 runner 使用随包 frozen owner 替换旧测试的 git-show 装配 setup；原 collector/transport 测试方法体不变。新增测试使用原受控 transport 配合 fake Proxy 响应，实际经过原 producer/store/cold reader/binding；不 mock 业务字典或 reader 成功结果。精确通过/失败/未运行状态见 TEST_REPORT.md。

不要上传真实请求、私有绝对路径、原三件内容、provider 元信息或凭据。固定源码、上述合成测试和脱敏执行结论不等于真实 provider、Mac、M15 页面或自然调度验收。
