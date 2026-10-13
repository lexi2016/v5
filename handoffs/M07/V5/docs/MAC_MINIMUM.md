# M07 最小 Mac 命令清单（未执行）

所有变量由实际环境确认；不猜活动目录或端口。以下只在已有 V5 clone 与全新隔离目录执行，不访问 V4 数据，不安装依赖。`M07_FIXED_COMMIT` 必须设成本次 GitHub 提交回执中的完整 40 位 SHA，不能使用浮动分支作验收对象。

## 1. 固定源码与隔离测试

```sh
# 先设置四个真实值，不能直接沿用示例占位符。
: "${V5_REPO:?existing V5 clone absolute path}"
: "${M07_ISOLATED:?new absolute isolated worktree path}"
: "${M07_FIXED_COMMIT:?full immutable commit SHA from handoff receipt}"
: "${V5_PYTHON:?existing suitable Python absolute path}"
cd "$V5_REPO"
git status --short
git rev-parse HEAD
git remote get-url origin
# origin 必须确认为 lexi2016/v5；前像登记后才继续。
git fetch origin dev/m07-github-handoff-20261011
git cat-file -e "$M07_FIXED_COMMIT^{commit}"
test ! -e "$M07_ISOLATED"
git worktree add --detach "$M07_ISOLATED" "$M07_FIXED_COMMIT"
cd "$M07_ISOLATED"
test "$(git rev-parse HEAD)" = "$M07_FIXED_COMMIT"
"$V5_PYTHON" -c 'import sys; print(sys.version); assert sys.version_info >= (3,14), "declared Python >=3.14 not available: stop, do not install or switch production"'
"$V5_PYTHON" handoffs/M07/delivery/verify_delivery.py
cd handoffs/M07/V5
PYTHONPATH=src "$V5_PYTHON" -m pytest -q
```

每条命令独立保留 exit、完整 stdout/stderr、开始结束时间。任何失败即停止后续激活，不把云端 Python 3.12.14 的通过替代此处结果。`verify_delivery.py` 是标准库只读校验器，核本交付全部原件/新增文件 SHA，不导入 owner、不执行选股。

## 2. 独立输出根

下方 `M07_OUTPUT` 必须是全新 V5 隔离输出路径，不是现有活动根或 V4 根。

```sh
: "${M07_OUTPUT:?new absolute M07 private output path}"
"$V5_PYTHON" - "$M07_OUTPUT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); assert p.is_absolute() and not p.exists()
assert not any(x.casefold() in ('v4','v3','v35','v3.5','v3_system') for x in p.parts)
p.mkdir(parents=False)
(p/'.v5-m07-output').write_bytes(b'v5.m07-private-output.v1\n')
(p/'ledger').mkdir()
(p/'ledger/.v5-daily-run-ledger').write_bytes(b'v5.daily-run-ledger.v1\n')
PY
```

合成演练已由第1步测试自动创建/清理隔离输入输出；不要把合成记录带进真实验收。

## 3. 真实输入与独立读回

此步需原 M05 六池、M01 RawStore 三元组及真实录制时钟、M04 小时 archive/source witness 与晨报 trio。先登记并复制已有原工件到独立输入根，保留字节/SHA；加 `.v5-m07-input` 标记只能在复制后的私有根。不能改源、补历史行情、从18篇展示archive造分数。缺项即保持 BLOCKED。

由这些已核原件填写 `M07_A_STAGE_HANDOFF.md` 的完整 request，保存成 `{ "request": ..., "output_root": ... }` 的 JSON。输出根必须是第2步路径。以下三个 JSON 文件由真实 identity 填写，不能粘贴随机 run/SHA。

```sh
: "${M07_RUN_JSON:?absolute verified request envelope JSON}"
: "${M07_READ_JSON:?absolute read envelope JSON}"
: "${M07_RESULT_DIR:?existing private evidence directory}"
PYTHONPATH=src "$V5_PYTHON" src/v5_shadow/a_stage_daily.py --run \
  < "$M07_RUN_JSON" > "$M07_RESULT_DIR/run.json"
# read envelope: {"output_root":"...","target_date":"YYYYMMDD","stage_id":"..."}
PYTHONPATH=src "$V5_PYTHON" src/v5_shadow/a_stage_daily.py --read \
  < "$M07_READ_JSON" > "$M07_RESULT_DIR/read.json"
```

必须逐字段核 generation/run/artifact/manifest/receipt SHA。`--run` 在返回业务 BLOCKED 时可能退出0，不能只看进程 exit；检查 JSON status。SUCCEEDED 也只证明保存读回，原 source_status=CANNOT_CONFIRM / selection_status=PARTIAL_WITH_ROWS 与 formal/natural=false 保留。未核活动 API、进程、端口和原 route 前，不接入页面、不操作自然调度。

## 4. 同槽回滚

从旧 `current.json` 保存的 reference（generation、target_date、stage_id、run_id、三个SHA）构造 `{ "output_root": ..., "reference": ... , "expected_generation": "当前generation" }`。先核旧产物存在且原reader通过，然后：

```sh
: "${M07_ROLLBACK_JSON:?absolute verified rollback envelope JSON}"
PYTHONPATH=src "$V5_PYTHON" src/v5_shadow/a_stage_daily.py --activate \
  < "$M07_ROLLBACK_JSON" > "$M07_RESULT_DIR/rollback.json"
PYTHONPATH=src "$V5_PYTHON" src/v5_shadow/a_stage_daily.py --read \
  < "$M07_READ_JSON" > "$M07_RESULT_DIR/rollback-read.json"
```

只切换一个A槽，精确CAS不符就停止。旧generation不删除；不对整个仓库reset、不重启其他模块、不改另一市场或V4。
