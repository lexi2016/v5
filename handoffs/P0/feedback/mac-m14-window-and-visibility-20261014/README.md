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
