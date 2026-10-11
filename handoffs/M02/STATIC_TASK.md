# M02｜保留原owner/readers的最小完整返修

本文件为源码与原静态review派生的任务说明，不是R4代码或实测记录。继续原M02 Chat，在`dev/m02-github-handoff-20261011`按固定交接commit读原件后交完整候选，不用ZIP替代GitHub。

## 原R3缺陷
1. 泛化`_reader_state`对任意无error字典给VALID，包括{}；原测试同时要求{}非VALID、又允许伪资格字典VALID，合同矛盾。
2. panel使用任意外部callback而非固定owner。真实`FrozenHK02Assets`为数据类，不能整体直接JSON序列化；现独立读回完全漏读panel。
3. `write_text`直接覆盖调用方路径，未有可信私有根/输入输出隔离/symlink约束、原子且不可变提交、幂等及失败保旧成功。
4. 磁盘JSON解析未核binding/receipt schema/hash和保存的root/files/SHA/owner/run/日期/结果身份；新参数可替换已保存来源。
5. 三日期/cutoff只被保存，没有参考日、日历、时区与真实取得/可得时点约束。
6. 正反patch只有注释，不是可应用diff；源码/测试闭环与交付身份未齐。固定F的实际src目录没有hk_source_daily.py，新增前像ABSENT须在后续实际分支再次核对。

## 必须复用的接口
- `membership_reader.read_private(root, files, target)`：files为精确七件相对路径→SHA256映射。复用原SDK/owner/七文件验证；真实成功有target_date、request_sha256、source_capsule_sha256、codes、source，不以无error替代。
- `native_identity_reader.read_private(binding, date)`：binding含root/files；真实成功有master、manifest、request_sha256、owner_source_sha256。保留原子进程、固定loader、输入前后快照等验证。
- panel经原pinned loader调用`load_frozen_hk_0_2_assets(asset_root)`。完整原函数在source内`V5/vendor/hk_preselection_baseline/upstreams/v3_shared_data/shared_data/hk_0_2.py`。保持原panel/model/name checksum和oracle身份验证；按真实数据类字段root、panel_path、panel_manifest、model_path、model_manifest、name_dictionary_path作可序列化身份投影，不另写假validator，不从原字节推断正式准入。

## snapshot依赖：精确既有来源，不新增整模块复制
原`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`文件已实际读取并核与原M02补包同字节：
- [manager_plan.py `_snapshot` L234–251](https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/src/v5_shadow/manager_plan.py#L234-L251)：整文件39957B，SHA256`fa6cbee7196d40acb96dc78693925561dbc4eba7c09313157af0f7a2f6dcca7b`，Git blob`5e05f82ec6d2d88f47e79d19e5caf433a0143f2c`。
- [announcement_bridge.py `_input_limit` L32–33](https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/src/v5_shadow/announcement_bridge.py#L32-L33)：SHA256`1fd9b3f03fb471c04e0750c1fa2a674dc87a1fb9a242c7f2657345f7931643b5`，Git blob`244260d7a10ca189a6132fda75ee641745bb8d72`。
本次只给固定原件定位和合同，不把它们的正文/函数片段加进M02材料。

`_snapshot(binding)`依赖os/hashlib、a_preselection._relative、composition.no_symlinks、module_api._open_directory/_read_regular及_input_limit。前四个原helper在本次source内。它返回同一relative→原始bytes映射；保留绝对root约束、禁止父级/绝对relative/路径逃逸与symlink、逐目录FD O_DIRECTORY/O_NOFOLLOW、文件O_RDONLY/O_NOFOLLOW/O_NONBLOCK、regular类型、单件限额、读前后inode/device/size/mtime_ns/ctime_ns稳定及实际长度、累计≤64MiB和每件声明SHA相等。单件默认16MiB，仅精确匹配`announcement_agent_runs/<32小写hex>/evidence/body_corpus.json`的原例外为32MiB。不能只保留总大小或hash而丢掉其余边界。

提出并实现范围清楚的M02独立只读snapshot接口，提交原接口到新接口的来源映射/精确差异和等价负测；如涉及共享接口修改则另列INTEGRATION_REQUEST，由统一集成处理。不导入整套经理/公告业务，不复制M18源码，不手写一个宽松“验证成功”替代原语义。原reader对binding的前后稳定性与身份校验不得削弱。

## 完整绑定与独立读回
- 只修M02封装/接线/提交/读回和本模块测试，原owner/readers核心保持；不新增采集、策略、交易或资格批准。
- 按真实三源成功合同报告各自结果/异常，完整保存固定输入SHA、owner/run、日期、cutoff及实际来源时间。created_at不等于历史可得性，缺时点证据拒绝对应用途。
- 实现可信私有root、输入输出隔离、安全路径、原子不可变binding+receipt、同输入幂等、失败保旧成功；不倒填日期或把资格字段强行True。
- 独立从磁盘binding/receipt核身份，再读取全部三源并对比保存的输入/结果。换root/files、篡改、错误日期、after-cutoff必须拒绝。
- 补正常三源→提交→独立读回和缺结构、异常、篡改、日期/cutoff、symlink/重叠、幂等、失败保旧成功负测。mock单测、原reader fixture、真实输入/自然运行分别记录，不混写通过。

## 交付
提交完整before/after与测试源码、逐文件SHA256/Git blob/原来源、仓库相对路径真实正向与反向patch（含新增源码和测试）、精确集成与Mac隔离验收说明。未执行项NOT_RUN；不能以缺Mac实时数据为缺源码/补丁的理由。原source、被退R3不覆盖；新候选固定commit交独审和Mac验收，材料提交不等于代码完成/部署。
