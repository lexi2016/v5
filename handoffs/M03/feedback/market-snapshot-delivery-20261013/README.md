# M03 独立收盘 market_snapshot 交付反馈

## 结论与核对范围

**本次两次提交还没有完成独立收盘采集任务。** 它们新增的是一个内存字典检查函数和两例对应测试，不能据此计为 collector、持久化快照或原 reader 总链完成。

固定核对：
- 分支：`dev/m03-github-handoff-20261011`。
- 实现提交：`bef2412d23f602697d012c96ad008151133dd6e7`；仅新增 45 行 `market_snapshot_adapter.py`。
- 测试提交及本次读取 HEAD：`3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f`；仅新增 34 行 `test_market_snapshot_adapter.py`。
- 同一固定树中的 R14 `us_source_daily.py`、原 collector wrapper、冻结 owner producer/store 合同作为对照。

这是提交给原 M03 Chat 的窄任务反馈。保留原 R14 已有完整链及历史验收，不要求重做它们。本次不修改产品、owner、PIN、transport、运行配置或测试。

## 静态确证的交付缺口

### 1. 尚无独立采集或物化接线

[新增实现 L25–40](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/after/V5/src/v5_shadow/market_snapshot_adapter.py#L25-L40) 的 `materialize_market_snapshot(payload, *, session, phase, cutoff)` 只取调用方字典、比较四项字段，然后返回原对象。

该文件没有调用原 producer/collector、`read_cold_snapshot` 或 `run_us_source`，没有受控输出根、原三件产物、持久化及冷读；原 R14 总入口也未在这两次提交中更改。因此它不能从真实授权行情输入产生收盘快照，新增函数名字不构成 materialization 证据。

### 2. 新正例不满足原最小快照合同

[新测试 L16–30](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/after/V5/tests/test_market_snapshot_adapter.py#L16-L30) 手写的 snapshot 只有 `status=READY`、`capture_session_date`、`capture_phase`、`captured_at`，并仅断言返回 READY。根据新增函数的静态条件，这个无行情、无原产物的字典就会被接受。

原 [`__validate_market_snapshot_body` L10–36](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/_research_peripheral_store_parts/market_validation.py#L10-L36) 要求 22 个顶层字段。上述正例缺少：
- `schema_version, source, provider, source_response_sha256, generated_at, mapping_version`
- `requested_symbol_count, available_symbol_count, provider_session_dates, provider_session_times`
- `quotes, rows, cannot_confirm`
- `recommendation_status, RESEARCH_ONLY, production_allowed, buy_gate_updated, orders_sent`

原 [L103–155](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/_research_peripheral_store_parts/market_validation.py#L103-L155) 还验证恰好 24 行、quotes/available symbols/汇总计数与 provider 日期时间一致；READY 行状态和 cannot_confirm 必须一致。[L166–173](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/_research_peripheral_store_parts/market_validation.py#L166-L173) 强制研究标记与三个 false 安全开关。新增函数均未验证，额外带入的 unsafe 字段也会原样返回。

这是静态可确定的合同差异，并非本次执行过该假字典或原 reader 的运行结果。不要把四字段对象当作原生产正例，也不要靠补常量 READY/安全字段来伪造来源。注意原 validator 允许空 `source_response_sha256` 字符串，`provider_receipt` 可选；不应额外发明比原合同更强的普遍要求。

### 3. 新测试没有覆盖新增独立链

两例分别检查“缺 market_snapshot 报错”和“四字段字典返回 READY”。没有实际经过 producer、原 store publish/read_exact、独立冷进程、三件字节 SHA 或 R14 binding；没有证明收盘窗口、错误报价、篡改/缺件、无授权不联网、失败不覆盖旧成功。

原 R14 的既有测试和历史 48 PASS 报告属于原链，不能自动作为这两个新增文件的独立收盘链验收。

### 4. 新文件尚未进入现有完整交付清单

本固定树的 [R14 MANIFEST.json](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/MANIFEST.json) 仍列原五个 after 文件，不含这次 adapter/tests；README 仍说明五文件，现有正反 patch 和 TEST_REPORT 未在这两次提交中更新。后续完整候选需让新文件、真实前后像、组装/回滚说明与测试命令对应，不能让使用旧 manifest/patch 的接收者漏装新入口。

## 可直接复用的原文件与函数

以下路径全部在上述固定 commit，不能换成另一个同名最新版：

1. 完整 quote producer：[`handoffs/M03/source/collector_owner/ops/us_market_digest.py` L479–540](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/ops/us_market_digest.py#L479-L540)，`build_us_market_snapshot`。必须保留公开入口随后执行的 `_clear_same_session_time_dispersion`，不能只抄拆分 body。`ops/_us_market_digest_parts/market_snapshot.py::_build_us_market_snapshot_body` L66–277 是原行情构造体；非 POST_CLOSE 和失败有完整 fail-closed 输出。
2. 原受控 loader/输出根/网络入口：[`handoffs/M03/source/V5/src/v5_shadow/cloud_us_collector.py`](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/V5/src/v5_shadow/cloud_us_collector.py)，`descriptor/verify/load_owner` L11/17/97，`initialize_output/admit_output` L112/121，`main` L130。descriptor PIN 为 `34f45318dd89132a496ac0edf98147455b41d9ea926198d83ce1bd8810c20d8b`，冻结 owner commit 为 `164c010c7eaa1659db9bfed0ff5f123c7a39eefc`。这些原身份及 transport 防护不放宽。
3. 原严格存储 reader：[`handoffs/M03/source/collector_owner/infrastructure/research_peripheral_store.py` L285–287](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/research_peripheral_store.py#L285-L287)，`ResearchPeripheralStore.read_exact`；实际核验体 [`infrastructure/_research_peripheral_store_parts/publish_read.py::_ResearchPeripheralStore_read_exact_body` L143–170](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/_research_peripheral_store_parts/publish_read.py#L143-L170) 核原 payload/receipt/manifest 和完整 envelope。snapshot 与 capture/窗口/late 身份绑定见 [`envelope_validation.py::_b04_validate_market_snapshot_capture_binding` L222–290](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/infrastructure/_research_peripheral_store_parts/envelope_validation.py#L222-L290)。
4. 已有 R14 完整链：[`handoffs/M03/candidate_r14_complete/after/V5/src/v5_shadow/us_source_daily.py`](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/after/V5/src/v5_shadow/us_source_daily.py)：`USSourceRequest` L28、`collector_argv/run_cold_collector` L127/156、`_reader_child_code/read_cold_snapshot` L167/212、`_stable_triplet` L271、`create_binding` L317、`_verify_binding/persist_binding` L345/358、`_copy_snapshot` L378、`run_us_source` L495。复用稳定三件复制、原 reader、物理 SHA、身份重验及 no-replace，而不是旁路自行声明成功。
5. 原格式离线 fixture：[`handoffs/M03/candidate_r14_complete/after/V5/tests/m03_fixture.py`](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/after/V5/tests/m03_fixture.py) 的 `original_script/make_source/offline_collector_script` L16/26/82；[`test_us_source_daily.py` L103–123](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/candidate_r14_complete/after/V5/tests/test_us_source_daily.py#L103-L123) 已有独立 capture-root→原 reader 的测试模式。这里只作为可复用接缝，不把其旧成功数冒充新增路径已测。

**独立行情边界：** 原 [`phase_payload.py` L167–208](https://github.com/lexi2016/v5/blob/3db5bc30a9b5c9ab31f1a123a9b84d047c1a7f4f/handoffs/M03/source/collector_owner/ops/_us_market_digest_parts/phase_payload.py#L167-L208) 先调用 `build_external_finance_payload` 获取 RSS，再调用 `build_us_market_snapshot`。因此仅再次调用旧完整 collector 也不能宣称新 quote-only 独立收盘通道已经实现。需明确复用原完整 quote producer，并说明独立快照怎样合法进入原严格存储/reader/三件产物链；不能用新闻 READY 代替行情，也不能凭空造新闻 envelope 通过原 reader。

## 原 Chat 下次最小完整交付

1. 在本模块原分支交实际可执行的独立收盘采集/物化入口及默认接线，明确请求、授权采集开关、私有根、原 producer/transport 和输出合同。复用上列源码；保留原 owner/PIN/时钟/日历/窗口/late/historical 规则，不新造行情算法或伪造当时可用性。
2. 给出到原严格 reader 与 R14 消费边界的实际调用链。严格区分 READY、NOT_DUE、SOURCE_MISSING、SOURCE_REJECTED/CANNOT_CONFIRM 和执行失败；payload/receipt/manifest SHA 必须对应同一真实生成且冷读通过的快照。原链不能直接承接独立输出时，交出最小兼容接线并验证，不能止于 return dict。
3. 新正例使用原 producer 的离线受控报价输入，实际落盘并另起进程冷读，证明所需行情请求发生、未依赖新闻 READY；至少补四字段假 READY、news-only、错误 session/phase/cutoff、坏/缺原三件与安全字段拒绝。原 fixture/clock/provider seam 仅用于离线测试，不进入默认生产路径。
4. 给完整累积源码和新增窄测试、准确文件清单/SHA、可复现命令与退出值、与候选一致的最小组装/回滚说明。只跑新增及受影响定向验收，不扩大泛审或重复无关模块测试。
5. 真实网络采集、Mac、页面、部署仍分别记录实际状态。未执行继续 NOT_RUN；源码已有但未测和入口尚未实现要分开。不得上传真实输入、私有绝对路径、凭据或被拒材料。

## 本次状态

- **STATIC_CONFIRMED**：实际读取上述固定 GitHub 文件、两次提交差异及同固定 R14/原 owner 合同，确证上述缺口。
- **NOT_RUN**：本次未执行 adapter、测试、collector、reader 子进程、网络请求、Mac、页面或部署。
- 本反馈提交仅新增本 README；原产品源码、测试和历史交付原件全部保留。由原 M03 Chat 继续编码。
