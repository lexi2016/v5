# M09 A收盘复盘：普通Chat可读取的固定源码附件

日期：2026-10-10。这是原18模块中的M09/P3材料补全，不是新实现或部署。普通Chat不能访问私有GitHub时，直接读取ZIP中的真实文件，无须用户再次搬运同一源码。

## 先读什么

1. `handoff/START_HERE.md`、`PROMPT_FOR_CHAT.md`、`ACCEPTANCE.md`、`SOURCE_MAP.md`：目标、边界、验收与Mac分工。
2. `source/V5/src/v5_shadow/`中的本模块目标、`source/V5/tests/`对应测试，以及`source/V5/contracts/`来源manifest。
3. 对应`source/V5/vendor/`固定原算法和`source/handoff/v4-running-source-20261005/canonical/`原owner。后者是历史donor，不能整份覆盖现有V5，更不是Mac活动目录。
4. `SOURCE_MANIFEST.json`逐文件核commit/path/Git blob/SHA-256/bytes；`FIXED_TREE_SELECTION.json`记录固定tree核对与新路径不存在证据。

## 内容和准确边界

固定产品源码版本：`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`。共52个源码/源码配置文件、404637字节，均保留原UTF-8字节，没有替换换行、改动算法或填占位body。包含完整现有a_close模型capsule、A wrapper/tests、原A panel producer、AShareReviewStore/正式review与chain相关原件及只读公共槽/身份/发布接口。真实panel、M07阶段工件、M12视频/ASR/OCR数据及其全部生产链未附；这些依赖不能伪造。

这不是整个仓库或可直接启动的完整运行闭包。附入的capsule清单完整不等于所有原producer动态依赖齐备；canonical的动态import、第三方Python库、本机原collector、文件根与认证/网络环境仍需按实际执行路径核。未附全部前端/浏览器构建依赖、外部provider SDK/操作系统设施、实际Mac数据、账户凭据或端口/进程快照；不要在普通Chat伪造实测结果。

可以现在继续：原件静态审查、原算法等价设计、模块内最小候选及失败用例、共享接口变更请求。活动Mac合同、窗口与绑定只在实际启用/真实输入验收前由嘻嘻核；不要因为现场信息未取得就只退回缺源清单。若静态依赖仍缺，指明具体import/调用/文件及为何阻塞，继续所有不依赖该项的工作。

## 写入边界

`SOURCE_MANIFEST.json.access`给每个源文件标明权限角色。M09独占可改的现有目标为：V5/src/v5_shadow/a_close_review.py, V5/tests/test_a_close_review.py。

拟新增路径（已核固定tree不存在；Mac应用时仍须重核）：V5/src/v5_shadow/a_close_daily.py, V5/tests/test_a_close_daily.py, V5/docs/M09_A_CLOSE_HANDOFF.md。

所有V4 donor、vendor和manifest只读。共享gateway/API、账本/调度、日历、身份校验、前端和其他模块只读；需修改则提交固定前像+函数/接口+兼容测试+发布/回滚说明给统一集成者。不得发布跨市场整文件覆盖。保留V4，不交易、不改BUY、不扩大凭据或安全权限。

## 状态与核验

只执行了文件制备、Git blob/SHA/字节比较和ZIP CRC检查。没有导入或运行产品，没有执行业务测试、行情采集、Mac操作、候选补丁或部署。产品测试/实际API/页面/自然触发/回滚全部NOT_RUN；旧报告只能按R登记。

`PACKAGE_VERIFICATION.json`是附件完整性回执，不能作为业务测试通过证据。ZIP内`FILES_SHA256.json`列出全部制备文件（清单自身除外）摘要；ZIP的SHA-256及大小另见ZIP旁`.sha256`。包内相同blob从已抓取字节复用时，manifest同时记原fetch路径，且目标路径由完整固定tree独立验证为同一blob。没有凭文件名复制不同版本。
