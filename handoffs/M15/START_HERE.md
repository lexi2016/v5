# M15 美股到港股映射：GitHub 源码与 R1 返修入口

本模块工作分支为 lexi2016/v5 的 dev/m15-github-handoff-20261011。继续唯一原会话 https://chatgpt.com/c/6aca4b1c-7bac-83ec-878c-d1fb0bd37b38 ，不得新增平行 M15。

## 阅读顺序

1. PUBLISH_SCOPE.md：本次只复制原 SOURCE 的74/88件；14件M18参考本体明确排除。不是完整可运行装配。
2. reviews/REVIEW_M15_R1.md：R1退回的准确原因与最小修复要求。
3. tasks/M15_RESUME_CODE_DELIVERY_20261011_1124.txt 及 tasks/latest_task_documents/：已有完整返修任务及更新过的原任务/来源索引。
4. source/：M15原算法、39件US owner闭包、M15适配器/测试、必要共享只读合同和原来源manifest。source/SOURCE_MANIFEST.json与CSV保留原始字节，包括未复制文件的原始条目；请结合PUBLISH_SCOPE看实际发布范围。
5. candidate_r1_rejected/：6件原R1候选及其原日志，另存不覆盖before。
6. evidence/M15_existing_paths_sha_readonly.json：现成Mac五件原文件的路径/字节/SHA核对元数据，不是其真实payload，不证明R1已通过。
7. PUBLISH_MANIFEST.json：本次85件已有材料原字节及发布来源清单。

## 明确状态

R1只给daily_us_owner.py增加两行ledger_run_id非空字符串检查，尚未完成M15材料入口、窄旧receipt兼容、按run/SHA精确读回、成功保留/未知attempt恢复及完整交付。原日志为11 passed、10 setup errors（缺真实REQUEST_PATH），无进程exit记录；不能当21通过或补造exit。runtime.patch头路径错误，reverse.patch与forward相同。当前未进行新的产品测试、真实业务验收或部署。

## 后续交付方式

用户已改为GitHub工作：此分支提交完整M15实现/专属测试/真实日志及固定candidate commit，回传精确diff和来源/SHA映射。旧文档中的ZIP交付或旧分支限制为历史内容，以本入口的模块独立分支工作方式为准。工具读取/写入失败须保留真实错误，不假造已读或已提交。

仅修改本M15允许的适配器、自有US映射/bridge、相应manifest/PIN与必要私有文件/专属测试；原39件算法不为凑变化重写，保留原四键/关系语义、源session/cutoff/PIT与实际时钟。共享接口、M02/M03/M04/M18和调度/API/UI仅提精确集成请求，不跨写。14件未复制的M18本体不是本次修复的实现许可；需要时明确缺件及必要性，由协调者处理，不能伪造闭包。

保留V4/main与现役系统，不交易、不扩大凭据或安全权限。Mac独立验收以修复后的固定候选为准；材料交接完成不等于业务验收完成。

