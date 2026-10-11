# 原15号模块实际源码补件

这是普通Chat无需访问私有GitHub即可读取的实际源码前像。固定基线为f7cb731c384ee6890a87d16c19a5b5a621779477。本包不是Chat新候选，没有新增/修复产品代码；没有导入或运行产品、执行产品测试、采集或操作Mac。

## 先读什么

1. task/START_HERE.md与task/PROMPT_FOR_CHAT.md：原M15单模块任务。
2. SOURCE_MANIFEST.json或.csv：每文件固定commit/path/Git blob/SHA256、字节数及可写/参考角色。
3. V5/src/v5_shadow下四个M15适配器，V5/tests下三个专属测试，V5/contracts/us_mapping_source_manifest.json。
4. V5/vendor/us_mapping_baseline完整39件原闭包；原字节保留，包括namespace、常量、JSON种子和日历。
5. 材料映射的M18原函数及直接依赖、references/R3下完整原US owner只是参考，不授权跨模块覆盖。

## 包含范围与改动权限

实际源码及配置共80件，1029947字节；其中10件是本次允许产出修改候选的既有M15目标（4适配器、2映射/消费bridge、1 source manifest、3专属tests）。其余均reference only，包含39件闭包中的原来源/通用依赖、必要共享运行helper、pyproject/uv.lock/日历，以及材料算法和集成参考。只允许根据任务要求新增必要M15专属文件/测试。

39件US闭包有完整字节；M18材料参考不是完整80件经理运行闭包，R3 donor也不是可直接替换当前运行环境的完整部署。manager_plan/current_us_research只为确认跨模块调用合同，未打包它们的全套公告/超跌运行依赖。材料参考中的workspace_projection还含不属本次纯映射路径的延迟workspace_plan/workspace_briefing调用；这不授权读取或执行整套M18。不得拿参考only目录宣称M18可运行，需额外确切文件时给文件级请求单。

请保留原四键daily与行业/个股材料两路径。M03采集/原source store、M02主表资格、M04归档生产、M18共享经理/gateway/UI由各自Chat处理。旧receipt只考虑M15消费bridge复用原store窄兼容；不改原store或旧receipt。完整任务边界在task/PROMPT_FOR_CHAT.md。

## 如何使用原件和证据

V5/保留原仓库相对路径，references/R3保留其原handoff路径。SOURCE_MANIFEST记录role与target_writable，不能以文件位于V5/就推定可写。原39件manifest的origin_commit/origin_path另留，当前实际前像身份始终以source_commit/source_path及blob为准。

PACKAGE_CHECKS只证明材料字节/清单完整性，不是业务测试通过。每件已按Git blob原始字节算法和SHA256核验，39件另比原source manifest，并核原descriptor canonical PIN；既有审查本地参考也与原commit/blob对照。ZIP完成后另给CRC及读回结果。

未附真实Mac数据、行情产物、用户私有材料、运行输出、凭据或虚拟环境。测试中声明的真实输入仍须真实原件，不能造数据或skip补绿；未知环境/缺原件标NOT_RUN。M15独立候选可以先交，跨模块集成和真实验收不能冒称完成。

## ZIP不被聊天界面接受时

随ZIP提供MODULE15_SOURCE_TEXT_01.txt起的分卷文本，每件含源身份、可写性和完整UTF-8源码。它们与ZIP对应同一内容；Content-Bytes声明正文精确字节数，顺序读取该长度后再读END FILE，可无损还原。不要把源码中出现的类似分隔符当边界。分卷文本可以直接作为普通文件上传同一个15号Chat，不要求Chat打开私有GitHub。
