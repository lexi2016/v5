# M14 真实全批采集终态摘要

本文件与 summary.json 为 **DERIVED_SUMMARY（派生摘要）**：转存 Mac 任务最终消息，不是原始 receipt，不声称与原 JSON 字节或 SHA 相同；本次文档写入者未执行测试或采集。未上传原始行情、逐股票数据文件或私有绝对路径。

- 来源：Mac thread `01a12e51-a0ec-705c-96e5-26cfd89360f8`，消息 `msg_0b47eb1b0178a3a6016ace7a63a8e487d1b7c70ae057a051de`。
- 固定候选：[02193d90221b24f59b0678fc3035eaa128791259](https://github.com/lexi2016/v5/commit/02193d90221b24f59b0678fc3035eaa128791259)。
- 2026-10-13 UTC 18:24:05.309966–18:36:25.267216（北京时间次日02:24–02:36），739.96秒，CAPTURED / exit 0。
- 新增687/687请求成功，3份旧 canary 回执逐字复用：共690份成功回执、80,792条完整响应记录。失败/未知/未执行/重试均0；固定端点单连接，最小请求开始间隔1.046427秒。
- 原2574缺失键覆盖2223，仍缺351键／24代码；HK.03469/20261012仍缺，未补零。
- 批量离线28/28 PASS；准备器7/8 PASS，一项为硬编码临时目录的Mac符号链接假设失败，历史保留，不称全绿。未改候选，真实物理路径等价检查及实际690成员／2574缺键准备通过。
- 只读checkpoint/resume审计exit 0；732保护文件（含714个.day）全部未变。

## 边界与下一步

未repair、未owner、未发布、未正式准入；repair_ready=false、natural_verified=false，完整模块验收未完成。同源adapter仍开发，不能把采集完成计作后续算法或owner通过。此前混源trade单位和price basis问题仍未证实，禁止据此乘100或混补；[前次口径问题摘要](../mac-m14-canary-m15-environment-summary-20261014/README.md)保留。

## 原消息报告的身份与指纹

这些是来源消息报告的原材料指纹，并非本派生摘要的指纹；原始材料仍在Mac保留。

- run_id：`1896a7a023d64143b682c5a410adeb43`
- plan SHA256：`d55c91362bdb6b895face0896e5ff411959196ccc1af7cb2c410be4de71c3166`
- round result SHA256：`a680e358a656bf875f888cbc10063ae0f5a1bb3a0c739735b00003ec80a8ab09`
- checkpoint SHA256：`6a932ff96382486ff069085d71d0a5ec149c9b6630fce5af1ca86356fad9f112`
- result.safe.json SHA256：`ff419cb48d2b76a010fcb5f5a6c6875c021c2337ea01ea866b49ce22c1933912`
