# V5项目方案与缺口执行计划

版本：2026-10-13统一执行方案。状态基线为20:23台账，补入19个原Chat本轮均已结束/该轮新增有效代码交付0，以及随后M02独立实现的完整候选776acce9328aa102e3db6973405f01260f15239d，38/38离线测试通过、35文件回读完成。M02候选现已Mac 38/38通过，新真实capture→恢复→binding→只读页面发布通过；原生视觉NOT_RUN，SOURCE_IDENTITY_ONLY/CANNOT_CONFIRM、PIT/资格false，仍非自然或完整验收。M03新固定候选efeaeb8已Mac离线23/23通过（75 blob/74 manifest），真实provider/network、HTTP和部署NOT_RUN。本文是后续执行依据，未启动的工作不记为已开工。

## 一、业务目标与首批端到端交付

### 1. 用户最终要得到什么

保留现役V4，把原18项来源、研究、选股、复盘与经理能力迁成一个可独立安装、启动、升级、每日运行并在普通页面验收的V5。可靠来源进入原算法，结果正确保存；页面能看到结果、理由、来源、日期、资格和缺口，失败后能定位、恢复、单模块回退，而不是靠人工不断催跑。

**V5可复用V4固定源码、算法、既有依赖和获准迁入的数据，但最终运行不得依赖正在运行的V4服务、V4调度、V4输出目录或暗中回退V4 API。** 原代码以完整闭包纳入V5版本，配置、输入快照、运行账本、输出和端口边界独立；迁移期借原产物验证与最终独立日生产分开验收。保留V4，不交易、不发订单、不改BUY门或风险语义，不扩系统权限或凭据。

18模块是业务职责边界，不要求重写18套算法、部署18个HTTP服务或另做18个页面。沿用原UI结构与成熟owner，兼容层只做合同/字段/路由转换，调度不包含选股算法。

### 2. 首批用户可用闭环

首批里程碑仍是原计划P1：**M13公告、M14超跌、M15美股到港股映射 → M18经理保存 → 普通API与原页面，同目标日、同run与原产物SHA可追溯。** 此处同run指页面/API/冷读对应同一经理已保存run/generation；上游模块保留各自原run、signal/session、取得时点与不可变引用，不强行统一run字符串或改写来源日期。 三条策略各自必须有原真实业务产物或经原合同证明的合法有效空；仅状态卡、fixture、字典validator、helper、悬空commit都不能签收这条闭环。

- 先把可用真实结果接通：M14已保存target14/signal13研究，690待核与历史不足是真实研究结果，现已独立接页并通过现役HTTP/DOM；它不是“正常无候选”、正式合格筛选或自然通过。
- 来源与业务并行：M02/M03独立采集补全不阻断M14已有结果的独立reader/API/分页页面，也不阻断M13/M15已有合法输入的读取、保存和接口工作。
- 经理聚合只消费已提交且原合同接受的引用。不能把旧三策略target12/source09改日套M06 target14，不能为跑通而制造manager_request、review决定或放宽PIT/窗口。
- 首批退出要核：三策略业务内容/合法有效空、原状态和理由完整可见，M18按明确target/cutoff保存，普通API/页及独立reader同run/SHA；页面刷新/日期切换不触发计算，缺lane不掩盖健康lane。若某lane只有占位/未知来源而无真实产物，首批仍未完成。
- 真实研究产物带CANNOT_CONFIRM或READY_WITH_GAPS时必须原样保留；页面接通不提升正式推荐资格。M14的690待核可以验页面真实展示，但不能被当成合法空池或正式筛选通过；是否可由某个经理请求消费，仍由原经理合同判断。

### 3. 原计划映射不变

本轮已读取[固定总计划24c6d60d](https://github.com/lexi2016/v4/blob/24c6d60d524f43fcf4209ec8b078ec02cb34417e/V5/docs/superpowers/plans/2026-10-09-v5-master-delivery.md)与[迁移执行计划d1bf0346](https://github.com/lexi2016/v4/blob/d1bf034640ca2e5957423de2745a98e159b69af2/V5/docs/superpowers/plans/2026-10-10-v5-migration-execution.md)。以下映射直接沿用原计划，后文“批次”只是排程，不是新增阶段。

|阶段|原范围|本方案用途|
|---|---|---|
|P0|发布、API、运行账本、调度、恢复与回滚底座|先行并服务每批业务；不扩成平台重建|
|P1|M13/M14/M15→M18|首批真实三策略与经理普通页面闭环|
|P2|M01/M02/M03/M05/M06|来源与预选；P1需要的来源和P1并行，不等全P2完成|
|P3|M07/M08/M09/M10|全部原阶段、竞价、尾盘/Stage8及收盘闭环|
|P4|M04/M11/M12/M16/M17|研究/视频/公开资料/尾盘辅助；M04可先为P1提供合法材料|
|P5|18模块整体、自然接续、独立交付与回滚|两个连续适用交易日及非每日业务按实际触发合同终验|

## 二、真实基线与完成定义

|层级|当前|解释|
|---|---:|---|
|部分代码入口接入|18/18|有入口、WAITING或阻塞接口不等于完整模块能力|
|真实输入或保存结果局部读回|14/18|M02/M03/M04/M06/M08/M09/M10/M12/M13/M14/M15/M16/M17/M18；类型含历史回放、恢复、保存读回，不能混成新日自然生产|
|真实数据/状态页面|14/18|同上；M14新target14独立页已现役发布、HTTP/DOM通过；原生视觉及全模块验收仍未过|
|整链自然自动通过|0|M06有限自然步骤累计1单列；整体经理接续未过|
|完整模块验收|0/18|0完成、18进行中，不因19条指令已保存而增加|

**最新实际执行状态：** 19个原Chat的本轮回复均已结束，该轮新增有效代码交付0；不能称它们正在后台并行编码。随后指定实现者已完成M02完整候选[776acce9328aa102e3db6973405f01260f15239d](https://github.com/lexi2016/v5/commit/776acce9328aa102e3db6973405f01260f15239d)：原分支正常CAS并核HEAD、38/38离线测试通过、35文件回读完成（33项manifest）。这是新增完整代码候选1；随后Mac 38/38通过，真实capture取得690 quotes、698 master及双板各698，恢复/冷读698。21:48新binding与M02-only发布完成，HTTP/DOM通过，未重启或切换产品代码；native visual NOT_RUN。仍为SOURCE_IDENTITY_ONLY/CANNOT_CONFIRM、PIT/资格false，不增加模块自然或完整验收计数。其余下文工作是计划和待派工责任，不能当作已开工。

**每模块完整验收必须同一条记录贯通：** 固定源码/依赖/配置 → 合法真实输入与原owner → 保存与新进程冷读 → 普通API/页面 → 实际触发/跨日/失败恢复 → 单模块回滚。源码、测试、部署、真实业务和自然结果分栏记证，不把测试数相加或用旧SHA证明当前HEAD。

数据不足不等于代码没有；代码有文件也不等于能力已实现。每个缺口分别标为代码、输入/业务合同、权限、时窗或待核。数据/权限/窗口不足只阻止依赖该条件的真实运行；源码、离线fixture、接口/失败边界、完整打包与测试继续做，不等未来窗口才编码。

## 三、依赖与并行批次

### 1. 已证依赖

- A链：M01→M05→M07→M09；M04向预选/阶段供研究材料，M12按可用正式视频材料供复盘。复盘/阶段结果供**下一交易日**预选，不能构成同日等待环。
- HK链：M02→M06→M08→M10；M02同时供M14价格/主表/资格，原日期分别验证。
- 首批三策略：M04→M13；M02→M14；M03+M04+M02→M15；M13/M14/M15的合法已提交结果→M18。
- M11依赖M04及在原时点已提交的市场/阶段证据；M16是固定候选公开资料job；M17是独立尾盘源/跟踪，不用阶段或超跌结果冒充。M18最终消费原合同规定的04—17已提交lane，但首批不得因其余辅助模块未齐而隐藏健康三策略。
- 任何具体原入口/日期/资格关系尚未核实的，列入对应模块待核输出，不推导新依赖或新增模块。

### 2. 立即可排的并行工作

下表是按本计划执行的队列，**M02已完成限定Mac、真实采集和只读页面发布验收；其余未启动工作按队列推进**。主控按可用执行位启动，每模块一个实现者；不把19个已结束Chat当19条活跃代码线。

|并行工作流|现在可做的完整交付|真实运行前置/停止点|首个验收出口|
|---|---|---|---|
|A1 M02来源|776acce已完成Mac 38/38及真实SDK→封存→恢复698→原binding/冷读→M02-only只读页面发布；不重复已验采集|SOURCE_IDENTITY_ONLY/CANNOT_CONFIRM；PIT/资格false、panel PENDING_PANEL_GATE，native visual NOT_RUN，后续真实调用仍按当前授权范围|保留新run/receipt与HTTP/DOM证据，继续按原合同解决目标资格/PIT及独立日常触发剩余验收；不把已成功限定链称全模块完成|
|A2 M03来源|固定efeaeb8完整候选已核75 blob/74 manifest，Mac release exit 0、新定向23/23 PASS、0 skip；原48项未重跑|真实provider/network、HTTP/DOM、发布及自然NOT_RUN；需适用US session与合法输入，新闻不能替代行情|复用离线CLI/持久化恢复证据，后续按授权验真实三件、P0/M15消费及服务页面；不把合成transport当真实采集|
|A3 M14真实页|fac269隔离已过；23:03固定组合现役切换PASS，690行22页HTTP/DOM及11路200/JSON/旧manager身份过|native visual NOT_RUN，旧超时根因未证；独立公告请求曾503后200，不称无间歇故障|保留新预览及旧61236回退，继续剩余真实资格/视觉/自然验收，不重owner或放宽等待|
|A4 M13公告|完整目录/正文/capture/审阅决策输入/导入/保存reader代码，先消费已有合法产品|新revision缺真实review决定时不能代填；缺决策不阻止离线合同与页面代码|原输入→已审核产品→消费引用同SHA；详情/分页失败状态和cutoff可定位|
|A5 M15映射|f7dd8e63已核531 blob/530 manifest，Mac新20 Python/7 Node/typecheck/build PASS；原40复用云证未重跑|合规范围3.14.6/2.3.3/24已补20项通过证据，uv.lock未同步；真实provider/资格/DOM/部署/自然未执行|保留原依赖上限，另证锁环境，再按授权核真实两路径与P0消费，不将隔离合成检查称全验收|
|A6 P0/M18|请求准备5c327e已Mac40/40及同target14 WAITING_SOURCES/exit2；原KeyError保留|M13未消费、M14 690pending非正式筛选、M15 NOT_RUN；request/template null|复用已修拒绝路径，补合法三策略原消费后再验真实请求/经理保存；不将正常WAITING算业务通过|
|A7 M04支撑|在已过完整编排上补首批13/15真正需要的来源/取得时间/正文引用缺口|缺历史取得时间不回填；未授权外传不做|原材料reader提供真实正文/来源/时点或明确UNKNOWN，供三策略同SHA消费|

M01/M05的A来源和预选代码可同时按其完整交付队列推进，但不是首批HK三策略页面的串行前置；M05新写门未获准只暂停该次真实生产，不停隔离开发。共享module_api、source_bundle、前端路由/主View和预览切换由P0唯一集成者按固定候选短批合入，不让A3/A6等同时覆盖同一文件。

### 3. 后续批次与退出条件

|批次（非新阶段）|范围与可并行方式|必须留下的可验出口|
|---|---|---|
|B 首批三策略收口|A1–A7有可用合同即可按lane接，不等全来源迁移；M18只消费原合同接受的同目标日引用|M13/M14/M15实际产物或合法空→M18保存→普通API/页和独立reader同run/SHA；缺口、资格、理由可见；不签假全绿|
|C 来源/预选全范围|M01/M02/M03完整日生产与M05七来源/M06原模型链，代码可在B期间并行|来源身份/三日期、集合/排序、有效空与缺源、失败保旧、原reader、所有范围清单齐；M05六执行lane与七业务来源映射已核|
|D 阶段/收盘|M07/M08与M09/M10按A/H两线并行，接口/fixture可先做，真实输入到位再验|全部原阶段含竞价/尾盘/HK Stage8，收盘普通API及页面；下一交易日预选依赖单列，不塞同日环|
|E 研究辅助全范围|M04各lane、M11六槽/日总结、M12真实触发生命周期、M16 job、M17原窗口跟踪可按独立owner并行|完整原生命周期、成功保留/失败恢复、普通页面及原触发语义；不得用一份存档代替全模块|
|F 自然与独立交付|依赖锁/安装包/启动和恢复脚本可前置准备；终验在业务链固定后统一执行|当前固定版完整回归、两个连续适用交易日自然接续、非每日模块按实际触发、独立V5运行和单模块回滚证据|

不承诺无依据的完成日期；以依赖满足、固定候选、Mac实际结果与真实窗口推进。窗口错过就记录MISSED/恢复身份，不回拨时钟；仍继续编码、隔离验证和为下一合法窗口准备输入合同。

## 四、18模块可执行缺口清单

每项“代码/证据”给出已知固定基线，**不是当前远端HEAD断言**；实际实施先读取该原分支HEAD并只改本模块差异。原Chat是模块交付责任入口，主控需锁定唯一真实实现者；当前Chat已结束，不等于其正在编码。共用P0与Mac职责在各项分别列出，未指定具体实现者的模块写待排，不虚报开工。

### M01 A行情与公式面板来源｜P2

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4d01-136c-83ec-83fd-2cac19e42e50)；`dev/m01-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [02cefc41](https://github.com/lexi2016/v5/commit/02cefc41aadb4358cb8485b71858ae5d6b903a56)；[Mac证据](https://github.com/lexi2016/v5/commit/ea96a80cf9d79e638ee08e15cb0bf92368261ada)。
- **已验证层级：** 接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。部分代码入口已接；公式/工程与阻塞卡已有证。真实新日来源读回、真实数据页、自然与完整验收未过。原10/09 V35公式READY/PASS，但总PARTIAL/REBUILD_REQUIRED/sync FAILED；旧V4身份仅09/11。
- **未完成缺口：** 待核代码覆盖：独立A来源日生产接管未证完整；输入：selector与M05输入身份不同，无官方generation绑定；待核：当前Windows authority/Mac调用的实际入口、固定源码与来源索引，不把旧文件存在当绑定。
- **依赖：** 原A universe/日线或VIPDOC/provider、字段单位和原公式；下游M05/M09。M01不依赖先做出A预选结果。
- **下一条完整交付：** 以现有02ce原工程为基线，交独立A来源→原公式/selector-ready面板→不可变generation/receipt→默认reader的完整可运行闭包；一次有界核查输出当前authority入口/文件/commit与缺失接口列表，随即补代码或标已具备，不停留在“继续核”。
- **验收标准：** 同一合法交易日来源/公式/05或09消费身份一致；坏单位/缺行情/错generation拒绝，失败保旧；新进程启动、保存冷读、API/页、下一适用日触发与单模块回滚分别留证。
- **责任与交接：** 原M01 Chat/唯一实现者（待排）负责采集与公式owner闭包；P0负责标准来源绑定/状态与调度接线；Mac核固定源码、真实来源与日期，不重做已过公式用例。

### M02 HK行情、主表与资格来源｜P2

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca47c7-0bd4-83e8-ab3b-3d4c2cee272a)；`dev/m02-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原owner](https://github.com/lexi2016/v5/commit/ce6cddce1ef52d63241f0d8192b6adcc118ea750)；[保存接线](https://github.com/lexi2016/v5/commit/a451275c5eee5ec63139b7e8f886624ebdd4c7d5)；[更正回执](https://github.com/lexi2016/v5/commit/7eac09efd3ffcb0e48d58b8d10e7b92a525c41df)；[完整collector候选776acce](https://github.com/lexi2016/v5/commit/776acce9328aa102e3db6973405f01260f15239d)及[启动/交付说明](https://github.com/lexi2016/v5/blob/776acce9328aa102e3db6973405f01260f15239d/integration_candidates/M02_hk_capture/README.md)。 [新Mac真实采集至页面回执](../../../../handoffs/P0/feedback/mac-m02-capture-to-page-20261013/README.md)与[原始脱敏receipt](../../../../handoffs/P0/feedback/mac-m02-capture-to-page-20261013/receipt.json)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。部分入口、真实三源build/冷读、公共安全投影和页面已过；membership7件/698、native4/HK02九资产，SOURCE_IDENTITY_ONLY、temporal CANNOT_CONFIRM、PIT/正式历史资格false。执行manual_controlled、natural_verified=false，原receipt.manual未核不赋值。
- **未完成缺口：** 验收：固定776acce已Mac 38/38通过，真实capture/七件恢复/原binding冷读/M02-only发布与HTTP/DOM通过；native visual NOT_RUN，独立日常/自然及全模块验收未过。旧collector因stock_owner NaN失败的历史保留，新严格producer的实际capture成功有独立回执。输入：完整目标资格/PIT仍未齐，panel_status=PENDING_PANEL_GATE，不能靠新代码宣称历史证据有效。
- **依赖：** 原HK provider/SDK、panel/master/membership三类各自身份、HK/Connect日历与真实取得时点；供M06/M08/M10/M14及M15身份。
- **下一条完整交付：** 复用固定776acce已通过的Mac、真实capture、恢复/冷读及页面发布证据，不重采或重做saved reader/安全页；按原合同补齐目标资格/PIT与独立日常触发/失败恢复的剩余输入、实现和验收，原生视觉单列待验。真实调用按实际授权与适用窗口推进。
- **验收标准：** 固定候选默认启动不依赖V4进程；原/新producer身份明确，旧未知或不安全仍拒绝，原字节不在旧身份下被清洗；真实任务须分别证SDK取得、合法封存、三源原reader、目标日期与消费，错误状态不伪报成功。
- **责任与交接：** 当前指定M02实现者已交固定候选并获限定Mac/真实链回执，原Chat为来源责任；P0沿原a451安全投影已发布新binding，未重启/切代码；Mac后续只验尚未覆盖部分，不能自动扩大调用或重复采集。
- **最新限定实测（2026-10-13北京时间）：** Mac 38/38；21:36真实capture为690 quotes、698 master、双板各698，恢复及独立冷reader 698。21:48新binding `314b316261ef10e9a628f997c63eb728e119a9d803b0db3c09a982cc8342a93a`，M02-only发布generation `18327ae3ac839284230437989c9418c326b8f850decc38448c354d0ddf8319f0`；HTTP直连/proxy/DOM通过、native visual NOT_RUN。M01/M03/M05 canonical与其他10路、M06 target14/100及旧经理run保持；无服务重启、无产品代码切换。SOURCE_IDENTITY_ONLY/CANNOT_CONFIRM、PIT/资格false，非自然/完整验收。

### M03 US行情来源｜P2

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8)；`dev/m03-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [3c3ed922](https://github.com/lexi2016/v5/commit/3c3ed922cb653bb8ef411bce685b1d47fb322f02)；[旧回放部署](https://github.com/lexi2016/v5/commit/aa59bfb8551b0d2f86ed88b28e9127354ff8b976)；[新交付不足反馈](https://github.com/lexi2016/v5/commit/528af98f28de0105f5d2229007cc93e345210311)。 [新完整候选efeaeb8](https://github.com/lexi2016/v5/commit/efeaeb8fc04474b1f38ebda98b35953b580049df)；[Mac离线回执](../../../../handoffs/P0/feedback/mac-m03-isolated-offline-20261013/README.md)及[receipt](../../../../handoffs/P0/feedback/mac-m03-isolated-offline-20261013/receipt.json)。
- **已验证层级：** 原20261009 POST_CLOSE三件录制回放→snapshot→binding→API/页证据保留；新候选efeaeb8已核75个Git blob、74项manifest与release SHA，Mac verify_release exit 0，新3个定向测试模块23/23 PASS、0 skip，候选字节未变。旧48项历史测试未重跑；该离线轮尚未运行真实provider/network，后续原窗口真实来源与M15消费见本节末条；后续3020单卡HTTP/DOM与CAS发布已过（见本节最新条）；原生视觉及自然仍未证明。
- **未完成缺口：** 新固定行情collector/默认入口候选已交且Mac离线23项通过，不能再标为仅字典validator或未交候选。已完成一次适用US session/cutoff真实采集、原三件保存/冷读及M15 seed消费；普通页面单卡发布已完成；待验下一适用session自动更新、原生可视及完整来源能力；12/13新闻三件仍不能替代行情snapshot。
- **依赖：** 原US provider、交易日/phase/session/DST与抓取cutoff；输出digest payload/manifest/receipt给M15，不能用US映射结果反充M03行情。
- **下一条完整交付：** 复用固定efeaeb8及此次Mac离线证据，复用本节末条已过真实provider→原三件→M15 seed证据，复用已过普通页面发布，继续下一适用session自动更新与剩余恢复验证，不重复采集或重算。已有23项与未受影响历史回放不重复运行。
- **验收标准：** 三件同session、SHA/receipt/manifest一致，取得不晚于消费cutoff；错session/缺报价/假READY明确拒绝，下一适用session自动更新且旧成功保留；普通来源页和M15消费同identity。
- **责任与交接：** M03候选已固定并完成本次Mac离线验收，产品失败仍回唯一实现者；P0负责来源→M15 request/页面接线；Mac后续只验尚未覆盖的真实session/服务与页面，不将合成transport测试称真实采集。
- **最新限定实测：** 2026-10-13 21:59:26.657973–21:59:46.409228（北京时间），既有Python 3.14.6，无依赖安装；release exit 0、新测试23/23 PASS，包含独立CLI拒绝及保存后回执丢失恢复且不再请求quote。只用合成时钟与transport，未操作现役M03、V4、共享输出或监听端口；无产品修改。

- **原窗口真实增量（2026-10-13 UTC20:15）：** 固定efeaeb8实际20:15:00.006819–20:15:01.191301 exit0，VALIDATED_SOURCE_BINDING，33/33报价＋24主题、HTTP200无fallback；capture b9bdd3ba013cb4bb3680f150，原三件/独立冷reader/磁盘binding通过，并于20:20后被M15 seed真实消费。仅主控单次原窗口执行，不是自然调度；此时新页面接线待回，后续3020单卡发布见下一条，不计完整验收。[合并派生反馈](../../../../handoffs/P0/feedback/mac-m03-m15-window-20261014/README.md)。

- **普通页单卡最终发布（2026-10-13 UTC21:33）：** e18c6c9aa8e5ba84dd0b0b412ed7d62b5ebc2b67的12 adapter＋6单卡/真实只读通过，但隔离publish_source_result因四现役路由未列allowed报SOURCE_MODULE_ID_REQUIRED，未触现役；失败保留。3020bb6b0abd30fc9a243cfdee7ec0f121e2c178精确两文件增量补齐四路由，前后SHA匹配、7/7单卡PASS，21:33:31.808–44.075单卡CAS及HTTP/DOM通过；generation7c2529a5…→5ac3f270…，仅1状态record改变，其余3卡/14路由/M15三records/M16/经理不变。33quotes/24themes及原capture/run/binding/sourceSHA一致，无重采或重启，仍50490/PID29056、54780/PID29127；该Mac轮native visual/广泛回归NOT_RUN；另主控补充云端全P0终态1378tests/48failures/89errors/17skips，M03新7项及15路由相关5项PASS，不将全量失败统称环境问题，也不抹除独立真实验收。14页面/0完整不变。[失败与最终发布证据](../../../../handoffs/P0/feedback/mac-m03-m15-window-20261014/README.md)。

### M04 研究情报与归档｜P4

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4d57-024c-83ec-9d59-f3b246eeda6a)；`dev/m04-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [完整编排](https://github.com/lexi2016/v5/commit/8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7)；[只读接线](https://github.com/lexi2016/v5/commit/447683268a289af9fe980b90807284de42f1ea13)；[Mac/部署](https://github.com/lexi2016/v5/commit/a8bb8cdaf058deee9eacc5c6b1b11b2e21d081a3)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。持久编排/失败续接工程已交且定向Mac过；18篇原归档冷读与页面已过，53范围外错误/PIT UNKNOWN保留。原reader、builder/import源码不应被说成不存在。
- **未完成缺口：** 输入：取得时点、主题、全lane真实覆盖未齐；待核代码覆盖：完整来源日流实际可运行覆盖需按已有编排核对，不能只增加reader wrapper；待核：两组原回归未验范围及首批13/15真正所需lane。
- **依赖：** 原小时研究/早报/公众号/正文/图片/OCR来源与真实捕获回执；供M05/M07/M11/M13/M15，非每个消费者都必须等全归档库迁完。
- **下一条完整交付：** 用已过编排完成首批所需资料的采集/原builder/import/store/新进程reader闭环，交每lane入口与成功/缺失/恢复范围表、必要代码差异和定向测试；不重读18篇充数。
- **验收标准：** 至少一个真实常规触发与失败续跑同原文/span/来源SHA，图片/OCR缺失明确；不补历史取得时间，消费者同SHA；随后覆盖原lane集合、普通页和实际触发/回滚。
- **责任与交接：** M04原Chat/唯一实现者待排负责来源及原编排；P0负责合法材料引用/来源页；Mac按lane验固定候选，成功前置节点不重做，真实材料不随源码自动上传。
- **最新候选验收（与旧已过编排分开）：** 原9736bf2e807b2aa22e2541a4375b182e1ddceb24的8 PASS / 2 FAIL / 11 ERROR原回执保留；含空格解释器测试shebang窄修后，固定8266c6ed9606b0912328670c7411743a85af5727于Mac22/22 PASS、0 FAIL/ERROR/SKIP，exit0，482 blob/481 manifest核验。只变测试夹具/report/log/RELEASE，业务与原owner字节不变；旧18篇/原scope suite未重跑，真实provider/network、部署/原生页面/自然未验，锁依赖NOT_RUN（pandas3.0.5/pyarrow25.0.1超声明上限）。[新旧原回执](../../../../handoffs/P0/feedback/mac-m04-8266c6-retest-20261013/README.md)。
- **研报普通页新发布（北京时间2026-10-14 00:01）：** 固定P0 d3c52b4f08cbe6af9f69326461109004ac36c95c绑定M04 8266c6，HTTP/jsdom DOM发布PASS；54780/PID11869与source51363/PID11000，旧56563/63668/V4保留，12路由/经理descriptor及2,688文件不变。实际仅20261012旧归档18条，均无正文、取得时点UNKNOWN、source_run_id=null；53范围外错误保留，小时未生成/公众号未配置。未新采集/补算，native visual工具超时NOT_RUN。[原回执及已知503问题](../../../../handoffs/P0/feedback/mac-research-d3c52b-deployed-20261014/README.md)。
- **快速切日问题限定修复（北京时间2026-10-14 00:16）：** 固定0a7d03c9e5d292ccffe2e09f1ca8be88feea50e1已前端发布PASS，Mac35/35定向与typecheck/build通过；实际最终日期自动读回、lane最大在途1，probe持续503三次退出并可手动恢复。仅54780/PID14238更新，后端51363/PID11000与2,688保护文件不变。原BUSY503失败历史保留，此限定页面问题已闭环，不宣称系统无503；18旧归档的无正文/UNKNOWN及native visual NOT_RUN、非自然/全模块边界不变。[修复发布原回执](../../../../handoffs/P0/feedback/mac-research-0a7d03-date-fix-20261014/README.md)。
- **新增来源合同兼容实测（北京时间2026-10-14 00:29）：** 固定a6ccecbadb19a036082c3e2790ba0a259f26ba4f，Mac Python3.13.12/pandas2.3.3/pyarrow23.0.1下27/27 PASS、零skip；实际合成1001行健康Parquet→原analyzer/capture正文与时点→冷reader通过，未知CLI信封fail-closed和合法空通过，484源文件哈希不变。仅离线兼容证据，全V5锁环境NOT_RUN、官方CLI未执行、安装CLI全文保证UNVERIFIED；未改全局声明/依赖/现役服务，真实capture及自然/全模块未验。该轮限定兼容profile当时尚待原作者完成，后续最终准备证据见下项。[原Mac回执](../../../../handoffs/P0/feedback/mac-m04-a6ccec-compatibility-20261014/result.json)。
- **最终profile准备（北京时间2026-10-14 00:37）：** 固定261cf0123dd7175bfcc6031a5dc201604a98a609，Mac33/33 PASS、零skip；独立M04环境精确匹配3.13.12/2.3.3/23.0.1，488源hash不变，validate/init exit0，独立空runtime且capture=0。该准备阶段最早10月14日08:30，生产/官方CLI当时尚未执行；后续真实capture恢复见末条，不能将当时login/全文UNVERIFIED泛化为已证全覆盖，CLI独立封包未完成；旧09日selector4989不宣称新鲜，全V5锁环境NOT_RUN。仅最终准备通过，不计真实源/自然/全模块。[准备原回执](../../../../handoffs/P0/feedback/mac-m04-261cf0-readiness-20261014/readiness.json)。

- **真实窗口失败→保存capture恢复（2026-10-14 UTC01:00）：** 261cf在00:30仅capture一次，30topics/22effective/21raw/11research/8articles；首篇evidence换行失败，63c1 Mac37后既有guard阻，d19f Mac43复用checkpoint后第二档非连续builder摘要阻，均保留。全8只读归类后d5983dc7d3dfc6825b7d09b5fb976197943de40a表示合同修复，494清单/Mac47 PASS零skip，01:00:33.469–34.656原claim单次resume SUCCEEDED/exit0，01:00:55.679–56.171独立原reader读8档exit0零写。1原quote/4空白映射/3原builder摘要NOT_A_SOURCE_QUOTE，002430原tag/decoder/标题compact身份已证；原receipt/checkpoint/capture及旧失败不变，后续capture0。未改页或部署，natural/PIT/production=false、bounded_has_more保留，14页面/0完整不变，不把21raw记21archives或恢复算自然。[完整派生链](../../../../handoffs/P0/feedback/mac-m04-real-window-recovery-20261014/README.md)。

### M05 A预选池｜P2

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4eef-525c-83e8-abb9-d8423024bf90)；`dev/m05-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [合法空适配](https://github.com/lexi2016/v5/commit/50adce44ea047c8ee9435a5e703a2125264243c4)；[release清单](https://github.com/lexi2016/v5/commit/5d868fc09fba7f7fe210e603a28015e271117077)；[原工程](https://github.com/lexi2016/v5/commit/2c5d1eb2c9572469bf04ad86fd61e92ee8674fe8)。
- **已验证层级：** 接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。部分入口已接；Mac7项合法空/非空回归及隔离历史120行strict READY冷读已过，但没有同日M01绑定/PIT，产品未保存/接真实页；不能增加真实产品计数。
- **未完成缺口：** 待核映射：原七业务来源V192/FUPAN/Stage7/公众号/白毛/hourly research/research preview，与现六执行lane/物理池并非已证明一一对应；代码按映射补缺。输入：M01官方generation/同日合同缺；权限：新单池permit/OPEN/build问题未获答复，只暂停该次真实应用写入。
- **依赖：** M01/M04及原七池算法；FUPAN/阶段材料按上一有效业务日到下一目标日，不能造成M05↔M07/M09同日循环；供M07。
- **下一条完整交付：** 以当前固定commit一次产出“七来源→build/消费lane→入口/物理产物/commit”映射，同一任务即转补实现或标已具备；映射随最终完整交付回执，不要求单独文档commit或等待确认。按确证缺口补完整聚合/保存reader/隔离CLI与release覆盖；不把六lane宣称七来源完成，不自动创建permit或OPEN门。
- **验收标准：** 七来源各适用状态齐、原去重/集合/顺序不变；verified empty≠缺源/CANNOT_CONFIRM，可选lane坏不清健康lane；经合法permit的真实产物、原reader、M07消费、API/页/下一日/回滚同identity。
- **责任与交接：** M05原Chat/唯一实现者待排负责七来源完整链与writer合同；P0负责M01/M04引用/下游接线；Mac可先离线fixture/reader验，获准后才做单池真实写门，不能全模块停工。

### M06 HK预选池｜P2

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4f4a-ef44-83ec-89e1-bcaaed88d4a5)；`dev/m06-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原owner](https://github.com/lexi2016/v5/commit/08ed9de9ddb5fd2c62eb1762df2f6106464d823b)；[current/daily](https://github.com/lexi2016/v5/commit/c518d0c4bf8d947881586a7ed667f2a9ac5c6d1e)；[自然与动态页证据](https://github.com/lexi2016/v5/commit/e200cafbece378343d04a654c9819746357ae03e)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。真实原模型100行、存量池双账本/current/动态页已过；17:32自然步骤一次成功，target14/signal/eligibility13，后续复用且窗口末无重owner/model。整链daily仍false、经理POST_OWNER请求缺失，有限自然不等完整模块。
- **未完成缺口：** 输入/资格：完整PIT/目标资格未齐；集成：合法下游manager request/引用接续未闭环（主要P0/M18责任）。代码完整性待核仅限模块独立日生产、输入/输出标准合同与失败恢复，不重写已过自然current链。
- **依赖：** M02真实panel/master/资格、HK02固定模型/名称资产/日历与原排序；供M08/M10及合法经理消费，不能静默读旧池。
- **下一条完整交付：** 沿已有完整owner补剩余标准结果/引用导出、原generator与独立V5来源配置、失败/UNKNOWN幂等边界的实际差异；若代码已具备，提交固定版本完整入口/依赖索引，不为制造commit重算模型。
- **验收标准：** 原新日Top100或合同允许存量模式分别留证，全100行排序/权重与三日期正确，坏日期/资格未知拒绝或保留状态；M08消费同identity，连续适用日、窗口关闭不补跑与回滚过。
- **责任与交接：** M06原Chat/唯一实现者待排核模块剩余代码；P0/M18负责下游请求/自动接续，不重复M06产品；Mac复用已过模型/自然证据，只验改动与真实下一合法窗口。

### M07 A阶段选股｜P3

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4fc6-4640-83ee-aab0-22512e215276)；`dev/m07-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [完整链](https://github.com/lexi2016/v5/commit/e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31)；[WAITING接线](https://github.com/lexi2016/v5/commit/eec2220b674182441d0f50d689c66ec2184527c6)；[Mac反馈](https://github.com/lexi2016/v5/commit/f901a43a3281e6663cda18261371f49cfc8bebad)。
- **已验证层级：** 接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。完整链Mac63+31和只读入口/HTTP/DOM已过；无合法真实stage绑定/股票页，四缺口WAITING，formal BLOCKED/temporal=false。
- **未完成缺口：** 输入：M05六物理池（与七业务来源映射待核）、M01 raw三件/记录时钟、M04小时见证/morning、M07已验证保存引用缺；待核代码覆盖：合法request/binding准备与全部原stage可运行覆盖须核后补，不能只做占位页。
- **依赖：** M05、M01实时/原录制与M04研究；普通/竞价/尾盘各自原窗口，供M09。
- **下一条完整交付：** 在e99b完整链上交合法四源准备/验证→原各阶段执行→保存/reader/页面的完整缺口包；一次列全普通/竞价/尾盘入口/commit及已有测试覆盖，补缺而不重写原算法。
- **验收标准：** 原每个A阶段包括竞价/尾盘有对应窗口真实输入与结果/冷读/页一致；错窗口/缺源明确拒绝，恢复身份单列；M09可追溯，下一适用触发及独立回滚过。
- **责任与交接：** M07原Chat/唯一实现者待排负责完整阶段链；P0绑定标准来源/页面及调度；Mac按原窗口验，不能用当前行情补早盘，已过63+31不无故重跑。

### M08 HK阶段选股｜P3

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb9208-1504-83ee-a9fd-d8feb3dcfb48)；`dev/m08-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原完整owner](https://github.com/lexi2016/v5/commit/8f08967ee01c2679dacd0d78d0a2a028867f1967)；[固定START_HERE](https://github.com/lexi2016/v5/blob/8f08967ee01c2679dacd0d78d0a2a028867f1967/handoffs/M08/START_HERE.md)；[保存接线](https://github.com/lexi2016/v5/commit/08c101d6e7f53d1d1519c3859c6b1d985c32d221)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。真实池适配、10套八阶段历史结果独立冷读/页面已过；历史局部不等全部真实新阶段生成。原40位SHA已核，原Chat错误展开的38位不采用。
- **未完成缺口：** 输入：Stage8完整重算输入、普通阶段时点/成员/单位/PIT/资格未齐；待核代码：竞价/Stage8/普通各入口和实际配置，不把旧只读包当全生产，也不认为全部owner未交。
- **依赖：** M06、M02实时/Connect资格、M04研究及HK日历；供M10七阶段归因，Stage8独立不混算。
- **下一条完整交付：** 基于完整固定owner核并补全部HK阶段/竞价/Stage8独立入口、保存reader与原页面合同，交阶段覆盖表/缺输入负例/启动说明，使用完整工具返回SHA，不手扩短hash。
- **验收标准：** 每个原窗口同日同源输入/结果/独立页一致，池日期与阶段身份不漂移；半日未知拒绝、单位/资格未知保留，M10七阶段引用正确、自然接续及独立回滚过。
- **责任与交接：** M08原Chat/唯一实现者待排负责完整阶段实现；P0独立路由/调度；Mac按固定闭包逐缺口验，已过10套历史读回不重做，404先核精确引用不归权限。

### M09 A收盘复盘｜P3

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb63a0-57a4-83ee-8f96-e5c6936b6405)；`v5/m09-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [研究候选](https://github.com/lexi2016/v5/commit/084df7c61e57e7615633828a0d6a5d9078dc9b1c)；[集成/部署](https://github.com/lexi2016/v5/commit/864fd1d9f2305c8fd236da6b363909ed92274d11)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。两日真实录制研究回放/冷读与页已过，PARTIAL/source_time/成员/PIT/资格边界保留；完整新日自然未过。
- **未完成缺口：** 输入：当日全panel、阶段证据与可用视频正式材料；待核代码覆盖：独立新日采集/owner/publisher/reader和双槽触发完整接管未实证，先核固定入口再补真实缺口，不另造模型。
- **依赖：** M01/M07/M12；16:05/17:10是原触发槽，15:30是输入门，不能混同。复盘结果供下一目标日预选。
- **下一条完整交付：** 交原两槽来源准备→确定性原模型→持久发布→原reader/API/页完整可运行包与缺阶段/错时点测试；复用已过回放，不校准常量改善结果。
- **验收标准：** 两槽各自完整真实输入/产物身份可核，缺阶段和正式材料独立披露；原模型等价、普通页可读，跨日/实际触发及与HK隔离回滚过。
- **责任与交接：** M09原Chat/唯一实现者待排用真实原分支v5/m09-handoff-20261011；P0负责A/H共享读路径隔离；Mac验原槽/全panel，不能拿阶段Top10替代。

### M10 HK收盘复盘｜P3

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb8fe5-807c-83e8-867b-f41893d0d4be)；`dev/m10-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [1c0d56d0](https://github.com/lexi2016/v5/commit/1c0d56d0ea350f8f2178d8b0c6b7e66dfa113585)；[Mac/部署](https://github.com/lexi2016/v5/commit/c64adfca99041951b45bc4fda600b99e68d07d5e)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。698录制输入、20/100/70/20投影、七阶段PARTIAL/null的发布冷读/页已过；新日完整scheduler/来源资格未过。
- **未完成缺口：** 输入：M02全声明收盘集合、M06池、M08七阶段；待核：原scheduler/runtime及历史未验依赖是否齐，不能将NOT_RUN推成物理缺件。
- **依赖：** M02/M06/M08；A/H日历分开，Stage8不得补成七阶段。
- **下一条完整交付：** 在原owner上补新日collector/原算法/publisher/普通reader的确证缺口、完整scheduler入口与依赖说明，交缺阶段/错日期/跨市场保护测试。
- **验收标准：** 一个合法新收盘日全链与下一适用日更新，20/100/七阶段可追溯、PARTIAL保持，API/页与冷读同run，回退不覆盖M09。
- **责任与交接：** M10原Chat/唯一实现者待排负责HK收盘全链；P0协调A/H普通路径和调度；Mac先核依赖后定向验，不重跑已过原回归充数。

### M11 盘中研究与研究复盘｜P4

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb8ea5-0d24-83e8-ad96-382d1699c591)；`dev/m11-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [完整owner](https://github.com/lexi2016/v5/commit/f932059eff5e425d0e3c381f9e4610e62e6e0cc2)；[安全修](https://github.com/lexi2016/v5/commit/cc29974b15f2199aef3f19100c91a9195f217074)；[接线](https://github.com/lexi2016/v5/commit/490529f549324fb435af56d5f728672ad6390b72)；[Mac](https://github.com/lexi2016/v5/commit/39a903afbdd95f110463c8372aa493e81b7209cd)。
- **已验证层级：** 接入已具备；真实/保存局部未过；数据页未过，仅阻塞/WAITING；完整0。默认owner/独立reader、六槽API、安全修及工程页已过；真实页仍六项WAITING，广域失败不能被窄修抹除。reflection原cache_root与wrapper各8/8存在，不再当缺件。
- **未完成缺口：** 输入/身份：原snapshot源hash/pins/当时可用证据未齐，r4身份不能混F版；权限：旧元信息外传未获准；时窗：今日15:00已MISSED，不可补采。代码侧可补独立合法输入/可信pins/原sentiment核心接线。
- **依赖：** M04、原slot配置及当时已提交市场/阶段；不能用收盘后资料冒充盘中。
- **下一条完整交付：** 沿现有完整owner补合法新构建身份/输入绑定、独立capture→原六槽/日总结→保存reader的缺口，交固定入口/来源清单与错时点/错pin负例；离线fixture和代码可做，未获准元信息不外传。
- **验收标准：** 原slot集合与日总结原引用/时点/结果一致，缺slot可见、中断续原步骤；实际下一适用触发、普通页和回滚过，源不齐不显示真实研究成功。
- **责任与交接：** M11原Chat/唯一实现者待排负责原研究生命周期和构建身份；P0负责已提交slot状态读取；Mac按固定候选/真实时点验，待答外传权限只挡对应材料传输；采集另外按真实窗口、来源准入和已有授权判断，不全模块停工。

### M12 视频FUPAN｜P4

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb99cc-7b94-83ec-97c6-edb09318fa50)；`dev/m12-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原生命周期](https://github.com/lexi2016/v5/commit/4bbf069b435d8f0ba28db8e2eba1d358ea5e283c)；[接线](https://github.com/lexi2016/v5/commit/c353334d70972033ae86f7175504ca675bafbb68)；[原生导入](https://github.com/lexi2016/v5/commit/345a75140d1a991b0e109bad4c90a1f5744434a1)；[真实反馈](https://github.com/lexi2016/v5/commit/92700169f97a7da17079f2d868fb86ed1242b5e0)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。原生命周期局部恢复、17原生件原样导入/冷读/HTTP/页已过；ASR待复核、字典缺失保留。真实新采集/完整自然生命周期未过，不能把旧档导入当新视频生成。
- **未完成缺口：** 代码待核：原采集/下载/ASR/OCR/字典/对齐/gap/发布各入口是否全封装可独立启动；输入/运行绑定：媒体来源及字典需合法可用；不推定原生命周期不存在。
- **依赖：** 原视频及各节点产物、字典/模型配置；供M09/下一目标日预选适用材料，按真实视频触发而非强编每日任务。
- **下一条完整交付：** 核已有4bb/c353完整节点表后，只补独立入口、显式重试/恢复、字典缺失处理、发布reader代码缺口，交成功节点复用/失败后续跑测试与启动说明。
- **验收标准：** 同视频全原节点可发布/冷读，后续失败不重下/重转成功媒体；ASR/字典缺口可见，页面节点状态与实际触发、回滚齐，不自动新ASR生产。
- **责任与交接：** M12原Chat/唯一实现者待排负责生命周期；P0隔离长任务与普通API并供材料引用；Mac从实际失败节点定向验，17件已过导入不重做。

### M13 公告研究与选股｜P1

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4a2f-ffc8-83e8-87af-a0f03cd54a35)；`dev/m13-partial-pages-20261012（已核开发分支，更早原主分支未确认，先只读核原Chat/分支）`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [308af268](https://github.com/lexi2016/v5/commit/308af26862daf005c5c5800d15c5053c84275938)；[页面证据](https://github.com/lexi2016/v5/commit/efdc43a955024042dfb78707c97b94e6f7d74fed)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。原公告保存研究与页面已有证，当前页32不是历史总量；PIT CANNOT_CONFIRM/资格NOT_ASSESSED。真实独审修订导入/后续日闭环未过。
- **未完成缺口：** 输入/业务合同：新revision缺真实review决定/ack与返回SHA；代码：详情/分页失败、capture与cutoff消费连接仍有断点，需要核完整原目录→正文→语义→导入链，不以新wrapper替代。
- **依赖：** M04合法材料、原公告目录/正文与publication/capture/cutoff、独立reviewer/修订父产品；供M18，不能假造决定或新队列/凭据。
- **下一条完整交付：** 以已有合法产品先接完整普通详情/reader与cutoff消费，同时补原独审提交/返回/导入合同的实际代码缺口、错误/未审可见状态和测试；新review输入未到仍可交代码。
- **验收标准：** 原目录→正文→合法独审导入→M18同SHA消费→普通API/页同run；未消费可定位，0/null/缺源分开，后续日/回滚成立；缺真实review不签业务链完成。
- **责任与交接：** M13原Chat/唯一实现者待排；原主分支先只读核，已知dev/m13-partial-pages-20261012不擅自当唯一原支。P0负责M18消费与普通详情路由；Mac核已有合法产品/真实review返回，不能替人审。

### M14 超跌研究与选股｜P1

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4e2a-ea0c-83e8-a4fa-dc01a13867bf)；`dev/m14-github-handoff-20261011；补充dev/m14-stored-supplement-20261012`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原封装](https://github.com/lexi2016/v5/commit/a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba)；[未完整接页反馈](https://github.com/lexi2016/v5/commit/8869a79d97b9b1eb2769b7aadf466d34b0e957c4)；原数值owner固定884548fea0a0056483e8175564eaee015a964023（所在仓库/branch待核，不拼URL）。 [fac269候选](https://github.com/lexi2016/v5/commit/fac269ade842eb1d9b54c604b77091b0cd58bd44)；[Mac原回执与后续部署状态](../../../../handoffs/P0/feedback/mac-m14-fac269-isolated-20261013/README.md)。 [现役发布成功与失败历史](../../../../handoffs/P0/feedback/mac-m14-deployed-20261013/README.md)。
- **已验证层级：** 新target14/signal13原保存run da7ae8f55b45416596e5c2d1e69b9b17仍为strict0/near0/pending690、READY_WITH_GAPS/正式CANNOT_CONFIRM。fac269隔离15 Vue/typecheck/build及真实分页通过后，23:03固定c7b→52e71→fac组合实际切换PASS并保留新预览；690行22页HTTP/DOM、其他11路200/JSON及旧manager descriptor核验通过。未重owner，native visual NOT_RUN，daily opt-in=false，不增加自然或完整验收计数。
- **未完成缺口：** 前次部署DOM等待超时并回退历史保留，重试成功不证明旧根因。success快照两个pending原浏览器请求无法续观；独立HTTP后验公告32/147与旧超跌strict31/214为200同身份，但首次并行公告503/CANNOT_CONFIRM保留，不称全无间歇故障。原生视觉NOT_RUN，历史不足、PIT/资格与完整验收仍未闭环。
- **依赖：** M02原panel/master/目标资格、原历史/单位与两门算法；现有真实保存run已可作为独立页输入，不必等M02新collector，也不必先有当日M18生产。
- **下一条完整交付：** 保留新预览与完整成功/失败证据，后续只处理剩余确证故障及原生视觉、合法输入/资格/自然与单模块验收；不为重试成功补造旧故障根因，不重owner或覆盖旧经理日期。
- **验收标准：** 新进程原reader与API每页合并结果同run/SHA，无漏重/截断；690待核和历史不足清晰，非正常空候选；错ref/date/私有路径不泄露、日期切换清旧、GET无生成，旧M18/其他17保持且可回退。
- **责任与交接（原发布历史，最新进程见本节末条）：** P0原固定组合发布时预览54780/PID3345、source56563/PID3337，旧61236留回退，M02 generation18327及V4/保护进程保持。Mac末次15:14:19 UTC健康200且进程存活；未改产品或400×100ms等待条件。剩余异常按原日志交唯一实现者，不推断根因。
- **有限canary与来源口径问题（北京时间2026-10-14 01:58–02:04）：** 固定c52aca63e7aac5a1f450bd5d1e11ae805fe0cb31离线18 PASS，真实3码各120 bars、原端点一次连接无重试，11键仅覆盖10，缺HK.03469/20261012；原decoder10键PASS/全11键missing，726保护文件不变。与旧panel比较发现混合历史来源及trade显著差异，单位/price basis未证，不能乘100或混补；当时停止混源修复并准备同源批量/窗口代码；后续批量采集见下一条，单位/price basis与资格问题仍未解决。[派生摘要证据](../../../../handoffs/P0/feedback/mac-m14-canary-m15-environment-summary-20261014/README.md)。

- **真实全批采集终态（北京时间2026-10-14 02:24–02:36）：** 固定02193d90221b24f59b0678fc3035eaa128791259实际CAPTURED/exit0，739.96秒；新增687/687成功＋3份旧canary逐字复用，共690回执/80792完整响应行，失败、未知、未执行、重试均0，单连接最小请求间隔1.046427秒。2574缺键覆盖2223，仍缺351键/24码，HK.03469/20261012仍缺；732保护文件含714个.day未变。批量离线28/28 PASS，准备器7/8的临时目录符号链接失败保留，物理路径等价核验通过，不称全绿。该采集阶段未repair/owner/发布/正式准入，repair_ready=false；随后同源adapter计算与页面发布见下一条，旧跨源trade口径问题不被采集成功消除。[终态派生摘要](../../../../handoffs/P0/feedback/mac-m14-batch-capture-20261014/README.md)。

- **同源计算与窗口页面最新验收（北京时间2026-10-14）：** 运行代码bbf3e43adc60ad41bdef95998f15483ff0988660、后续文档c9f8c7b41e492cb8017c68ac848cdc8f4ff35718；Mac33/33 PASS，复用690回执无新网络，40930行/690股，cutoff2026-10-13T18:40:58.776354Z。首次输出根未初始化在计算前失败保留，初始化后唯一实际owner run9c70cc6cb8e34afb9e34b366acf8becd及新旧冷读通过；仍strict0/near0/pending690，688历史缺口、2原始异常、另3 previous5重叠缺口，全690响应缺20260925，不改日历/补零/混源。初次reader投影展示缺口保留；a7eb3a9c4cf9f35ab7ba9830d41a29644201a788已4投影＋5Vue/typecheck/build及隔离/发布HTTP-DOM PASS，公开cutoff/行数/同源合同/scale1/原缺口，机器字段折叠。当前source58799/PID26199、54780/PID26268；13其他路由、732原文件、2760journal及owner产物不变，发布未重算。native visual NOT_RUN，单位/price basis/资格未证、自然与完整0/18不变。[合并增量验收](../../../../handoffs/P0/feedback/mac-m14-window-and-visibility-20261014/README.md)。

- **P0槽修隔离验收（2026-10-13 UTC22:42）：** 固定0ac1e78ccb54049e0a4a66d6254e5ecb68810086，Mac槽8/8及原M14/API合成23/23 PASS，精确前后SHA/清单/正反patch通过，临时目录与进程已清理。真实690行读/发布/现役变更未执行：安全检查拒绝，具体用户批准请求Sentinel_7aaff2c41a408191a58afcfa40ed7e72待答。合成690不计真实验收，不改变页面或14/0计数。[派生隔离反馈](../../../../handoffs/P0/feedback/mac-m14-slot-isolated-20261014/README.md)。

### M15 美股到港股映射｜P1

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca4b1c-7bac-83ec-878c-d1fb0bd37b38)；`dev/m15-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [1dede80b](https://github.com/lexi2016/v5/commit/1dede80b4ff18781849e87e85ca693890ed57979)；[页面证据](https://github.com/lexi2016/v5/commit/d53e0820318462806d9e67dae1818bb684b38ade)。 [最终完整候选f7dd8e63](https://github.com/lexi2016/v5/commit/f7dd8e63a7c9fac67ad1cd84b3d6ebc2dbced5af)；[候选README](https://github.com/lexi2016/v5/blob/f7dd8e63a7c9fac67ad1cd84b3d6ebc2dbced5af/integration_candidates/M15_mapping/README.md)。 [Mac原回执](../../../../handoffs/P0/feedback/mac-m15-f7dd-isolated-20261013/result.json)。
- **已验证层级：** 原四关系/三HK保存读回与页面历史保留；最终f7dd8e63已531 blob/530 manifest核验，RELEASE SHA-256为8cb4cd4db7b9e8dccba527ec844dde9f7787d54ac1dd88cae0ded97e6db23507。Mac新增20 Python与7 Node、typecheck/build通过，候选字节未变；原40项复用此前云端证据，未在Mac重跑。两条原cold reader在合成fixture上MATCHED；该隔离轮未运行真实provider；后续原窗口seed真实消费/保存/冷读已通过（见末条），源资格、material、自然仍未过；后续821a25普通页HTTP/DOM及发布已过（见最新条），完整0。
- **未完成缺口：** 首轮Mac使用超声明版本的历史保留；现已找到满足声明范围的3.14.6/2.3.3/24环境，新增20项各有通过证据（19初次PASS＋1沙箱loopback单项补跑PASS）。uv.lock未同步，完整锁安装不冒称通过；M03真实snapshot及seed消费现已通过；material正文span/取得时点与HK身份、PIT/资格、原生可视及完整验收仍待验；seed普通页HTTP/DOM与发布已通过。
- **依赖：** M03同session行情、原种子/registry；M04原主体/正文/命题/真实可用时点及M02 native/目标资格；供M18。种子daily和材料（行业/主题、个股）路径分别验。
- **下一条完整交付：** 复用f7dd8e63既有Node/typecheck/build与最新合规范围环境20项证据，不再把已消除的版本范围缺口当阻塞；复用已过M03真实三件与seed消费，按实际授权推进未完成的material路径、P0/M18合法消费及普通页。uv.lock/完整安装另记，不提前采集或owner。
- **验收标准：** 两路径各有真实结果或按原合同准确拒绝，保存/普通页同身份；原范围外未知、目标资格和自然身份不变，M18同session合法消费，下一适用session/回滚过。
- **责任与交接：** M15唯一实现者保留最终固定候选与依赖声明；Mac隔离检查回执已到，锁依赖/material真实源/原生视觉等剩余范围另行验收，seed真实来源消费及普通页发布已过。P0负责必要标准引用与M18展示接线，不把合成或云端历史结果计为真实生产。
- **环境复验摘要（2026-10-13 18:09 UTC）：** 现有Python3.14.6/pandas2.3.3/pyarrow24.0.0及三时区符合README；首次19 PASS/1沙箱loopback错误、exit1，仅该项补跑PASS/exit0，20项各有证据而非一次全绿。530 release核验，544现有文件字节不变；旧40/Node/build未重跑，未安装/改声明/同步uv.lock，新采集及owner未运行。[派生摘要](../../../../handoffs/P0/feedback/mac-m14-canary-m15-environment-summary-20261014/summary.json)。

- **原窗口seed真实增量（2026-10-13 UTC20:20）：** f7dd在20:20:00.011283之后prepare，20:20:00.704290冷读完成，prepare/init/run/persist/read全0、COMPLETED/MATCHED。delivery50eda19e511e4247ab07ac9ee2f647e1，owner08f7e457adb046df9db509df43326a29，原四关系仅2匹配；session13/target14、资格CANNOT_CONFIRM/覆盖PARTIAL、material=null，historical availability未建立。主控原窗口单次执行，非自然调度；当时尚未部署；后续821a25发布见下一条，不增加完整模块计数。[身份及指纹](../../../../handoffs/P0/feedback/mac-m03-m15-window-20261014/summary.json)。

- **seed普通页发布（2026-10-13 UTC20:38）：** 固定821a25b1667a28073360c96cf8702ab57dbd233f，532 manifest核验，仅重export、不producer；typecheck/build及隔离/发布HTTP-DOM PASS，原owner08f7e457adb046df9db509df43326a29/artifact/delivery保持。20:37:52–20:38:04发布source49527/PID28669、54780/PID28760，旧60473回退；14其他路由不变。session13/target14、2匹配/PARTIAL/两个原因/CANNOT_CONFIRM/材料NOT_RUN原样显示，native visual NOT_RUN，14页面和0完整不变。[派生发布增量](../../../../handoffs/P0/feedback/mac-m03-m15-window-20261014/README.md)。

### M16 经理候选公开资料任务｜P4

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb9ad6-5dc8-83ec-b3bd-bd3a447de94a)；`dev/m16-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [loader](https://github.com/lexi2016/v5/commit/5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a)；[只读接线](https://github.com/lexi2016/v5/commit/257ca6425c4d489e09430605ee82bf22a4e02da8)；[Mac](https://github.com/lexi2016/v5/commit/711d1cf68d26609a62241862f4f12291279e2f40)。 [完整生命周期候选ac1d14](https://github.com/lexi2016/v5/commit/ac1d1404ee76ca18a55dc65451b34868de6db552)；[Mac隔离原回执](../../../../handoffs/P0/feedback/mac-m16-ac1d14-isolated-20261013/result.json)。
- **已验证层级：** 原loader Mac32、真实10行PARTIAL_WITH_ROWS冷读/页历史保留。新固定ac1d14已155 blob/154 manifest核验，Mac31/31合成隔离PASS、exit0；首轮1 PASS/30 setup ERROR因TMPDIR经过/var symlink，改真实非symlink TMPDIR后通过，未改产品/候选字节。旧32未重跑，完整模块0。
- **未完成缺口：** 新生命周期候选已有隔离成功证据，不再将ensure/events/retry/cancel/reader一律标为未交代码。完整锁环境、原生可视、自然及生命周期剩余场景仍待验；限定真实PDF/provider与现有页面部署已由本节末条单次生产补证，但部分资料未形成事实、历史PIT/正式资格仍false。Python3.14.6不同于README云端3.12.14，未安装依赖。
- **依赖：** 原固定候选、公开资料provider、事件与job状态机；不依赖所有经理计划先完成才核独立job工程。
- **下一条完整交付：** 复用ac1d14的31项合成隔离证据与原32历史，复用下述已完成的单次真实provider/PDF、保存reader/API及部署证据，按实际授权补完整锁环境、资料缺口与生命周期剩余验收。保持GET无创建副作用、失败/取消/重试合同，不自动新外采。
- **验收标准：** 限定既有候选真实任务的提交/运行/结果、失败重试、取消/事件更新可追踪；GET无副作用，长任务不阻塞经理读取，状态/原PDF未核边界保留、单job回退过。
- **责任与交接：** M16唯一实现者保留固定生命周期候选；P0仅接请求/状态读取与长任务隔离，Mac后续按获准候选/调用范围验未覆盖部分。此次31 PASS不提升真实来源、部署、自然或全模块状态。
- **新增真实输入接线（北京时间2026-10-14 01:11）：** 固定2e49a397d99de8b0315628c97c01a4fd1a3a823a，新增12/12定向通过，旧31未重跑；M08 date12/STAGE_0935_0940原10行完整导出，新输入身份与原字段保持。只读50024/PID22335三次GET200无写，NOT_MATERIALIZED、product/job=null，仅返回输入身份/数量；producer关闭、未ensure/PDF网络/主页面部署，PIT=false，不计研究产品或业务完成。[真实接线原回执](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/m16-service.json)。

- **新增单次真实生产及部署（2026-10-13 19:26 UTC终态）：** 固定2e49a397d99de8b0315628c97c01a4fd1a3a823a，从job/product空执行一次ensure/attempt1，19:21:04–19:23:07 exit0，PARTIAL_WITH_ROWS 10条（6 READY/4 CANNOT_CONFIRM）、144结构化事实；1成员官方活跃主体未确认，3成员PDF未形成结构化事实。原事件9=1 eligible/8 unconfirmed，新闻156份覆盖9/10。历史20261012/cutoff09:40+08不改、PIT/historical_system_available=false、10条formal全false。新进程原reader及50024 API同product，54780 HTTP/DOM通过；source60473/PID26856、preview PID26954，旧58799回退。首次DOM资源加载检查失败自动回退，仅修验证脚本后通过，无改产品/重采集；候选/准备输入/M08及V4/M14/经理保持。新增真实生产与部署一次，页面仍14/18、完整仍0/18。[派生增量反馈](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/m16-production-summary.json)。

- **单次apply及确证页面阻塞（2026-10-13 UTC20:38）：** 固定68e4ec21895ba534a043f035e259bcd29e8edc30在20:33:20.230–20:33:22.979仅apply一次exit0，无网络/ensure/retry/events；三目标行只变事实/指定财务字段，其他七行和新闻事件、PIT/cutoff保持。新generation e0dc3261f4b944b394454055a56ba2fb，原store冷读9 READY/1 CANNOT_CONFIRM、216facts；新receipt缺status触发m16_readonly_worker._members()的M16_TERMINAL_STATUS，新generation普通页未发布、仍旧6/4。50024 API虽9/1会重投影catalyst，不能称字节同product。当时未手补/重复apply，原作者随后固定恢复已通过见下一条；完整仍0。[派生apply及阻塞反馈](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/m16-apply-summary.json)。

- **receipt恢复及9/1普通页完成（2026-10-13 UTC20:52）：** 固定1666211d8f6471b992c6d501adc926c1fa4fd5e3，228 manifest/9联合回归PASS、preview不改runtime；20:50:28.990–20:50:32.741仅恢复一次exit0，无PDF/network/ensure/retry/events，原product403cd39a…字节不变、旧commit/jobs/receipts保留，不计新采集或新产品。new job mr-receipt-20261012-a78f9ff40b74a61c-172c971165d3、generation a856bd7a2e1947e2871b4d04fdcc46d4，原reader/P0 project及隔离/发布HTTP-DOM均9 READY/1 CANNOT_CONFIRM、216facts。20:52:03–15部署source50490/PID29056、54780/PID29127，旧49527回退，前端未改、M15三records及14其他路由保持；原receipt.status阻塞已由此恢复闭合，02915官方主体/PIT/财务资格缺口与native visual NOT_RUN保留，14页面/0完整不变。[恢复派生反馈](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/m16-apply-summary.json)。

- **02915独立缓存接纳与10/10普通页（2026-10-13 UTC21:55）：** 22ca08ee138711ac91a731bf1458a0373b4a3a42 Mac6/6 PASS但preview因M16_PROVIDER_CURRENT_PARSE_CACHE_REQUIRED失败，独立缓存24facts/65页已在、未apply，历史保留。d18469212c86bec95303ca746cb4b90dd9a863de显式只读cache-root+SHA窄修，231清单/8定向PASS，零写preview后21:53:12–19唯一apply；原store/P0冷读及21:54:52–21:55:04普通页HTTP-DOM PASS，READY10/10、240facts，generation d0b51df656b24e5d8d4e6d8d59960957。仅02915财务及允许派生字段变，其余九行/新闻事件/PIT/历史/输入/原时间不变，无网络/解析/复制，两缓存保持。14兄弟路由/M15三records/经理/M03 active5ac3f270…保持，旧50490回退。先前02915缺事实状态已解决但历史PIT/财务资格边界未提升；目录POST独立复验/原生视觉/本次Mac全套回归NOT_RUN，14页面/0完整不变。[失败与接纳派生反馈](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/m16-apply-summary.json)。

### M17 尾盘量价发现与持续跟踪｜P4

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6acb914e-09e8-83ec-8f94-ca05638f5436)；`dev/m17-github-handoff-20261011`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [原分支已知版本](https://github.com/lexi2016/v5/commit/6d459cbc1e694eed413d142c75be64241a727e7f)；[late只读](https://github.com/lexi2016/v5/commit/64e112573eb5cbac47ff2db1dd0887f459f38213)；[已过读回](https://github.com/lexi2016/v5/commit/f350602512ee14f825bb53a976fbaada93a0b921)。
- **已验证层级：** 接入已具备；真实/保存局部已证；数据页已有局部（见边界）；完整0。late100行原reader/API/页已过，不是15:30见证；1530本地源码/依赖存在，历史47PASS/1SKIP不能代替原branch固定交付。
- **未完成缺口：** 代码确证：完整1530闭包未挂原分支commit，未挂tree/patch不算交付；输入/时窗：原15:30现场snapshot/history/资格与后续跟踪须按原合同，late不能补现场；旧Git blob审批归属/终态未知，不猜或重复写。
- **依赖：** 原15:30股票/universe/snapshot/history/资格、catalyst/prior/active mode；独立于Stage/超跌，供经理已提交尾盘/跟踪引用。
- **下一条完整交付：** 完成原prepare_universe/materialize/reader/持续跟踪的可运行闭包、依赖/真实文件清单、剩余定向测试及启动说明，正常CAS固定原branch并逐字读回；不重复已过late链。
- **验收标准：** 先工程可运行与坏输入拒绝；再真正原窗口产物→后续跟踪→经理理由/失效条件同identity，现场/盘后恢复分别记录；无时窗就MISSED，跨日/幂等/回滚过。
- **责任与交接：** M17原Chat/唯一实现者待排负责完整固定交付；P0接入标准tail/ledger/API，保留现late页；Mac固定commit后验残余parquet/原窗口，不伪造时间。

### M18 经理决策账本、汇总与计划｜P1

- **原责任入口与分支：** [原Chat](https://chatgpt.com/c/6aca3024-d568-83ee-9878-6698803373e3)；`dev/m18-bounded-manager-readback-20261012（已核开发分支，其他原主分支未知；共享框架在P0分支）`。原Chat/分支未知部分保持待核，不自创替代。
- **已有代码与证据：** [daily/同run候选](https://github.com/lexi2016/v5/commit/c7b815c065da83bd2db2b3023be4607ce9f194ec)；[导航窄修](https://github.com/lexi2016/v5/commit/52e71c8b85caef2874e4f3c9403e77592f5fb2c9)；[最新Mac反馈](https://github.com/lexi2016/v5/commit/dd2962f869ed04562707f202aa11d0cd342ccba8)。 [原准备041375](https://github.com/lexi2016/v5/commit/041375daf965b7e600d9ee1c8839a3de0c90e29f)；[窄修5c327e](https://github.com/lexi2016/v5/commit/5c327e45d99468d0ade73ee4acff6e0130f02852)；[真实失败及复验](../../../../handoffs/P0/feedback/mac-m16-m18-bounded-20261014/README.md)。
- **已验证层级：** 旧真实保存账本/三策略页及c7b框架证据保留；新增请求准备候选041375在真实target14缺M15时KeyError/exit1，失败保留。窄修5c327e已Mac40/40 PASS，原请求/原cutoff实际准备正常WAITING_SOURCES、exit2，request/template与US引用null；4,590保护文件字节/大小/mtime不变，未新经理owner、refresh、daily或部署，完整0。
- **未完成缺口：** 请求准备代码及缺M15字段的拒绝路径已修复，不能再把所有缺请求归为未交代码。真实三lane均不准入：M13原公告分析未消费/PARTIAL；M14 CANNOT_CONFIRM且690 pending不构成合法空/正式筛选；M15 NOT_RUN。manager_request/template仍null，旧target12/source09不能改日，M06不得替代三策略，原08:45–09:00窗口不补跑。
- **依赖：** 原计划context/target/cutoff及已提交04—17适用产物；首批是M13/M14/M15→M18，不反向拥有上游算法/采集。
- **下一条完整交付：** 复用固定5c327e的40项和真实WAITING回执，优先解决三策略合法输入/原消费合同；到齐后才由原准备入口生成请求/模板并验原ledger/reader、P0同run接线。不能用合成引用或690 pending填平来源缺口，旧239未重跑，不重复已过框架。
- **验收标准：** 13/14/15原产物经原经理保存，普通API/页及独立reader同run/SHA；显式旧run不跳，opt-in无current503、坏generation409/未知run503语义保持；六字段同run/PIT/窗口不变、读不执行、跨日/自然/回滚过。
- **责任与交接：** M18唯一实现者保留原KeyError与窄修证据；P0唯一集成共享框架，Mac后续只验合法真实来源与剩余业务/部署范围。当前正常WAITING是正确拒绝，不是经理业务成功或自然验收。

## 五、P0集成、Mac验收与唯一写入规则

P0原Chat：[主框架原会话](https://chatgpt.com/c/6acc9a79-4364-83ee-8b6d-e9fb51798e5b)；原分支`dev/v5-main-integration-20261012`。c7b/52e71与fac269固定组合已于23:03完成M14现役切换，daily opt-in仍关闭；现役M02安全页、M06动态页及旧经理身份保持，不应被整棵新HEAD覆盖。

|职责|唯一承担者与可并行范围|明确不能代替的工作|
|---|---|---|
|模块业务代码|主控为每模块指定一个真实实现者，原Chat为源码/合同责任入口；不同模块私有namespace可并行|原Chat回复/保存指令不等于后台coding，不再给已结束19轮发泛化催促|
|共享集成源码|P0唯一集成者负责module_api、source_bundle、shared registry/daily、descriptor及主前端路由/View；模块交固定接口/patch|两个实现者不可同时写同一共享路径/强推HEAD；小批是完整业务增量，不是无尽helper切片|
|Mac验收/发布|一个验收/发布队列，对固定commit/准确文件manifest定向验证，单一预览切换者|Mac不能边验边修第二版产品；新失败回原实现者，保留原trace/运行身份|
|源码/方案审查|可并行只读，给具体源代码事实/待核项/判定|不能用审查替代码、复制旧测试数或将未验证当缺源码|
|文档入仓|唯一文档writer将本统一主文档及README入口按实际授权固定；详细历史引用原台账/回执|不再复制多份逐小时台账成新“主计划”，文档提交不是产品进展|

固定候选进入Mac队列前必须齐：源码完整闭包/来源归属、依赖和配置样例、原算法入口、运行/停止/恢复/回滚说明、针对改动的离线结果、原分支完整40位commit和文件/树清单。同版本且未受影响的既有证据直接复用；共享接口变化或最终release组合仍跑受影响测试及必要整体回归。遇新失败不扩成全库无界pytest，P5当前固定release完整回归要求保留。

每次Mac交接写明：候选与源SHA、输入类型和run/日期、调用/文件写入范围、保护文件/进程、预期产物与拒绝码、是否允许真实provider/model/应用写门、页面与回退步骤。未获得相应真实执行许可的只验离线部分，不创建新许可、凭据或生产根。

## 六、验收包、阻塞处理与独立交付

### 1. 单一验收记录与证据包

每模块只保留一条主验收记录M01…M18；不把源码、页面、自然拆成多个“模块完成”。每次有效增量追加以下字段，详细日志用固定链接引用而不复制进本计划：

1. 代码：原owner/adapter/依赖/配置完整SHA、原branch commit和已核文件manifest，工具返回完整SHA直接复制，不手工扩短hash；固定路径可打开。
2. 输入：target/signal/eligibility/US session，真实来源SHA/取得时点/原receipt；原件、canonical摘要和安全投影摘要分开。fixture、录制回放、手动恢复、手动受控执行、自然分别标明。
3. 执行：真实触发类型、起止、run、exit、成功/失败/未知码；未跑写NOT_RUN。已保存指令、原Chat ack、未挂tree/片段不算代码交付。
4. 持久化：原产物、immutable发布/账本、冷reader同run/SHA；坏日期/坏pin/过早as_of/冲突CAS必须拒绝，失败保旧，不把unknown当零。
5. API/页面：普通而非测试专用入口、同run字段与完整分页，缺口/资格可见，错误清旧，GET无生成。jsdom/合成浏览器与Mac原生视觉分开。
6. 自动与回退：合法实际触发/跨日、同输入幂等、异常/重启恢复、单模块回退与其他模块保护；非每日任务按实际业务触发。

### 2. 待核项必须有限且能转交付

|待核问题|限定核查输出|转实现/已具备的判定|
|---|---|---|
|M05七来源vs六执行lane|原七来源逐项映射到现build/消费lane、物理产物、入口/commit和覆盖测试|证明合并等价则标已具备；确实遗漏则给唯一代码差异与验收，不再停在“核是否齐”|
|M01 authority/Mac/Windows绑定|当前可用原入口、活动版本、来源/公式/receipt索引与边界|有效入口闭包齐即接V5配置；缺跨端运行接口就明确实现；数据没有则独立标数据阻塞|
|M13/M18原主分支|从原Chat/原仓库只读确认原branch与HEAD，不拿派生只读分支猜主支|确认后用原支正常CAS；未知时不创建替代主分支或覆盖main|
|已交完整owner是否独立可启动（M04/08/09/10/11/12/16等）|固定commit的一次文件/入口/依赖/启动命令及阶段覆盖表|入口/测试足证则复用，不重写；缺失接口立即列入模块下一完整交付，不能无界扫描|
|原计划未核训练入口/8910范围|只登记其是否属于现18职责及已授权迁移范围、来源证据|未核不静默删、不计入18或自创新模块；需要范围变化先明确影响|

这些核查与其他独立代码流并行，不设“全项目审完才能编码”的门。M02限定真实采集到页面链已验，保留PIT/资格、自然与原生视觉的剩余边界；M03新候选已过Mac离线验收，推进未过真实/接线范围；M14固定组合已现役HTTP/DOM发布通过、旧失败与间歇503证据保留，M15隔离检查已过、锁依赖和真实/部署仍待验，不再做一轮总审。

### 3. 数据、权限、时窗分别处理

- 数据不足：保留原日期/取得时点/数量/缺口；代码与fixture先交。M14缺历史不补成零/合格，M03无snapshot不拿新闻替，M01无generation不拼旧身份。
- M05新permit/OPEN/build未获答复：暂停该次应用写入，继续已授权源码、离线fixture、接口和release工作；不重复提同问题、不把整个模块停工。
- M11元信息外传未获答复：不上传私有输入/manifest材料，继续合法本地/隔离代码与接口；代码分支授权不自动覆盖数据外传。
- 原窗口已过：记MISSED/恢复身份，准备下一合法窗口；不补跑M17 15:30或M18 08:45–09:00，不拿手动调用算自然。
- 工具失败：区分DOM/网络超时、明确拒绝、不存在和错误引用；不把404归权限/源码缺失。遇授权拒绝按具体动作/目标停下，由主控处理真实授权，不能换路绕过。

重试与恢复复用现有 run_ledger/dispatch，不引入通用自动重跑。逐 owner 给出 reason code 对应的可重试/须先核对/不可重试表，沿用总 attempt 上限；仅已证无外部效果、仍在原窗口内的暂时失败可重试。RUNNING/超时/回执丢失先用原冷 reader 核 run/reference/receipt/current 与账本，不删除 claim 或伪造安全标记。为本次接线补三类必要故障证据：已保存但回执丢失、current/CAS已提交但响应丢失、确证未执行的安全重试。分别验证不重复 owner、旧成功不变、不能确认时继续阻断；已有同版本覆盖直接复用。官方与固定函数依据见 [比较补充](OPEN_SOURCE_WORKFLOW_COMPARISON.md)，这些是待落实验收，不是新增完成结论。

### 4. 独立V5最终打包与运行证明

代码/打包准备不必等未来交易日。候选收敛后固定一个可交付release：完整V5源码/原owner闭包、锁定依赖、配置样例与身份清单、独立数据目录/迁移导入工具、全部worker/API/前端/调度启动停止脚本、健康/版本/故障定位及单模块回滚说明。

现有 run_shadow.py 源码包入口及 main_runtime.main/module_api.main 均保留；在 release 中明确采用源码包或安装式命令中的一种实际交付方式，不强制为形式引入新工具。若补 pyproject 的 [project.scripts]，只薄封原入口并保留 guard/配置验证；固定 Python/依赖与非 src 资源清单，在仓库外工作目录按说明安装/启动，核 help/validate/status不触发owner、显式tick沿原准入、资源/版本/退出码与停止恢复正确。源码CLI存在与安装包实跑分开记证，未实跑仍NOT_RUN；不依赖V4活动目录/任意PYTHONPATH，不因打包自动启用调度。依据见 [比较补充](OPEN_SOURCE_WORKFLOW_COMPARISON.md)。

Mac在获准的隔离环境/新根按文档从零启动，证明没有访问V4运行服务/活动源码/写入根/自动fallback；不为验证而停止或破坏现役V4。若隔离验证无法证明某调用独立，明确标运行依赖未解除，不能交“最终独立V5”。复用固定V4代码与数据必须有真实来源记录和新V5身份，不伪装原生产回执。

P5退出必须同时具备：当前固定release完整回归与API合同；18模块各自真实输入/计算保存/页面/失败恢复及回退；**两个连续适用交易日**完整自然接续；非每日任务按其实际触发合同；真实原生页面交互与版本/来源可核；独立启动/升级/回滚演练和用户可照做的说明。自然验证等待真实适用窗口，但不是继续编码的前置条件。

## 七、实施控制与下一步交付顺序

1. 先完成本统一计划的轻量可执行性核对，由唯一文档writer固定主文档并在README给入口；不并行再造另一份项目总方案。
2. 保存M02固定776acce的Mac 38/38、新真实采集→恢复→原binding冷读→只读页面发布回执；不重复已过链。native visual NOT_RUN、PIT/资格false、自然及完整验收未过，按授权与实际回执推进剩余项。其余新派工按本方案A1–A7优先级锁定唯一实现者和完整交付，不重复已结束19Chat轮次。
3. 保留已发布M14独立真实页并处理剩余验收，优先补M03新候选尚未覆盖的真实provider/消费接线、M13/M15首批合同与P0/M18合法request；来源/页面/请求代码并行，共享文件串行合入。每条只以可运行固定交付进入Mac队列。
4. 每次状态只报四件：实际固定了什么、实测了什么、原页面/业务变化、剩余确证缺口。收到新结果先更新对应Mxx一条记录；未commit、未跑、未部署分别说清，不用更多报告/催促替代执行。
5. 首批业务闭环签收后推进原全范围阶段/研究辅助，再完成自然与独立release终验；已有输入可先验，不等所有未来来源齐才接页面。

### 证据入口

- [原总计划与P0—P5固定定义](https://github.com/lexi2016/v4/blob/24c6d60d524f43fcf4209ec8b078ec02cb34417e/V5/docs/superpowers/plans/2026-10-09-v5-master-delivery.md)
- [原迁移计划、18模块唯一退出、首批三策略业务目标](https://github.com/lexi2016/v4/blob/d1bf034640ca2e5957423de2745a98e159b69af2/V5/docs/superpowers/plans/2026-10-10-v5-migration-execution.md)
- [当前已落仓工作规范索引](https://github.com/lexi2016/v5/blob/43c658817dc45bb8641dc55f3185d60794b3f10d/V5/docs/workflow/2026-10-13-delivery-reset/README.md)
- [19项任务清单固定版及M08完整引用更正](https://github.com/lexi2016/v5/blob/da55ec61f2ee4729ad6156a9e532ed0b0b776438/V5/docs/workflow/2026-10-13-delivery-reset/MODULE_TASKS.md)
- 已发送20:23台账作为历史状态基线；本文逐模块链接给出必要固定源码/回执，不复制逐小时日志。规范/文档提交不等于产品完成。
