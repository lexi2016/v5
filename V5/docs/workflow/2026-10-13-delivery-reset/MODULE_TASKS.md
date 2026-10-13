# V5 原模块任务索引（2026-10-13）

本索引汇总 M01–M18 与 P0 的原会话、既有开发分支、已证版本、已知缺口和下一项完整交付。状态来自 2026-10-13 20:10 的交接清单；各模块开始前须重新核对原分支 HEAD、已交源码与最新回执。这里的固定版本不是当前远端 HEAD 声明。

本文件是待执行/接续任务索引，不是消息送达回执；不据此认定任何原会话已经收到指令。原分支尚未确认的项目先核实，不能自创替代分支。已通过内容不重做；未验收不等于没有代码。

共同交付要求见 [WORKFLOW.md](WORKFLOW.md)。各模块交完整源码、依赖配置、可运行入口、隔离测试结果、停止与回退说明，以及原开发分支可读回的固定 commit。共享集成文件由 P0 单一写入者协调；保留 V4、来源身份、PIT、时间窗、资格和风险门，不以开发任务替代真实生产准入。

## M01 A行情与公式面板来源
原Chat：https://chatgpt.com/c/6aca4d01-136c-83ec-83fd-2cac19e42e50
原分支：dev/m01-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：02cefc41aadb4358cb8485b71858ae5d6b903a56；Mac ea96a80cf9d79e638ee08e15cb0bf92368261ada
当前缺口：已过公式/工程和来源阻塞接口不重做；原10/09 V35公式READY/PASS但总PARTIAL、REBUILD_REQUIRED、sync FAILED，selector与M05输入身份不同，缺官方generation绑定。
下一项完整交付：先核现有独立来源工程是否完整，再补合法generation重建/同日身份与recording-clock准入、保存及原reader接线缺口，交隔离正反测试与启动入口；禁止拼旧09/11身份放行或自动新采集。

## M02 HK行情、主表与资格来源
原Chat：https://chatgpt.com/c/6aca47c7-0bd4-83e8-ab3b-3d4c2cee272a
原分支：dev/m02-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：原owner ce6cddce1ef52d63241f0d8192b6adcc118ea750；P0保存接线 a451275c5eee5ec63139b7e8f886624ebdd4c7d5；更正Mac回执7eac09efd3ffcb0e48d58b8d10e7b92a525c41df
当前缺口：原三源build/cold-read和安全保存接页已通过，仅SOURCE_IDENTITY_ONLY、PIT/历史资格false；实际collector仍因stock_owner NaN在最终capture失败，RAW_CAPTURED独立恢复不是完整collector成功。
下一项完整交付：补独立collector完整可运行入口及严格新producer兼容，核已有真实HOME启动配置；NaN需按明确新身份/合同处理，不能清洗旧原件或放宽原validator，已有三源reader/安全接页不重做。

## M03 US行情来源
原Chat：https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8
原分支：dev/m03-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：3c3ed922cb653bb8ef411bce685b1d47fb322f02；集成/部署aa59bfb8551b0d2f86ed88b28e9127354ff8b976
当前缺口：20261009 POST_CLOSE原三件→snapshot→binding→API录制回放已过，未证实新的独立自然行情采集；12/13新闻三件不能当market_snapshot。
下一项完整交付：先核现有完整交付，补独立市场行情snapshot采集/持久化及原三件默认冷读配置与接线的实际缺口，交可运行默认入口、负例测试和固定commit；不改成新闻管线、不自动生产。

## M04 研究情报与归档
原Chat：https://chatgpt.com/c/6aca4d57-024c-83ec-9d59-f3b246eeda6a
原分支：dev/m04-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：完整编排8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7；只读接线447683268a289af9fe980b90807284de42f1ea13；Mac a8bb8cdaf058deee9eacc5c6b1b11b2e21d081a3
当前缺口：8a3完整持久编排/失败续接工程及18篇原档只读页已过，原reader本已存在；新真实采集、合法获取时间/主题、全lanes/PIT未验，不能称现有builder/import物理不存在。
下一项完整交付：先核已交捕获→原builder→import/store→冷reader完整链，再补独立配置/采集入口/失败恢复及未覆盖lane的代码差异与测试、启动说明，保留53范围外错误和UNKNOWN，不重做18篇读回。

## M05 A预选池
原Chat：https://chatgpt.com/c/6aca4eef-525c-83e8-abb9-d8423024bf90
原分支：dev/m05-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：50adce44ea047c8ee9435a5e703a2125264243c4；release材料5d868fc09fba7f7fe210e603a28015e271117077；现役原owner基线2c5d1eb2c9572469bf04ad86fd61e92ee8674fe8
当前缺口：50ad零行适配Mac7过、隔离历史120行/strict READY冷读过；该历史回放没有同日M01绑定/PIT，单池新permit/OPEN/build尚未获准，产品未保存。
下一项完整交付：核50ad/5d的完整六lane执行、adapter/writer release覆盖及原保存reader是否齐，缺则补隔离入口/配置/测试和完整启动交付；真实应用写门/生产仍停在既有批准边界，不造manifest或自动开门。

## M06 HK预选池
原Chat：https://chatgpt.com/c/6aca4f4a-ef44-83ec-89e1-bcaaed88d4a5
原分支：dev/m06-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：原完整owner08ed9de9ddb5fd2c62eb1762df2f6106464d823b；P0自然current c518d0c4bf8d947881586a7ed667f2a9ac5c6d1e；回执e200cafbece378343d04a654c9819746357ae03e
当前缺口：原模型100行、存量池、双账本/current、动态页以及一次有限自然步骤已过，18:30后无重复生产；整体daily/经理接续未完成，不是要求重写M06已过链。
下一项完整交付：先核模块独立采集/模型/存储/reader交付完整性，仅补尚缺的标准结果/引用导出与P0后续request合同、隔离失败/UNKNOWN边界或运行说明；保持原窗口/PIT/资格，禁止重复真实model或自动补跑。

## M07 A阶段选股
原Chat：https://chatgpt.com/c/6aca4fc6-4640-83ee-aab0-22512e215276
原分支：dev/m07-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：完整链e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31；P0只读eec2220b674182441d0f50d689c66ec2184527c6；Mac f901a43a3281e6663cda18261371f49cfc8bebad
当前缺口：e99b完整链Mac63+31及eec只读WAITING入口已过；四缺口为M05六物理池、M01 raw三件/时钟、M04小时见证/morning、M07已验证保存引用，formal仍BLOCKED。
下一项完整交付：在完整原链上核并补合法四源request/binding准备、独立阶段计算→保存→原reader接线的未完成代码，交完整隔离正反测试/CLI/固定commit；不要再做占位WAITING页或放宽temporal=false。

## M08 HK阶段选股
原Chat：https://chatgpt.com/c/6acb9208-1504-83ee-a9fd-d8feb3dcfb48
原分支：dev/m08-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：原owner8f08967ee01c2679dacd0d78d0a2a028867f1967；保存接线08c101d6e7f53d1d1519c3859c6b1d985c32d221；Mac bae6184b99d289f394b0cc3c3d5370e9f3155715
当前缺口：真池适配、10套八阶段保存读回和页面已过；Stage8完整重算输入，以及普通阶段时点/成员/单位、PIT/资格仍未闭环。
下一项完整交付：先核独立八阶段owner/输入准备/保存reader与scheduler入口是否全交，只补未实现部分并给缺件拒绝/阶段一致性测试和启动说明；不重算已过历史样本、不补造Stage8来源。

## M09 A收盘复盘
原Chat：https://chatgpt.com/c/6acb63a0-57a4-83ee-8f96-e5c6936b6405
原分支：v5/m09-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：084df7c61e57e7615633828a0d6a5d9078dc9b1c；集成/部署864fd1d9f2305c8fd236da6b363909ed92274d11
当前缺口：两日真实录制研究回放/冷读及页面已过，仍PARTIAL，来源时点、成员、资格/PIT和每日自然接续未闭环。
下一项完整交付：核现有完整候选的独立采集/研究owner/保存/reader/daily入口，补实际缺失接线、来源门控配置和隔离测试/启动交付；保留PARTIAL/false，不重做两日已验回放。

## M10 HK收盘复盘
原Chat：https://chatgpt.com/c/6acb8fe5-807c-83e8-867b-f41893d0d4be
原分支：dev/m10-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：1c0d56d0ea350f8f2178d8b0c6b7e66dfa113585；Mac/部署c64adfca99041951b45bc4fda600b99e68d07d5e
当前缺口：698行录制回放/发布冷读和页面已过，20/100/70/20投影及七阶段PARTIAL/null保持；完整scheduler、来源PIT/资格仍未实证。
下一项完整交付：先核现有冻结依赖与完整scheduler/runtime入口是否齐，再补独立执行/发布/读取的缺失部分及隔离测试、启动说明；不把未验依赖叫缺文件，也不重复已通过产品回归或填平PARTIAL。

## M11 盘中研究与研究复盘
原Chat：https://chatgpt.com/c/6acb8ea5-0d24-83e8-ad96-382d1699c591
原分支：dev/m11-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：完整工程f932059eff5e425d0e3c381f9e4610e62e6e0cc2；安全修cc29974b15f2199aef3f19100c91a9195f217074；接线490529f549324fb435af56d5f728672ad6390b72、fixture f176d7076d4a844b8203ee8aa664f182ee284fe7；Mac39a903afbdd95f110463c8372aa493e81b7209cd
当前缺口：完整默认owner/独立reader、API六槽及安全边界工程已过，页面仍六项WAITING；真实来源hash/pins/原身份不一致，今日采集窗口已过，元信息外传批准未到。
下一项完整交付：核已有完整代码后补独立合法snapshot输入获取/新构建身份与可信pins配置、真实sentiment核心/六槽保存reader链的实际缺口，交离线合同/负例/启动代码并固定原支；不补采旧窗口、不上传未授权材料或伪造r4身份。

## M12 视频FUPAN
原Chat：https://chatgpt.com/c/6acb99cc-7b94-83ec-97c6-edb09318fa50
原分支：dev/m12-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：原生命周期4bbf069b435d8f0ba28db8e2eba1d358ea5e283c；接线c353334d70972033ae86f7175504ca675bafbb68；原生导入345a75140d1a991b0e109bad4c90a1f5744434a1；Mac92700169f97a7da17079f2d868fb86ed1242b5e0
当前缺口：原4bb生命周期、c353接入及17原生件导入/cold-read/页面已过，ASR待复核和字典缺失保留，真实采集/producer自然生命周期未完整验收。
下一项完整交付：先核原生命周期完整可运行交付，再补独立采集/原ASR调用、显式重试恢复、字典缺失处理及原reader接线的实际缺口，交完整离线测试/CLI/启动说明；不重做17件导入、不自动ASR或消除人工复核标志。

## M13 公告研究与选股
原Chat：https://chatgpt.com/c/6aca4a2f-ffc8-83e8-87af-a0f03cd54a35
原分支：dev/m13-partial-pages-20261012（已核开发分支，更早原主分支未确认，先只读核原Chat/分支）
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：308af26862daf005c5c5800d15c5053c84275938；页面efdc43a955024042dfb78707c97b94e6f7d74fed
当前缺口：保存公告研究/页面已过；引用详情/capture合同、分页失败/PIT/资格仍有边界，新revision没有审阅决策，不能直接产正式选股。
下一项完整交付：核完整原owner交付后补独立采集/capture、审阅决策输入入口、引用详情/保存reader与接口的缺失代码和测试；保留未审/缺来源的明确拒绝，不代替用户审阅或自动新生产。

## M14 超跌研究与选股
原Chat：https://chatgpt.com/c/6aca4e2a-ea0c-83e8-a4fa-dc01a13867bf
原分支：dev/m14-github-handoff-20261011；补充dev/m14-stored-supplement-20261012
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：封装a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba；旧页6feeafdec3e14ddac82e1a843dd91998818293fe；本轮原数值owner固定884548fea0a0056483e8175564eaee015a964023（所在仓库/branch本清单未核，不拼造链接）
当前缺口：固定原数值owner一次+冷read已保存target14/signal13研究，strict0/near0/pending690是历史不足，不能当正常无候选；现页只读旧M18 rebound，无独立M14路由，强接会经理日期错配。
下一项完整交付：交独立M14 root+4ref原reader/API、分页、frontend proxy与组件完整接线和隔离测试/启动说明，保留原字段/690待核/旧经理run；不重跑数值owner、不补09 supplement、不强接旧manager，共享API与P0协调后固定原支。

## M15 美股到港股映射
原Chat：https://chatgpt.com/c/6aca4b1c-7bac-83ec-878c-d1fb0bd37b38
原分支：dev/m15-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：1dede80b4ff18781849e87e85ca693890ed57979；页面d53e0820318462806d9e67dae1818bb684b38ade
当前缺口：既有四关系/三HK读回和页面已过；独立owner、多源daily、PIT/资格未闭环，12/13新闻三件不含市场snapshot。
下一项完整交付：先核完整现有代码，再补独立多源输入（行情与新闻分别验）、原映射计算→保存→reader与daily接线的缺口，交缺snapshot/身份错配测试和启动交付；不把新闻伪装市场快照、不重复旧映射。

## M16 经理候选公开资料任务
原Chat：https://chatgpt.com/c/6acb9ad6-5dc8-83ec-b3bd-bd3a447de94a
原分支：dev/m16-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：loader5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a；P0只读257ca6425c4d489e09430605ee82bf22a4e02da8；Mac711d1cf68d26609a62241862f4f12291279e2f40
当前缺口：loader Mac32及原10行PARTIAL_WITH_ROWS同字节迁移/冷读/页已过，PDF原件、provider完整性、完整producer生命周期仍未验，不能因材料未验推定现有factory不存在。
下一项完整交付：先核默认worker/factory/owner已有完整代码，再补独立公开资料采集→原producer→保存reader/API的实际缺口及离线PDF/provider/恢复测试和启动说明；不重做loader或10行读取、不自动外部采集。

## M17 尾盘量价发现与持续跟踪
原Chat：https://chatgpt.com/c/6acb914e-09e8-83ec-8f94-ca05638f5436
原分支：dev/m17-github-handoff-20261011
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：原分支最近确认6d459cbc1e694eed413d142c75be64241a727e7f；已部署late只读64e112573eb5cbac47ff2db1dd0887f459f38213；1530候选尚无分支commit
当前缺口：late100行只读链已过；1530冻结原源码/依赖存在，但完整闭包尚未固定到原branch commit，不能用未挂树或旧47PASS/1SKIP代替交付，旧审批归属/终态未知。
下一项完整交付：完成1530完整可运行闭包、依赖清单、原算法prepare/materialize/reader与集成代码及测试/启动说明，在真实原分支正常固定commit并读回；不重复late已过部分、不回填15:30时窗，真实输入/准入缺口明确拒绝。

## M18 经理决策账本、汇总与计划
原Chat：https://chatgpt.com/c/6aca3024-d568-83ee-9878-6698803373e3
原分支：dev/m18-bounded-manager-readback-20261012（已核开发分支，其他原主分支未知；共享框架在P0分支）
最近已证固定版本（按来源/集成区分，非当前HEAD断言）：旧保存账本/P0集成5b32a0916fbe486bbf7a33c1ce6ad9e3e4618e51；新daily/同run显示c7b815c065da83bd2db2b3023be4607ce9f194ec、导航52e71c8b85caef2874e4f3c9403e77592f5fb2c9；Mac反馈dd2962f869ed04562707f202aa11d0cd342ccba8已过（不沿用旧19:23“未固定”状态）
当前缺口：当日bundle仍缺合法manager_request/template，旧三策略target12/source09不能改日套M06 target14；P0新版daily/同run显示产品与导航已Mac通过，不能沿用“未固定”旧状态。
下一项完整交付：仅补模块侧完整请求/template准备与验证、三策略同run/日期/PIT/window合规接入、原ledger/计划保存reader的实际缺口及隔离测试/启动交付，并对接已过P0框架；不重写该产品，不补跑08:45–09:00窗口或自动生成正式经理计划。

## P0 主框架、调度与集成
原Chat：https://chatgpt.com/c/6acc9a79-4364-83ee-8b6d-e9fb51798e5b
原分支：dev/v5-main-integration-20261012
最近已证固定版本：daily/同run显示c7b815c065da83bd2db2b3023be4607ce9f194ec、导航52e71c8b85caef2874e4f3c9403e77592f5fb2c9；Mac反馈dd2962f869ed04562707f202aa11d0cd342ccba8已核通过；M02接线a451275c5eee5ec63139b7e8f886624ebdd4c7d5/更正反馈7eac09efd3ffcb0e48d58b8d10e7b92a525c41df。
当前缺口：主框架daily/同run显示及导航产品已Mac通过，不再重做；真实当日manager_request/template和三策略合法同run输入尚缺，M14缺独立读取/API/页集成，源模块剩余能力需接完整。
下一项完整交付：在已过产品上补未完集成与可校验真实request准备代码/配置、模块标准引用与独立状态展示、目标回归和完整启动说明，原分支固定commit；保持显式opt-in/旧run、CAS双descriptor、六字段同run/PIT/时间窗，禁止改日套旧三策略、补跑旧窗口或自动新生产。
