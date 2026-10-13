# M16真实输入只读接线与M18准备窄修回执

本目录集中转存Mac普通消息的五份原JSON，保留原字段/字节/换行；转存者未重测或执行服务。来源消息：msg_0b47eb1b0178a3a6016ace68b304e887d1979a963d131d1b26（四旧件）、msg_0b47eb1b0178a3a6016ace6996116487d1985abde944b034e7（新复验）。

## M16：输入接线成功，研究产品未生成

候选2e49a397d99de8b0315628c97c01a4fd1a3a823a：原M08 20261012/STAGE_0935_0940的10行导出为新独立输入，原行/envelope与来源保持不变；12/12定向通过，旧31不重跑。只读服务50024/PID22335三次GET200，无写入，返回NOT_MATERIALIZED、product=null、job=null，展示输入身份/数量而非逐行研究产品。producer关闭、未ensure、未外部PDF/网络/模型、未部署主页面，PIT=false，不计业务完成。

## M18：真实KeyError保留，窄修后正常WAITING

原041375daf965b7e600d9ee1c8839a3de0c90e29f的target14实际准备因M15 NOT_RUN缺artifact_sha256抛KeyError、exit1，保留preparation与diagnostic；前序端口沙箱错误及targeted结果亦保留。

窄修5c327e45d99468d0ade73ee4acff6e0130f02852：2026-10-14 01:25北京时间，指定40/40 PASS、零FAIL/ERROR/SKIP，旧239未重跑；同一原请求/原cutoff准备exit2、WAITING_SOURCES，manager request/template及US引用均null，不将无效来源构造成请求。4,590保护文件字节/大小/mtime不变，未refresh、未生产owner、未daily或部署。

三lane缺口仍在：M13公告未被原分析消费（PARTIAL）；M14 CANNOT_CONFIRM、690 pending不是合法空/正式筛选；M15 NOT_RUN。M06仅保留来源引用，不替代三策略。diagnostic中的局部pending_count=0不能覆盖原M14观察690，原JSON保持并明确此边界。

既有环境实际为Python3.14.6/pandas2.3.3/pyarrow24.0.0，先前M04环境清单遗漏该组合；本次未重跑M04，也不回溯改写其专用profile证据。

## 原文件SHA-256

- m16-service.json：777c5435fb233d97cf0d25318950418afb2d3e5a3d9729a3780438256a1eb4fd
- m18-prior-targeted.json：3dc0b15364489b59f3a6cae42ed557556465db326232ac7007324dde6e6c3a5f
- m18-prior-preparation.json：26d6404a7035b81e1bfffc12b5797e5675062c9a64d353c1c82cd326cd253730
- m18-prior-diagnostic.json：78b05dfd1fda92acadfde0ecf0f63a129b64e5ec0574cbfb67dadc800852d207
- m18-recheck.json：a7802a0da490c3d81b614a56e80b2550f8ec14a838237b6f21f17188c7e0b7c4

## M16 单次真实生产与现有页发布增量（19:26 UTC终态）

本节及 m16-production-summary.json 为 **DERIVED_SUMMARY**，转存Mac普通消息 `msg_0b47eb1b0178a3a6016ace861d071087d18be7579582d0eee5`；未取得原文件字节，不声称与原JSON的SHA相同，文档写入者未执行测试。以上五份原JSON保持不变，初次NOT_MATERIALIZED是执行前历史。

固定2e49a397d99de8b0315628c97c01a4fd1a3a823a执行前job/product为空；一次ensure、attempt1，UTC2026-10-13 19:21:04–19:23:07 exit0，无retry/独立events refresh，12项测试未重跑。实际保存PARTIAL_WITH_ROWS：10条中6 READY、4 CANNOT_CONFIRM，144条结构化事实。HK.02915为ISSUER_NOT_IN_OFFICIAL_ACTIVE_LIST；HK.02583/01081/00376为PDF_NO_STRUCTURED_FACTS（文件取回解析但未建立事实）。原事件9个＝1 eligible＋8 unconfirmed；公共新闻156份覆盖9/10，部分覆盖保留。

历史日期20261012、cutoff2026-10-12T09:40:00+08:00，PIT=false、historical_system_available=false，10条formal_eligible全false；不是当日实时结果。新进程原reader、50024 API与原保存reader核验同product，54780 HTTP/DOM通过。新source60473/PID26856，预览54780/PID26954；旧58799与绑定保留回退。首次DOM资源加载验证失败自动回退，仅修验证脚本后复验，未改产品或重采集。

候选、准备输入、M08原资料不变，V4/其他预览/M14/经理保留。此次新增实际生产及发布一次，已有M16页面不重复增加14/18页面计数；自然及完整模块0/18不变。原生视觉没有新增通过证据。

身份与来源报告指纹见[m16-production-summary.json](m16-production-summary.json)。来源result.safe.json SHA256为`71141c89e0f9c64d3ebbb9c0d72b699758f1a32970f2c87b6a38127ae250e7bf`，原字节仍在Mac，不上传原事实/新闻/股票行或私有路径。

## M16 单次apply与新generation页面阻塞（20:38 UTC增量）

DERIVED_SUMMARY，来源Mac消息 `msg_0b47eb1b0178a3a6016ace96c8380487d1bfeafc431b928802`；精确身份见[m16-apply-summary.json](m16-apply-summary.json)，无原receipt字节同一性声明。

固定68e4ec21895ba534a043f035e259bcd29e8edc30，仅apply一次，UTC20:33:20.230–20:33:22.979 exit0；network/ensure/retry/events全0。三目标行仅事实与指定财务派生字段变化；剔除财务键后新闻/事件嵌套对象完全相同，其余七行、PIT/cutoff/原生成时间不变。

原store新进程冷读9 READY/1 CANNOT_CONFIRM、216facts，02915仍未确认；新generation e0dc3261f4b944b394454055a56ba2fb。确切阻塞：新receipt没有status，m16_readonly_worker._members()要求receipt/job终态一致，报M16_TERMINAL_STATUS。未手补receipt、未重复apply，旧commit/job/receipt保留。

50024 API已显示9/1，但会重投影catalyst分类与缺口，不声称响应与保存product字节相同；普通页仍旧6/4引用，新generation未部署。原作者正在修合同，尚无修复通过结论。来源报告result.safe SHA256：`70c1d4e3f37c692410503826e669e935b662ed707d009e0bcf97372a53a0755d`。PIT/正式/自然及完整验收不提升，页面计数14、完整0。

## M16 receipt恢复与9/1普通页完成（20:52 UTC增量）

DERIVED_SUMMARY，来源Mac普通消息 `msg_0b47eb1b0178a3a6016ace9a151b0087d18ece877dee868aba`，不冒称原字节。固定1666211d8f6471b992c6d501adc926c1fa4fd5e3，228 manifest核验、原P0联合回归9/9 PASS；默认preview通过且runtime未变。仅恢复一次，UTC20:50:28.990–20:50:32.741 exit0，无PDF重解析/network/ensure/retry/events。原product字节不变，旧commit原字节归档、旧jobs/receipts完整保留；这是receipt恢复，不是新采集或新产品。

新job mr-receipt-20261012-a78f9ff40b74a61c-172c971165d3、generation a856bd7a2e1947e2871b4d04fdcc46d4、attempt1；完整三项指纹见[m16-apply-summary.json](m16-apply-summary.json)的receipt_recovery_increment。新进程原reader、原P0 project、隔离及发布HTTP/DOM均9 READY/1 CANNOT_CONFIRM、216facts通过。前述M16_TERMINAL_STATUS阻塞历史保留，此固定恢复已完成并接入普通页，不再将普通页记为旧6/4。

UTC20:52:03–20:52:15最小发布source50490/PID29056、54780/PID29127，旧49527回退；前端文件未改，M15三条保存records及其余14路由/经理/保护端口保持。02915官方活跃主体未确认、历史PIT=false、财务缺口/资格限制保留，native visual NOT_RUN，14页面/0完整不变。

来源报告result.safe SHA256：`c978416fb2a3eb0d9114a613040087883a9a0b914d4c66a6fc6bbaa7de907bbc`，不是本摘要指纹。
