> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 专属 Chat 任务：把原 A 收盘算法接成 V5 真实日复盘

你负责原18模块中的 M09 A收盘复盘。用户已逐项批准下面的目标。请从随附原始源码和任务书直接开始模块局部实现，不重复索要已经明确的范围批准，也不要把工作退回为等待18模块全量计划。

新工作目的仓库是用户指定的独立私有 `lexi2016/v5`；新仓库创建/固定提交状态见 `PUBLICATION_IDENTITY.json`。原始来源是 `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`，只读保留。禁止向v4写M09。仓库暂不可访问时，直接使用同附的离线原ZIP，不要求用户再复制源码。

先读 `TASK_M09.md`、`ASSEMBLY.md`、`DEPENDENCY_MANIFEST.json`、`DELIVERY_CONTRACT.md`。原ZIP `v5-module09-source-20261010.zip` 为145374 bytes、52份源码/配置，SHA-256为 `ee45e1cb627df660d15574a5a0a023be00e7fac0a29e983109b202e7e3af25fa`。按照解压说明核验原件；原ZIP里的旧handoff只作历史参考，本次任务书为当前要求。

使用适用的Superpowers流程：先做局部诊断与短计划，再test-driven-development先失败用例，最后verification-before-completion。若涉及已有故障先用systematic-debugging。不要把已经批准的完整业务目标再拆成逐步审批；真正影响安全/权限/凭据或超范围的动作才停下说明。若你的执行环境没有这些技能，明确缺失，按同样的诊断、失败用例、最小实现、实测证据顺序继续，不能假称调用过技能。

业务闭环：复用 `build_review_from_panel → build_close_model → build_close_review_chain → build_a_share_review → AShareReviewStore` 的原算法与正式产品构造，将真实交易日T的panel和当时可用的阶段/视频证据形成新复盘，在V5私有根保存/独立读回，并经统一集成接入普通API/原ReviewView的V5预览。展示涨跌平、行业、角色、模型情景和证据缺口。保留原研究资格/PIT未知、固定情景概率、禁用LLM/WATCH_ONLY/安全标志；不交易，不改BUY，不碰V4，不扩系统安全权限或凭据访问。

注意当前差异：现有 `a_close_review.py` 只做SYNTHETIC/RECORDED_INPUT_REPLAY；新 `a_close_daily.py`、其测试和M09说明在固定基线不存在，正是你需要新增的生产适配，不可把回放放宽或改名冒生产。包内纯producer的12个内部静态import已齐，不要泛称writer源码缺失；环境/动态绑定另核。完整API facade/UI/video runner不在本闭包，需按取件单做窄集成，不要把M12生产链搬进M09。

日期：M09就是T当日收盘，不套M13的source9/target12，不要求未来日期已经有API输出。panel.trade_date、模型review_date、review.trade_date、API请求日一致；原模型15:30标签、来源capture/available、严格15:00 PIT和16:05/17:10触发槽分别记录，不能互相代替。原始panel、成员与时点SHA是真输入；尚未生成的review/store/API响应是你要产出的输出，禁止倒要它们作为前置条件。

两槽：16:05和17:10（Asia/Shanghai）都留独立触发回执；完整计算身份相同可复用，晚到且cutoff前可用的新材料创建后槽新run；17:10之后的材料不得回填两个旧槽。失败保旧成功，缺阶段/视频为独立PARTIAL/CANNOT_CONFIRM。原replace会覆盖同日payload，不能只靠supersession摘要声称前槽成功完整保留；需要私有不可变run/generation保护。只有普通GET/刷新/返回/切日不能采集或生产。

工作范围：模块源码/测试/说明可交完整候选。原始donor/vendor/manifest不改；新增冻结闭包若必要，提交逐文件来源与新目标/manifest候选，由统一集成收录。共享gateway/API/ledger/scheduler/UI/日历及其他模块只提交函数级接口请求，不能整文件覆盖，单模块独立发布回滚。原API strict Review Core分支可能绕过legacy store，必须用现场绑定和实际原页面消费证据确认接通，不能只检查HTTP200。

先给首个可用成果：具体断点、模块局部计划、失败用例和开始实现的文件清单。继续完成完整after树、正向/反向diff、原件/候选SHA、实际测试命令和完整日志、原算法逐字段等价、Mac验收/回滚和精确依赖缺口。不能只交Markdown或GitHub链接。详见DELIVERY_CONTRACT；新私库发布时同固定commit离线ZIP必须一起给，免得私库connector缺失再次阻断。

Mac实物由现有Mac执行者按 `MAC_READONLY_TAKEOUT.md` 取得；当现场件未到时，先完成不依赖它们的工程实现/可控fixture验证，明确NOT_RUN/BLOCKED层次，不伪造实测。真实运行、API/原页、自然两槽与回滚由Mac独立验证。未知路径不猜，缺输出不当缺输入，失败和历史回放不冒当前自然成功。
