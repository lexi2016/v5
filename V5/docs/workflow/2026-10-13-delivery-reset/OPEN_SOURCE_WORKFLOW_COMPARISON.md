# V5 工作流设计与成熟开源实践比较

日期：2026-10-13

## 目的与边界

本文只做架构研究与执行方案补充，不修改产品代码、不改变18模块目标、不改变PIT、交易、权限或凭据边界。

基线：`PROJECT_EXECUTION_PLAN.md`（d9a484600f1db7acffbb5790d59e1e206f0cc01b）。当前计划要求保留18模块职责边界、P0-P5迁移路线，并优先完成 M13/M14/M15→M18 普通页面闭环。

## 外部案例选择

选择与V5约束最接近的三个方向：

1. Apache Airflow
   - 官方文档：https://airflow.apache.org/docs/
   - 关注点：DAG调度、任务状态、重试、依赖编排。

2. Dagster
   - 官方文档：https://docs.dagster.io/
   - 关注点：软件定义资产、输入输出管理、可观察性。

3. Prefect
   - 官方文档：https://docs.prefect.io/
   - 关注点：任务状态、缓存、幂等恢复。

## 核心比较

|领域|V5当前设计|成熟实践|适用性|最小调整建议|
|-|-|-|-|-|
|模块职责|18模块按业务职责拆分，兼容层连接原owner/reader|Dagster强调资产边界和依赖声明|高|继续保持模块边界，不引入新平台|
|不可变输入|run、identity、SHA、cold reader、保存产物|Dagster asset materialization强调持久资产；IO manager负责保存和加载|高|统一记录输入快照、产物引用，不改算法|
|调度|P0 daily tick/dispatch，显式opt-in|Airflow通过DAG定义任务依赖和调度|中高|补充调度合同文档，不改现有dispatch语义|
|重试恢复|ledger、CAS、readback、失败保留|Prefect cache/state机制强调持久结果和幂等恢复|高|继续强化run identity和幂等键|
|页面接入|API只读读取保存结果|Dagster UI围绕资产状态展示|中|继续source→saved result链路|
|配置隔离|模块配置、root、release identity|Airflow connections/config分离实践|中|保持现有配置合同，不引入全局配置中心|

## 详细差距表

|V5证据|成熟实践|适用结论|调整|验收影响|
|-|-|-|-|-|
|`module_api.py`提供只读读取、身份校验、页面接口|Dagster IO manager分离存储读取职责|方向一致|不改接口，仅补文档化合同|页面必须验证SHA/run|
|M18使用descriptor、bundle、reader|Dagster asset materialization|高度适配|保持immutable artifact模式|禁止页面触发计算|
|P0 ledger记录run状态|Prefect cache key/state思想|部分适配|明确哪些状态可重用、哪些必须重新执行|避免重复owner执行|
|daily dispatch显式lane|Airflow DAG依赖|部分适配|增加lane依赖说明|不改现有lane|
|18模块独立owner/reader|Dagster asset graph|适配|维护模块职责图|避免平台化重构|

## 已可保留设计

1. 不可变产物 + SHA引用：符合成熟数据编排方向。
2. reader与producer分离：符合资产读取/生成分离原则。
3. 显式状态：READY、PARTIAL、CANNOT_CONFIRM优于隐藏失败。
4. 独立模块合同：比重做统一大框架风险更低。

## 不采用的实践

1. 不引入新的调度平台。
   - 原因：V5已有P0 dispatch/ledger合同，替换会扩大范围。

2. 不把18模块改造成单一资产图平台。
   - 原因：会破坏已有owner、reader和验证边界。

3. 不把缓存结果当业务成功。
   - 原因：V5要求真实输入、PIT、资格和readback验证。

## 实施建议（非代码变更）

优先补齐：

1. 每模块固定输入/输出/identity说明。
2. 调度lane依赖和失败恢复说明。
3. source→saved result→page验收清单。
4. 运行状态与业务状态分离。

不建议：

- 新建通用工作流平台。
- 替换现有算法。
- 改写PIT窗口。
- 放宽失败状态。

## 证据等级

已核：V5执行计划、GitHub源码路径、公开官方文档。

推断：成熟实践对V5架构方向的启发。

待核：不同模块实际生产窗口、数据源稳定性、完整18模块终验。
