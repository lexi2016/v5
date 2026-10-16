# 原18模块交接矩阵

编号与名称取自固定统一执行计划，B01=M18，不新增M19。P0是共享底座，不是第19模块。P1=M13/M14/M15/M18；P2=M01/M02/M03/M05/M06；P3=M07–M10；P4=M04/M11/M12/M16/M17；P5为整体终验。

本次只读核实了分支HEAD和非截断源码树，未运行产品测试。以下“已有验证”摘录仓库历史回执/计划，不是2026-10-16新验收；完整验收未知项不得自动变成PASS。SOURCE_PRESENT不等于完整闭包已独立启动，PARTIAL补丁也不等于整模块无源码。更晚的限定增量见VERIFIED_GAPS_AND_EVIDENCE.md。各分支内before、rejected、reference等必须按原清单选择，不能直接混入release。

## M01 A行情与公式面板来源（P2）

- 固定源码：[`dev/m01-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/ea96a80cf9d79e638ee08e15cb0bf92368261ada)，`ea96a80cf9d79e638ee08e15cb0bf92368261ada`；本次树核验115文件。
- 源码层级：来源/公式候选与历史回执；不认定真实新日闭环完整。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。部分代码入口已接；公式/工程与阻塞卡已有证。真实新日来源读回、真实数据页、自然与完整验收未过。原10/09 V35公式READY/PASS，但总PARTIAL/REBUILD_REQUIRED/sync FAILED；旧V4身份仅09/11。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：待核代码覆盖：独立A来源日生产接管未证完整；输入：selector与M05输入身份不同，无官方generation绑定；待核：当前Windows authority/Mac调用的实际入口、固定源码与来源索引，不把旧文件存在当绑定。
- 原退出标准：同一合法交易日来源/公式/05或09消费身份一致；坏单位/缺行情/错generation拒绝，失败保旧；新进程启动、保存冷读、API/页、下一适用日触发与单模块回滚分别留证。
- [原M01具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/ea96a80cf9d79e638ee08e15cb0bf92368261ada/handoffs/M01/START_HERE.md)。

## M02 HK行情、主表与资格来源（P2）

- 固定源码：[`dev/m02-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/776acce9328aa102e3db6973405f01260f15239d)，`776acce9328aa102e3db6973405f01260f15239d`；本次树核验149文件。
- 源码层级：已有完整候选报告；本次核了树，未重验全部运行闭包。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。部分入口、真实三源build/冷读、公共安全投影和页面已过；membership7件/698、native4/HK02九资产，SOURCE_IDENTITY_ONLY、temporal CANNOT_CONFIRM、PIT/正式历史资格false。执行manual_controlled、natural_verified=false，原receipt.manual未核不赋值。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：验收：固定776acce已Mac 38/38通过，真实capture/七件恢复/原binding冷读/M02-only发布与HTTP/DOM通过；native visual NOT_RUN，独立日常/自然及全模块验收未过。旧collector因stock_owner NaN失败的历史保留，新严格producer的实际capture成功有独立回执。输入：完整目标资格/PIT仍未齐，panel_status=PENDING_PANEL_GATE，不能靠新代码宣称历史证据有效。
- 原退出标准：固定候选默认启动不依赖V4进程；原/新producer身份明确，旧未知或不安全仍拒绝，原字节不在旧身份下被清洗；真实任务须分别证SDK取得、合法封存、三源原reader、目标日期与消费，错误状态不伪报成功。
- [原M02具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/776acce9328aa102e3db6973405f01260f15239d/handoffs/M02/START_HERE.md)。

## M03 US行情来源（P2）

> 后续限定状态：真实M03→M15 seed与普通页已通过；原队列中NOT_RUN只属较早阶段，见问题包第2节。

- 固定源码：[`dev/m03-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/3020bb6b0abd30fc9a243cfdee7ec0f121e2c178)，`3020bb6b0abd30fc9a243cfdee7ec0f121e2c178`；本次树核验200文件。
- 源码层级：包含完整行情collector候选、旧被拒版本和接页增量；按manifest选原件。
- 历史已有验证（报告层，未本轮重跑）：原20261009 POST_CLOSE三件录制回放→snapshot→binding→API/页证据保留；新候选efeaeb8已核75个Git blob、74项manifest与release SHA，Mac verify_release exit 0，新3个定向测试模块23/23 PASS、0 skip，候选字节未变。旧48项历史测试未重跑；该离线轮尚未运行真实provider/network，后续原窗口真实来源与M15消费见本节末条；后续3020单卡HTTP/DOM与CAS发布已过（见本节最新条）；原生视觉及自然仍未证明。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：新固定行情collector/默认入口候选已交且Mac离线23项通过，不能再标为仅字典validator或未交候选。已完成一次适用US session/cutoff真实采集、原三件保存/冷读及M15 seed消费；普通页面单卡发布已完成；待验下一适用session自动更新、原生可视及完整来源能力；12/13新闻三件仍不能替代行情snapshot。
- 原退出标准：三件同session、SHA/receipt/manifest一致，取得不晚于消费cutoff；错session/缺报价/假READY明确拒绝，下一适用session自动更新且旧成功保留；普通来源页和M15消费同identity。
- [原M03具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/3020bb6b0abd30fc9a243cfdee7ec0f121e2c178/handoffs/M03/START_HERE.md)。

## M04 研究情报与归档（P4）

> 后续限定状态：真实8档恢复及多根隔离通过，Mac实际发布被拒；云端已接固定包，不能据此称Mac已发布。

- 固定源码：[`dev/m04-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/0bb46df890d4b1a57fcc17982a9800cac2f18146)，`0bb46df890d4b1a57fcc17982a9800cac2f18146`；本次树核验995文件。
- 源码层级：包含M04_capture完整候选及modules/M04；环境和来源闭包需原manifest约束。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。持久编排/失败续接工程已交且定向Mac过；18篇原归档冷读与页面已过，53范围外错误/PIT UNKNOWN保留。原reader、builder/import源码不应被说成不存在。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入：取得时点、主题、全lane真实覆盖未齐；待核代码覆盖：完整来源日流实际可运行覆盖需按已有编排核对，不能只增加reader wrapper；待核：两组原回归未验范围及首批13/15真正所需lane。
- 原退出标准：至少一个真实常规触发与失败续跑同原文/span/来源SHA，图片/OCR缺失明确；不补历史取得时间，消费者同SHA；随后覆盖原lane集合、普通页和实际触发/回滚。
- [原M04具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/0bb46df890d4b1a57fcc17982a9800cac2f18146/integration_candidates/M04_capture/README.md)。

## M05 A预选池（P2）

- 固定源码：[`dev/m05-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/5d868fc09fba7f7fe210e603a28015e271117077)，`5d868fc09fba7f7fe210e603a28015e271117077`；本次树核验152文件。
- 源码层级：实际源码与release；七业务来源/六执行lane覆盖仍待精确映射。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。部分入口已接；Mac7项合法空/非空回归及隔离历史120行strict READY冷读已过，但没有同日M01绑定/PIT，产品未保存/接真实页；不能增加真实产品计数。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：待核映射：原七业务来源V192/FUPAN/Stage7/公众号/白毛/hourly research/research preview，与现六执行lane/物理池并非已证明一一对应；代码按映射补缺。输入：M01官方generation/同日合同缺；权限：新单池permit/OPEN/build问题未获答复，只暂停该次真实应用写入。
- 原退出标准：七来源各适用状态齐、原去重/集合/顺序不变；verified empty≠缺源/CANNOT_CONFIRM，可选lane坏不清健康lane；经合法permit的真实产物、原reader、M07消费、API/页/下一日/回滚同identity。
- [原M05具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/5d868fc09fba7f7fe210e603a28015e271117077/handoffs/M05/START_HERE.md)。

## M06 HK预选池（P2）

- 固定源码：[`dev/m06-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/ddb07572e7bd24efff2a9624806e2487129d208a)，`ddb07572e7bd24efff2a9624806e2487129d208a`；本次树核验212文件。
- 源码层级：原source、patch及daily增量；已过自然current有限步骤不等全链。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。真实原模型100行、存量池双账本/current/动态页已过；17:32自然步骤一次成功，target14/signal/eligibility13，后续复用且窗口末无重owner/model。整链daily仍false、经理POST_OWNER请求缺失，有限自然不等完整模块。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入/资格：完整PIT/目标资格未齐；集成：合法下游manager request/引用接续未闭环（主要P0/M18责任）。代码完整性待核仅限模块独立日生产、输入/输出标准合同与失败恢复，不重写已过自然current链。
- 原退出标准：原新日Top100或合同允许存量模式分别留证，全100行排序/权重与三日期正确，坏日期/资格未知拒绝或保留状态；M08消费同identity，连续适用日、窗口关闭不补跑与回滚过。
- [原M06具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/ddb07572e7bd24efff2a9624806e2487129d208a/handoffs/M06/START_HERE.md)。

## M07 A阶段选股（P3）

- 固定源码：[`dev/m07-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31)，`e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31`；本次树核验159文件。
- 源码层级：已有完整链交付/OWNER_CLOSURE；本次未重跑。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。完整链Mac63+31和只读入口/HTTP/DOM已过；无合法真实stage绑定/股票页，四缺口WAITING，formal BLOCKED/temporal=false。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入：M05六物理池（与七业务来源映射待核）、M01 raw三件/记录时钟、M04小时见证/morning、M07已验证保存引用缺；待核代码覆盖：合法request/binding准备与全部原stage可运行覆盖须核后补，不能只做占位页。
- 原退出标准：原每个A阶段包括竞价/尾盘有对应窗口真实输入与结果/冷读/页一致；错窗口/缺源明确拒绝，恢复身份单列；M09可追溯，下一适用触发及独立回滚过。
- [原M07具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31/handoffs/M07/DELIVERY.json)。

## M08 HK阶段选股（P3）

- 固定源码：[`dev/m08-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/01f1a6347722081cbbf97b54204bf033e6d01938)，`01f1a6347722081cbbf97b54204bf033e6d01938`；本次树核验214文件。
- 源码层级：已有完整owner报告；全部窗口与Stage8实际覆盖仍待验。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。真实池适配、10套八阶段历史结果独立冷读/页面已过；历史局部不等全部真实新阶段生成。原40位SHA已核，原Chat错误展开的38位不采用。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入：Stage8完整重算输入、普通阶段时点/成员/单位/PIT/资格未齐；待核代码：竞价/Stage8/普通各入口和实际配置，不把旧只读包当全生产，也不认为全部owner未交。
- 原退出标准：每个原窗口同日同源输入/结果/独立页一致，池日期与阶段身份不漂移；半日未知拒绝、单位/资格未知保留，M10七阶段引用正确、自然接续及独立回滚过。
- [原M08具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/01f1a6347722081cbbf97b54204bf033e6d01938/handoffs/M08/START_HERE.md)。

## M09 A收盘复盘（P3）

- 固定源码：[`v5/m09-handoff-20261011`](https://github.com/lexi2016/v5/tree/3d1d04283f4d5ca05923b05c496a97e79145d275)，`3d1d04283f4d5ca05923b05c496a97e79145d275`；本次树核验1099文件。
- 源码层级：完整候选、before/after/历史回放并存，不可整树无脑叠加。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。两日真实录制研究回放/冷读与页已过，PARTIAL/source_time/成员/PIT/资格边界保留；完整新日自然未过。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入：当日全panel、阶段证据与可用视频正式材料；待核代码覆盖：独立新日采集/owner/publisher/reader和双槽触发完整接管未实证，先核固定入口再补真实缺口，不另造模型。
- 原退出标准：两槽各自完整真实输入/产物身份可核，缺阶段和正式材料独立披露；原模型等价、普通页可读，跨日/实际触发及与HK隔离回滚过。
- [原M09具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/3d1d04283f4d5ca05923b05c496a97e79145d275/M09_CLOSE_CHAIN_20261012/START_HERE.md)。

## M10 HK收盘复盘（P3）

- 固定源码：[`dev/m10-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/9ab214b0ad5542111c04d10f50cac989644205f7)，`9ab214b0ad5542111c04d10f50cac989644205f7`；本次树核验189文件。
- 源码层级：原HK收盘源码与回执；完整新日scheduler能力待验。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。698录制输入、20/100/70/20投影、七阶段PARTIAL/null的发布冷读/页已过；新日完整scheduler/来源资格未过。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入：M02全声明收盘集合、M06池、M08七阶段；待核：原scheduler/runtime及历史未验依赖是否齐，不能将NOT_RUN推成物理缺件。
- 原退出标准：一个合法新收盘日全链与下一适用日更新，20/100/七阶段可追溯、PARTIAL保持，API/页与冷读同run，回退不覆盖M09。
- [原M10具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/9ab214b0ad5542111c04d10f50cac989644205f7/handoffs/M10/START_HERE.md)。

## M11 盘中研究与研究复盘（P4）

- 固定源码：[`dev/m11-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/6abba1b36dce3d9696b5a0e401ba86a96d9b10ec)，`6abba1b36dce3d9696b5a0e401ba86a96d9b10ec`；本次树核验333文件。
- 源码层级：原owner、依赖、fixture与补丁存在，不属于只有方案。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。默认owner/独立reader、六槽API、安全修及工程页已过；真实页仍六项WAITING，广域失败不能被窄修抹除。reflection原cache_root与wrapper各8/8存在，不再当缺件。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入/身份：原snapshot源hash/pins/当时可用证据未齐，r4身份不能混F版；权限：旧元信息外传未获准；时窗：今日15:00已MISSED，不可补采。代码侧可补独立合法输入/可信pins/原sentiment核心接线。
- 原退出标准：原slot集合与日总结原引用/时点/结果一致，缺slot可见、中断续原步骤；实际下一适用触发、普通页和回滚过，源不齐不显示真实研究成功。
- [原M11具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/6abba1b36dce3d9696b5a0e401ba86a96d9b10ec/handoffs/M11/START_HERE.md)。

## M12 视频FUPAN（P4）

- 固定源码：[`dev/m12-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/385b1068054f3d20688344961b3a3cf34d6a7bb4)，`385b1068054f3d20688344961b3a3cf34d6a7bb4`；本次树核验139文件。
- 源码层级：原生命周期源码与集成补充存在；真实新视频全链未验。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。原生命周期局部恢复、17原生件原样导入/冷读/HTTP/页已过；ASR待复核、字典缺失保留。真实新采集/完整自然生命周期未过，不能把旧档导入当新视频生成。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：代码待核：原采集/下载/ASR/OCR/字典/对齐/gap/发布各入口是否全封装可独立启动；输入/运行绑定：媒体来源及字典需合法可用；不推定原生命周期不存在。
- 原退出标准：同视频全原节点可发布/冷读，后续失败不重下/重转成功媒体；ASR/字典缺口可见，页面节点状态与实际触发、回滚齐，不自动新ASR生产。
- [原M12具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/385b1068054f3d20688344961b3a3cf34d6a7bb4/handoffs/M12/START_HERE.md)。

## M13 公告研究与选股（P1）

- 固定源码：[`dev/m13-partial-pages-20261012`](https://github.com/lexi2016/v5/tree/308af26862daf005c5c5800d15c5053c84275938)，`308af26862daf005c5c5800d15c5053c84275938`；本次树核验10文件。
- 源码层级：仅10文件partial-pages补充；不是完整公告owner，原主分支待核。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。原公告保存研究与页面已有证，当前页32不是历史总量；PIT CANNOT_CONFIRM/资格NOT_ASSESSED。真实独审修订导入/后续日闭环未过。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：输入/业务合同：新revision缺真实review决定/ack与返回SHA；代码：详情/分页失败、capture与cutoff消费连接仍有断点，需要核完整原目录→正文→语义→导入链，不以新wrapper替代。
- 原退出标准：原目录→正文→合法独审导入→M18同SHA消费→普通API/页同run；未消费可定位，0/null/缺源分开，后续日/回滚成立；缺真实review不签业务链完成。
- [原M13具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/308af26862daf005c5c5800d15c5053c84275938/README.md)。

## M14 超跌研究与选股（P1）

> 后续限定状态：690 pending/40930行真实研究页HTTP/DOM已有发布回执；三码61/61不代表全690，单位/资格/PIT保留。

- 固定源码：[`dev/m14-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/ad9a61d26c487748ba017b69250571ae5a38bbab)，`ad9a61d26c487748ba017b69250571ae5a38bbab`；本次树核验220文件。
- 源码层级：原source、历史被拒候选、canary/接页候选并存；不是所有数据已合格。
- 历史已有验证（报告层，未本轮重跑）：新target14/signal13原保存run da7ae8f55b45416596e5c2d1e69b9b17仍为strict0/near0/pending690、READY_WITH_GAPS/正式CANNOT_CONFIRM。fac269隔离15 Vue/typecheck/build及真实分页通过后，23:03固定c7b→52e71→fac组合实际切换PASS并保留新预览；690行22页HTTP/DOM、其他11路200/JSON及旧manager descriptor核验通过。未重owner，native visual NOT_RUN，daily opt-in=false，不增加自然或完整验收计数。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：前次部署DOM等待超时并回退历史保留，重试成功不证明旧根因。success快照两个pending原浏览器请求无法续观；独立HTTP后验公告32/147与旧超跌strict31/214为200同身份，但首次并行公告503/CANNOT_CONFIRM保留，不称全无间歇故障。原生视觉NOT_RUN，历史不足、PIT/资格与完整验收仍未闭环。
- 原退出标准：新进程原reader与API每页合并结果同run/SHA，无漏重/截断；690待核和历史不足清晰，非正常空候选；错ref/date/私有路径不泄露、日期切换清旧、GET无生成，旧M18/其他17保持且可回退。
- [原M14具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/ad9a61d26c487748ba017b69250571ae5a38bbab/handoffs/M14/START_HERE.md)。

## M15 美股到港股映射（P1）

> 后续限定状态：seed两匹配保存/普通页发布已过，material与自然仍未过；不能把旧NOT_RUN描述当最终状态。

- 固定源码：[`dev/m15-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/821a25b1667a28073360c96cf8702ab57dbd233f)，`821a25b1667a28073360c96cf8702ab57dbd233f`；本次树核验681文件。
- 源码层级：包含M15_mapping实际runtime候选、release与原材料；seed与material分开。
- 历史已有验证（报告层，未本轮重跑）：原四关系/三HK保存读回与页面历史保留；最终f7dd8e63已531 blob/530 manifest核验，RELEASE SHA-256为8cb4cd4db7b9e8dccba527ec844dde9f7787d54ac1dd88cae0ded97e6db23507。Mac新增20 Python与7 Node、typecheck/build通过，候选字节未变；原40项复用此前云端证据，未在Mac重跑。两条原cold reader在合成fixture上MATCHED；该隔离轮未运行真实provider；后续原窗口seed真实消费/保存/冷读已通过（见末条），源资格、material、自然仍未过；后续821a25普通页HTTP/DOM及发布已过（见最新条），完整0。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：首轮Mac使用超声明版本的历史保留；现已找到满足声明范围的3.14.6/2.3.3/24环境，新增20项各有通过证据（19初次PASS＋1沙箱loopback单项补跑PASS）。uv.lock未同步，完整锁安装不冒称通过；M03真实snapshot及seed消费现已通过；material正文span/取得时点与HK身份、PIT/资格、原生可视及完整验收仍待验；seed普通页HTTP/DOM与发布已通过。
- 原退出标准：两路径各有真实结果或按原合同准确拒绝，保存/普通页同身份；原范围外未知、目标资格和自然身份不变，M18同session合法消费，下一适用session/回滚过。
- [原M15具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/821a25b1667a28073360c96cf8702ab57dbd233f/handoffs/M15/START_HERE.md)。

## M16 经理候选公开资料任务（P4）

> 后续限定状态：原缓存接纳与receipt问题已有固定修复，最后240facts/10 READY的普通页通过，历史PIT/正式资格未提升。

- 固定源码：[`dev/m16-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/d18469212c86bec95303ca746cb4b90dd9a863de)，`d18469212c86bec95303ca746cb4b90dd9a863de`；本次树核验403文件。
- 源码层级：包含独立生命周期/接纳修复候选和原source；不等所有job能力终验。
- 历史已有验证（报告层，未本轮重跑）：原loader Mac32、真实10行PARTIAL_WITH_ROWS冷读/页历史保留。新固定ac1d14已155 blob/154 manifest核验，Mac31/31合成隔离PASS、exit0；首轮1 PASS/30 setup ERROR因TMPDIR经过/var symlink，改真实非symlink TMPDIR后通过，未改产品/候选字节。旧32未重跑，完整模块0。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：新生命周期候选已有隔离成功证据，不再将ensure/events/retry/cancel/reader一律标为未交代码。完整锁环境、原生可视、自然及生命周期剩余场景仍待验；限定真实PDF/provider与现有页面部署已由本节末条单次生产补证，但部分资料未形成事实、历史PIT/正式资格仍false。Python3.14.6不同于README云端3.12.14，未安装依赖。
- 原退出标准：限定既有候选真实任务的提交/运行/结果、失败重试、取消/事件更新可追踪；GET无副作用，长任务不阻塞经理读取，状态/原PDF未核边界保留、单job回退过。
- [原M16具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/d18469212c86bec95303ca746cb4b90dd9a863de/handoffs/M16/START_HERE.md)。

## M17 尾盘量价发现与持续跟踪（P4）

> 后续限定状态：P0/M17缺FastAPI的工程阻塞已由后续锁闭包修复；完整模块、实际15:30和持续跟踪自然证据仍未完成。

- 固定源码：[`dev/m17-github-handoff-20261011`](https://github.com/lexi2016/v5/tree/6d459cbc1e694eed413d142c75be64241a727e7f)，`6d459cbc1e694eed413d142c75be64241a727e7f`；本次树核验314文件。
- 源码层级：实际owner/vendor与1530闭包参考；不能用late读回替代15:30现场。
- 历史已有验证（报告层，未本轮重跑）：接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。late100行原reader/API/页已过，不是15:30见证；1530本地源码/依赖存在，历史47PASS/1SKIP不能代替原branch固定交付。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：代码确证：完整1530闭包未挂原分支commit，未挂tree/patch不算交付；输入/时窗：原15:30现场snapshot/history/资格与后续跟踪须按原合同，late不能补现场；旧Git blob审批归属/终态未知，不猜或重复写。
- 原退出标准：先工程可运行与坏输入拒绝；再真正原窗口产物→后续跟踪→经理理由/失效条件同identity，现场/盘后恢复分别记录；无时窗就MISSED，跨日/幂等/回滚过。
- [原M17具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/6d459cbc1e694eed413d142c75be64241a727e7f/handoffs/M17/START_HERE.md)。

## M18 经理决策账本、汇总与计划（P1）

> 后续限定状态：5c327e正常WAITING是历史拒绝路径通过；10/15恢复发布修复只有未提交自报，未含在本包源码。

- 固定源码：[`dev/m18-bounded-manager-readback-20261012`](https://github.com/lexi2016/v5/tree/5c327e45d99468d0ade73ee4acff6e0130f02852)，`5c327e45d99468d0ade73ee4acff6e0130f02852`；本次树核验1370文件。
- 源码层级：bounded/request-binding源码候选；另有daily/offline小补充，完整首批经理业务未验。
- 历史已有验证（报告层，未本轮重跑）：旧真实保存账本/三策略页及c7b框架证据保留；新增请求准备候选041375在真实target14缺M15时KeyError/exit1，失败保留。窄修5c327e已Mac40/40 PASS，原请求/原cutoff实际准备正常WAITING_SOURCES、exit2，request/template与US引用null；4,590保护文件字节/大小/mtime不变，未新经理owner、refresh、daily或部署，完整0。
- 现有计划的待解缺口（须核是否已被后续增量关闭）：请求准备代码及缺M15字段的拒绝路径已修复，不能再把所有缺请求归为未交代码。真实三lane均不准入：M13原公告分析未消费/PARTIAL；M14 CANNOT_CONFIRM且690 pending不构成合法空/正式筛选；M15 NOT_RUN。manager_request/template仍null，旧target12/source09不能改日，M06不得替代三策略，原08:45–09:00窗口不补跑。
- 原退出标准：13/14/15原产物经原经理保存，普通API/页及独立reader同run/SHA；显式旧run不跳，opt-in无current503、坏generation409/未知run503语义保持；六字段同run/PIT/窗口不变、读不执行、跨日/自然/回滚过。
- [原M18具体计划/后续增量](https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/V5/docs/workflow/2026-10-13-delivery-reset/PROJECT_EXECUTION_PLAN.md)；[该候选的源码/说明入口](https://github.com/lexi2016/v5/blob/5c327e45d99468d0ade73ee4acff6e0130f02852/integration_candidates/M18_request_binding/README.md)。

