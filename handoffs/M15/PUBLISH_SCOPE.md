# M15 本次发布范围

原SOURCE为88件，本次保留原字节复制74件，明确排除下列14件跨模块M18参考本体。原SOURCE_MANIFEST.json/CSV仍为原版，不删条目、不宣称其80项本体全部在此。另保留R1候选6件、独审1件、最新返修任务1件、Mac五件身份元数据1件、更新任务/索引2件，共85件已有材料。新增入口/本范围/发布manifest只是交接文档。

这些排除项只列原v4已存在的固定源码身份供定位，不取自也不指向此前被拒的M18或M13候选包；本次不复制它们。已有其他模块blob存在也不等于本模块拥有修改许可。

## 明确未复制的14件

- V5/vendor/manager_plan_baseline/v4/manager_research/issuer_us_relations.py
  - bytes: 15653; Git blob: d5cf87f1eb80d020743c8a73cab0640152912ce4; SHA256: 75fdca7a3c8bc1e8f385a023d47df640f002096921d6a0f3af8ea6cc466ee00f
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/issuer_us_relations.py
- V5/vendor/manager_plan_baseline/v4/manager_research/research_evidence.py
  - bytes: 28636; Git blob: ec5d612601508f91ede01e07d0fff9426930c275; SHA256: d2539b676d5779d9369fd8aba187c0565fcc38dbb0e89596d1248668fda4a7d5
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/research_evidence.py
- V5/vendor/manager_plan_baseline/v4/manager_research/research_attention.py
  - bytes: 35615; Git blob: d604a4f4dadac305e1d618c2b9c0325a32e852f1; SHA256: ccf9246193e082f6fd09e83fae0df00533c8dc0ef27ebb5f5335dfc35d76be96
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/research_attention.py
- V5/vendor/manager_plan_baseline/v4/manager_research/mapping_plan_admission.py
  - bytes: 3494; Git blob: ae1c647eb79e9f17b1c3decfff880654fbd900d1; SHA256: 4c48df3e93b599d1f9d12e7af3385c5084bf3d4fefc102085ab60211e82a31cc
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/mapping_plan_admission.py
- V5/src/v5_shadow/current_us_research.py
  - bytes: 10269; Git blob: 1e4483e91551dc08ae5954a8cce2d18842195a19; SHA256: b6c8ce065cc2d2a2d35ba4b9e305bc9695825c9c2b30704b3acb90909749c0bb
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/src/v5_shadow/current_us_research.py
- V5/src/v5_shadow/manager_plan.py
  - bytes: 39957; Git blob: 5e05f82ec6d2d88f47e79d19e5caf433a0143f2c; SHA256: fa6cbee7196d40acb96dc78693925561dbc4eba7c09313157af0f7a2f6dcca7b
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/src/v5_shadow/manager_plan.py
- V5/vendor/manager_plan_baseline/v4/manager_research/workspace_projection.py
  - bytes: 31337; Git blob: 08978f4da5e9823358e7e20f798eeeaea6dce76d; SHA256: 9c5ae5eda8aa43536ddd9a5a287da2a9d27cccde308e128652d9bc4f7dffb2c4
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/workspace_projection.py
- V5/vendor/manager_plan_baseline/v4/manager_research/attention_decision.py
  - bytes: 9179; Git blob: deae8d18c88682eb8e06593603485dcab043b4be; SHA256: 4b84e0469a5267771ccfe9f9f5040fc829e82f7a1b24afdeed11ebef0cb7d640
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/attention_decision.py
- V5/vendor/manager_plan_baseline/v4/manager_research/evidence_identity.py
  - bytes: 5276; Git blob: f29fdc0361647d842de5b4b90ee2cae715361ebc; SHA256: 6ff16b31c8e23f3bbceea7acc22cf866afc29db6f9f67158381cec2c23b3d053
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/evidence_identity.py
- V5/vendor/manager_plan_baseline/v4/manager_research/announcement_materials.py
  - bytes: 10727; Git blob: fbd174f760613d5388cc2683235cf2e57048741b; SHA256: 7163ca75e883d173ce7a831076402b06906951323dd54f82b2500c6b9ad60df1
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/announcement_materials.py
- V5/vendor/manager_plan_baseline/v4/manager_research/workspace_semantics.py
  - bytes: 33731; Git blob: 438a5c0198f39000a645323a3177cf1964ca4cbb; SHA256: dc8d1d330e4fdacf2ef7169a7ac62874bfd3e2658f8b4bcff0773e06e32c4f7f
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/workspace_semantics.py
- V5/vendor/manager_plan_baseline/v4/manager_research/contracts.py
  - bytes: 12756; Git blob: 643abdd5bff9a196bb993275e5f57bea79881e90; SHA256: d90f0027a8383f20a299e3058d69716e62737e9e5300afc61a8ef2ed949d402f
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/contracts.py
- V5/vendor/manager_plan_baseline/v4/manager_research/safety.py
  - bytes: 3272; Git blob: 117439469386ffb3d58c9d047766c6c5cccbd06a; SHA256: c82fcdee6845e765783584f5ac46a9d4ca6b6b9fda1c3c2e919c17ab17c7f3e8
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/vendor/manager_plan_baseline/v4/manager_research/safety.py
- V5/contracts/manager_plan_source_manifest.json
  - bytes: 29148; Git blob: ed8abe0e2286fd3e830ff08d4b3adeb7f48a0ea8; SHA256: 92c445765cdfe4a76531bc4929622ef3878b58702b4a2aa3f56dc0da8b2c3767
  - 固定原源码: https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/contracts/manager_plan_source_manifest.json

## 保留的M15条件原算法donor

references/R3/handoff/manager-daily-r3-repair-20261009/after/api_current/v4/manager_research/us_mapping_research.py 来自独立固定donor 8c8e35d9d53431c9082dec49f4976e363c275765（Git blob e0fc26de11bdff6b77577b067ecf15f0dc929f12；SHA256 f4a0919382d6daecaac67429a886980197fc2476f99de3ccda241fb1da8ba8b7），不假归于f7cb731c。它仅为M15原映射的条件参考；当前任务并未认定原M15调用有kwargs错配，也不能只摘签名就替换owner。

## 未包含与未证明

没有真实US三文件payload、材料正文、运行敏感配置、凭据或完整M18系统。Mac记录只有路径/大小/SHA和时间身份；它不是实测原文替代品。此前R1日志与审查保留原状态，不新增成功宣称。14项排除意味着不得称本次源码是原88完整装配或已可运行闭包。
