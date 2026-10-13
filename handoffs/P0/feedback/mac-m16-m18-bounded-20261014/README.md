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
