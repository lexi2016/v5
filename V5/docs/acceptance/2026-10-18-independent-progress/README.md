# V5 进展与验收状态（2026-10-18）

## 当前结论

V5 已完成一批只读 UI/API、发布桥接、日期身份和测试 harness 修复，但仍 **NOT_ACCEPTED**，不能视为全量验收通过或可替代 V4。PR #4 保持 Draft/open；本次提交只加入进度、测试证据与下一步交付文档，不修改产品运行源码、不合并、不部署。

证据测试基线：`91f1dbe18e9da1d6abbdb974c600c8196a9b796e`。2026-10-18 06:55 UTC核查PR4远端HEAD仍为该SHA。此后文档提交不是新产品测试；如分支再有产品变化，需要另测新HEAD。测试主机为隔离Linux环境，不能冒称用户Mac、真实浏览器或生产环境验收。

## 已有实现与验证

PR4所列修复涵盖：保存结果的精确日期/run读取；requested_date与实际research_date区分；旧研究接口GET-only别名；M16日期保留；真实采集准备状态；中文可操作诊断；IPC stderr/退出处理；长状态值与导航身份；发布桥接输入SHA校验；M17错误分类；P0只读runtime示例。模块存在不代表真实数据、自然调度和V4同等功能已验收。

本地独立测试结果：
- typecheck PASS，exit 0。
- 同一基线既有定向p0 164/164、M09 4/4 PASS；后续全量轮未重复这两项独立命令。
- 全量Vitest首轮471 PASS / 14 FAIL / 6 SKIP，exit 1。
- 仅绑定仓库生成器明确标识的synthetic Recovery样本后，重跑474 PASS / 11 FAIL / 6 SKIP，exit 1。合成样本不等于真实业务证据。
- 相关Python unittest 52 PASS，exit 0；不包括未被unittest收集的pytest函数。
- runtime额外组出现pytest缺依赖，仍BLOCKED/NOT_RUN；未安装或绕过权限。

[完整测试结果](TEST_RESULTS.md)逐项记录四组11项失败：3项真实Recovery回执、1项云端workspace响应、1项原689行OCT2投影、6项原owner observations材料缺失。当前证明的是输入/交付依赖缺口，不能证明业务断言错误，也不能据此判功能通过。

## 尚未闭环

真实采集入口绑定/周五数据、实际浏览器和HTTP验收、自然调度与连续两天证据、现役V4身份及完整功能对齐仍待验收。本轮没有重跑build/HTTP/浏览器/真实采集；PR4已有CI结果属于另一验证环境，不与本地结果混写。daily_manager_reconcile在该固定HEAD的源码内容及tracked文件名未找到，需准确路径/commit映射，保持NOT_FOUND/NOT_RUN。

## 最小下一步

1. 补四组原件的来源、内容SHA、授权可读位置及环境变量，保留严格断言；不能造数、空JSON、静默skip或删除测试。
2. 原件就绪后先跑四个失败文件，再跑全量Vitest，交固定SHA、环境、退出码及日志。
3. runtime/M18 pytest回归须在获准依赖或已有适合环境中单独执行；未收集不算通过。
4. 真实采集/浏览器/自然调度/V4 parity分别提供原始证据。保留V4，不执行交易，不改变安全设置或凭据。

[下一轮交付Prompt](UPDATED_CHAT_PROMPT.md)仅存仓库，尚未向外部Chat发送。[历史定向复核](REPORT_91f1dbe.md)与[日志说明和原始hash](LOG_MANIFEST.md)保留测试阶段边界。

发布范围：进展与必要脱敏文本证据。未上传私人会话链接、凭据、原始业务响应、真实owner数据或合成JSON。日志内本地根路径已替换；前端长日志为明确节选，不冒充完整原日志。本次发布由用户明确要求更新V5进展至GitHub。
