# V5 P0 主框架与模块集成任务书

交付对象：独立 Chat「V5 P0｜主框架与模块集成」  
日期：2026-10-12  
任务性质：执行原 V5 总计划的 P0 集成，接入已交付模块。平台能力不新增业务编号，不设 M19。

## 1 要交付什么

请直接完成可运行的完整代码、配置、测试和运行说明，把现有 V5 后端、模块、每日入口与普通主页面装成一套系统。沿用现有算法、owner、账本和发布机制；优先贯通公告 M13、超跌 M14、美股映射 M15 到经理 M18 的真实业务链，再按注册表接入其余模块。

用户要的是可每日运行、能在普通页面看到当日结果、可独立升级和回滚的 V5。只交首页、状态卡、接口示例、伪代码、TODO 或若干独立 helper，不满足交付要求。未就绪模块必须明确显示 NOT_READY 及具体缺口；这使底座可以先运行，但不等于该模块或整个 V5 已完成。

分工按本轮约定执行：本 Chat 是本任务唯一代码作者，完成代码与自查后交固定 GitHub commit；嘻嘻负责调度和汇总；现有 Mac 任务直接对固定版本集成、测试和部署。发现问题形成可复现反馈，通过 GitHub 和本 Chat 返修同一候选，不增加重复源码二审，不让两个作者同时改同一文件。

## 2 固定源码入口

### 本次集成基线

- 私有仓库：`lexi2016/v5`
- 开发分支：`dev/v5-main-integration-20261012`
- 固定 source commit：`d5f11b1dd070d49a8760aa603f9c0a00eea908cf`
- 固定 source tree：`4217c5c52acf054a963961ee65d1d290a33f20eb`
- 先读 [START_HERE.md](https://github.com/lexi2016/v5/blob/d5f11b1dd070d49a8760aa603f9c0a00eea908cf/START_HERE.md) 和 [SOURCE_MANIFEST.json](https://github.com/lexi2016/v5/blob/d5f11b1dd070d49a8760aa603f9c0a00eea908cf/SOURCE_MANIFEST.json)，再读 [V5 源码](https://github.com/lexi2016/v5/tree/d5f11b1dd070d49a8760aa603f9c0a00eea908cf/V5)。P0 辅助材料在仓库根的 `integration_tests/`、`saved_product_readback.py`、`schedule-binding.json`。
- 本次实际发布 711 件源码/工程材料，加 2 件说明清单和继承 README 共 714 文件；分支/tree 已核，属于机械装配，产品及测试 **NOT_RUN**。688 件原底座源码保留后叠加 42 次选定映射；具体 donor/blob/bytes 以 manifest 为准。
- 此源包明确缺下列 6 原件，前端完整快照仍待固定 commit；不能称完整前后端发行。后端统一启动/注册/接线代码可以先行，不因前端快照或将来真实交易日输入暂停全部开发。
- 工作要求：以以上固定 commit 为起点；写入前读分支实际 HEAD，保留其后已明确接入的新改动。分支名称只用于协作，不能替代固定源码身份。

原始源码与可移植配置改动必须分开记录。以下 6 原件因本机路径元数据未复制，manifest 的 `privacy_exclusions` 保留其原 donor/blob/bytes 与排除原因：

- `V5/producers/archive-acquisition-v2/source/ops/run_zsxq_hourly_delta.py`
- `V5/ui/manager-workbench/NEXT.md`
- `V5/ui/manager-workbench/source/apps/web/src/api/managerWorkspace.announcementReview.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/manager-selection/__tests__/workspaceAfterReadback.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/manager-selection/catalystObservationPanel.runtime.spec.ts`
- `V5/ui/manager-workbench/source/apps/web/src/views/ManagerSelectionView.spec.ts`

任务书和交接清单只用仓库相对路径及逻辑 root 名称，不复制私人路径。若需改为配置注入，提交明确的最小 diff 和测试，保持原 PIN/hash/capsule 校验语义；不能删除身份检查、伪造原件 SHA 或为了可移植而把未知来源标为通过。受阻文件列出仓库相对路径与缺口类型，继续其余不依赖的实现；被拒材料不得换路径重传。

采集侧明确待配置化的原件为 `V5/producers/archive-acquisition-v2/source/ops/run_zsxq_hourly_delta.py`：L31—32/L38—39 含本机 CLI 和证券 parquet 的硬编码路径。本文件在固定初始包中缺失。可以只读原固定仓库中的已有源码作为实现参考；提交可移植修件时改成显式环境变量/配置路径，缺配置即 NOT_READY，不能默认访问用户本机对应目录。此改动不需要新权限或凭据，不得阻断统一框架开发。

该 producer 的 SHA 被 acquisition manifest 的 L7/L32 绑定，`article_v2.capture` L56—59 消费 `after_sha256`。修件必须同步派生 manifest、保留原 snapshot 来源身份、记录新代码 SHA，并测试合法配置、缺配置、错根/错 SHA 的拒绝；不能把修改后代码继续标成原 SHA，不能只改路径而绕过原绑定校验。精确 manifest 路径以原树实际文件为准。

### 原计划仍为验收依据

1. [V5 全系统迁移与交付总计划](https://github.com/lexi2016/v4/blob/24c6d60d524f43fcf4209ec8b078ec02cb34417e/V5/docs/superpowers/plans/2026-10-09-v5-master-delivery.md)，尤其 §1 的 M01—M18、§3 的 P0—P5。
2. [V4 到 V5 迁移执行计划](https://github.com/lexi2016/v4/blob/d1bf034640ca2e5957423de2745a98e159b69af2/V5/docs/superpowers/plans/2026-10-10-v5-migration-execution.md)，尤其 §4—5 的依赖顺序、三策略首批退出条件。

原 V5 源基线是 `lexi2016/v4@6daed6271313b5ae5324c8948f163258ab8d1fa3/V5`：完整目录 772 文件，排除 docs/handoff 历史材料的源码核心 694 文件。此计数只说明源集合，不证明 18 模块已验收。集成包在此基础上叠加以下固定候选；以最终 manifest 的逐文件身份为准，不整目录覆盖新版本。

| 叠加来源 | 固定身份与使用要求 |
|---|---|
| P0 已有接线 | `5a2cbd69e8a3eb99fc2167f0d2a41638b5af2c03` 的已选三文件；其余原依赖来自固定核心树 |
| M13 已验改件 | `308af26862daf005c5c5800d15c5053c84275938` 的八文件；经理重叠文件服从下行容量版本 |
| 经理容量协议 | `0b3495b5ded5c0a6a132de1b10108c4d7ff761f6` 的 `manager_plan.py`、`manager_result_transport.py`，保留 M13 行为并扩展合法大结果读取；不能覆盖回旧 P0 版本 |
| M14 owner | `a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba` 的已选九文件；研究投影保持原资格限制 |
| 经理装配修件 | `21602c9e16732ae6cd869b26a630ce3764f725a4`，已有 16 项隔离测试通过的回执；不是自然运行证明 |
| M18 v2 分页 | `8bea98c2bd506d42c00f2616dd04949d7a2b232d`；合法约 30MB 完整经理响应已能形成离线 bundle，尚缺 CAS 发布、只读 HTTP、普通页面的已验桥接 |

这些身份用于防止回退和串件，不要求重审或重写所有模块。M18、M13 或其他原模块 Chat 有更新时，由嘻嘻给出固定增量与唯一写入者，再最小接入；不要凭分支最新文件猜版本。

## 3 当前断点与文件边界

### 后端已有能力

当前链路是 `daily_tick.tick → daily_dispatch → owner receipts → assemble_manager_request → run_manager_daily`。这条链要接续使用。

| 文件范围 | 本任务责任 |
|---|---|
| `V5/src/v5_shadow/daily_tick.py`、`daily_dispatch.py` | 统一显式绑定、日期和窗口准入、每日调用与安全恢复，不写策略算法 |
| `daily_owner_adapters.py`、`daily_manager_assembly.py` | 对接现有 owner 小回执；封存固定输入与 cutoff；三策略和已有引用装配到原经理 |
| `run_ledger.py` | 复用现有身份、claim、receipt、重试门禁；保持已保存状态兼容 |
| `module_artifacts.py`、`module_api.py` | 复用不可变对象、generation、CAS 激活和独立回滚，补必要的有限对象读取 |
| `api_gateway.py` | 薄路由和只读兼容；不得调用 owner、采集或选股 |
| `composition.py`、`cli.py` | 现有 composition 只装配 `rebound_shadow`；不得把它误报为 18 模块注册或统一系统启动 |
| `manager_plan.py`、`manager_result_transport.py` | 使用已固定容量协议，保持原业务和身份；确需窄接口修改时与原 M18 合并到唯一版本 |
| `m18_offline_v2.py`、`m18_offline_pages.py`、`m18_offline_v2_process.py` | 消费已保存 v2 generation，接发布与渐进读取；不重算经理结果 |

当前 `api_gateway` 与 `module_api` 分别启动，没有统一的 18 模块注册。`run_ledger.LANES` 只有 `announcement`、`us_mapping`、`rebound`、`manager_plan`、`hk_preselection`、`a_stage`。模块编号、服务实例、调度 lane 不是一对一关系，不能把 18 个卡片或 18 个 lane 名字当成模块接通。

本 P0 首批维持现有六 lane 账本兼容。其他模块先有显式注册、原 owner/读取入口及触发合同，缺执行适配时标明 NOT_READY；需要新 lane 的模块在其实际接线时做窄兼容扩展与迁移测试。不得把多个独立模块强塞同一 lane 冒充独立幂等，也不得用临时第二套运行账本替代原账本。

### 前端源的准确边界

现有基础树位于 [canonical/apps/web](https://github.com/lexi2016/v4/tree/e9c94a13a1407449a16b3fa731bd0ef46867cf34/handoff/v4-running-source-20261005/canonical/apps/web)，固定 tree 为 `5c41fd3f116da0e3dfd8d14aa923fda7fae9f59b`，110 文件。其主链是 `index.html → src/main.ts → src/App.vue`；`src/app_shell/useAppShell.ts::openManagerSelection` 跳转 `/manager-selection/?date=…`，`src/manager-selection/main.ts` 挂载 `ManagerSelectionView`。

`V5/ui/manager-workbench` 是变更 overlay，不是可独立构建的完整前端。采用当前 `6daed627…` 的 23 项变更映射，按 manifest 的 `source → path` 装配到基础树，不反向覆盖为 `e9c94a13…` 的旧 12 项版本。package/lock/构建配置沿基础树复用，不换前端框架或增加无必要依赖。

当前已定位的历史组合仍应标 `FRONTEND_SOURCE_INCOMPLETE`。可核 125 件来自 canonical 基础树、23 项 overlay 和已定位测试补件；这不是完整前端。缺固定 GitHub 匹配来源的八件为：

- `tsconfig.cloud-product.json`
- `daily-research-command/index.html`、`manager-selection/index.html`
- `src/manager-selection/dailyResearchRun.ts`、`announcementAnalysis.ts`、`cloudActualReadback.spec.ts`
- `src/api/managerAnnouncementAnalysis.ts`、`cloudRecoveryContract.spec.ts`

另有 `src/manager-selection/researchAttention.ts` 的 canonical 旧件与本机历史交接版本不同，必须核当前原字节。Vite 声明三个入口，因此两个缺 HTML 直接影响完整 build。原测试引用的五件业务 observation fixture 仅留本机，不能制造替代 fixture 并宣称原业务测试通过。`WorkspaceReadback`/`workspaceReader` 属于此前候选，不能假设已在当前普通页面部署。

Mac 正在向独立分支 `dev/p0-frontend-source-20261012` 提交当前前端快照，固定 commit 与逐文件 manifest 待回。它应提供当前完整根、三个 HTML 入口及可发布测试，排除含私人绝对路径的材料。收到后以其已验证 commit 和实际文件闭包更新以上缺件状态，不用 125/134 文件计数代替逐项核对；没有固定回执前保持未齐。本机旧交接字节不能自动当作当前 GitHub 前像，也不能未经确认上传真实业务 fixture。

对纯接线缺件，本 Chat 应补齐最小可构建实现和合成测试；若是已有业务实现，则通过嘻嘻取得精确原件，继续不依赖该文件的工作。不要用空组件或空业务响应让构建通过。原 App、HTML 和 runtimeLabel 仍带 V4/V3.5 身份，不存在已验的新 V5 18 模块首页；本任务需要真实完成 V5 壳和身份展示。

## 4 先完成最小统一启动

在 V5 内提供一个稳定、可复制执行的命令入口，实际串起已配置的模块只读 API、兼容网关、前端构建产物和每日 tick。优先扩展现有 CLI；确需新入口时只加一个薄 `V5/src/v5_shadow/runtime.py` 和必要脚本，不再引入通用服务框架。

入口至少支持配置校验、启动只读服务、查看实际运行身份、受控停止本次启动实例、执行一次已授权 tick。建议在现有 CLI 下提供等效子命令；若用新 `runtime.py`，交付以下命令合同，并在 README 给实际工作目录/现有 Python 的调用方式：

```text
python -m v5_shadow.runtime validate --config <V5本地配置>
python -m v5_shadow.runtime start --config <V5本地配置>
python -m v5_shadow.runtime status --config <V5本地配置>
python -m v5_shadow.runtime tick --config <V5本地配置>
python -m v5_shadow.runtime stop --config <V5本地配置>
```

这些是本任务待实现命令，不是现有能力声明。`validate/status` 只读；`start` 只启动登记的服务；`tick` 调用原 daily 入口并执行原窗口/授权门禁；`stop` 仅停止身份核验匹配的本次 V5 实例。不得只交 shell 片段让 Mac 人工猜启动顺序。

- 启动前校验固定代码/配置/注册表身份、绑定根、端口和路由唯一性。数据根不可越界、互相覆盖或通过 symlink 指向 V4 可写路径。
- 使用现有 Python/前端依赖；模块 API 可以按隔离需要起多个进程，但不要求 18 个 HTTP 服务。
- 网关、前端读取与 daily producer 的生命周期分开。启动主页面、健康探测、GET、页面刷新、切日期均不得触发 producer。
- 单个模块 NOT_READY 或进程故障不阻断无依赖的健康模块启动；依赖它的模块显示精确原因。基础配置整体冲突则明确拒绝启动。
- 运行状态报告实际 PID/端口/启动时间、代码 commit、配置和 manifest SHA、已绑定模块/route、活动 publication generation。不能只回显配置内容作为健康证明。
- 停止/重启只针对登记且核验身份的本次 V5 进程，不使用宽泛 kill，不触碰 V4 和 8910。旧进程持有固定 root FD 时，按原合同起新实例后核实切换，不能只改目录指针。
- Mac 配置中保留一键启动、状态检查、日志位置和回滚命令。日志只记录必要身份/状态/错误码，不外传私有正文或凭据。

## 5 显式注册 M01 到 M18

提交一份可机器校验的注册配置及小型读取器。可命名 `V5/config/module_registry.json`、`V5/src/v5_shadow/module_registry.py`；如果最终源中已有等效配置，直接扩展。以下是本任务要求的新注册合同，不声称原代码已支持。

顶层字段：`schema_version`、`system_id=V5`、`release_id`、`source_commit`、`modules`。这里的 source_commit 是固定输入基线；实际部署候选 commit 在部署 manifest 中由已创建的提交解析，不能要求提交文件自包含自身尚未生成的 commit SHA。配置的原字节 SHA 和 schema 版本进入启动身份与部署 manifest。

每个模块记录至少包含：

| 字段 | 合同 |
|---|---|
| `module_id`、`name` | M01—M18 恰好各一次；沿原计划命名 |
| `implementation` | 固定 source commit、实际源路径、必要实现摘要；未提供则明确缺件，不用空字符串伪造 identity |
| `owner_entry`、`read_entry` | 已验证的可调用原入口或 `null`；静态白名单解析，不从外部字符串执行任意命令 |
| `binding_status`、`not_ready_reasons` | `BOUND` 或 `NOT_READY`；BOUND 只代表运行接线可用，不能代表业务/自然验收完成 |
| `dependencies` | 模块 ID、`required`、所需产物/合同、同日或跨日关系、来源时段/日期规则。可选研究缺项不能阻断无依赖 lane |
| `trigger` | `scheduled`、`event`、`manual` 或 `read_only`；只绑定原实际触发。未核实时标 NOT_READY，不制造每天执行 |
| `schedule_binding` | 已核日历、时区、slot/cutoff/deadline 配置引用或 `null`；不把未核默认时刻升级成自然运行合同 |
| `ledger_binding` | 现有 lane/原任务状态入口，或 `null` 加明确未接线原因；不能将 M 编号直接当 lane |
| `storage_bindings` | 逻辑输入/私有输出根引用和只读/可写边界；实际 Mac 路径留本地配置，不硬编码来源机器路径 |
| `publication`、`routes` | module_id/release_id/routes 绑定、只读路由与回滚单位；严格复用已有发布配置合同 |
| `ui_entry` | 真实原页面/视图入口或 `null`；没有页面不得挂成功链接 |
| `acceptance` | 分开记录固定代码测试、Mac 验证、API/页面、自然运行证据引用。未执行保留 `NOT_RUN` |

模块名与最小依赖表：

| ID | 名称 | 必须保留的依赖与触发含义 |
|---|---|---|
| M01 | A行情与公式面板来源 | 原 A 来源 owner，避免第二活动采集源 |
| M02 | HK行情、主表与资格来源 | 价格、主表、资格各自日期和取得时点 |
| M03 | US行情来源 | 原 US session/provider/cutoff |
| M04 | 研究情报与归档 | 各原采集/归档 lane 独立结果 |
| M05 | A预选池 | M01 为主，M04 研究材料及 M12 跨日材料按原合同 |
| M06 | HK预选池 | M02，原 Top100 与日期合同 |
| M07 | A阶段选股 | M05、原实时源；M04 依其可选性 |
| M08 | HK阶段选股 | M06、原实时源；保留竞价/Stage8 |
| M09 | A收盘复盘 | M01/M07，M12 材料按适用跨日关系 |
| M10 | HK收盘复盘 | M02/M06/M08 |
| M11 | 盘中研究与研究复盘 | M04 及已提交市场/阶段证据 |
| M12 | 视频FUPAN | 原视频/ASR/OCR/对齐节点，独立恢复，供后续 M05/M09 |
| M13 | 公告研究与选股 | M04 及原公告目录/正文/真实 reviewer 通道 |
| M14 | 超跌研究与选股 | M02 原面板/主表/历史，原两门规则 |
| M15 | 美股到港股映射 | M03+M04+M02；保留关系可用时间和有限范围 |
| M16 | 经理候选公开资料任务 | M04/原固定候选及显式 job，GET 不触发 |
| M17 | 尾盘量价发现与持续跟踪 | 独立窗口与持续跟踪，不并入 Stage 或超跌 |
| M18 | 经理决策账本、汇总与计划 | 首批 M13/M14/M15；其余原可消费 04—17 产物逐项接入 |

拓扑校验必须区分同日 DAG 与跨交易日边：01→05→07→09；02→06→08→10；03+04+02→15；02→14；04→13；13/14/15→18。复盘供下一交易日预选、M12 给后续材料均不能强塞成同日循环。注册表必须检出未知模块、重复 ID、未知依赖、同日环、路由/写根冲突和代码身份不符。

## 6 每日执行与同 run 装配

1. 每日入口读取明确当日 bundle 和批准的来源绑定，核 target_date、来源日期、可用时刻、cutoff、代码/配置/依赖身份。不得把昨天 bundle 改日期、扫描任意 latest 或把当前输入冒充历史 PIT。
2. 继续使用原 claim/finish/read_run；重复 tick 对同身份复用成功，不重复计算。原 RUNNING 无明确完成回执时保持结果未知，不按超时盲目重试。
3. 调度只处理依赖与时间，不承载选股逻辑。每 job、claim 等待后及 owner 调用前核实际时钟/交易日；两种经理入口 `manager_request`、`manager_template` 必须服从同一准入。错窗记录未执行，允许读取已有成果，不补跑 producer。
4. 已有默认 08:00/08:45/09:00 明确标为未核 V4 schedule，不能当实际自然时窗。A 复盘 16:05/17:10、HK 16:10 与半日规则按原已核 catalog/实际配置；未核半日不能猜时间。
5. M13 保留原 announcement binding、publication_date 与 target_date；读回可用研究材料和业务阻断分别处理，不静默删绑定。M15 用精确当日原 owner run/artifact 读回；不能回退已验 guard/receipt 修件。
6. M14 使用当前 `read_rebound_owner` 与 `manager_projection` 的研究输出，接 `rebound_research_observation`，不混旧 `rebound_observation` 或正式 `rebound`。保持 CANNOT_CONFIRM、eligible_screen=null、formal_eligible=false 和 natural_verified=false 的真实语义。
7. native master 和 archives 使用现有 reader 校验固定闭包，不能拿参考时段主表冒充当日港股通 membership。缺项、unknown、rejected 按原合同保留，不为体积清空内容。
8. 经理只消费已提交引用。封存实际 request.now/cutoff 和输入身份，同一封存 request 重试不改变时间；输入真正变化才形成新计算身份。每策略独立结果、理由、日期、资格限制和缺口进入同一经理 run。
9. 保存、精确读回和发布是独立阶段。保存后有不可变小 checkpoint，关联原 ledger claim、request/source/config identity、owner run、plan/raw/response SHA。发布失败或 CAS 冲突只重试同一已保存结果，refresh 调用不能增加。
10. 若 latest 已移走而现 owner 不能安全读取旧 exact run，明确冲突并保留 checkpoint，不能换新 run 或重新 refresh。需要窄 exact-run 能力时复用原 owner 校验，由唯一 M18 作者提供，不写 `json.load` 验证替身。

现有 ledger identity 的七字段及终态保持兼容：lane、target_date、input_sha256、research_cutoff、code_sha256、config_sha256、dependency_sha256；终态仍 SUCCEEDED/FAILED/BLOCKED。系统展示层可有 NOT_READY、过期和发布待完成等状态，但不得未经迁移就写进旧 ledger 枚举。

未来交易日真实 PIT 输入是自然验收条件，不是编写代码和做隔离模拟测试的前置。缺真实输入时交完整实现、合成 fixture 与明确待验项；不能凭模拟时钟签自然通过，也不能让所有开发停等下个交易日。

## 7 发布 大结果和只读 HTTP

继续沿 `module_artifacts` 的不可变对象与 CAS activation，按模块保留旧 active 和回滚点。源码 commit、业务 owner run、v2 generation、publication generation 是不同身份，必须分别记录。

- M18 v2 六字段 `run_id`、`target_date`、`plan_sha256`、`raw_sha256`、`response_sha256`、`input_identity` 从保存、bundle、发布、HTTP 到页面一致；另校验 v2 generation_id、manifest_sha256、profile_sha256。
- `module_artifacts` 的 active/module generation 与 v2 generation_id 不能互填 CAS expected_generation。
- 复用现有小响应通路；大结果提供 overview、有限分页 detail 和按需 content。不能把约 30MB JSON 或整代约 42MB records 一次塞进旧发布器/HTTP，也不能提高全局 16MiB 限额绕过合同。
- 调用原 v2 Reader/verify_page/verify_content 完整验证；请求中固定 generation/manifest/profile/六字段 identity，分页、selection、cursor、offset 按原合同核对。响应不能拿自报期望值验证自身。
- GET 只读已发布对象：不创建缓存、不补文件、不修改 latest/ledger、不调用 owner。未知/未发布/损坏对象返回明确错误；路径、query、偏移和体积均有限制，不暴露本机真实根或正文错误栈。
- 每个 HTTP 响应、首次 overview 和单次详情均有可测预算；不要求浏览器先加载全体详情才能渲染。未加载是 NOT_LOADED，不能当 0 或空集。
- CAS 冲突保留原 active，新候选不能覆盖他人 generation。重试只消费相同已保存 bundle，兼容旧小结果并支持单模块回滚。

## 8 普通 V5 主页面

复用原 App/useAppShell、业务视图和 manager 页面，完成一个真实 V5 主入口，不重新设计 18 个空页面。

主页面应能看到目标日期、实际 V5 发布/代码身份、M01—M18 的真实就绪和运行状态、最近成功/最近尝试、来源日期、run、是否过期、具体阻断原因，并进入已有业务视图。首次重点让三策略及 M18 的股票、理由、资格限制、未评估范围和缺口在普通经理页可读。

- 页面数据来自已提交只读接口，与显示的 run/generation/日期固定绑定。切日期或 view、刷新、返回、快速重复点击和慢响应乱序不能串 run；取消或丢弃过期请求。
- 单模块失败不清空其他已成功模块；今日失败可显示旧成功，但显式标旧日/过期及本次失败。
- 没有真实结果时说明 NOT_READY 或 BLOCKED 及下一步，不能用演示数字、空数组、0 候选或“健康”卡伪装完成。
- 旧小 workspace 路径兼容；大结果走 v2 渐进读取，保留 overview/detail/content 的未加载状态和错误。
- HTTP GET 和页面点击不得隐式生成策略或研究 job。原本有副作用的显式按钮保留原边界与用户确认要求。
- 标题、导航、health、静态 build manifest 与实际服务都须可核为 V5。旧 54779 预览仍是 V4 标题/旧 run，不能把它作为本次新框架部署证明。

## 9 实现与验收顺序

按下面顺序连续实现，不每完成一项就等待用户再次许可。先写能暴露断点的测试，再修实现，保留实际命令与结果。遇到纯接口歧义按原合同做最小选择并记录；遇到范围、安全、凭据或真实外部副作用新授权问题，停相关动作并向嘻嘻报精确阻断，继续独立工作。

### A 固定源与配置

- 固定源码闭包、前端 overlay 映射、源缺件清单；不混旧经理容量版本。
- 完成注册 schema 与恰好 18 条记录、DAG/跨日/路由/根/身份校验。
- 完成统一启动入口；演示真实配置校验、启动、健康读回、受控停止及模块故障隔离。

### B 首条完整链与发布恢复

- 三策略已存产物 → 原经理同 run 保存/独立读回 → 小 checkpoint → 原发布/CAS → gateway → 普通页面。
- 测缺一策略仍保留其他两路；测试原拒绝/有效空/unknown 不混。
- 测保存后发布失败、CAS 冲突、进程中断和回执丢失：重复 tick/恢复不再次 refresh，旧 active 保留。
- 测同输入重复、改变输入、错日期/错 SHA/错 run、latest 移动、跨窗口/锁等待/跨日、未核半日与缺真实 bundle。

### C 大结果与页面

- 约 30MB 完整响应 → 已保存 v2 bundle → 有限对象发布 → HTTP → 普通页面渐进显示。
- 校验六字段 identity、两类 generation、响应预算、错页/错 cursor/错 hash 拒绝、旧小结果兼容。
- 记录 GET 前后文件/ledger/owner 调用不变；页面首次不加载全部正文。
- 页面真实测试日期、刷新、前后导航、缺数据、超时、慢响应乱序和恢复。

### D Mac 实测与单模块回滚

- Chat 提交唯一固定候选，Mac 使用既有依赖和隔离 V5 根直接测试；不拿其他 commit 的测试结果拼成当前全套通过。
- Mac 核启动进程/端口/源码/配置/静态 manifest，验证浏览器实际访问该候选；单发布窗口切换。
- 至少一个真实模块做 worker→产物→API→普通页面→回滚全链；回滚该模块时其他模块 API 和 V4 保持可用。
- 启用日调度后核真实安装/运行状态与自然窗口；只渲染 Disabled plist 或有源码文件，不算服务已启动。
- 问题反馈含固定 commit、实际命令、FAIL/NOT_RUN、错误与预期、最小复现、必要身份摘要；回本 Chat 修复，不另造平行实现。

### E 保留原 P0 到 P5 完成门

| 阶段 | 必须证明 |
|---|---|
| P0 | 统一接线可运行，幂等/未知副作用门禁/发布/CAS/只读 API/独立回滚闭环，至少一条真实原页面链 |
| P1 | 公告、超跌、US 三策略均有真实结果或原算法验证的有效空，经 M18 同 run 保存/普通 API/页面一致；缺输入不计业务完成 |
| P2 | M01/M02/M03/M05/M06 精确来源与池合同，真实连续接续，旧成功可追溯，不替换 V4 活动源 |
| P3 | M07/M08 各实际窗口与 M09/M10 每槽的新日计算、日期/实时输入/普通页面、市场独立回滚 |
| P4 | M04/M11/M12/M16/M17 原实际触发及节点恢复，独立产物，GET 无生成副作用 |
| P5 | 当前固定版本全套回归和构建；18 模块逐项真实输入/计算保存/API/页面/调度或实际触发/隔离回滚；两个连续适用交易日自然运行证据 |

本 Chat 交付 P0 完整代码和本批接线，登记 P1—P5 的准确剩余项。不能把 P0 工程通过、数个页面成功、US 四键结果或一次模拟运行改称全系统完成；完整验收仍按原计划推进。已有同版本有效证据直接引用，不重复做无变化源码审查。

## 10 交付清单与边界

交付必须同时包含：

1. 固定 commit 的完整源码、必要配置和锁文件；新增/修改文件清单与前像/后像身份。补丁可辅助，但不能只有 diff 或代码摘录。
2. 18 模块注册表、依赖与触发绑定、当前 BOUND/NOT_READY 原因、已有接口到 V5 路由/页面的真实映射。
3. 一个能直接执行的统一入口和 Mac 运行说明：校验、启动、健康、一次 tick、真实调度配置、日志定位、停止和单模块回滚。
4. 当前固定版本实际运行的后端测试、前端 test/typecheck/build 和集成测试结果；逐项 PASS/FAIL/NOT_RUN，说明运行环境及剩余原因，不编造通过数。
5. source/deployment manifest：代码 commit、配置/注册表/build SHA、每模块 source/release、owner run 引用、publication generation、回滚引用；不包含凭据或私有正文。
6. 合成隔离测试 fixture 和复现命令；真实 PIT/业务正文留 Mac 本地，测试 fixture 明确标合成，不能作为自然证据。
7. 一段简短交接：本次实际接通了什么、普通页面入口、Mac 待验什么、哪些模块仍 NOT_READY，以及下一步原模块返修项。

最终回复请先给固定 GitHub commit 和完整文件入口，再给实际测试与剩余项。若没有执行工具，明确标 NOT_RUN 并交完整可执行测试，不把建议命令当已跑结果。

始终保留 V4 现役、V4 源和数据、8910 及当前可用预览回滚点；只操作已授权 V5 工作目录和开发分支。不执行交易、不发订单、不改 BUY 门、不创建或扩大凭据/安全权限、不向外部上传真实业务输入，不新增无关依赖和服务，不重写 18 套算法。工具拒绝时返回准确 action/target/error，不能换路线绕过。
