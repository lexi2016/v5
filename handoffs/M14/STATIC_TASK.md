# M14 下一次完整代码返修任务（静态交接）

这是根据原固定SOURCE与`review/REVIEW_M14_R1.md`编写的派生任务，不是新实测日志或R2实现。继续原M14 Chat，在私有`lexi2016/v5`的`dev/m14-github-handoff-20261011`按固定交接commit读取实际文件后交完整代码。

## 最窄代码闭包
基于`source/BASELINE_F/V5`，修复下列6件及M14针对性测试，保留准确原前像：
- `V5/vendor/rebound_baseline/v4/manager_research/workspace_plan.py`
- `V5/contracts/rebound_source_manifest.json`
- `V5/contracts/rebound_owner_capsule.json`
- `V5/src/v5_shadow/rebound_owner.py`
- `V5/contracts/rebound_observation_capsule.json`
- `V5/src/v5_shadow/rebound_observation.py`

R1只改vendor两处数值比较，不是完整修复。必须逐项解决：
1. M14-R1-01 / P1：新vendor字节必须贯通source manifest、owner capsule/PIN、observation bindings/PIN。按各自canonical digest与原始文件digest规则生成；保留历史donor身份，新字节记录真实新commit/path/blob，不能伪归旧commit。
2. M14-R1-02 / P1：最终源码定稿后重算准确setup/arithmetic/row/background位置、span SHA与结构数量。R1净增13行使旧row失效，不能只改hash或照抄旧R1行号。保留fail-closed并覆盖source/span/结构/PIN篡改拒绝。
3. M14-R1-03 / P1：原完整五日、缺/重复日和非零均值守卫内，量能精度须在float除法之前处理。保持原值、窗口及阈值；历史静态反例是previous5各0.1/current0.15，不能先float除再Decimal。原独审说明等价cross multiplication，不引入新策略或单位证明。
4. M14-R1-04 / P2：价格bool、返回cutoff、near gate/gap使用同一精确cutoff来源，展示保留原float/JSON类型，分组、排序、未知语义不改。

## 保留与测试要求
- 保留原60证券session高点与5完整session量能规则、半日边界、strict/near/pending/excluded/unresolved守恒，不填0、不缩分母、不改准入标签。
- F已有`_same_code`和`_align_repair_trade_dates`，不要重写日期兼容；保留原owner identity/date测试。
- 在真实主函数及原AST抽取函数做逐字段/顺序/理由差分：0.28/0.35、0.56/0.70、略高/低、量能1.5和0.1/0.15反例、None/NaN/inf/zero mean、缺/重复日期。不能mock掉身份检查换绿。
- 所有未实际执行的检查标NOT_RUN。原pyproject要求Python>=3.14；源码/lock存在不证明依赖已安装。不得以py_compile、pyc、7-byte exit记录代替owner/AST/Mac验收。

## 精确交付
在本模块分支保存完整before/after源码、全部新增/修改测试、逐文件SHA/blob及来源映射、仓库相对路径正向与真正反向patch、隔离apply/rollback说明。实际运行时再提交真实命令/解释器/退出值与允许范围的脱敏日志；本次交接没有运行日志。
列出S daily确切checkout/PIN与shared adapter、M18消费所需的精确INTEGRATION_REQUEST，不跨改它们，不把4份S参考当完整checkout。本次未复制M18、Mac补包或现场输入，缺实际输入不妨碍上述源/数学/身份修复，但不得伪造正式准入。
最终返回固定GitHub commit、准确文件diff和未验项，由Mac隔离验收。不要把本次材料commit或R1稿当产品功能完成。
