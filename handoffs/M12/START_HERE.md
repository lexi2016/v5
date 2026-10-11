# V5 M12 首次完整代码交接

这是一份输入材料交接，尚未产生本模块产品候选、测试或部署证明。

1. 实际使用 GitHub 插件固定到发送者提供的本仓库 commit 读取 `PROMPT_FOR_CHAT.txt`，执行完整任务。
2. 读取 `original_source/SOURCE_MANIFEST.json`、`original_source/START_HERE.md`、`original_source/handoff/SOURCE_MAP.md`、`original_source/reference-plans/` 与所有必要 donor/test 原文件。
3. 读取 `integration_source_supplement/SOURCE_MANIFEST.json`、README 与只读原接线前像。
4. 本分支源码 F 固定为 f7cb731c384ee6890a87d16c19a5b5a621779477，目标为独立私有 lexi2016/v5。原18模块和原总计划不改号。以 PROMPT_FOR_CHAT 为最新完整交付要求，源包较旧的只交接线建议条款已经升级为实际 integration_candidate 整合代码，仍禁止直接覆盖共享路径。
5. 使用 GPT-6 极高推理与真实 Superpowers，交完整 after、前后 SHA、有效正反 patch、原始测试日志，以及原 owner→私有保存→新进程读回→调度/API/页面实际代码。真实服务缺失不妨碍离线工程实现。
6. 保留 V4、不交易、不扩大权限或凭据访问。所有源文件、候选代码、测试、日志及后续交付都通过 GitHub；读取失败时报告精确调用与错误，不默认改为 ZIP。

## 实际开发分支与后续提交

仓库为独立私有 `lexi2016/v5`，本模块开发分支为 `dev/m12-github-handoff-20261011`，交接路径为 `handoffs/M12/`。从发送者提供的固定交接 commit 核 SHA 后读取全部文件，并在同一开发分支继续提交完整实现。该分支以干净 main 基线 `2489ea1e04a26a9e2f318f498ac3f5f8c970fe48` 隔离建立，不带 M09 或其他模块候选。不要修改 main、其他模块分支或 V4，不 force、不覆盖并发，不自行合并。交付时返回真实最终 commit、目录入口和验证状态。

最新用户要求：所有模块会话和交付均通过 GitHub。本段覆盖原材料中 ZIP/附件交付措辞；原源码与原 manifest 字节保留。固定原件是参考/前像，不是写入活动共享路径的授权。
