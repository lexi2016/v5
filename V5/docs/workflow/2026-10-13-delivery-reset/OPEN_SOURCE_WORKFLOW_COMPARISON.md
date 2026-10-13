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

