# M14真实canary/来源口径问题与M15环境复验摘要

记录类型：DERIVED_SUMMARY。本文件及summary.json由主控交办和已读取的Mac普通消息归纳，不是原raw receipt，也不声称与Mac原文件SHA相同。未上传原始行情、逐行OHLC或私有目录；转存者未测试、采集或运行owner。

## M14：有限真实canary成功，混源补齐停止

固定c52aca63e7aac5a1f450bd5d1e11ae805fe0cb31（原owner基线884548fea0a0056483e8175564eaee015a964023），18/18离线PASS。2026-10-13 17:58:16–17:58:17 UTC，仅一次原端点连接，3码各一次120 bars请求，无重试；11目标键仅覆盖10，仍缺HK.03469/20261012。726保护文件哈希不变，未repair/owner/发布，repair_ready=false。

后续只读原decoder对10个已返回键PASS，全部11键报RAW_REPAIR_EXACT_KEYS_MISSING；缺失未补零。原panel SHA为5f278c2d4d106f1c7085fc44cba89dab28f9ba91bc63de6fcf00ed86b3f45b51，manifest为b4857921d9c9333c3ee4a2f774f79c2ec3b6ba2b0de2063b97f55ddb869d7bb7，存在多种历史来源。最新重叠日trade口径：面板/新响应分别为HK.00001 3498184/34982、HK.02825 10000/100、HK.03469 200/2；数值比例不能证明单位，不能擅自乘100，价格基础/复权同样未证。原decoder还报告三个非目标历史日OHLC错误，保留其问题，不修改产品校验。

因此停止混源补齐，不将新响应拼入旧panel；后续仅准备批量原源与同源窗口代码，尚未实际执行，不计新批量数据/资格通过。Mac提供的比较JSON为压缩排版内容；本件只归纳问题，未以该文本冒充原字节报告。

## M15：声明范围内环境已有通过证据，uv.lock未同步

固定f7dd8e63a7c9fac67ad1cd84b3d6ebc2dbced5af，现有Python3.14.6/pandas2.3.3/pyarrow24.0.0满足README范围，港/沪/纽约时区可用。2026-10-13 18:09:24–30 UTC新增20项首次19 PASS/1沙箱loopback绑定错误、exit1；18:09:51–52仅补跑该项PASS、exit0。20项各有通过证据，不能称一次20/20 exit0。旧40、Node/build未重跑。530 release文件核验，候选目录现有544文件前后不变；未安装依赖或改声明，uv.lock未同步，不冒称完整锁安装验证。

真实source/owner未执行。M03 session20261013→M15 target20261014的真实三件仍缺；窗口与原cutoff保持，不能用环境通过替代输入准入或提前运行。

## 来源消息

- canary：msg_0b47eb1b0178a3a6016ace7160b68487d19d22cafc8acee64c
- 只读口径：msg_0b47eb1b0178a3a6016ace72b7385887d1b8044941be2211f3
- M15环境：msg_0b47eb1b0178a3a6016ace7410cf9887d1a670f26ecc8f0b43
