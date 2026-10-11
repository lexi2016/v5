# M02｜HK行情、证券主表与资格来源：GitHub 源码交接

仓库：私有`lexi2016/v5`。模块分支：`dev/m02-github-handoff-20261011`。共同基线：`2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`。
接续原Chat：https://chatgpt.com/c/6aca47c7-0bd4-83e8-ab3b-3d4c2cee272a 。不新开模块。
请使用交接消息给出的固定commit读本目录；分支名可移动，不代替固定身份。

## 阅读入口
1. [STATIC_TASK.md](STATIC_TASK.md)：原R3应完成的最小源码返修和原snapshot接口依赖。
2. [review/REVIEW_M02_R3.md](review/REVIEW_M02_R3.md)：原独立静态审查，R3仍拒收。
3. [source/V5](source/V5)：固定`lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477`原源码，保持字节。优先读capture_master、hk_membership_recovery、membership_reader、native_identity_reader与对应测试。
4. [PUBLICATION_SCOPE.json](PUBLICATION_SCOPE.json)：83件原字节材料的准确路径、SHA256/Git blob和12件expanded-source排除项，另3份派生说明，总86件。

原SOURCE_CORE的8件正文已逐字核与expanded一致，只保留一份正文，另在[provenance/CORE_SOURCE_MANIFEST.json](provenance/CORE_SOURCE_MANIFEST.json)保留原8条manifest。[source/SOURCE_MANIFEST.json](source/SOURCE_MANIFEST.json)是原expanded82件Git原件的完整清单，不代表该清单所有正文都在本次范围内。本次expanded正文/metadata实际73件，12件排除。

## 本次保留
- 原4个M02目标与必要shared helpers、M02测试和合成fixture。
- security_master8件、hk_membership3件、hk_preselection34件，共45件原owner胶囊，及各自3份原manifest。每件原SHA已核；不改变原reader/loader/七文件/SDK/owner身份验证。
- `candidate_r3_rejected/`保留R3的8份非日志材料。两份Python是被退代码和矛盾测试；正反patch只有注释，不能应用。SHA清单是原提供方6条清单，本次PUBLICATION_SCOPE另覆盖全部保留字节。原Mac验收说明只是历史候选清单，不表示Mac已操作。

原R3 ZIP实核SHA为`0300e944c81888484cc0e9fb68093b9035fdfafe0b61cf19f4954f84b22bd910`。历史Chat曾拼错该SHA，应以实际字节和原独审记录为准。

## 实际尚缺的接口
`native_identity_reader.worker`会调用原`manager_plan._snapshot`。本次不复制经理/公告整模块来凑闭包；该原函数及必要语义已从固定GitHub原件核实，见STATIC_TASK的准确URL。M02需要明确、保持校验语义的独立只读snapshot接口及等价测试。这是待实现的代码依赖隔离，不是“无权限”或“源码不存在”。
`test_manager_membership.py`与`test_native_identity_reader.py`含经理端到端导入，保留为M02回归参考，但当前窄树不保证其完整集成可执行。

## 限定状态
本次仅源码/静态任务交接，没有安装任何R3到运行目录，没有修复代码、import、执行产品或测试。不是完整运行发行物；环境/锁、实际panel/model/master/membership、真实时点/资格证据与完整下游集成不在本次材料内。
不上传ZIP、日志/pyc、Mac补包或真实数据、凭据及其他模块实现。保留V4/main/其他分支，不交易、不扩大凭据或权限。
原Chat下一轮通过本模块GitHub分支交完整候选/测试/差异与固定commit；原source、被退R3和review保持，不能把材料数量当功能完成。没有实际执行的测试继续NOT_RUN；由现有Mac隔离验收后再决定应用或部署。GitHub读取出错时回真实工具、固定路径和原错误，不猜内容。
