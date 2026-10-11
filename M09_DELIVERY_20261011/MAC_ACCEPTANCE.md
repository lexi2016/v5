# M09 Mac 独立验收与单模块回滚执行手册

**文档状态：候选配套验收手册；Mac 执行状态 NOT_RUN。所有本候选的 Mac 执行、活动 API、原页面、自然调度、现场回滚均为 `NOT_RUN`。** 本文给出现有 Mac 执行者可独立运行的步骤和应交回证据；命令、示例回执字段和预期结果都不是执行记录。独立审查的提交见证、保存输入验读、已加载代码身份和 API 原字节摘要链问题，已在当前冻结云端候选以六个独立测试确认修复；这不代替 Mac 验收。执行前须采用交付者固定后的完整候选及其最终 SHA。

依据：本轮 `FINAL_SUPPLEMENT_R3.md`、`TASK_M09.md`、`DELIVERY_CONTRACT.md`、`RUNTIME_INPUT_ADDENDUM_R2.md`；原件 `panel_evidence.json`、`timing_and_authority.json`、`versions.json`、`actual_api_binding.json`、`runtime_bindings.json`；接口草案 `M09-IR-001-READ_COMPOSITION.md`、`M09-IR-002-REVIEW_UI.md`、`M09-IR-003-PUBLICATION_AND_DISPATCH.md`。原取件单中的“不运行产品”限制适用于那次只读取件；本草案描述的是后续已批准的隔离候选验证，不授权写入现役 V4。

本手册对应本交付 `SOURCE_IDENTITY.json` 的最终源码；实际 GitHub 完整提交见离线包外层 `EXPORT_VERIFICATION.json`。下面 `/absolute/verified/delivery` 指离线 `repository/M09_DELIVERY_20261011` 或 Git checkout 中同名目录。`original/` 已完整包含；runtime 原 ZIP 在仓库 `handoff/m09-20261011/`，先按 README 解压并核原件。helper 和独立测试保留了 `evidence/...` 原路径，同时在 `tools/`、`tests/` 提供完全相同的便捷副本。

## 1. 固定对象和范围

| 身份 | 已知值及含义 |
| --- | --- |
| 原 donor | `lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`；原字节不改 |
| 当前报告的 V5 handoff | `lexi2016/v5@782bfc9ae91ff9cfe897afffc52aad43b7c1b78c`；与最终实现 commit 区分，不能拿来冒充 Mac 活动源码 commit |
| 本地重建 52 文件基线 | `e45aee9e185dda6f9d4b5032e6d60231cce27809`；这是材料重建提交，不是完整 donor 仓库 |
| 候选布局 | `after/V5/...`；不删除一级 V5，不往 V4 checkout、旧 vendor 或旧 manifest 写回 |
| 本候选最终身份 | 由最终交付的 `CHANGED_FILES.json`、代码/包 SHA、完整候选 commit 填回；本文不预填进行中的代码 SHA |
| 普通读面 | 已核附件为 `GET /api/v3/review?date=T`，App.vue → ReviewView → `market_reviews.A` → AshareReviewPanel；活动接线由共享 owner 负责 |
| 唯一两个槽 | 上海时区 `16:05`、`17:10`；旧 close_chain 显示节点和 M12 晚间节点都不是新增触发授权 |

只在一个新的候选材料目录和新的、显式选择的 M09 私有验收目录工作。复用现有核准解释器，读取原材料，允许候选向自己的测试根写入完整 run、attempt、generation。禁止把 API 全局 `store.root` 指到 M09/V3.5 来“修好”读面；禁止运行 M12 采集来补证；不创建额外服务器、页面、调度或第三槽。

## 2. 路径及现有环境核对

下列变量必须赋为执行者已经核实的绝对路径。`M09_SESSION` 是新的空验收目录，不能放在原件、`after`、任何现役 V4/V3.5 根内部，也不能用 symlink 指向这些位置。变量名是工作变量，不是已建立的发布配置。

```bash
export M09_PYTHON='/Users/lexi/Library/Application Support/com.lexi.v4.local/runtime/venvs/v3.5-mac/bin/python'
export M09_AFTER='/absolute/verified/delivery/after'
export M09_BEFORE='/absolute/verified/delivery/before'
export M09_ORIGINAL='/absolute/verified/delivery/original'
export M09_RUNTIME_INPUTS='/absolute/verified/material/runtime_inputs/M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011'
export M09_DONOR="$M09_BEFORE/handoff/v4-running-source-20261005/canonical"
export M09_MAC_DRAFT='/absolute/verified/delivery/evidence/mac_draft'
export M09_REVIEW_TESTS='/absolute/verified/delivery/evidence/independent_review'
export M09_LOGGER='/absolute/verified/delivery/evidence/run_logged.py'
export M09_SESSION='/absolute/new/m09-independent-mac-acceptance'
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
```

先核这些位置存在、父目录无符号链接、解释器是已有原核准环境，并用 Python 的 `Path.mkdir(mode=0o700)` 创建尚不存在的 `M09_SESSION`，不要用 `mkdir -p` 合并旧验收结果。每次重做使用新的 session 名，保留旧日志。

```bash
"$M09_PYTHON" -I -B - <<'PY'
from pathlib import Path
import hashlib, importlib.metadata, json, os, platform, sys
root = Path(os.environ['M09_SESSION'])
assert root.is_absolute() and root != Path('/') and '..' not in root.parts
for p in (root, *root.parents):
    assert not p.is_symlink(), str(p)
for key in ('M09_AFTER', 'M09_BEFORE', 'M09_ORIGINAL', 'M09_RUNTIME_INPUTS'):
    p = Path(os.environ[key])
    assert p.is_dir() and not root.is_relative_to(p) and not p.is_relative_to(root)
assert all(p not in ('com.lexi.v4.local', 'com.lexi.v35.local') for p in root.parts)
root.mkdir(mode=0o700)
versions = {}
for name in ('pandas','pyarrow','numpy','pytest','python-dateutil','pytz','tzdata','six'):
    try: versions[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: versions[name] = None
declaration = Path(os.environ['M09_AFTER']) / 'V5/pyproject.toml'
paths = {key:os.environ[key] for key in ('M09_AFTER','M09_BEFORE','M09_ORIGINAL',
         'M09_RUNTIME_INPUTS','M09_DONOR','M09_MAC_DRAFT','M09_REVIEW_TESTS','M09_LOGGER','M09_SESSION')}
out = dict(python=sys.version, executable=sys.executable, platform=platform.platform(), paths=paths,
           packages=versions, pyproject_sha256=hashlib.sha256(declaration.read_bytes()).hexdigest(),
           dependency_changes=False, mac_acceptance='NOT_RUN')
(root / 'environment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
PY
```

附件环境是 Python **3.14.6**、pandas **3.0.5**、pyarrow **25.0.1**、pytest **9.1.1**。固定 `V5/pyproject.toml` 仍声明 Python `>=3.14`、pandas `>=2.3,<3`、pyarrow `>=21,<25`，原字节 SHA 为 `0a1824d3b255ee7f8391919254b2c21bf0deaf6da11a1b8cfc3e3a58c6fd4584`。Python 满足下界，pandas 和 pyarrow 超出声明范围。两份随附件复制的 `uv.lock` 原字节 SHA 均为 `53e998f444eaa6d0e926fda277183b7086c4e53ce5fddb49ce663a2e6d66d91c`。

在这个未改环境上跑出的结果，只证明该实际环境中的工程/诊断行为；不能记为声明依赖范围兼容通过。若存在另一套已批准、已安装的兼容环境，独立记录路径和版本再执行；不要安装、升级、降级、改锁文件或放宽依赖范围。若解释器已不存在，记录精确缺失并只阻断该运行步骤。

## 3. 应用前像、源码身份与补丁往返

先核离线包的最终 SHA、字节、CRC、成员清单和 SHA 清单；原三份 ZIP 及其 manifest 保持原字节。核 `CHANGED_FILES.json` 每个路径的动作、前像/新增不存在证据、候选 SHA，并将未在清单内的差异视为阻断。新 M09 capsule 应为 16 个精确 donor 文件及独立 manifest；旧三文件 replay capsule 和现有 `a_close_review.py` 的 replay 拒绝边界不能被放宽。

以下命令核完整 52 份 donor 材料映射，输出仅是原字节验证：

```bash
"$M09_PYTHON" -I -B - <<'PY'
from pathlib import Path
import hashlib, json, os
original = Path(os.environ['M09_ORIGINAL'])
before = Path(os.environ['M09_BEFORE'])
manifest = json.loads((original/'SOURCE_MANIFEST.json').read_bytes())
assert manifest['baseline_commit']=='f7cb731c384ee6890a87d16c19a5b5a621779477'
assert len(manifest['files'])==52
for item in manifest['files']:
    a=(original/item['archive_path']).read_bytes()
    b=(before/item['path']).read_bytes()
    assert a==b and len(b)==item['bytes'],item['path']
    assert hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==item['blob_sha'],item['path']
print('ORIGINAL_BYTES_VERIFIED: 52 files; product execution is not proved')
PY
```

再以 `PYTHONPATH="$M09_AFTER/V5/src"` 调用 `v5_shadow.a_close_daily_sources.sources_identity()`，保存全部 manifest、donor 路径/blob/raw SHA、loader 和依赖版本；与最终 `SOURCE_DEPENDENCIES.json` 对照。这是静态身份与可导入验证，不是 producer/parquet/Mac 成功证明。源/依赖在运行前后应重新核对；发生已加载源码变化时要求新进程，不能让旧代码记录新磁盘文件 SHA。

补丁只应用于**独立复制**的 `before`，不在活动 checkout 或实际 `after` 上试反向补丁。保存真实完整日志：`git apply --check forward.patch` → apply → 逐文件/全树对照最终 after → `git apply --check reverse.patch` → apply → 逐字节恢复 before。保持仓库相对 `V5/...` 路径，不猜 `-p` 参数，不隐式重定位。候选新文件也必须包含在往返比对中。发生前像冲突先定位最小差异，不能强制覆盖现有改动。

## 4. 真实完整命令和日志规则

各运行步骤使用交付的 `run_logged.py`，保存 command、cwd、开始/结束 UTC 与上海时间、exit、完整 stdout/stderr 及 SHA。环境快照、最终源码 SHA 和日志放在同一 session。不要只保留终端尾部或 PASS 摘要；失败 trace 原样保留。`FAILED / BLOCKED / NOT_RUN / SKIPPED` 都不计 PASS。每个测试套件的实际数量以本次固定候选日志为准，本文不硬编码开发中的测试数量。

若执行者把独立测试移到最终交付的 `tests/`，保留源代码原字节并更新路径映射；下面命令的 `M09_REVIEW_TESTS` 必须指到包含四个独立测试文件的实际目录。四个文件共六个测试，其中输入快照测试含四种独立破坏子用例。

## 5. 工程层：定向 unittest、原算法对照、故障与回滚

使用标准库 unittest，不启动 pytest 安装，不通过包安装导入候选：

```bash
PYTHONPATH="$M09_AFTER/V5/src:$M09_AFTER/V5/tests" \
M09_ORIGINAL_SOURCE_ROOT="$M09_DONOR" \
"$M09_PYTHON" -B "$M09_LOGGER" \
  --name mac_m09_unittest --cwd "$M09_AFTER" --out "$M09_SESSION/logs" -- \
  "$M09_PYTHON" -B -m unittest -v \
  test_a_close_review test_a_close_daily_sources test_a_close_daily test_a_close_daily_api test_daily_close_plan
```

这覆盖准入、原完整 product/store/reader、两槽身份、并发、后槽失败、timeout、CAS、private-root/symlink、原生 schema/安全边界和 API 的 A-only 组合。原算法对照 fixture 必须标 SYNTHETIC；全部 review/publication/independent-reader 字段与数组顺序精确比较，不删除拒绝码或“归一化”掉安全差异。当前原算法对照测试用 admitted-frame I/O，**即使 Mac 安装 pyarrow，也不能用它证明真实 parquet 解码等价**；本步骤与第 6 节真实 decode 分开。

对独立审查留下的故障执行原样回归：

```bash
M09_REVIEW_SNAPSHOT="$M09_AFTER" PYTHONPATH="$M09_REVIEW_TESTS" \
"$M09_PYTHON" -B "$M09_LOGGER" \
  --name mac_independent_integrity --cwd "$M09_AFTER" --out "$M09_SESSION/logs" -- \
  "$M09_PYTHON" -B -m unittest -v \
    test_review_findings test_api_raw_digest \
    test_preimported_helper_identity test_restored_helper_identity
```

通过条件包括：

| 故障 | 必须观察的结果 |
| --- | --- |
| 硬退出恰在 head rename 后、成功回执前 | 真实子进程结束；独立读仍服务已核前代或明确无结果；未提交代不能被报告 VERIFIED |
| 同一中断 attempt 重试 | UNKNOWN 与恢复回执有据；新 attempt 才能再次执行；不能把未知当自然成功 |
| calculation / 保存 panel / 成员快照被破坏 | 直接读、复用、发布和回滚拒绝坏输入证据；不继续给该坏代 VERIFIED |
| 长驻进程加载后源码被替换 | 明确拒绝并要求重启；禁止执行旧代码而记录新 SHA |
| raw review identity 被伪改但仍是合法 hex | API 拒绝跨层摘要错配 |
| worker 外部 product root | worker 拒绝不属于初始化 M09 私有 run 的任意路径 |
| payload/receipt/manifest 半写、receipt 例外、timeout、CAS | 真实错误独立保存，前槽已核成功仍可服务；没有自动重跑 M12 |

当前提交见证由 generation 绑定创建 trigger/request、匹配不可变成功回执，再允许公开读取。公开 GET 在不完整 head 期间可只读返回同日经核前代并带 `publication_recovery` 说明；真正恢复写入只在下一次持日期锁的执行路径发生。内部 precommit 验读 helper 的最终名称以固定候选为准，**不让 API/UI 调用私有 precommit helper**。同样，`latest_attempt` 是独立观察，不属于被服务 record/generation 的计算摘要。已加载代码检查还必须拒绝两种 helper 缓存情形：旧 helper 已导入后磁盘改变；改变过的 helper 已导入后磁盘又恢复原 F 字节。第二种情形由最后一个独立测试明确检查 executing code-object 分支。

附带持久化工程演示脚本可让执行者直接检查私有目录中的两代完整结果和回滚回执：

```bash
"$M09_PYTHON" -B "$M09_LOGGER" \
  --name mac_generation_walkthrough --cwd "$M09_AFTER" --out "$M09_SESSION/logs" -- \
  "$M09_PYTHON" -B "$M09_MAC_DRAFT/mac_generation_walkthrough.py" \
    --after "$M09_AFTER" --out "$M09_SESSION/engineering_walkthrough"
```

脚本只创建 SYNTHETIC 数据：16:05 成功 → 17:10 复用、两份回执 → 配置变化产生新 run → CAS 失败保旧 → 负 amount 拒绝保旧 → pinned 读前代 → 只回滚 M09 head → 重复读与 HK sentinel 不变。所有 runs 保留，前后全文件 SHA 对照。这个 HK sentinel 是纯函数隔离验证，**不是活动 HK API 验收**。脚本不包含伪造自然触发。

## 6. 真实历史输入：保留原字节，真实解码，要求拒绝

真实 T 固定为 `20261009`，只作 `RECORDED_INPUT_REPLAY` 历史诊断。不能改成某个未来 T 或把今天运行时间当来源时间。

| 原件 | 字节 / 原字节 SHA-256 | 含义 |
| --- | --- | --- |
| 8 列投影 parquet | 279209 / `7dfa12fa03ad76d5e946088f88993748a3fffd8943281a12eb364c35712f8c47` | 5126 条原 T 行和原 Arrow 类型；未清洗 |
| 成员文本 | 51260 / `b1f561b1d18a5341784c4906b0e3bbbf21d7d092823e4a60c2787fdf004d91fb` | 原源 T 切片全部声明成员；不证明全市场 |
| 原源 receipt | 80017050 / `de652e8ddc540433bef8d0dd9f13da54eb973cf520156109d9e61794dace2a6e` | PARTIAL、REBUILD_REQUIRED、coverage 0.8858620689655172；不能包装成 READY |
| 三份原 pointer | 每份 242 / `91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d` | 原 Mac 绝对路径证据；保留原字节，不修改 |
| 原完整 panel（未随包） | 1383142544 / `25aaa10f2080a72f0f9266a9456a3c3968dd1370068f31b0fb9106ea34434485` | 与投影是两个不同对象，不要求 SHA 相同 |

已有原取件统计：2 行 `bar_close_pos` 缺失；137 行 `name` 为空字符串；240 行行业 code/name 为空字符串。源 receipt 的 accepted_count=5138、target_count=5800 与 panel 5126 是不同计数，不制造 12 行差异的解释。sync 记录时间范围是 17:01:05.003487+08:00—17:09:06.622525+08:00；formula 17:09:17—17:11:27 无时区后缀；最终 panel 的 available_at 仍未知。不能从 formula、mtime、pointer 创建时间或 `as_of=15:30` 推出任一槽可用或严格 15:00 PIT。

```bash
"$M09_PYTHON" -B "$M09_LOGGER" \
  --name mac_real_uncleaned_diagnostic --cwd "$M09_AFTER" --out "$M09_SESSION/logs" -- \
  "$M09_PYTHON" -B "$M09_MAC_DRAFT/mac_real_input_check.py" \
    --after "$M09_AFTER" --runtime-inputs "$M09_RUNTIME_INPUTS" \
    --out "$M09_SESSION/real_uncleaned_diagnostic"
```

脚本验证 R2 runtime manifest 的 40 项原字节，复制六份必要原件到新目录，另建 `candidate_panel_pointer.txt` 指向复制的投影。三份原 pointer 不变；新 pointer 的创建时间只表示本地映射时间。它使用**实际安装的 pyarrow**解码真实投影，核 8 列、行数/成员/缺值统计；没有 fill/drop/dedup/数字字符串转换或生成行情。

随后以精确历史 T 分别诊断 16:05、17:10，要求两者 `admitted=false`。原件未证明的来源 ID/version、最终 captured/acquired/available、成员来源时间保留 null；可报告的状态/权威/coverage 取已有证据。原源 receipt 超过当前 16 MiB JSON 准入上限，预计附加 `SOURCE_RECEIPT_NOT_BOUND / OWNED_FILE_TOO_LARGE`。这是应交回的真实限制，不能缩写成一个冒充原 receipt 的 READY JSON，也不应为该坏输入直接提高边界。

通过本步骤意味着**真实解码与预期拒绝被观察到**，并不是“真实价格链成功”。`SOURCE_AUTHORITY_NOT_READY`、未知来源时点、`PANEL_NUMBER_INVALID`、`PANEL_TEXT_MISSING` 等应可见。脚本在另一个新 M09 私有根保存两份 `RECORDED_INPUT_REPLAY` 失败 attempt，验证没有可服务 generation；原材料和复制原件前后 SHA 不变。若解析失败或统计不符，保留 traceback 和实际环境，记为 FAILED/BLOCKED，不再把该步骤称解码通过。

### 可选原算法未清洗诊断

如需观察原算法对真实坏值的实际行为，在**单独进程**用已核 `M09_DONOR` 的原 `ops.build_a_share_close_review` 和真实 pyarrow 调用。只使用新建 local pointer；`--data-root` 必须是 `M09_SESSION` 下另一个未使用目录，run_id 明确含 `RECORDED_INPUT_REPLAY`。完整命令形态：

```bash
PYTHONPATH="$M09_DONOR" \
"$M09_PYTHON" -B "$M09_LOGGER" \
  --name mac_original_uncleaned_probe --cwd "$M09_SESSION" --out "$M09_SESSION/logs" -- \
  "$M09_PYTHON" -B -m ops.build_a_share_close_review \
    --data-root "$M09_SESSION/original_uncleaned_probe_store" \
    --date 20261009 \
    --panel-pointer "$M09_SESSION/real_uncleaned_diagnostic/relocated_source/candidate_panel_pointer.txt" \
    --run-id RECORDED_INPUT_REPLAY_MAC_DIAGNOSTIC_20261009
```

执行前在该同等隔离导入环境中核 `ops/domains/contracts/infrastructure` 所加载模块 `__file__` 均来自 donor，且字节与 manifest 一致，避免混入安装的同名应用包；不能在已经导入 candidate 裸同名包的进程中混跑。原函数若抛出异常，原样保留全部 trace；不修模型绕开。原函数若返回，保存完整 review/model/chain/publication，用新建原 `AShareReviewStore(...).read_review(T)` 独立读回再记录字段；不得发布为 daily 成功或把模型的静默过滤输出当全声明输入的准入成功。本次草案对此仍为 `NOT_RUN`。

## 7. 普通 API 与原页：共享 owner 接好后才执行

活动附件 URL 为 `http://127.0.0.1:8873/api/v3/review?date=20261009`、release 为 `hk-dated-name-20261011-r2`、取件时 PID 为 55132。URL、release、PID 都必须现场重核，不能用旧 PID 当本次证明。已知 API root 是 `com.lexi.v4.local/state/data`，旧 producer root 是 `com.lexi.v35.local/state/data`；这个差异不能通过写 V4 或更改全局根来掩盖。

只有共享 owner 返回固定集成 commit、函数级 diff、实际 V5 M09 private binding、原 shared 文件前像 SHA 和回滚方式之后，才验收相应接线。不能把“源码子组件已附齐”当浏览器已经运行。调用的是现有 ordinary GET 与原 ReviewView，HTTP 不能提供 arbitrary root/path/code。

先保存明确路径的 V4 source/pointer/store/receipt/manifest 的存在性、bytes、raw SHA，以及服务配置的去秘密摘要和活动服务状态。只点查已批准列表，不导出全部进程环境或扩大权限；记录缺失文件，不创建它们。保存当前 HK、research、其他模块绑定的 canonical subtree SHA。

在隔离或固定发布窗口中，请求精确 T：

```bash
curl --fail-with-body --silent --show-error \
  --dump-header "$M09_SESSION/api_T.headers.txt" \
  --output "$M09_SESSION/api_T.body.json" \
  "${M09_CONFIRMED_API_BASE}/api/v3/review?date=${M09_ACCEPTANCE_T}"
```

`M09_CONFIRMED_API_BASE` 和 `M09_ACCEPTANCE_T` 来自现场绑定及已提交结果，不能预填一个未来日。若现有 curl 不支持该选项，记录工具版本并由 owner 用既有等价 GET 客户端保存状态码、headers、原 response bytes；不安装工具。预期 GET 验证：

1. 请求 T = `market_reviews.A.trade_date` = `market_reviews.A.model_review.review_date` = record/generation 日 = `market_reviews.A.m09_publication.trade_date`；`market_reviews.A.model_review.run_id` 与被服务 generation 的 run 一致。`next_day_trigger_tree` 是原产品字段，不能改变复盘日。
2. 固定一次被服务 generation，分别核 source SHA、canonical native-review SHA、raw store-review SHA、record SHA、generation SHA、API response raw SHA。各 SHA 含义不同，不要求字符串全相等；加了 API metadata 的 A 对象不能直接当原 canonical review 重算。
3. 原涨跌平守恒、行业/角色顺序/分数/理由、原情景概率 0.12/0.28/0.60、触发/失效条件、WATCH_ONLY、`core_stocks=[]`、LLM 禁用、`CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED`、研究/学习/泛化和严格 PIT 缺口保留。视频链 READY 也不能改“模型未消费视频”。
4. 价格成功与整体 PARTIAL、latest_attempt FAILED/UNKNOWN、未提交 head 恢复状态分别显示；晚槽失败不覆盖前槽成功的 run、computed_at 或 digest。
5. 目标日无结果是精确日 MISSING/CANNOT_CONFIRM，无旧根、另一日或 latest 成功补位。重复 GET、刷新、返回、切日、重复点击不计算/采集、不 POST、不新增 run/attempt、不改变 head。记录网络请求和私有输出前后 SHA；必要服务访问日志增长与产品状态文件变化分开。
6. A 发布/回滚前后 HK 与所有不属于 A 的字段不变。对 live 变化的 HK 若无法获得稳定同一快照，保留不确定性并另做冻结引用比较，不因正常市场变化强行宣布模块隔离通过。

在原 ReviewView 的 A 面板显式刷新，保存 URL/T、截图与网络 response 身份对应，核实际涨/跌/平、行业/角色、情景和证据缺口显示。保留 native model.status=`INDEPENDENT_CLOSE_REVIEW_READY`；不能借伪造 rich tier 隐藏原生字段。快速 T1→T2→返回、重复点击/刷新时旧响应不得覆盖新请求日。HK 原入口也要点查。浏览器验收是独立外部证据，不能写回冻结 chain 的 `UI_ACCEPTANCE_PENDING`。

## 8. 自动层：两个真实槽、睡眠/重启与跨日

先核实际 dispatcher checkout、owner、日历、时区、slot/job/attempt 身份和 M09 私有绑定；冻结 workload 定义只证明机会存在。共享 ledger 不能用 T 的 logical key 在 16:05 成功后吞掉 17:10 独立触发。

| 场景 | 自然/工程证据的要求 |
| --- | --- |
| 两槽输入/代码/配置完全相同 | 一次成功计算、两份真实触发回执；第二份明确复用，保持原 computed_at |
| 后槽有当时已可用的新材料 | `available_at <= cutoff`，同日新材料进入 identity，产生新 run；旧 run 完整保留 |
| 17:10 后到达视频 | 不准进入16:05/17:10旧 run，不设第三槽；缺口如实保留 |
| 来源时间未知/未来/异日 | 不制造来源时间；相应材料拒绝或 UNKNOWN，严格 PIT 仍 false |
| 后槽坏输入、超时、CAS、中断 | 前槽已核成功持续可读；失败/UNKNOWN attempt 单列 |
| Mac 睡眠/重启跨过窗口 | 记录实际唤醒/启动与错过窗口；不能回填 NATURAL，人工恢复用 MANUAL_RECOVERY 或历史 replay 实际分类 |
| 中断后重新执行 | 先核不完整提交见证和前代；带新 attempt 的恢复独立记账，不覆盖旧 UNKNOWN |
| 跨交易日 | 新日使用真实日历和新日真实来源；请求上一日只读上一日，不暗选未来日 |

真实自然检查只能等待接线后的实际适用交易日窗口；不要用手动调用、改系统时钟、指定过去 triggered_at、已有 `REPLAY_RESEARCH_V1_20261009_001` 或补写回执冒充自然证据。不为了验证睡眠/重启而未经授权终止活动 V4 或重启机器；先做隔离进程故障工程验证，真实恢复观察由现有 Mac owner 在获准窗口完成。

## 9. 现场独立回滚：先验读前代，再只切 M09

工程脚本的 rollback 已可检查 API 函数形态；现场步骤必须基于实际绑定及部署授权。不要在全局共享响应上撤回 HK，不能删 runs/objects/generations，也不以 reverse.patch 覆盖活动改动。

1. 保存当前 T 被服务 `generation_sha256` 为 expected new generation，并记录实际 binding/transport 身份和全部前像。明确哪个 head/binding 决定服务可见性；若还有 shared transport，不能把两个先后 rename 叫原子事务。
2. 从该代 predecessor 链选择有据的上一个 M09 generation，先调用 `read_a_close_daily(root,T,generation_sha256=old_sha)` 验完整输入、calculation、原 store、record、提交见证和安全边界。不能因为文件名像 SHA 或“以前成功过”就激活。
3. 调用唯一 M09 回滚入口，传真实 CAS expected。函数级形态如下，值从已捕获对象读取：

   ```python
   receipt = rollback_a_close_daily(
       approved_m09_root, T,
       target_generation_sha256=verified_old_sha,
       expected_generation_sha256=captured_new_sha,
       reason=recorded_actual_reason,
   )
   ```

4. 发生 CAS 冲突时停止本次切换，保留冲突证据并重新读当前状态；不能自动强制覆盖后来成功。若异常结果不确定，先只读核对实际 head 和 receipt，不能重复盲切。
5. pinned 及 ordinary GET 读回 T，核实际返回旧 model run/record/generation；原页显式刷新。保持新旧 runs、失败 attempts 和 rollback receipt 全部存在且原字节不变。回滚到前代不会让 latest_attempt 必须指向该旧 run。
6. 对照 HK/research/其他模块 canonical 子树、V4 指定文件的存在性/raw SHA/bytes、原服务状态和源码/配置前像。发现差异按实际范围报告，不扩成全局回滚或更改 V4。

从未有可服务成功时，不能凭空给 `rollback_a_close_daily` 一个目标；共享 owner 只能按已记录绑定撤回 M09 预览选择，使原绑定回到原状，且单独证明另一市场保留。

## 10. 五层结论模板和回传

| 验证层 | 本草案时实际状态 | 填为完成前必须具备 |
| --- | --- | --- |
| 1 工程 | Mac `NOT_RUN`；云端最终结论引用最终固定候选日志，不由本草案填 PASS | 前像/after/patch 往返、依赖身份、定向/必要回归、独立故障修复 GREEN、隔离回滚；超范围环境说明保留 |
| 2 真实数据 | 真实历史原件已附；本候选 Mac decode/诊断 `NOT_RUN`；已知准入缺值/权威/时间阻断 | 未清洗解码/拒绝日志可完成相应诊断；真实成功还需合格同日来源、完整成员和可靠时间，再走原算法→writer→独立 reader |
| 3 消费 | `NOT_RUN / SHARED_OWNER_BINDING_REQUIRED` | 固定活动普通 API/原 ReviewView 接线、精确 T/run/各类 SHA、无计算副作用、HK隔离和截图 |
| 4 自动 | `NOT_RUN` | 已有两槽真实自然触发、独立触发/计算身份、失败保旧、错过窗口和恢复的真实回执 |
| 5 完整 | `NOT_RUN / INCOMPLETE` | 前四层、本候选必要回归、单模块发布/回滚以及连续两个适用交易日的自然接续全部齐全 |

每项回传：`status`、实际 command/cwd、环境/代码/锁文件身份、UTC/上海起止、exit、stdout/stderr原件及 SHA、测试数及 skip 原因、输入/输出引用、日期与时间语义、下一步具体阻断。区分“预期拒绝测试通过”与“真实模型成功”；区分“原件统计复核”与“自然窗口/PIT证据”；区分“纯函数 HK sentinel 保留”与“活动另一市场未变”。不用倒要尚未生成的 review/store/API/UI 作为实现输入。

本草案及两个 helper 只是在独立验收目录准备的可审查材料。最终交付者将它们纳入包时应补齐正式相对路径映射、helper SHA、可复用的独立测试来源，以及实际完成的云端 helper 检查结果；所有没有发生的 Mac 事实继续保持 NOT_RUN。
