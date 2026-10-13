# M14 现役发布成功与失败历史（2026-10-13）

本目录转存主控读取的 Mac 回执，转存者未执行部署或重测。success.json 与 prior-failure.json 均按原字节保留，分别为12,017 / 6,642 bytes；原SHA-256：
- success：28da4bacbc6fbc02bc36c961d02b34abe93d4d19a3e4e96d01bb3a5ac985510c
- prior-failure：6d8dce6271eaa9009ca38e8822f53e70acdc96e128e99cf2a01eccafd1a45e0e

## 发布及保护

北京时间23:03，固定c7b→52e71→fac269组合实际切换PASS，保留新预览54780/PID3345与source56563/PID3337。M14原保存690行/22页HTTP与DOM通过，其他11路明确HTTP200且JSON一致，旧manager descriptor精确保持。旧61236保留回退；M02 generation18327ae3ac839284230437989c9418c326b8f850decc38448c354d0ddf8319f0、V4与保护进程保持。未改产品、未放宽400×100ms等待条件；未重owner/采集。daily opt-in=false，native visual仍NOT_RUN（transport closed）。

前次DOM初始等待超时及自动回退完整保留于prior-failure.json。一次重试成功不证明旧超时根因，根因仍未证实。

## success快照之后的独立只读核验

以下为主控转述最新Mac原消息，不改success.json：快照中两个pending原浏览器请求已无法继续观察，不能宣称它们已完成。另行独立HTTP请求核得：
- 公告：32/147，余115；15:13:29 UTC起，4.324524秒，HTTP200，身份同run/generation。
- 旧超跌strict：31/214，余183；15:13:33 UTC起，4.501014秒，HTTP200，身份同run/generation。
- 首次并行公告在15:10:31 UTC返回503/CANNOT_CONFIRM，该失败保留；后续200不能证明完全没有间歇故障，不给根因结论。
- 15:14:19 UTC末次健康核验HTTP200，新进程仍存活。

现役页面发布通过不改变READY_WITH_GAPS、历史不足、正式资格/PIT或自然验收边界，也不是原生浏览器视觉通过。
