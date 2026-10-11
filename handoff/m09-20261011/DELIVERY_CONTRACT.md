> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 候选、验收与返工交付合同

## 必交实体，不接受只报结论

1. `after/`：完整候选源码树及测试源码，保留精确相对路径；原件只读复制不得暗改。新增的冻结闭包/loader/manifest若必要一并交付；共享文件只交独立接口请求，由唯一集成者写入。
2. `before/` 与 `CHANGED_FILES.json`：每个修改/删除文件的原字节和SHA、每个新增路径在固定baseline不存在的证据、全部after文件SHA、动作和原因。基线完整commit与新候选commit/包SHA不能只写短码。
3. `forward.patch` 与 `reverse.patch`：完整unified/binary diff，含新增/删除；提交正向check/apply、反向check/apply的真实日志和全树哈希比对。反向补丁仅用于隔离验证，不意味着允许覆盖现役改动。
4. `SOURCE_DEPENDENCIES.json`：donor来源repo/commit/path/blob/rawSHA/字节、新目标映射、全部内部import/动态读文件/外部依赖、实际Python与已安装库版本/锁文件SHA、缺漏的影响范围。静态存在、可导入、测试已跑分开。
5. `tests/` 与 `logs/`：失败用例源码、真实完整命令、cwd、环境身份、起止UTC及上海时间、exit、stdout/stderr、测试计数与skip原因、日志SHA。先失败再修复的RED/GREEN证据与最终固定候选回归分开；缺RED不能编造。NOT_RUN、BLOCKED、FAILED、SKIPPED不得算PASS。
6. `INPUTS_MANIFEST.json` / `OUTPUTS_MANIFEST.json`：真实输入和待实现输出严格分开。真实panel/成员/来源时点/输入SHA/只读快照、M07/M12当时可用引用，与新review/model/store/receipt/API evidence分别记账。synthetic/replay/manual recovery/natural run不可混算。
7. `ALGORITHM_PARITY.json`：在同一不可变输入上的原/after代码身份、字段列表、比较规则、差异与容许理由。原异常必须保留trace；不能改算法绕过。
8. `MAC_ACCEPTANCE.md`：原→候选前像核对、实际应用后SHA、精准测试/真实输入/独立读回/API/原页验收、单模块发布与回滚步骤/回执。普通Chat若无Mac访问，必须明确未做，由现有Mac执行者独立填回。
9. `INTERFACE_REQUESTS/`：公共改动的请求ID、owner、前像commit/path/SHA、函数/route、旧新schema和例子、身份/日期/状态语义、兼容性、双方测试、发布顺序及回滚。不以整个shared文件替换其他模块候选。
10. 新私有 `lexi2016/v5` 的固定版本链接与从同一完整commit导出的实际离线ZIP、成员清单、SHA、bytes、CRC/逐文件匹配结果；不只交私库链接。若尚未发布，交本地完整包并如实留待发布字段。

## 算法等价必须覆盖

同日全部声明输入的代码集合/顺序、涨跌平守恒（up+down+flat等于已准入总数）、行业指标与排序、角色归属/顺序/分数/理由、scenario_tree原固定0.12/0.28/0.60与触发/失效条件、market_regime/risk_tone、core_stocks不从观察池晋升、quality_gate、source_role、原拒绝码/未知/研究资格、安全标志。概率是冻结旧常量，不宣称已校准；LLM仍禁用，不把视频链READY推导成模型已消费视频。

允许变化仅限事先列明的封装、身份/来源追踪、私有存储、只读发布与展示。原算法内容、拒绝原因和安全含义不能通过“归一化比较”删掉。run_id/实际时间等运行元数据可按明确映射比较，禁止笼统忽略所有差异。

## 负例/故障矩阵

- T非法、休市、时区错位、panel含异日、类型导致日期过滤空、pointer不存在/越界/symlink/计算中变更、parquet SHA变化。
- 缺8列任一、重复代码、成员漏/多、用Top10冒完整、非法A后缀、NaN/Inf/字符串数字、负amount、bar_close_pos越界、行业缺失；拒绝/未知不静默置0。
- 缺成员来源或时间、capture/available/cutoff顺序非法、晚到视频17:10后、可用时点未知、伪造未来来源；不得回填旧槽。
- 两槽同输入：只算一次（若完整identity确实相同）但两个触发receipt；输入/配置/代码变更必须新run，不能仅按T复用。
- 同槽重复/并发、后槽失败/超时、中断在payload/receipt/manifest任一步、独立读回SHA不符、generation CAS冲突；latest_attempt不掩盖latest_success。
- 缺M07阶段/视频/ASR/OCR/对齐/缺口：price成功可保留、链缺口可见；M09不得重跑M12，不能把历史成品当当时可用材料。
- A/H共享普通URL：A发布与A回滚不变HK；GET/刷新/返回/切日/重复点击不生产，目标日无结果明确缺失，旧日成功明确旧日。
- 单模块升级/回滚、跨日、睡眠/重启后恢复、错过窗口如实标记；不改V4资产/进程、不扩权限、不交易。

## 五层状态

1. 工程层：完整候选、前像/after/diff核对、定向与所需回归/负例有真实日志。
2. 真实数据层：真实T panel/成员/时点/SHA准入，原算法→原writer→独立reader同运行身份；工程fixture不计本层。
3. 消费层：活动普通API和原ReviewView确实读该T已提交产物，同run及各自类型SHA链；截图/响应/无副作用证据。
4. 自动层：既有两槽真实触发、幂等/新输入/失败保旧/恢复事实。手动触发不能冒自然证据。
5. 完整层：前四层、当前固定候选整体必要回归、模块隔离发布回滚和连续两个适用交易日自然接续证据齐全。没有足够自然窗口就保留未完成，不把材料交付或一次回放叫完整完成。

## 每次结果只说新增事实

优先交已完成实体与准确阻断；不用先等待一份18模块大计划。禁止要求用户提供尚未生成的M09输出才开始写代码；原件输入不足仅阻断相关真实验收，接口/环境不足仅阻断相关集成验收。发现超出已批准范围或安全/凭据变化时停止该步骤，继续独立的已授权工作。
