# V5 工作流设计与成熟开源实践比较（证据补件）

日期：2026-10-13

## 范围

本文为架构研究补件，不修改产品代码，不改变18模块、PIT、交易、安全、权限或凭据边界。

证据等级：
- VERIFIED：实际读取的V5源码/官方文档。
- INFERENCE：适配判断。
- TODO：后续验收。

## 外部官方来源（访问：2026-10-13）

### Dagster
官方：
- https://docs.dagster.io/concepts/io-management/io-managers

核验结论：IO manager用于分离业务计算和输入输出存储职责。

### Prefect
官方：
- https://docs.prefect.io/v3/concepts/caching

核验结论：缓存键基于任务输入、代码定义、运行上下文，并要求结果持久化后复用。

### Vite
官方：
- https://vite.dev/config/server-options

核验结论：server.proxy提供开发期前后端路径代理，属于前端运行配置，不是业务接口层。

## 六项比较

|领域|V5当前证据|成熟实践证据|适用性|最小调整|
|-|-|-|-|-|
|模块职责|18模块按owner/reader/publication职责拆分；P0负责接线|Dagster IO manager分离业务计算与存储|适用原则|继续保持模块边界，不引入资产平台|
|独立采集与不可变输入|V5使用run、identity、SHA、cold reader、immutable artifact|Dagster asset materialization强调持久化资产|适用原则|继续补模块输入输出合同|
|幂等|V5使用ledger、CAS、generation、readback|Prefect cache key避免重复执行并复用持久结果|部分适用|保留V5业务identity，不采用通用cache替代|
|调度/失败恢复|P0 daily tick、dispatch、ledger状态；失败不伪成功|Prefect state/cache恢复模型|部分适用|补状态文档，不替换P0 dispatch|
|前后端只读接入|`V5/src/v5_shadow/module_api.py`提供只读API；`frontend/src/views/SavedManagerResultView.vue`读取保存结果|Vite proxy隔离开发请求路径|适用|保持source→saved result→page链路|
|独立打包/配置|Python模块、配置合同、root/release identity|成熟项目分离运行配置与业务代码|适用|补entrypoint和配置说明，不引入平台|

## V5固定源码入口

已核路径：

- `V5/src/v5_shadow/module_api.py`
  - VERIFIED：只读模块API、identity校验、保存结果读取入口。

- `V5/src/v5_shadow/daily_tick.py`
  - VERIFIED：daily lane入口与显式opt-in控制。

- `V5/src/v5_shadow/daily_owner_adapters.py`
  - VERIFIED：owner消费、readback和publication接线。

- `frontend/src/views/SavedManagerResultView.vue`
  - VERIFIED：Vue保存结果展示入口。

- `frontend/vite.config.ts`
  - VERIFIED：Vite运行配置入口。

## 差距与调整结论

### 已可保留

1. immutable artifact + SHA

理由：与资产持久化方向一致，但V5额外要求金融研究场景identity和PIT约束。

2. producer/reader分离

理由：与IO职责分离一致。

3. ledger + CAS + readback

理由：比普通缓存更适合需要审计的研究流程。

### 不采用

1. 不引入Airflow/Dagster/Prefect作为V5调度平台。

理由：V5已有P0 dispatch、ledger和业务窗口合同。

2. 不使用通用cache代替研究结果identity。

理由：缓存命中不等于真实输入、资格和PIT满足。

3. 不重构Vue/Vite体系。

理由：当前只读结果页面已经存在明确source到saved result链路。

## 验收影响

需要继续验证：

- 每模块 source snapshot → owner → immutable save → cold reader → API/page。
- 调度状态与业务状态分离。
- 页面刷新、日期切换不触发重新计算。
- 缺数据保持WAITING/PARTIAL/CANNOT_CONFIRM。

## 不产生代码调整的原因

本补件发现的是架构原则差异，不是已确认产品缺陷。当前最小调整为文档化合同，而不是引入新框架或修改现有运行边界。

## 限定补充：可安装入口、条件重试与结果未知后的恢复

补充日期/官方文档访问日期：**2026-10-13**。本节由后续限定证据核对补充；前文原 P0 在 `6b86e3fa97193fc6a9ffeeefc891813279920b96` 的比较与“不引入大型调度平台”结论保留。下述 V5 源码均实际读取自该固定提交；只做源码/文档比对，未构建安装包、运行测试、操作 Mac 或调用真实来源。新增验收条目均为 **TODO，不计产品完成**。

### A. 打包：已有源码入口，缺的是安装后完整运行证据

**官方依据（VERIFIED）：** PyPA 当前在线规范与指南，页面标示最后更新 2026-10-12；不是特定 setuptools 版本承诺。[pyproject entry points](https://packaging.python.org/en/latest/specifications/pyproject-toml/#entry-points) 规定 `[project.scripts]` 对应安装分发的 console scripts；[命令包装与退出码合同](https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts) 说明包装器调用无参数函数，并传递整数退出码；[build backend、依赖与 Python 版本声明](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) 与业务运行配置分开。

**V5 对照（VERIFIED）：** [V5/pyproject.toml](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/pyproject.toml#L1-L12) 已有 setuptools 构建、v5-shadow 0.1.0、Python ≥3.14、pandas/pyarrow 与 src 包发现，但没有 `[project.scripts]`。[run_shadow.py::main](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/run_shadow.py#L1-L26) 明确是源码包入口；[main_runtime.main](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/main_runtime.py#L75-L89) 已分 validate/start/status/stop/tick/source-bundle；[module_api.main](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/module_api.py#L1109-L1119) 已有只读 API CLI。故不能称“没有启动入口”，也不能仅凭 pyproject 宣称已独立安装验收。

**最小采用（INFERENCE→TODO）：** 在现计划第六节独立交付中固定一种实际交付方式，优先保留已用源码包；若选择安装式 console script，仅薄封现有入口并保留隔离/配置验证，不新增命令框架或绕过原 guard。把 Python/依赖、vendor/contract 等非 src 资源、配置样例与现有 `uv.lock` 纳入同一 release 清单；本次未构建 wheel，不断言其当前是否漏装资源。

**验收：** 在获准的干净 V5 隔离目录，按交付说明从仓库外工作目录启动；无需依赖 V4 活动目录或任意 PYTHONPATH。help/validate/status 不触发 owner；显式 tick 才走原准入。校验实际包文件/版本/资源、退出码、只读 API 与停止/恢复；调度安装或启用仍是独立获准动作。已有 [runtime 入口测试](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/tests/test_p0_runtime_entrypoints.py#L1-L23) 只证明源码中的 callable/status 隔离等测试设计，不代表安装包已实跑。

### B. 重试：借鉴按步骤、有条件、有上限，不新增全局自动重跑

**官方依据（VERIFIED）：** Prefect **v3** 在线文档，页面未给固定补丁版本；不据此推断 V5 安装了 Prefect。[阶段级重试](https://docs.prefect.io/v3/how-to-guides/workflows/retries#retry-parts-of-a-workflow)、[条件判断](https://docs.prefect.io/v3/how-to-guides/workflows/retries#retry-with-a-custom-condition) 和[等待/退避](https://docs.prefect.io/v3/how-to-guides/workflows/retries#retry-with-configurable-delay) 分别控制重试范围、是否允许及延迟。可借鉴原则，不照搬其参数值、异常示例或框架。

**V5 对照（VERIFIED）：** [run_ledger.claim_run](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/run_ledger.py#L82-L96) 已实现总 attempt 默认 2、允许范围 1–3；成功复用，RUNNING/未知不重试，前次必须明确 `retry_safe_without_external_effect=true` 才可再 claim。这里限制的是**总 attempt 数**，不能把外部框架的 retries 次数直接抄进来。[dispatch_due](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/daily_dispatch.py#L20-L79) 每次先验窗口/绑定，单 lane 异常不阻止独立 lane，未设自动重试循环。

**最小采用（INFERENCE→TODO）：** P0 与模块交接只补一份按原 reason code 的“可重试/须恢复核对/不可重试”判定及已有上限，不增加通用重试服务。只对确认未产生外部效果的暂时失败，在原窗口内允许后续调度重试；缺授权、坏身份、业务拒绝和错过窗口不是自动重试理由。如某来源确需退避，先核原 provider/owner 合同，在原 owner 内设置有限延迟并复验 deadline，不统一套指数退避或延长窗口。

**验收：** 复用已有 [test_run_ledger.py](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/tests/test_run_ledger.py#L19-L48) 的成功复用、未知不重试、无外部效果失败到上限、不安全失败阻断、输入变化另记与冷读要求；结合 [test_daily_dispatch.py](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/tests/test_daily_dispatch.py#L22-L54) 的单 lane 隔离、错过窗口/坏绑定不调用，记录真实 owner 调用次数。只补本次改动尚未覆盖的情形；本次未重跑，不重报 PASS。

### C. 恢复：执行终态、业务资格和发布可见性分别判定

**官方依据（VERIFIED）：** Prefect **v3** 的 [state types](https://docs.prefect.io/v3/concepts/states#state-types) 区分 AwaitingRetry、Failed、TimedOut、Crashed 等；[返回值与最终状态](https://docs.prefect.io/v3/concepts/states#final-state-determination) 说明正常返回并不自动证明业务产物满足应用合同。因此这里只借鉴“明确状态及其转换”，不将其 Completed 等同 V5 的正式资格或自然验收。

**V5 对照（VERIFIED）：** [finish_run](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/run_ledger.py#L99-L111) 要求成功具有 product_reference/readback，拒绝 stale claim，并保持 natural_verified=false。[dispatch_due 的异常路径](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/daily_dispatch.py#L72-L79) 保留 RUNNING，返回 OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY；[daily_tick.tick](https://github.com/lexi2016/v5/blob/6b86e3fa97193fc6a9ffeeefc891813279920b96/V5/src/v5_shadow/daily_tick.py#L112-L144) 对 current 更新未知要求只读核 current 与双账本，不重 owner，并保留 MISSED_PLAN_WINDOW_NO_BACKFILL。上述已是应保留的实现；通用 ledger 本文件没有“超时自动解锁重跑”入口。

**最小采用（INFERENCE→TODO）：** 对本轮实际接入的 owner，列明结果未知时该调用哪个原冷 reader、核哪组 run/reference/receipt/current 与账本，以及谁能完成后续受控状态核对。若相应 owner 恢复入口尚未核实，标待核/未闭环，不能直接宣称系统没有或已有通用恢复。即使进程退出，也不据此重试；只读验证可证明已保存时复用原结果，无法确认副作用时继续阻断，不能删除 claim 或伪造无效果标记。

**验收：** 有限故障注入覆盖“owner 已保存但回执丢失”“current/CAS 已提交但响应失败”“真正未执行且已证可重试”三类；新进程独立读回后按原入口恢复，原成功 SHA 保留、不重复 owner、不将旧/未知结果标今日自然成功。执行状态、业务资格/PIT、已保存、已发布、自然触发分别记录；只读页面不承担恢复执行。

**计划影响仅两处：** 在现计划“阻塞处理”补 B/C 的有限恢复证据；在“独立交付”补 A 的安装/入口/资源验证。无新增模块、库或平台要求，无产品代码修改；保留原 owner/reader、SHA、ledger、CAS 和单 writer 边界。
