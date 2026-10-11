# M09 只读适配器：实现与验证记录

本文件记录 M09 模块内的 API 读投影候选及接口请求。共享 API、前端、调度、manifest 和 V4 路径没有在本子任务中改写。共享接口请求是待 owner 集成的增量合同，不能当作已部署结果。

## 1. 固定候选

| 文件（相对 m09_work） | SHA-256 |
| --- | --- |
| after/V5/src/v5_shadow/a_close_daily_api.py | `74c4925c4ba5aa0d973ead806fed57cdf3416db08db0c1124b2e5fcf84003c16` |
| after/V5/tests/test_a_close_daily_api.py | `bfa1476b2f9de7ee2c5733d84a436ddee25784c33e2c90083f64b41ce850e777` |

对外仅有三个 M09 边界：

```python
project_committed_review(committed, requested_date) -> dict
read_a_close_preview(root, requested_date) -> dict
merge_a_close_preview(existing_envelope, preview) -> dict
```

`read_a_close_preview` 只调用一次 `read_a_close_daily(root, T)`。完整结果直接使用 reader 已钉住并验读的 generation 与其身份；不再次读取 head。仅当 reader 返回 None，才查询同根同日的 `read_a_close_latest_attempt(root, T)`，为 MISSING 对象补充独立尝试说明。主读取异常给出 CANNOT_CONFIRM；尝试元数据读取异常保留 MISSING，并增加 `M09_LATEST_ATTEMPT_READ_FAILED`。两条路径均不写文件，不调用 producer、采集、调度、发布、修复或重试。

## 2. 保留与校验

有效投影深拷贝完整原生 review，原 model、顺序、角色、情景权重、as_of、来源、视频未消费和研究限制保持原值。原产品没有顶层 status 时，增加 record.business_status；增加 COMPACT_NATIVE 表面选择，避免现有 UI 的 rich 分支遮蔽原生模型。

校验覆盖 T、model run、record/generation schema 与规范 JSON 摘要链，以及 source_sha256 的独立含义。原 store 必须记录精确 T 的 review、receipt 和 manifest 三个路径；各项 raw SHA 格式和正整数 bytes 合法。`identity.raw_review_sha256` 必须等于 record.store_files 中该 T review 的 raw SHA。适配器不重新编码原始文件来猜测 raw SHA；原字节实际校验属于底层 reader。

原生 close_chain 必须存在，schema、10 个任务的顺序、每个节点的业务日及三个 false 安全标志均须符合冻结合同。原生模型 READY、确定性 Python、禁用语义调用、零调用/视频证据计数、研究限制与模型推广/泛化/学习状态保持冻结值；模型 READY 不升级业务或链状态。

`m09_publication` 使用 `v5.m09.read_evidence.v1`，明确区分 source、canonical review、raw review、record、generation 五类摘要。它保留 record 的 data_kind、execution_kind、computed_at、membership、provenance、evidence_status、scope 及记录层 cannot_confirm。REAL 可对应 DAILY_RESEARCH 或 HISTORICAL_REPLAY；SYNTHETIC 只对应 ENGINEERING；RECORDED_INPUT_REPLAY 只对应 HISTORICAL_REPLAY。VERIFIED 只表示本次读回合同通过，不能证明完整业务、全市场集合、自然触发、来源独立证明或严格 15:00 PIT。

最新尝试的 `latest_attempt`/`latest_attempt_status` 与原记录独立。后来 FAILED/UNKNOWN 的尝试可以对应不同的 run；不会覆盖被服务成功的 model、identity、computed_at、business_status 或 read_status。没有可用尝试时两个字段为 null。可选 `publication_recovery` 同样独立深拷贝；对经核同日 predecessor 的实际选择和证明由 reader 负责，适配器不推断、不改 head。

## 3. A-only 合并边界

| 允许改变的键 | 行为 |
| --- | --- |
| market_reviews.A | 替换为精确 T 的 M09 投影 |
| 已存在 fupan_review_v3 | 与当前 A 的原生兼容别名对齐 |
| review_core_bundle | 移除已通过活动源码证明为 A-owned 的旧归属 |
| review_evidence_layers | 移除已通过活动源码证明为 A-owned 的旧归属 |
| m09_publication | 当前 A 元数据的独立深拷贝 |

HK 子树、research_review、intraday_research、reference_snapshot、全局安全标志以及未知或混合市场字段深度相等。测试同时检查输入不被修改和输出不共享可变对象。不能把上述针对已查明 A-owned 字段的处理推广到其他未知 evidence。

## 4. 实际执行证据

最后一次针对适配器的命令：

```text
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m unittest discover -s tests -p test_a_close_daily_api.py -v
```

工作目录为 `m09_work/after/V5`，环境为 `PYTHONPATH=m09_work/after/V5/src` 的绝对路径及 `PYTHONDONTWRITEBYTECODE=1`。真实执行器为 Python 3.12.14 / Linux。候选 pyproject 声明 Python >=3.14；本结果是当前工程环境的行为证据，不是支持环境或 Mac 兼容性证明。没有安装依赖或放宽声明。

**2026-10-11 10:48:10.745558 UTC 至 10:48:11.039316 UTC：33 tests，全部通过，exit code 0，无 errors、failures 或 skips。** 这批 fixture 全部用于工程合同测试；将 record 分类改为 REAL/HISTORICAL_REPLAY 的测试仅验证合法分类配对，不是运行真实数据或自然槽的证据。

| 最后一轮证据文件 | 内容 |
| --- | --- |
| logs/adapter_missing_attempt_recovery_red.metadata.json | 修改前 RED，33 tests，3 个预期断言失败，真实 child exit code 1 |
| logs/adapter_missing_attempt_recovery_red.stderr.log | 首次失败的完整输出 |
| logs/adapter_missing_attempt_recovery_green.metadata.json | 当前固定 source/test SHA、命令、环境、UTC/上海时间及日志摘要 |
| logs/adapter_missing_attempt_recovery_green.stderr.log | 33 tests 通过；SHA `ef38c47d3e98cb453a1354dbaf8a3100fa097c9d46d6c3b0629846677c65cc96` |

此前的 adapter_red、identity、limits、native_contract、latest_attempt、raw_identity 各轮真实 RED/GREEN 日志保留，未覆盖失败输出。`adapter_limits_red` 首轮测试还含两个测试断言 KeyError，后续 `adapter_limits_assertion_red` 修正了断言并保留三个真实功能失败。`adapter_assembled_suite` 是 core 尚未出现时的中间组合尝试，含 30 个 core 缺模块失败，不能作为最终整套回归结论。主任务在 core 固定后另行执行最终组合与实际 reader 集成验证，本文件仅主张上述适配器测试。

## 5. 共享 owner 请求

| 请求 | 必要变更 |
| --- | --- |
| M09-IR-001-READ_COMPOSITION.md | 在旧 strict/legacy A 分支之前选择可信 a_close_reader；绕过旧 A evidence reread；精确 T、只读、HK 保留 |
| M09-IR-002-REVIEW_UI.md | 保留原生面板，增补固定情景权重、分层缺口、分类/来源/摘要及独立尝试/恢复说明 |
| M09-IR-003-PUBLICATION_AND_DISPATCH.md | 说明 M09 与共享 transport schema 的区别；由 owner 扩展真实 lane/calendar/binding；两个槽独立回执与可审查回滚 |

三份请求包含具体 before SHA、函数边界、类型/调用草案、共享 owner 测试及回滚要求。16 个附件源文件的 raw SHA、字节数和按字节计算的 Git blob SHA1 已再次逐一复算，全部吻合 `M09_INTERFACE_BEFORE_IMAGES.json`。这里证明的是附件与固定源前像；活动 Mac 源 commit 仍为 UNKNOWN，不能将用户提供的 V5 handoff commit 冒充活动 Mac commit。

共享源集成、前端构建/组件渲染、实际 Mac API/浏览器、自然运行、V4 现场前后比较、部署和现场回滚均 **NOT_RUN**。本子任务未操作这些现场能力；接口请求中的共享测试状态继续保留 NOT_RUN。
