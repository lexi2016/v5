# M01：R15 完整核心上的默认来源入口修复

## 本轮结论

候选源码已完整实现。云端 44 项测试中 36 PASS，8 项原 reader 的真实 Parquet fixture 测试因现有 Python 缺 pyarrow 而明确 NOT_RUN/SKIP；没有安装或伪造替代 reader。Mac 工程验收尚未执行。本报告不是 M01 生产验收，不代表真实行情、公式业务、API/页面或自然运行通过。

固定父提交：a76c2746727883e44eff0d336c2f839d7c9f4081。
分支：dev/m01-github-handoff-20261011。仓库：lexi2016/v5。

## 实际修改

仅在 R15 完整 a_source_daily.py 上追加原依赖的内部导入，补齐创建/读取两个 roots 入口。调用者不再提供 SafeRoot、reader、composition 函数或 pointer 常量。

- 内部使用原 infrastructure.owned_io.SafeRoot、infrastructure.formula_generation.read_formula_generation / FORMULA_GENERATION_POINTER_NAME，以及原 v5_shadow.composition.no_symlinks / shadow_root。
- 双入口共用上下文和 bounded reader。校验原始 str/Path 类型、绝对路径、NUL、反斜线、..、source 已存在目录、marker 与双向 root 不重叠；目录追加 pointer 文件名后再次检查 symlink；返回 path 同样检查原始类型、词法、祖先和 source containment。
- 日期先于 roots 校验。拒绝在任何锁/写入之前发生。
- 12 个 R15 类/函数定义 AST 原样保留，包括 schema r15、严格 parser/重复键、generation_id、全部 SHA、精确 relative、完整投影、create/read/verify、窄 FileNotFoundError、锁内 require_absent、最终独立来源读回及本次 expected 比较。
- 无 owner、PIN、guard、共享 composition、V4、main、集成分支、UI/API 或服务端口修改。未执行真实网络采集、交易或使用交易凭据。

## 测试证据

1. 先将新测试运行于精确 R15 前像：44 项，7 failures、44 errors（包括多个 subtest，主要是缺默认入口的必填安全外参及返回 path 保护），8 skips，exit 1。见 evidence/RED_R15.log。
2. 修复后的完整候选 suite：44 项，36 PASS，8 SKIP，exit 0。见 evidence/GREEN_FINAL.log。覆盖双入口早期拒绝、bound reader、parser、日期/generation_id/SHA、精确 relative、读回漂移、锁内无覆盖、竞争文件保留、非缺失错误传播、原成功保留等。
3. 强制真实 reader/Parquet 模式：实际运行返回 ModuleNotFoundError: No module named 'pyarrow'，exit 1，见 evidence/REQUIRE_PARQUET.log。8 项源码均已写完，Mac 应使用现有 pyarrow 解释器运行，禁止把 SKIP 算 PASS。
4. 默认解释器 pytest 尝试实际返回 No module named pytest，exit 1；因此本候选无依赖 unittest runner 运行全部自身测试。原 SOURCE 是不完整 donor 测试闭包（已存 DEPENDENCY_GAPS_STATIC.json），没有把 donor 的全量测试声称通过。
5. 真实正反 patch 分别由精确 R15 前像和本候选后像生成，已执行 git apply --check、apply、after SHA、reverse check、reverse apply、before SHA。两份 patch 不同向、不从 /dev/null 冒充前像。见 evidence/PATCH_ROUNDTRIP.json。
6. 71 件 SOURCE 文件均与父提交的发布 manifest SHA256 相同；固定原件不被候选替换。见 evidence/SOURCE_IDENTITY_CHECK.json。
7. 独立短审未发现该 wrapper 增量的阻断问题；确认 12 个 R15 核心 AST 不变。见 evidence/INDEPENDENT_REVIEW.md。

## 测试边界

所有生成数据都明确为合成、离线测试数据。Parquet fixture 直接满足本包原 formula_generation.py 的既有严格 schema/manifest/receipt/selector/source/sidecar SHA 合同，调用默认入口且不注入替代 reader；只证明工程绑定行为，不证明原公式算法、单位、真实 universe/coverage 或生产来源采集正确。没有重写原 owner。

历史 R6 是另一候选；其两组成功和七项缺陷复现仍仅属 NOT_PRODUCTION_ACCEPTED 的历史记录，本轮没有引用作通过数。

## 后续五层状态

- 代码候选：完整交付；云边界/核心工程验证 36 PASS，8 项 Parquet 待 Mac。
- Mac 工程测试：本提交时 NOT_RUN；父任务将用已存在解释器隔离复跑。
- 真实源→公式→保存/独立读回：NOT_RUN，不由合成 fixture 替代。
- API/原页面：NOT_RUN，由唯一整合者接线。
- 自然接续、发布与回滚：NOT_RUN；本分支发布只保存候选工件。
