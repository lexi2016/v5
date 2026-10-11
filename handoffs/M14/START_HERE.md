# M14｜超跌研究与选股：GitHub 源码与 R1 静态返修交接

目标仓库：私有 `lexi2016/v5`。独立开发分支：`dev/m14-github-handoff-20261011`。
原 Chat：https://chatgpt.com/c/6aca4e2a-ea0c-83e8-a4fa-dc01a13867bf 。接续原会话，不另开模块。
共同提交基线：`2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`。使用交接消息给出的固定 commit 阅读本目录；该固定版本由发布后的远端读回回执确定，不把分支名当不可变版本。

## 顺序
1. 读 [STATIC_TASK.md](STATIC_TASK.md) 与原 [静态独审](review/REVIEW_M14_R1.md)。
2. 读 [PUBLICATION_SCOPE.json](PUBLICATION_SCOPE.json)：113 件原始字节材料和两份派生说明的精确路径、大小、SHA256、Git blob、来源及排除清单。连同该范围清单，本次新增116件。
3. 原固定 F 源码在 [source/BASELINE_F/V5](source/BASELINE_F/V5)，F=`f7cb731c384ee6890a87d16c19a5b5a621779477`。原 [SOURCE_MANIFEST.json](source/SOURCE_MANIFEST.json) 是原包159份Git原件的完整身份账本；本次只复制107件source文件，不能把清单内未复制条目称已齐。
4. [candidate_r1_rejected](candidate_r1_rejected) 是被退回的 R1 before/after/patch/身份/提供方说明。状态 **RETURN_FOR_MINIMAL_REPAIR**。before与F的rebound vendor逐字一致；after不是可运行验收版，未装到任何runtime目录。REPORT中的编译自报不是本次独立测试证据；原patch保留历史`/tmp`工具路径，不能直接当仓库相对路径补丁应用。

## 原件与窄范围
- 保留原M14源码、6文件修复链相关合同、测试；21件薄适配组成静态import/owner identity依赖范围。
- 原rebound vendor 18件为既有冻结来源；HK vendor 34件与manifest是`rebound_panel_repair._verify_owner`真实要求的只读身份依赖，不授权改M02采集或模型。
- `source/DONOR_D`仅保留独立D before/after和oversold针对性测试。D=`d659ff0dbcc00aa1944908cfc8b44443642ea171`，是不同V4前像的参考，不能整文件移植到F，也不能把D测试当F运行结果。混公告patch/fixture不在本次范围。
- `source/SEPARATE_OWNER_S`仅4份独立M14 daily/recovery参考；S=`2d8e38ec61792b3e75581f96318e9c284f72b7ba`，未与F混合，也不构成完整、clean的S checkout。
- `daily_rebound_owner.py`原桥保留作接线依据；其调用`daily_owner_adapters`的跨模块依赖不在此窄材料内。后续只提精确集成请求，不为闭包而复制M18/公告实现。
- 原SOURCE包63件未复制。M18参考、非M14薄适配、全局计划、含用户home路径文档、旧Mac补包/运行盘点、日志、pyc全部排除。不上传ZIP、真实panel/parquet或凭据。

## 当前状态
6文件source manifest → owner capsule/PIN → observation capsule/PIN/AST闭包仍未修复；量能精度与cutoff/near展示问题见独审。原源码身份/字节检查完成不等于产品测试通过。
本次仅发布源码与静态任务。未执行产品、pytest、Mac测试、provider采集、真实数据准入、API/页面、自然运行或部署。正式资格/单位/finality/成员覆盖仍需实际证据，不能由数值修复或合成用例推断。

## 下一次交付
所有工程工作继续通过GitHub。原Chat应在本模块独立开发分支提交完整候选源码、测试和精确来源/差异；不以ZIP替代。原source、R1和审查保留不覆盖；候选与运行验收状态分开。不能读取时给实际工具/路径/错误，不猜缺失内容或把GitHub不可访问当既成事实。
保留V4、main、其他模块与原业务算法；不交易、不扩大凭据或权限。shared daily、M18、M02、UI/gateway/scheduler只交精确集成请求；由统一集成验收后决定应用。固定commit和逐文件差异交Mac隔离验收后才可讨论部署。
