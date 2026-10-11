# M16 默认装配原源码补件

这三份文件是固定原源码参考，不是可运行依赖闭包。源仓库 lexi2016/v4，固定 commit f7cb731c384ee6890a87d16c19a5b5a621779477；原路径、Git blob、SHA256、字节数见 SOURCE_MANIFEST.json。原文件保持完整原字节，本次不改产品实现或现有测试反馈。

## 阅读位置

- apps/api/v35_api/app.py：3848–3889 行私有 manager package alias loader；5523–5537 行真实 observation reader；5551–5583 行 material/provider/service 装配；4299–4452 行 projection 与 4191–4208 行 reducer。原源内的路径/环境变量名仅为装配历史参考，不提供实际 runtime 配置。
- stage_center/consumer.py：原 StageSelectionConsumer 构造为 (root, *, a_name_pool_root=None, runner_receipt_root=None)；get(date, stage, *, markets=None, allow_backfill=False)。它是已落盘 selection 的只读消费边界。
- stage_center/selection.py：SelectionStore.read_verified 的 latest/manifest/receipt/artifact 身份验证路径。

## 本轮返修目的

结合既有 M16 源树和独立 review，核真实默认装配所需的私有 runtime、真实 service/provider/material store 与 observation reader，给后续修复准确的调用签名和依赖依据。不能以 fake reader/空 lambda/动态补造依赖来宣称默认闭环通过。具体修复任务以父任务将提供的完整 review 为准，本补件不会自动触发新一轮 Chat。

不要导入整份 app 启动其他模块；不要复制默认 V4 写根或部署/执行这三份源码。M16 使用其私有 runtime 与显式隔离根，不能改 V4、main 或其他模块。

## 已确认缺件

consumer 顶层还依赖 preselection_pool_store、stage_center.contracts 和 selection；selection 依赖 calendar/contracts/_selection_parts.schema_values。固定源中的 schema_values、store_verification、artifact_codec、primitives_io 均引用 ._namespace.read_global，但 canonical/stage_center/_selection_parts/_namespace.py 实际 GitHub 读取返回 404 NOT_FOUND。原 stage_center/__init__.py 还会引入 acquisition/candidate_input/raw_store。

本目录不包含、也不伪造 _namespace.py。三件参考源码不能当作可运行闭包；缺件需要原 owner 提供可核实来源，不能凭想象补成“通过”。这次未运行产品测试、未调用外网 provider、未部署。

