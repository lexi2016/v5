# M07 调度端接续源码候选（2026-10-13）

## 结论与口径

本次是调度端基于固定原件接续实现，不是原 Chat 返回，也不是 Mac 部署验收。
原分支 `dev/m07-github-handoff-20261011` 的基线为 `0358c532ecf51c0c00c65f1e2c4493ffcbd1d7d0`。
旧 `SOURCE_BASELINE.json` 保留原样，继续说明其记录的旧 R4 状态；本候选以 `DELIVERY.json`、`OWNER_CLOSURE.json` 和本说明为准。

本候选已实现可执行的原 owner 链：M05 物理池快照准入 → M01 原 RawStore 验证 → M04 原 ResearchContext/HourlyResearchStore/晨报 reader → 原 A live 或独立 auction selector → 原 SelectionStore 私有发布 → 新进程独立读回 → 原 run_ledger。
没有 selector 或 publisher 回调，没有用测试桩冒充原算法。

`SUCCEEDED` 只表示这次回放的私有产物已保存并独立读回。所有输出始终 `natural_verified=false`、`formal_eligibility_verified=false`、`production_allowed=false`、`buy_gate_updated=false`、`orders_sent=false`。
正式资格没有接入，原 envelope 保留 `source_status=CANNOT_CONFIRM`；有行时原 owner 映射为 `selection_status=PARTIAL_WITH_ROWS`，并携带 `FORMAL_OVERLAY_CANNOT_CONFIRM`。这是原合同，不能写成 READY、真实数据通过、自然接续通过或模块完整完成。

## 原件与最小改动

- `a_stage_daily.py`：替换被拒 R4，新增具体准入、独立进程、原 owner 调用、发布/读回/回滚和账本接线。
- `test_a_stage_daily.py`、`m07_fixture.py`：全合成新输入，原 owner 发布或验证真实三元组；包含算法字段/排序/Top10等价及拒绝用例。
- `daily_ledger_fixture.py`：补齐旧账本测试缺失的夹具，逐字取自 V5 `acf8d23f9c191e4cb2da5737ca715002e83648c2`。
- `owner/` 与 `OWNER_CLOSURE.json`：97 个自包含依赖文件，约 1 MB。运行时不访问 V4 仓库、V4 工程或全局 Python 的同名业务模块。普通/HK 共享 vendor 和 manifest 未修改。
- 原 `run_ledger.py`、`stage_selection.py`、原两套测试、其余共享文件均逐字保留。没有改 P0、M08/M09、页面、gateway、调度或系统设置。

主要 donor 固定于 V4 `d1bf034640ca2e5957423de2745a98e159b69af2` 的 `handoff/v4-running-source-20261005/canonical/`。每文件原 repo/commit/path/Git blob/原SHA256/候选SHA256均在闭包清单。
该 canonical 树漏带多个拆分包的 `_namespace.py`；这些位置均采用原 M07 baseline 中同一已冻结 helper 字节，清单明确记载实际来源，没有捏造 canonical 原路径。

唯一 donor 修改为 `stage_center/_raw_store_parts/receipt_identity.py` 的 M07 私有接口兼容补丁：原 facade 传 `allow_temporal_false_observation`，原 body 不接受，实跑产生 TypeError。M01 固定 `02cefc41aadb4358cb8485b71858ae5d6b903a56` 无该文件或修复。经统一集成者授权，body 新增默认 False 参数；任何 True、None、0、1 均显式拒绝，默认/显式 False 仍保留原逐行 temporal=true 验证。没有开放 HK after-fact 或 temporal=false。原 SHA、新 SHA、红绿证据和 unified diff 都已保存。

## 入口矩阵

| 阶段 | 固定 A 窗口 | 原计算入口 | 当前状态 |
|---|---|---|---|
| STAGE_0925 | 09:20–09:25；cutoff 09:25:05 | select_a_0925_auction | 独立原算法、价量/昨收准入，合成回放已测；Mac活动绑定未核 |
| STAGE_0930_0935 | 09:30–09:35 | select_a_live_stage | 真实原reader/selector/store链，合成已测 |
| STAGE_0935_0940 | 09:35–09:40 | select_a_live_stage | 使用原stage合同；活动录制未核 |
| STAGE_0940_0945 | 09:40–09:45 | select_a_live_stage | 同上 |
| STAGE_0945_1030 | 09:45–10:30 | select_a_live_stage | 同上 |
| STAGE_1300_1315 | 13:00–13:15 | select_a_live_stage | 同上 |
| STAGE_1445_1500 | 14:45–15:00 | select_a_live_stage | A原尾盘窗口合成已测 |
| STAGE_1545_1555 | 仅HK | 不调用A | 明确拒绝 |

cutoff 以冻结 `stage_center/contracts.py` 为准；外层请求用带时区完整时间，原 RawStore receipt 的 cutoff_at 保留原 HH:MM:SS 字符串。RawStore 行时钟保留原 `YYYY-MM-DD HH:MM:SS`（Asia/Shanghai），不能用录制时间覆盖行情时钟。竞价价格、昨收、量额和盘口从已核 raw trio 带入独立原入口，成交额不作为推荐score。

## 输入合同

Python：`run_a_stage_daily(request, output_root=...)`。
CLI：`python src/v5_shadow/a_stage_daily.py --run`，stdin为 `{ "request": ..., "output_root": "绝对私有目录" }`。
具体可执行的合成样例由 `tests/m07_fixture.py::make_case` 生成；它只是测试输入生产器，不能标注真实行情。

request 固定字段：

- schema_version=`v5.m07_daily_request.v1`，target_date=`YYYYMMDD`，stage_id，cutoff=完整带时区时间
- data_kind 仅 SYNTHETIC 或 RECORDED_INPUT_REPLAY；trigger 仅 RECORDED_INPUT_REPLAY 或 MANUAL_RECOVERY；natural必须false
- pool_source_dates：原六个A池各自预期signal_date。该绑定必须由已有M05合同和真实工件核定，不能为迁就旧数据改日期
- inputs：pool/live/research/morning各有绝对root及精确相对文件名→原字节SHA256的files映射
- recording：原M01 run_id、artifact/manifest/receipt SHA、真实 captured_at、acquired_at；时钟必须窗内且不在未来
- expected_generation：首次为空；替换当前同一A槽必须给当前已核generation。相同请求成功重试复用，不重算

四个输入root都必须是独立V5副本，已有 `.v5-m07-input`，内容 `v5.m07-input-copy.v1\n`。入口只读取这些原字节，再复制到临时私有快照；原 owner 的锁/恢复只发生在副本。原输入字节在读取后不变。不能在 V4 活动根创建标记，也不能把 V4 根当副本。

pool为原六池 artifact/manifest/receipt；使用原 strict snapshot 聚合，不从展示行授予成员资格。原aggregate只有至少一个验证合格的非空贡献池才ready，全合法空仍保持原 `A_POOL_AGGREGATE_NO_VALID_ROWS` 阻断，不伪装阶段成功空。缺码与requested count精确核对；READY却缺码拒绝。已有部分行情可保留行及缺码诊断，不提升为READY。

research为原小时manifest/receipt/archive及其绑定source witness；morning为原晨报manifest/receipt/payload/latest。原reader按精确日期及实际source时间选择不晚于截止的slot。缺news/research必需分数保持None并阻断selector，绝不补0。原M04固定18篇历史article archive不是这一分数合同，不能作为替代。

SHA和原owner验证证明已声明工件的完整性与内部绑定，不能独自证明外部采集事实、Mac活动路由或自然运行；本候选不声称这些资格。真实录制缺失必须补上游原工件或保持阻断，不能用当前数据补历史。

## 存储、读取、重试与回滚

output_root须是已有独立空/私有目录，标记 `.v5-m07-output`=`v5.m07-private-output.v1\n`；`ledger/.v5-daily-run-ledger`保留原标记。

- 原run_ledger identity严格保持原七字段、lane=`a_stage`。阶段、截止、输入、配置、代码和闭包身份均入摘要
- 每个identity有独立 `generations/<identity_sha256>`，其中由原SelectionStore创建原CSV/manifest/receipt/latest
- 新进程用原reader核同run和三种SHA之后，才通过expected-generation/CAS更新本模块current.json
- 原账本不修改：中断RUNNING/未知结果不自动重试。保存前明确失败BLOCKED；可能已写出的异常保持OUTCOME_UNKNOWN，需核原产物后处理
- `read_a_stage_daily(root,date,stage)` / `--read`只读已提交结果，不claim、不采集、不恢复、不写文件
- `activate_a_stage_generation(root,reference,expected_generation=...)` / `--activate`仅激活或回滚一个已独立验证的A槽；旧generation完整保留，须精确CAS。无任意路径或另一市场路由参数

Python审计边界拒绝网络/子进程及私有目录外写入；这里只宣称 `PYTHON_GUARDS_ONLY_OS_UNVERIFIED`，不是OS隔离认证。Mac需额外核实际进程与root。云端测试不证明Mac文件系统/进程行为。

## 等价和本轮证据

- 对同一准入数组直接调用固定原selector，与M07返回artifact逐字段比较；普通与竞价都有正控。原selection、a_live、a_auction、research_context、publication和verification算法字节未改
- 保留原A代码格式与batch acquisition rank；同分稳定排序、Top10、scores、reason/card、source_status和缺码均按原owner。包装增加的差异限于输入/代码身份、V5私有存储路径、回放标志和明确formal阻断
- 一次初测错误地预期有行时selection_status=CANNOT_CONFIRM；按原 `selection_envelope.py` 更正为PARTIAL_WITH_ROWS，source_status仍CANNOT_CONFIRM。没有改owner或掩盖产品不足
- 实际命令/版本/结果在 `delivery/TEST_REPORT.json` 与 `delivery/final-full-suite.log`。原R4两测试确实因缺publisher参数失败，原账本测试缺fixture；均保留初测事实
- 本轮均是新合成输入，无真实市场正控、无旧98PASS拼接、无Mac执行、无原UI/API验收、无自然两个交易日证据

## Mac最小落地与回滚顺序（本轮未执行）

1. 只读登记Mac当前repo/分支/HEAD、dirty文件、实际Python、活动worker/root/端口/generation。不要假定GitHub HEAD就是Mac前像。
2. fetch原分支后，以本次已确认固定commit新建隔离worktree或目录；不要覆盖活动V4/V5、不要reset hard、不要安装/升级依赖。完整使用 `handoffs/M07/`，owner相对位置不能拆散。
3. 在隔离目录执行 `cd handoffs/M07/V5`；用已存在的合适Python运行 `PYTHONPATH=src "$V5_PYTHON" -m pytest -q`。若pytest或声明的Python>=3.14不满足，登记环境缺口，不静默换生产解释器。云验证用现有Python3.12，不能当作Mac3.14独验。
4. 逐项核DELIVERY和OWNER_CLOSURE文件SHA。原共享ledger、stage wrapper前像必须与本次固定清单匹配。漂移即停止，给精确diff。
5. 独立创建M07输出root及标记、ledger标记。先仅合成演练；真实输入从已核M05/M01/M04工件另复制，登记原SHA/日期/录制时钟/源root，不修改原字节。将准确request-envelope保存在私有目录。
6. `PYTHONPATH=src "$V5_PYTHON" src/v5_shadow/a_stage_daily.py --run < request-envelope.json > result.json`。逐命令保存exit/完整输出/开始结束。JSON BLOCKED或UNKNOWN不等于业务成功；即使SUCCEEDED仍须检查原selection状态和formal/natural flags。
7. 用另一次 `--read` 读同date/stage，核generation/run/artifact/manifest/receipt SHA。再由统一集成者单写普通API/原页面的只读绑定，M09读同一reference；GET不得调用--run。活动路由未核前不要猜端口或切换生产。
8. 验证失败，仅用经核旧reference和当前generation通过`--activate`回滚该A槽，再独立读回。另一市场/原V4字节、原API保持可读。旧日期需如实显示。

## 交统一集成者的接口请求

请求ID M07_READONLY_BINDING_20261013；只涉及现有模块owner读取接线，不新增服务器/调度器/模块。

- 原 `module_api.py` 基线Git blob `3fdea5f256b2dc70df141a0e70dbbc1396abb859`；`api_gateway.py` blob `c5677fb59a4847a24f16a12d5412fce293168fc0`；`daily_dispatch.py` blob `f5d45abea6a159f01756decb23049b825cd0f906` 均未改
- 读接口：调用read_a_stage_daily(私有root,target_date,stage_id)，按原页面route的已核schema做只读适配；保留generation/run/SHA和原partial/cannot_confirm，不制造READY
- 执行接口：仅在原活动窗口/录制和来源身份全部核实后绑定run_a_stage_daily，输入request如上。当前不授权natural=true；自然调度未接入
- 发布顺序：独立候选测试→真实源原owner验证→独立发布读回→原API只读→原页面→另一市场/回滚验证→自然证据
- M09引用同一已核reference；不自行改M09源码。以上接线需统一集成者在其共享固定基线上实施，本候选没有偷偷接入P0

## 五层验收

1. 代码候选：固定源码/完整闭包/合成全套测试可复核；等待Mac独验与真实输入逐字段对照
2. 真实数据：NOT_RUN；正式资格：BLOCKED
3. 原API/页面：NOT_RUN
4. 自然自动接续：NOT_RUN，候选强制natural=false
5. 模块完整验收：NOT_COMPLETE
