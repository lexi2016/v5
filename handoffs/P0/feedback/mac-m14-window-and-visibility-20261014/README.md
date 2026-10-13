# M14 同源计算、reader 与窗口页面验收

**DERIVED_SUMMARY**：依据 Mac 普通消息转存的增量摘要，不是原始 JSON；来源曾压缩排版，不能声称原字节或原 SHA 一致。本次文档写入者未执行 Mac 测试。完整来源消息 ID、固定代码及来源报告的 SHA 见 [summary.json](summary.json)。不上传原始行情或私有路径。

## 已有记录与本轮增量

[前批采集终态](../mac-m14-batch-capture-20261014/README.md)已记录690回执与原缺键覆盖，本轮不重复计采集。运行代码 bbf3e43adc60ad41bdef95998f15483ff0988660；后续文档 c9f8c7b41e492cb8017c68ac848cdc8f4ff35718。

- 33/33定向PASS，Python3.14.6/pandas2.3.3/pyarrow24.0.0。复用690回执，无新增网络，装配40930行／690股，日期20260720–20261013；真实cutoff为2026-10-13T18:40:58.776354Z。
- 首次CLI因新输出根未初始化，在计算前退出且未产生run；按原marker初始化后仅实际计算一次，UTC18:41:42.547322–18:41:50.805855、exit0。保留此前失败。
- 新run 9c70cc6cb8e34afb9e34b366acf8becd，新旧引用独立冷读均MATCHED。strict0/near0/pending690/excluded0/unresolved0，READY_WITH_GAPS / CANNOT_CONFIRM；原80%／1.5不改、同源trade scale1。
- 690响应均缺原prior60要求的20260925；688历史缺口、2原始行异常，另3个previous5缺口与前者重叠，不能相加成成员数。全部成员/空signal行保留，不改日历、不补零、不混旧面板；单位、price basis及目标资格未证。

## reader 发布与展示缺口修复

初次同版reader发布已核新run及690pending，但公开投影裁掉cutoff/source_contract/pending_reasons，页面也未展示40930行；此阶段不能称已显示cutoff。随后固定 [a7eb3a9c4cf9f35ab7ba9830d41a29644201a788](https://github.com/lexi2016/v5/commit/a7eb3a9c4cf9f35ab7ba9830d41a29644201a788) 窄补公开投影和组件，Mac 4投影＋5Vue、typecheck/build全部PASS，隔离及发布后HTTP/DOM均同run，状态DEPLOYED_HTTP_DOM_PASS。

页面已显示真实cutoff、40930行／690股、同源合同与scale1，以及688历史缺口／2原始异常／另3 previous5缺口；机器字段默认折叠。未保存的逐日缺口或坏行数值不由页面编造。原生可视验证NOT_RUN。

当前source58799/PID26199，页面54780/PID26268；旧58025/PID25773与旧前端保留回滚，未触发。13条其他source路由、经理、M02/M06、研报queue源码不变；732原保护文件、2760journal及owner产物不变。发布过程没有新采集、重算、日历修改或交易。

## 仍未完成

原同源完整窗口仍有缺口；此前跨源口径问题没有被采集或页面发布消除。正式准入、自然及完整模块验收均未通过，完整模块计数维持0/18。

## Futu 三代码独立完整窗口补验（增量）

本节同为DERIVED_SUMMARY，依据Mac消息 `msg_0b47eb1b0178a3a6016ace8327ff2487d1b63040313f80923d` 与 `msg_0b47eb1b0178a3a6016ace83caac4c87d18f103e002cf92e93`；未上传原始行情或重建原receipt。

- 固定候选 [ad9a61d26c487748ba017b69250571ae5a38bbab](https://github.com/lexi2016/v5/commit/ad9a61d26c487748ba017b69250571ae5a38bbab)，Mac离线13/13 PASS。UTC2026-10-13 19:11:22.384–19:11:26.835唯一一次真实采集，exit0、无超时；同连接3请求，各单页，无重试/分页/订阅/交易。
- HK.00001、HK.00376、HK.01191各覆盖原61/61交易日，均含20260925、OHLC异常0；两个指定异常日（00376的20260831、01191的20260724）在Futu原值中满足OHLC包络。仅记录校验结论，不上传原行情行。
- 前后quota均96已用/4剩余，增量0。SDK10.06.6608，来源FUTU_HISTORY_K_DAY_AUTYPE_NONE_SDK_NATIVE，AuType.NONE_UNADJUSTED，价格/量/额scale1；UNIT_UNVERIFIED，币种未证明、provider finality未背书。
- 732保护文件及原owner产物未变，无PyTDX混源、无改日历、无owner重跑或页面部署；repair_ready/owner_admission/formal/historical_pit均false，现役页面仍前述690pending。
- 下一缺口：原owner要求原690成员集合一致，3码通过不等于全池；Futu剩余4代码quota不足全690。原量门同源比值不需据此乘100，但不能宣称单位或跨源等价已证。完整模块0/18不变。

来源报告的原文件SHA256（不是本摘要SHA）：summary `e88b0972e02a08be2c59106b56a50981303e5669490d057ab7e46281830d7354`；supervisor `3fced8e9e5a19aa936b556f628e73dfc925e9ea47333458e8edff8fa9dd9096f`；result.safe `571d52e60c45712f5de57afef46f658898833bd9c117d27c7e51e0c93e38dc0c`。
