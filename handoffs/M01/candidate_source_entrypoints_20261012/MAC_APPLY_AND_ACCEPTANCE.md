# M01 隔离应用、验收与回滚

本目录是候选，不自动安装或部署。先固定本次 GitHub commit，再使用既有 Mac 任务和既有依赖；不需要新建外部 Chat、安装软件或扩展权限。

## 首先验证

核仓库/分支/固定 commit 与 BEFORE_AFTER_SHA256.json；原 source、reference_r15、candidate_r17_rejected、reviews、historical_r6_mac 原件保持。候选只拥有 V5/src/v5_shadow/a_source_daily.py 和 V5/tests/test_a_source_daily.py 两条 donor 命名空间路径。实际活动 checkout/root 由现场核实，不能把历史 canonical 当活动树。

## 独立全套 fixture 测试

从固定候选 checkout 根，使用现有 Python（已由父任务独立确认含 pandas/pyarrow），执行：

    "$PYTHON" handoffs/M01/candidate_source_entrypoints_20261012/run_tests.py --source handoffs/M01/source --require-parquet

无真实行情网络、凭据、交易调用。runner 仅在当前测试进程把固定 source 的 V5/src 和 canonical 原依赖加入 imports；没有改系统 PYTHONPATH 或共享源码。所有 44 项都必须执行，8 项不能再跳过。保存完整命令、解释器身份、stdout/stderr、exit、通过/失败/skip 数与 candidate SHA。

## patch 验证

runtime.patch 的前像是 reference_r15，不是 R17，也不是未经核对的 Mac active。先把 reference_r15 的两个完整文件复制到新隔离目录，逐文件核 before SHA，执行：

    git apply --check /absolute/path/to/runtime.patch
    git apply /absolute/path/to/runtime.patch

核 after SHA 并运行测试。回滚在同一隔离副本执行：

    git apply --check /absolute/path/to/reverse.patch
    git apply /absolute/path/to/reverse.patch

核 before SHA 恢复。若活动前像不同，停止活动安装并报告差异，不 force、不整包覆盖。完整 before 和 after 已随候选保存。

## 接入前检查

唯一整合者确认原 SafeRoot/formula_generation 和 V5 composition 的实际 import 绑定，保持原 source root、private marker、权限与 owner。默认调用：

    create_binding_from_roots(private_root=..., source_root=..., generation_pointer=..., target_date='YYYYMMDD')
    read_binding_from_roots(private_root=..., source_root=..., relative=binding_relative(binding))

输出仍 schema v5.m01.a_source_binding.r15；cutoff_status=UNVERIFIED。不能升为交易许可或完整日历/cutoff就绪。异常保留准确原因；来源失效不覆盖旧 binding。生成后读回拒绝漂移时，未覆盖既有成功，候选新文件可能保留供核查，调用仍失败，不应展示成功。

真实 owner/来源与 M05/M09 消费、API/原页面、自然运行和发布窗口均由父任务/唯一整合者后续独立验收。本候选不更改 V4、main、任何现役根或端口。
