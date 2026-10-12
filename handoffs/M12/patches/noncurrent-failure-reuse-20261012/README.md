# M12：非 current 失败 run 的最小复用修复

基线：lexi2016/v5 的 769db376cf8ab0c2c1f69e31239aec38494ddd82（候选 befa4124149396cf3c052ba6532cfa7897be62df 加 Mac 17 项验收反馈）。仅更新原开发分支，原 donor、反馈、V4 与其他模块不改。

## 修复与边界

- 根因：A 成功后，B 的 ASR 失败被不可变保存，owner current 保持 A。重复 B 只检查 current，漏掉已存 B，又执行 ASR，最终触发 ImmutableRunError。
- producer 在 capture/ASR 和缓存处理前检查本次确定 run。仅复用 receipt.status == ACQUIRE_FAILED 的已校验失败证据，返回原 manifest，计数为本次 0。失败 receipt、artifact、current 和 V5 latest_success 不改。
- core 将原 inspect_bundle 完整校验体原样提取为共享内部函数。非 current run 从自己的 receipt 绑定 manifest SHA、请求 input_digest、exact date/run，再走相同 artifact/SHA/安全标记/内部 pointer 校验；不临时改 current.json。原校验体逐字节比对相同，见 patch-verification.json。
- 失败 ASR sentinel 仍不当成功缓存。ASR_FAILED 不升级；ASR_REVIEW_REQUIRED 仍须人工审核。没有改网络许可、安全标记、作者/日期筛选、immutable 写入门或发布资格门。
- 历史成功 run 不通过此失败复用途径重新晋升：A 成功 → B 成功 → 再次 A，保留原 ImmutableRunError，提前拒绝且 latest_success 仍为 B。
- discovery 为计算候选身份仍会调用；“零重复”仅指 capture/ASR。测试只使用合成 AcquisitionTools，并阻断 socket 网络，不是实际视频采集或真实 ASR 验收。
- 代码摘要属于 owner 身份。安装本补丁改变源码摘要，会形成新 run 身份；本修复不承诺跨版本旧失败 run 一律零 ASR。相同已固定代码、输入、配置、工具身份下的重复 B 才直接复用原失败证据。

## 已有恢复身份合同

原 ProducerConfig.fingerprint 已包含 extra。测试通过原 run_video(..., config=ProducerConfig(..., extra={"recovery_attempt": "explicit-attempt-C"})) 显式改变配置身份，无新增 retry 参数或新框架。修好合成 ASR 后，C 在同 BV/媒体 SHA 下复用媒体，仅新执行一次 ASR，产生不同不可变 run；B 与旧媒体字节不变，C 状态保持 ASR_REVIEW_REQUIRED。重复 C 直接复用。

这只证明原 owner API 的现有配置身份机制。recovery_attempt 是测试所用 extra 键名，不是新标准接口。V5 run_video_fupan 目前没有对外暴露 owner config/专门 retry 身份参数；其 source_identity/tool_identity/config_identity 仅写外围 envelope，不能声称改变这些字符串就能恢复 B。同身份依赖变好仍返回原失败证据。本补丁没有扩展该 wrapper；owner C 不自动晋升 V5 latest_success。

## 文件与 PIN

生产差分仅 core.py、producer.py；tests/m12 原 17 项全部保留，追加 4 项。PIN.json 固定源提交、原/新 Git blob、SHA256、字节数。before/、after/ 为完整三文件，runtime.patch 与 reverse.patch 已分别 apply --check、应用后 SHA 和回退 SHA 实测。

原 donor 副本留在 handoffs/M12/original_source，不修改其原始 pin/manifest 来伪装 vendor 未变化。本目录 PIN 是这次 V5 vendor 小补丁的显式增量记录。

## 实测证据

verification/commands.json 记录解释器、命令、起止时间与退出码；stdout/stderr 分文件保留。

- 合成原 producer：新增 4 项对原生产代码实测红灯。重复失败两个状态触发 ImmutableRunError；篡改场景也证实 ASR 被重复执行。
- 最终候选新增 4 项 / 8 个 subtest：unittest 全通过，exit 0。
- 最终候选整个当前 M12 可运行模块：21 项 / 21 个 subtest，全通过，exit 0。原 17 项保留，未与历史运行相加。
- 云 pytest 未安装，命令返回 No module named pytest，exit 1。未安装或下载软件。
- 独立审查发现历史成功复用可能倒退 latest_success；已追加对应红绿回归并将复用限定为 ACQUIRE_FAILED。没有修改 wrapper 发布逻辑。

Mac 新候选独验、真实视频/ASR、API/UI接线、自然调度均未执行。本补丁仅完成此失败复用代码缺口，不宣称 M12 整模块验收结束。

## Mac 仅新增回归

核验集成者提供的最终固定提交后，在该分支候选根目录使用既有 Python 3.14.6 / pytest 9.0.2（沿用原 site path 和无插件自动加载配置，不安装任何依赖）：

    "$PYTHON" -B -m pytest -q -p no:cacheprovider tests/m12/test_video_fupan_default_chain.py -k 'noncurrent_failed_run or owner_new_config_attempt or historical_success_is_not_repromoted'

预期：4 passed，8 subtests passed，17 deselected。若沿用的 pytest 显示格式不同，以收集到相同四个测试、所有子场景通过及 exit 0 为准。不重跑旧 17 项。

无 pytest 的等价既有 stdlib 命令：

    PYTHONPATH=tests/m12 "$PYTHON" -B -m unittest -v test_video_fupan_default_chain.VideoFupanDefaultChainTests.test_noncurrent_failed_run_reuses_exact_evidence_without_capture_or_asr test_video_fupan_default_chain.VideoFupanDefaultChainTests.test_owner_new_config_attempt_recovers_failed_asr_into_new_immutable_run test_video_fupan_default_chain.VideoFupanDefaultChainTests.test_noncurrent_failed_run_tampering_is_rejected_before_capture_or_asr test_video_fupan_default_chain.VideoFupanDefaultChainTests.test_historical_success_is_not_repromoted_by_failure_reuse_path

预期 Ran 4 tests / OK / exit 0。这四项使用临时 V5 私有根，不访问真实媒体、业务根或凭据。

## 回退

只对匹配本目录 after SHA 的候选运行 reverse.patch；先 git apply --check。回退会恢复三个代码/测试前像，不触碰任何运行数据、失败证据、current/latest 指针、原反馈或 V4。若集成后文件已变，不强行应用，交统一集成者按 PIN 处理。补丁不包含部署动作。
