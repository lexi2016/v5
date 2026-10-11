> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

# M09 R2：真实历史输入与现场接线增补

日期：2026-10-11。本版在R1任务材料上新增Mac只读取件，不改原52份源码基线，不混入候选实现。R1原包已完整保留。新增输入包 `M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip` 为7577304字节、41成员，SHA-256 `24eb6689e336c45e63d0bc071722ea0379c9b98a2961a60a54dd8807999f2f44`。云端独立核ZIP CRC、40项manifest、18项来源复制索引全部匹配。

## 一、已到真实输入，不再泛称“没有panel”

T=`20261009`。新增包有原panel的T日完整8列投影 `originals/panel_20261009_required8.parquet`，279209字节，SHA-256 `7dfa12fa03ad76d5e946088f88993748a3fffd8943281a12eb364c35712f8c47`。保留原行序、Arrow类型、所有T行，没有去重/填值/合成。

原panel全文件为1383142544字节，SHA-256 `25aaa10f2080a72f0f9266a9456a3c3968dd1370068f31b0fb9106ea34434485`；约1.38GB原全文件不在包内。两者的SHA不应相等。原pointer原字节与SHA附入，原绝对Mac路径只作证据；未来候选应在私有目录新建指向已解压投影的本地指针，不能修改或直接复用跨机绝对路径。

Mac提取元数据记5126行/5126唯一代码。云端独立复数成员文本确为5126行/5126唯一；未安装pyarrow，因此本次没有在云端再次解码parquet重算列统计，也没有运行产品。parquet字节与Macmanifest已独立核对。不能把该限制冒称统计第二次运行通过。

必须保留数据缺口：

- 2行缺失bar_close_pos
- 137行name为空字符串
- 240行tdx_industry_code与tdx_industry_name为空字符串
- 源回执原JSON为status=PARTIAL、authority_status=REBUILD_REQUIRED、coverage_rate=0.8858620689655172
- 回执accepted_count=5138、target_count=5800，panel row_count=5126；这是不同计数，不能把5138直接当panel成员，也不能编造12行差异原因

`membership_20261009.txt`证明“原源T切片的完整成员”，不证明全市场或完整权威输入。该真实历史原件可用于历史诊断/回放、保真/拒绝路径与接线工程；不能升级成16:05/17:10自然运行或完整PIT生产准入证据。

## 二、真实时间仍有限制

原回执的同步记录时段为2026-10-09 17:01:05.003487+08:00至17:09:06.622525+08:00。formula记录开始17:09:17、完成17:11:27，未带时区后缀；最终panel没有明确available_at。不能用mtime、文件名或formula时间补造available_at，也不能证明17:10槽前已可用。

结论：保留真实T历史回放用途和原时间证据；不得回填16:05，自然17:10准入同样未证，严格15:00 PIT未证。以后新日自然运行由当时真实来源/时点决定，不能因此把整个daily实现无限期阻断。

## 三、真正断点已从猜测变为现场事实

1. scheduler实际checkout为 `.../com.lexi.v4.local/releases/hk-auto-d1-20261011-r1/app`。其 `infrastructure/scheduling/executor_registry_review.py::_a_share_close_review` 先 `resolve_selector_panel(selector_data_root, request.business_date)`，再写 `{producer_data_root}/.dispatcher_tmp/selector_panel_pointer.txt`，以该指针调用 `ops.build_a_share_close_review --data-root <producer_data_root> --date T --panel-pointer <pointer>`。
2. producer实际root为 `/Users/lexi/Library/Application Support/com.lexi.v35.local/state/data`。原review/receipt已经存在且摘要匹配，run_id=`REPLAY_RESEARCH_V1_20261009_001`。这是历史存量对照，不是本次V5输出或自然槽回执。
3. 活动API是 `http://127.0.0.1:8873/api/v3/review?date=20261009`，release=`hk-dated-name-20261011-r2`，PID取件时为55132；进程会变，这些是快照。API `app.py` 把 `store.root` 传给 `create_review_router`，该root为 `/Users/lexi/Library/Application Support/com.lexi.v4.local/state/data`，与producer root不同。
4. 活动 `review_core_a_share_bundle_required` 仅在目标日current.json存在时为true。本次目标日current不存在，原router走legacy AShareReviewStore/阶段fallback，实际GET A状态为PARTIAL_STAGE_EVIDENCE、source_role=V3_5_STAGE_EVIDENCE_PARTIAL。不能把V3.5根已有review误认为API已读到。
5. 原页面消费链已附：`App.vue::loadCloseReview('A') → api/review.ts::loadReview(T) → GET /api/v3/review?date=T → ReviewView.vue → AshareReviewPanel(:review=current.market_reviews.A)`。真实 `AshareReviewPanel.vue` 子组件未附本包，后续若需改字段展示，应由统一集成者精确取该组件及其必要依赖，不阻断daily核心。
6. 在本次检查的V5 publication配置范围内未找到M09配置。不能发明module_id/release_id/data_root/routes/marker，也不能把manager或announcement配置改作M09。新M09私有配置和只读兼容绑定是代码/集成要交付的部分，不是要求用户预先生成的输入。
7. 冻结runtime_workloads仍为1605/1710，目标T在已配置dispatcher root未找到精确a_share_close_review槽回执。不能用定义、文件存在或历史run_id倒推两槽已执行。

现场producer、AShareReviewStore、runtime_workloads、market_calendar四份源码与原固定F逐字节相同，原52文件版本继续不变。活动API/UI等取件作为另一个有来源的现场参考层，不覆盖原baseline。

## 四、必须补的代码与集成接线

- 新增真正 `a_close_daily` 准入/运行适配，分别保存原始输入身份、数据质量问题、来源权威/PIT/时间限制、价格模型与阶段/视频链状态。遇到坏值按合同拒绝对应生产准入并保留诊断，不得填零/填行业/删行来伪造完整。
- 真实历史T原件用于未清洗的诊断/原算法对照：原算法若返回或报错，完整保留；不提前承诺它必然生成完整价格成功。可控的有效工程fixture用于隔离测试正常路径，清楚标SYNTHETIC，不能替换此真实输入证据。
- 缺M07/M12当前已提交材料保持PARTIAL/CANNOT_CONFIRM；模型数值有结果也不能消除输入权威/PIT/视频消费限制。M09不补造/重跑视频工件。
- 将原writer封装到M09私有不可变run根，独立读回校验后发布V5 generation。失败attempt与latest_success分开；原replace只留摘要，不能覆盖前槽唯一完整成功副本。
- 统一集成者给出新的M09配置与精确route→module→generation→私有root绑定，并把已提交M09 A结果合入原读面，HK保持原有绑定。不能为“读到”而把V4全局root改成V3.5或M09，更不能写入V4来迎合旧API。
- 在当前UI只读GET链上检验A字段消费；已存在的研究复盘手动POST generate入口属于另一功能，不把M09读取隐式接成模型/视频生成。
- 补两槽触发/计算身份区分、同输入复用两receipt、晚到素材新run、失败保旧、独立发布回滚验收。无自然回执则相关验收NOT_RUN，不阻断工程实现。

## 五、环境版本差异需要实测，不能擅改

现场Python3.14.6、pandas3.0.5、pyarrow25.0.1、pytest9.1.1；解释器路径与两份uv.lock已附。固定V5声明为pandas>=2.3,<3、pyarrow>=21,<25，现有pandas/pyarrow超范围。Python版本满足声明，依赖范围不满足声明。

交付时标明实际环境和原声明差异，优先查现有已批准可用环境；不得擅自安装、升级/降级包或改pyproject宽松范围来隐去差异。兼容问题只阻断需要该环境证明的运行层，不阻断静态设计、代码候选和测试源码。

## 六、可选材料的“未找到”仅限实际检查范围

本次未在检查过的consumer/producer根定位到请求的视频pointer/session/alignment/gap，也未建立正式M07/M12工件引用。不要推断全盘不存在。

进一步窄取件：原node的stock mentions线索是 `close_review_sources/{T}/bilibili/transcript_stockdict/stock_mentions.json`，本次inventory中查的是较浅的 `.../bilibili/stock_mentions.json`。若该字段影响后续集成，补核正确已知路径；不必为此停止基础实现。有效的current_asr_pointer路径本次已查，未找到。

新增包中的collect.py、finalize.py仅为取件溯源，不在云端执行。新review/store/API/UI仍属实现输出。完整目标、原算法不变边界及after/diff/测试交付标准继续按主任务书执行。
