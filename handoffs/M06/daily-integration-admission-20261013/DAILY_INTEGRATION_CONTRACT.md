# M06 daily 接线补件（仅文档，2026-10-13）

## 固定对象与结论

- M06 完整候选：`08ed9de9ddb5fd2c62eb1762df2f6106464d823b`，源码根 `handoffs/M06/source/`。
- 本次核查的 P0 已部署产品：`287de959ac160f6ae2792ca1f9684b4c86750012`。本文不把该历史固定版本等同于未来分支 HEAD。
- 原独立 Mac 存量池成功证据：`7006c6ab6e2b4f1f9f6a00da0b3b490dcd4d4fd8` 的 `handoffs/M06/feedback/mac-08ed9de9-real-admission-20261013/verification.json` 与 `committed-reference.json`。
- target=`20261013`，signal/eligibility=`20261012`；已有 ledger run=`f745c78857d54fa89849f2adbfa3602f`。`EXISTING_VERIFIED_POOL` 已成功，不重复执行。该成功不是冻结模型重算成功，也不是自动调度证明。
- 模型文件/PIN 与原输入确实存在。18 个输入/资产身份见 `report.json`；仅上传相对路径、大小与 SHA256，不上传内容。

## 当前 P0 实际缺口

以下均按 P0 固定版本核查，不能用注册表或页面替代真实接线：

| 源码相对路径 / 函数 | 当前行为 / 缺口 |
| --- | --- |
| `V5/src/v5_shadow/main_registry.py` | `M06_HK_PRESELECTION` 文本登记 READY，指向 `daily_owner_adapters`；并不创建运行 binding。 |
| `V5/src/v5_shadow/daily_tick.py::tick(config)` | 从 `bundle_root/{today}.json` 读显式 jobs；普通 bindings 仅 us_mapping/announcement/rebound，另有 M17 特例。无 M06 owner_request 解析、日期/资产绑定或 adapter。未知 lane 被拒绝。 |
| `V5/src/v5_shadow/daily_tick.py::default_slots(target)` | 普通槽为 08:00–08:45、research_cutoff=08:00（HK）；这是未核为 V4 原时段的新 V5 默认值，不能直接当 M06 原生成时段。 |
| `V5/src/v5_shadow/daily_dispatch.py::dispatch_due(schedule, bindings, ledger_root)` | `LANES` 仅 announcement/us_mapping/rebound/manager_close_recapture。M06 尚不准入，且未建立 callable binding。 |
| `V5/src/v5_shadow/daily_owner_adapters.py` | 无调用 M06 `produce_hk02_daily` 的 adapter、无独立 reader 成功转换。 |
| `V5/src/v5_shadow/run_ledger.py` | 接受 `hk_preselection` lane 只表示 ledger schema 允许，不能证明 tick/dispatch 已接。 |
| `V5/src/v5_shadow/m06_readonly.py::read_record(config, query)` / `m06_readonly_worker.py` | 仅投影固定 committed reference；GET `/api/v5/source-bundle/hk-preselection` 无生成/调度意义。 |

`dispatch_due` 现有普通 job 合同包含 `lane`, `identity`, `scheduled_at`, `deadline`, `half_day_bound`, `max_attempts`, `owner_request`。identity 七字段为 lane/target_date/input_sha256/research_cutoff/code_sha256/config_sha256/dependency_sha256。binding 需相同 code/config/dependency 摘要和 `invoke(owner_request, ledger_run_id)` callable；owner_request 的 canonical JSON SHA 必须等于 input_sha256。普通 lane 要求本日目标、已核交易日/半日条件、`scheduled_at <= now < deadline`、`research_cutoff <= now`。调用前 claim，调用后将 receipt 交 finish_run；未知结果保留 RUNNING，不自动重试。

因此接线不只是向 LANES 添加名字。M06 自身已经管理私有 `.m06-ledger`、claim、exact committed readback 与 finish。P0/M06 原 Chat 必须明确两层 ledger 身份和 run 映射，避免双重 claim、把 publication identity 当 ledger UUID、或把 M06 完整返回字典未经转换当通用 receipt。错误/未知结果及幂等读回必须保留。

## M06 公开原入口及签名

固定文件：`handoffs/M06/source/V5/src/v5_shadow/hk_preselection_daily.py`。

```python
from v5_shadow.hk_preselection_daily import produce_hk02_daily

produce_hk02_daily(
    *, store_root, asset_root, private_root,
    signal_date, target_date, eligibility_source_date,
    cutoff, files, execution_mode='MANUAL_RECOVERY'
)
```

这是公开 Python callable，不是已接 P0 的 CLI。文件 `__main__` 仅接受内部 `--worker/--calendar/--assets`；不要把内部 worker 当成跳过 parent admission 的生产入口。

- `store_root`：显式原输入快照根；`asset_root`：冻结 panel/model/name 闭包根；`private_root`：独立输出根，必须已有精确 `.v5-shadow-root` 标记，且与输入/资产不重叠、无 symlink 祖先。
- `files`：asset_root 内相对路径到原字节 SHA256 的完整映射；包括存在的可选 names pointer/manifest/receipt/字典，不能静默省略。
- 日期是 YYYYMMDD；signal 必须为 target 的原 HK securities 前交易日，eligibility 不晚于 target。cutoff 必须带时区、HK 日期等于 target；calendar、原 source/master、代码与运行依赖都需严格验收。
- mode 仅 `NATURAL`, `MANUAL_RECOVERY`, `RECORDED_INPUT_REPLAY`。NATURAL 只是触发标签，不提升 natural_verified。
- 成功返回 `status='SUCCEEDED'`, `reused`, `computation_identity`, `ledger_run_id`, `committed_reference`, `producer_receipt`, `row_count`, `trigger_receipt` 与安全字段。公开独立读回为 `hk_preselection_publication.read_verified_hk_preselection_reference(bound_root, reference)`。成功不能只看退出码或 UI 100 行。

## 两分支的精确选择

`produce_hk02_daily` 检查输入 `latest.json` 中是否存在 `target_date + '/HK_CONNECT_D1_TOP100_0_2'`：

1. 存在：先走原严格 consumer；损坏/错日/身份不符直接拒绝，不降级成 missing。NATURAL/MANUAL_RECOVERY 仍验证冻结资产并比对该池原 panel/model provenance。producer receipt 为 `EXISTING_VERIFIED_POOL`、`model_weights_reverified=false`；只对显式 RECORDED_INPUT_REPLAY 允许无资产的 recorded-only 消费。
2. 真正不存在：只复制已声明 master/source 与冻结资产到任务 staging，满足运行时和时间门槛后才调用原 `materialize_frozen_hk_0_2`。成功生成 receipt 才标 `FROZEN_MODEL_PRODUCER` 和 producer model_weights_reverified=true；随后仍须严格 consumer、原行一致、不可变发布、独立读回。consumer 的 model_weights_reverified=false 继续保留，不与 producer 字段混同。
3. 同一七字段 identity 已 SUCCEEDED：走原 exact reference 读回并复用，不重算；RUNNING/未知或不可 retry 状态不得自行清除/重试。

## 已有资产，不缺模型下载

模型相对路径 `model/20260716/models.joblib`；原 PIN `3b0d5d5239342439cabf25b30012365a64d78839bc3cd4d90bad7be6ff4aaa07`；原 manifest 为 155 特征、extra_trees/hgb_depth6/logit/random_forest 四键，trained_through=20260716。panel SHA 为 `f556891592618f32c6aa57d3d439663d2bebcabc2aae7ba559c82d3a9586154d`，through date=20261012。匹配既有 HK02 运行时证据：Python 3.13.12、scikit-learn 1.9.0、joblib 1.5.3，已有 pyarrow 23.0.1；无须安装。源码/输入 hash 存在不等于 joblib 已加载、155 特征计算成功或 >=500 eligible signal-date symbols 已核，本次不执行这些动作。

## 旧 cutoff 与新生成的具体准入要求

旧请求 cutoff=`2026-10-12T17:11:34.690550+00:00`（HK 2026-10-13 01:11:34.690550），固定成功时间为 17:12:06–17:12:11 UTC。它只约束此前已发布的原池输入；复用并不要求新 publication 捕获时间。`_producer_worker` 第172行则明确在 `now > research_cutoff` 时拒绝 `HK_SOURCE_AFTER_CUTOFF`；严格原 consumer 同样拒绝原池 captured/finished 晚于 cutoff。故旧请求不可复用作新生成请求，且只把 cutoff 改为调用开始的 now，worker 随后启动也会超过它。

独立重新生成需新合法请求、独立输入快照/输出身份，以及 target HK 当日实际未来完成 deadline/cutoff，覆盖真实模型计算与原发布耗时；不得改旧时间、回填 captured_at、删除现役池，或伪称旧池不存在。若目标是对已有池独立重算校验，应先明确该验证模式及隔离存储合同，而不是隐藏 force 行为。

**接线必须处理时间合同差异**：现 P0 普通 dispatcher 禁止未来 `identity.research_cutoff`，而 M06 generator 要求执行不晚于 owner_request 的 cutoff。不能把未来 owner cutoff 原封不动映射到普通 dispatch identity 后称可运行，也不能为接 M06 放宽所有 lane。原 P0/M06 Chat 应明确区分调度时已观测的 admission identity/cutoff 与 M06 实际完成 deadline、精确输入及 publication cutoff；说明它们的哈希/run 映射并交独立有界 adapter 候选及针对性验证。本文不预先声称该实现已存在。

## 交付范围和不可冒称

本补件仅供原 P0/M06 Chat 实施 daily 接线：保留现有成功 reference、原模型/规则/PIN/安全标记，给出完整显式绑定、异常/重复/截止/读回合同与独立候选。不得让旧100行页面、READY 文本或存量复用继续冒称自动调度、模型重算或 natural_verified。

当前尚未执行模型重算。本轮不调用 provider/owner、不重测、不部署、不修改调度或运行代码。上传内容只有本文、先前核查结论和脱敏摘要；不含模型二进制、原业务数据、私人绝对路径、解释器路径、凭据或配置秘密。
