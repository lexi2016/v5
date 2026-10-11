# M01实际源码审阅补包：A行情与原公式

固定f7cb731c384ee6890a87d16c19a5b5a621779477，lexi2016/v4。共63份GitHub原件，包含A同步、input manifest、formula increment、共享panel入口、相关parts/原公式authority、直接IO/锁/日历/存储依赖、5份原定向测试和V5现有快照身份工具。每件Git blob、SHA256、bytes见SOURCE_MANIFEST.json，均按connector原字节核验；只进行静态解析和ZIP哈希/CRC，不执行产品或测试。

## 最小目标
V5/src/v5_shadow/a_source_daily.py在固定树尚不存在，不能提供捏造的“现有文件”。Chat应复用包内原owner和现有工具，提出最小私有A源→原公式generation→M05/M09来源binding候选。原parts/authority是donor，不许直接改现役V4；共享panel含HK分支只为保持原文件完整，不允许M01修改HK逻辑。

## 关键阅读顺序
1. handoff/v4-running-source-20261005/canonical/ops/a_share_daily_sync.py与_a_share_daily_sync_parts
2. a_formula_input_manifest.py、a_formula_increment.py及各自parts
3. macos_research_panel_daily.py与a_formula_execution、a_market_capture、formula_pointer、bounded_execution等parts
4. infrastructure/formula_generation.py和upstreams/v3_shared_data/shared_data/a_formula_authority.py
5. 原tests/test_a_share_daily_sync.py、test_a_formula_input_manifest.py、test_a_formula_increment_offline.py、test_a_formula_authority.py、test_macos_research_panel_daily_ensure.py
6. V5/src/v5_shadow/input_snapshot.py及其共用边界；TASK_DOCUMENTS四份任务书

## 已知准确的静态来源缺口
固定GitHub树中四个A/panel parts目录的_namespace.py不存在：ops/_a_share_daily_sync_parts、_a_formula_input_manifest_parts、_a_formula_increment_parts、_macos_research_panel_daily_parts。现存parts确实有相对import；DEPENDENCY_GAPS_STATIC.json列每个引用。该事实不能推断Mac现役必缺。不能据此宣称本ZIP可独立运行全部原测试。

为便于理解旧parts转发方式，另附V5/vendor/a_preselection_baseline/domains/_preselection_materializer_parts/_namespace.py真实通用donor字节。它没有安装到上述缺失路径，没有冒称是四个原入口的现役前像。Chat若需采用该复用方式，须在候选中明确来源映射/新增路径/闭包身份；嘻嘻实际安装前优先核现役完整owner与已授权来源。

STATIC_IMPORT_INDEX.json只是语法级from-import索引，不是运行时依赖证明。外部numpy/pandas/pyarrow/pytdx和原Windows/Mac authority实际绑定、公式种子/CSV合同、现役源/输出root需要Mac现有环境核实。此包没有Mac行情原件、种子、凭据或新SDK安装。

## 分工与边界
Chat给静态最小候选、前后SHA、patch、定向用例；嘻嘻Mac落地与独立验收。缺当前active前像不阻挡写候选，缺原代码时只列上面的精确项，不再索要整库。共享UI/gateway/调度/contract注册只提变更请求；保留V4与8910，不交易、不扩凭据/权限。全部实际测试与自然生产仍NOT_RUN。
