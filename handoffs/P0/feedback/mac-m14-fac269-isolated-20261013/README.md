# M14 fac269 Mac 隔离验收及后续部署状态

本目录转存主控提供的 Mac 原回执，未重测。result.json 原字节保留：10,599 bytes，SHA-256 35b11ec6d0a3c0d54c9c6fb2edc1395cae2f1b90c52355702b31f7e03a46a8d1。

固定候选 fac269ade842eb1d9b54c604b77091b0cd58bd44：隔离 Vue 15项、typecheck/build、真实保存结果690行/22页 HTTP 与 DOM 通过；未重跑owner，原生视觉NOT_RUN。READY_WITH_GAPS及资格/自然false保留。

原result记录于2026-10-13 22:18:28（北京时间），当时部署因活动前像不匹配而NOT_RUN。该历史不覆盖或改写。

主控后续状态：现役组合 c7b→fac 的切换尝试在 DOM 初始等待超时后自动回退，未成功部署。该新组合的完整日志尚待返回，Mac正在只读定位；此处不预判产品或测试根因，不将隔离通过称为现役发布成功。
