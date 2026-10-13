# M07 最小 P0 接线与 Mac 接入清单

本次调度端接续；原 M07 `e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31` 已由 Mac 隔离验收（反馈 `0cb27e282eefeeb02211259b857713b2215184f2`，63 tests + 31 subtests），该结果不等于本次 P0 接线已部署。

## 固定内容与边界

- `V5/source_owners/m07/`：112个逐字固定源文件（97原owner文件、13原V5支持文件、原闭包清单、原合成测试夹具）；`V5/contracts/m07_runtime.json` 同时固定新进程桥，共113项。原算法与ledger没有修改。测试夹具仅被测试主动调用，执行或页面不导入它。
- 实际入口：`v5_shadow.p0_a_stage.run_explicit` / `python -m v5_shadow.p0_a_stage`。默认关闭；必须 registration.enabled=true 且外层allow_execution=true，以及完整RECORDED_INPUT_REPLAY请求。原准入/窗口/时钟/源SHA/发布/独立读回/ledger由固定原链执行。无HTTP执行入口、无自然任务、无自动重试授权。
- GET `/api/v5/source-bundle/a-stage-saved`：仅按固定references调用原reader；可用date、stage独立筛选，不匹配即WAITING。没有binding时返回具体M05六池/M01原三元组与录制时钟/M04原小时witness和晨报/已保存reference缺口。未读运行ledger、不恢复、不生成、不发布。
- 页面复用默认SavedManagerResultView的源模块区域；新增“A股阶段选股 · M07已保存结果”导航。旧 `?view=legacy` 的执行按钮与原App完全未动。
- 合成类型和原产物显式SYNTHETIC证据不得显示为真实结果。固定SHA/冷读证明内部完整性，不证明外部行情真实性；formal/natural/production/buy/order旗保持false，原PARTIAL_WITH_ROWS/CANNOT_CONFIRM不升级。
- 仅表示已保存结果可读，不代表完整模块验收、真实数据、自然接续或页面部署已完成。

## 配置合同

现有source_bundle module_api.routes追加上述单条GET route即可显示WAITING；不需要创建假binding。只有真实已核产物才添加 `m07_a_stage_binding`：

`{ output_root: 绝对M07私有输出根, python_executable: 已验现有解释器调用路径, python_sha256: 解释器实际目标字节SHA256, data_kind: "RECORDED_INPUT_REPLAY", references: [ {generation,target_date,stage_id,run_id,artifact_sha256,manifest_sha256,receipt_sha256} ] }`

references同日期/阶段不得重复；默认读取显式列表首条，不猜“今日最新”，页面始终显示原日期。python_executable可为现有venv链接，保留原调用路径并核实际目标SHA，不安装依赖。无真实结果时保持binding缺失。

显式CLI stdin固定三键 `{registration, request, allow_execution}`；registration四键 `{enabled,output_root,python_executable,python_sha256}`。request完全沿用e99的原 `v5.m07_daily_request.v1` 合同；缺真实工件不得改标合成数据、补历史时钟、编造资格。最小关闭探针：

```sh
printf '%s\n' '{"registration":null,"request":null,"allow_execution":false}' | PYTHONPATH=src "$V5_PYTHON" -m v5_shadow.p0_a_stage
```

## Mac 最小步骤（本次未执行）

1. 登记活动HEAD/dirty/进程/端口/配置/原source_bundle路由前像；fetch唯一P0分支，用本交付完整固定SHA建新隔离目录，保留V4及活动目录，不reset、不安装依赖。保留M16和其他模块的现有字段。
2. 按 `SOURCE_CLOSURE.json` 核每个候选文件SHA；按runtime清单核113项，确认复制原ledger与e99完全一致。Python使用已验现有3.14环境；现有venv路径及目标SHA登记真实值。
3. `cd V5; PYTHONPATH=src "$V5_PYTHON" -m pytest -q tests/test_m07_p0_integration.py tests/test_module_api.py tests/test_p0_main_registry.py`。前端 `npm run test:p0`、`npm test -- tests/m07SavedStage.test.ts`、`npm run typecheck`、`npm run build`。分别保存exit和完整输出；云端未完成Vue工具链验证。
4. 仅为现有source_bundle配置增加M07只读route，binding缺失；经原P0发布流程替换本次受影响源/静态构建，保留其他routes/bindings/M16。前端单条proxy复用原 `V5_SOURCE_BUNDLE_TARGET`，不猜新端口。
5. 独立GET应为WAITING，核四项具体缺口、无股票行、全false旗；页面点击M07导航可打开对应区域，刷新只GET。验证POST405、GET前后数据/ledger无变化、M11/M12/M16原路由保持可读。
6. 没有真实M05/M01/M04原件时到此停止，不调用真实worker。真实工件另行逐项审核、显式运行成功并独立原reader核reference后，才绑定真实保存结果；继续保留partial/formal阻断口径。
7. 回滚只恢复上述窄修改的API配置和上一已验静态构建/模块进程绑定；保留产物和原ledger，不回退整份P0 HEAD、不动V4/其他模块。原M07 generation回滚仍按e99的精确CAS接口。

## 当前验证

云端定向后端29 PASS（M07 15、原module_api 11、原registry 3；含M11/M12/M16无binding交叉读取）；前端19项Node行为/导航PASS，实际导航函数jsdom PASS。均非真实市场输入。Vue挂载7例、typecheck、build未运行：现有云环境缺vitest/vue-tsc/vite，未安装。完整P0全仓库suite未在此次稀疏任务检出中运行；Mac须执行其现有集成检查。精确命令和日志见 `TEST_REPORT.json`。
