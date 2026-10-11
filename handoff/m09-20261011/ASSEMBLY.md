> R3本轮最终版：先读 FINAL_SUPPLEMENT_R3.md，再读R2现场说明。活动AshareReviewPanel最小直接依赖已补齐；正确transcript_stockdict/stock_mentions路径在两个已核root均缺失已证，不再待补。附三份原字节内ZIP；R2旧包另行保留，本轮只提交本R3。其他数据质量/PIT/环境兼容/GitHub待建限制不变。

> R2现场输入增补（2026-10-11）：先读 RUNTIME_INPUT_ADDENDUM_R2.md。本包已附T=20261009真实8列panel投影及Mac源码/运行绑定；旧文中“尚待取得”须以R2已取得清单更新。5126行原样保留但存在缺值、来源REBUILD_REQUIRED、完整available_at/PIT未知；只可作真实历史诊断/回放材料，不作16:05/17:10自然成功。Mac pandas3.0.5/pyarrow25.0.1超原声明范围，旧REPLAY不当新生产。新私有lexi2016/v5登录/固定身份仍待建立；本次可先提交完整自包含Chat材料，不冒称GitHub已提交，不改回v4。

# M09 离线解压与装配

这些是交接包操作/未来验证命令，不是本轮产品测试日志。只能在新的隔离材料目录执行，不能指向 V4 checkout、活动 data_root、既有候选目录或未核实的 Mac 路径。

## 1. 解压固定原件并按52文件manifest核字节

以下工作目录应先包含本次交接包和 `v5-module09-source-20261010.zip`。ZIP 的成员根就是 `source/`、`handoff/` 等，没有额外顶层目录。

```sh
# 在新、空、可写的材料目录中操作。INPUT_ZIP 取实际已落盘附件路径。
export INPUT_ZIP="$(pwd)/v5-module09-source-20261010.zip"
export M09_WORK="$(pwd)/m09-isolated-work"
python3 - <<'PY'
import hashlib, json, os, shutil, stat, zipfile
from pathlib import Path, PurePosixPath
z = Path(os.environ['INPUT_ZIP'])
w = Path(os.environ['M09_WORK'])
expected = 'ee45e1cb627df660d15574a5a0a023be00e7fac0a29e983109b202e7e3af25fa'
assert z.is_file() and z.stat().st_size == 145374
assert hashlib.sha256(z.read_bytes()).hexdigest() == expected
assert not w.exists(), 'Refuse to merge into an existing work directory'
w.mkdir()
o = w / 'original'
o.mkdir()
with zipfile.ZipFile(z) as archive:
    assert archive.testzip() is None
    names = set()
    for info in archive.infolist():
        p = PurePosixPath(info.filename)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
        assert info.filename not in names
        names.add(info.filename)
        assert not stat.S_ISLNK(info.external_attr >> 16)
    archive.extractall(o)
m = json.loads((o / 'SOURCE_MANIFEST.json').read_text())
assert m['baseline_commit'] == 'f7cb731c384ee6890a87d16c19a5b5a621779477'
assert len(m['files']) == 52
for item in m['files']:
    data = (o / item['archive_path']).read_bytes()
    assert len(data) == item['bytes'], item['path']
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
assert sum(i['bytes'] for i in m['files']) == 404637
shutil.copytree(o / 'source', w / 'after')
print('PASS: fixed source assembly only; product tests NOT_RUN')
print('Original:', o)
print('Candidate baseline:', w / 'after')
PY
```

`original/` 永远保留原字节。`after/` 是完整候选基树，在候选中修改模块白名单；初次装配后其内容仍只是baseline，不得以 after 目录名当实现证据。`after/handoff/.../canonical` 是原件副本，仍不可改、不可部署成现役V4。

原 manifest 的 `path` 相对原仓库根；`archive_path` 相对 original 解压根。这两者都不是 Mac 活动路径。包中全部52份源码及说明已离线附入，无须 Chat 先连私库才能读源。

## 2. 导入根和依赖

- V5 Python 包候选根为 `after/V5/src`；模块是 `v5_shadow`。它的冻结model capsule仍按 `after/V5/vendor/a_close_baseline` 和 `after/V5/contracts` 定位。
- 原 producer 源根为 `original/source/handoff/v4-running-source-20261005/canonical`。此根下 `ops`、`domains` 可作为 Python namespace packages；不要为了“修import”发明缺失初始化源码或串用活动全局同名包。
- 原 producer 12文件静态闭包、全部52文件SHA和import清单见 `DEPENDENCY_MANIFEST.json` / `ORIGINAL_SOURCE_MANIFEST.json`。新的冻结命名空间/loader若有需要，交新文件和新manifest候选，原manifest不改。
- Python >=3.14、pandas >=2.3,<3、pyarrow >=21,<25 是固定 pyproject 的声明，pytest无该文件版本钉死。采用现有Mac批准环境；取现有解释器/锁文件/安装版本，不擅自安装或升级来凑测试。
- 原 API fragments、完整UI、shared video node不是该12文件纯producer闭包；其缺漏只影响相应集成/测试，不能通过复制半个应用假装完整运行。

## 3. 在未来执行者上的工程测试路径

候选完成并审阅环境后，V5定向命令应以实际解释器和绝对根执行，例如：

```sh
# PYTHON 是现场核实的现有解释器，不是文字占位符本身。
cd "$M09_WORK/after"
PYTHONPATH="$PWD/V5/src" "$PYTHON" -m pytest \
  V5/tests/test_a_close_review.py V5/tests/test_a_close_daily.py
```

本轮不执行这条命令；新daily test当前尚未产生。候选作者必须返回其实际用过的精准命令、依赖身份、全量stdout/stderr和exit，不能把示例命令当已跑结果。原producer等价应单独隔离进程加载original donor，向V5私有临时store写入，绝不可用V4根；实际命令由候选根据真实CLI/fixture交齐，不能同进程混入不同 `domains` 实例。

## 4. 原件、候选与diff必须同时交付

交付的 `before/` 为被修改的原文件原字节；`after/` 为完整选定基树加全部候选更改（不能只交伪代码或摘录）。`CHANGED_FILES.json` 给完整路径、旧文件SHA或 `ABSENT_AT_BASELINE`、新文件SHA、动作与理由。生成patch时必须捕获新增/删除文件和必要二进制，而不是只看已跟踪文件。

推荐在隔离本地Git工作树里用完整baseline产生原始commit，再装候选并 `git add -N -- .`，导出 `git diff --binary --full-index HEAD` 及其 `-R` 版本；不配置或推送任何remote。前后树路径都相对同一仓库根。候选作者应报告具体命令和base commit，而不是把此建议当已执行。

独立验证者从清洁baseline副本做 `git apply --check forward.patch`，应用后逐文件/全树比对完整after；再在已应用副本做 `git apply --check reverse.patch`，反向应用并逐字节恢复baseline。补丁的strip/root设置必须在真实日志里证明；不同根名造成的patch问题不能交给用户猜。

## 5. 新私库同固定版本离线导出

此包已包含原 F 的离线源码，不依赖私库连接。新 `lexi2016/v5` 一旦发布材料/候选，要再次记录该仓库完整40位commit、分支、已推送验证和文件清单，并从这个准确commit导出离线ZIP。不能只发GitHub链接，也不能让离线包夹入该commit以后未提交的文件。

在已授权发布者的 v5 checkout 中，可用 `git archive --format=zip --output <confirmed-output.zip> <full-v5-commit> <exact-published-paths...>`；必须先确认仓库是 `lexi2016/v5`、commit存在、exact paths齐全。导出后重核CRC、成员、每个文件与 `git show <commit>:<path>` 的字节，并给ZIP SHA/bytes。新repo commit尚未确认时留 `PENDING_REPOSITORY_CREATION_OR_PUBLICATION`，不伪造链接、SHA或“同版本已交”。

## R2 新增现场输入解压

原52文件的装配完全不变。另将 `M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip` 解到新的 `runtime_inputs/`，其内部含 `M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011/` 顶层目录。先核ZIP字节/SHA/CRC，再按包内MANIFEST核40个文件；不要运行里面的collect.py/finalize.py。

```sh
python3 - <<'PY_RUNTIME'
from pathlib import Path, PurePosixPath
import hashlib, json, stat, zipfile
z = Path('M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011.zip')
out = Path('runtime_inputs')
assert not out.exists(), 'Refuse to overwrite existing runtime material'
assert z.stat().st_size == 7577304
assert hashlib.sha256(z.read_bytes()).hexdigest() == '24eb6689e336c45e63d0bc071722ea0379c9b98a2961a60a54dd8807999f2f44'
with zipfile.ZipFile(z) as f:
    assert f.testzip() is None and len(f.infolist()) == 41
    names = set()
    for i in f.infolist():
        p = PurePosixPath(i.filename)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename
        assert not stat.S_ISLNK(i.external_attr >> 16) and i.filename not in names
        names.add(i.filename)
    f.extractall(out)
root = out / 'M09_ORIGINAL_INPUTS_RUNTIME_BINDINGS_20261011'
m = json.loads((root / 'MANIFEST.json').read_text())
assert len(m['files']) == 40
for item in m['files']:
    b = (root / item['path']).read_bytes()
    assert len(b) == item['bytes']
    assert hashlib.sha256(b).hexdigest() == item['sha256']
print('PASS: runtime material bytes only; product execution NOT_RUN')
print('Historical T input:', root / 'originals/panel_20261009_required8.parquet')
PY_RUNTIME
```

未来实现运行时，原Mac绝对pointer只当证据；在批准的候选私有目录创建新pointer指向已解压T投影，并记录投影SHA和原panelSHA映射。原来源available_at缺失、数据质量和权威状态必须随输入传入，不把候选指针创建时间充当原数据时间。这个原件不经过填值/清洗；正常工程用例另用明确标为合成的fixture。
