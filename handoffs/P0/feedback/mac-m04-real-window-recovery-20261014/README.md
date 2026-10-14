# M04真实窗口失败与保存capture恢复

**DERIVED_SUMMARY**：早期失败链由主控已核回执转述，最终结果直接读取Mac thread `01a12e51-a0ec-705c-96e5-26cfd89360f8` 消息 `msg_0b47eb1b0178a3a6016aced480999487d1924093c024a1a7e6`。本写入者未采集、恢复或重测；不上传原正文/私有路径，不把此摘要冒称原receipt字节。原身份及来源报告指纹见[summary.json](summary.json)。

## 保留完整失败链

1. 261cf0123dd7175bfcc6031a5dc201604a98a609在2026-10-14 UTC00:30原窗口仅capture一次：30 topics、22 effective、21 raw、11 research、8 articles；首次在第1篇evidence换行表示处失败。
2. 63c1候选Mac37 PASS后，resume被已有guard阻止。
3. d19f候选Mac43 PASS，复用原checkpoint通过，但第2档原builder非连续摘要表示再次拒绝。
4. 一次对全部8档只读归类后，d5983dc7d3dfc6825b7d09b5fb976197943de40a修复表示合同。短标识63c1/d19f仅按已核摘要引用，不擅自展开SHA。

## 最终恢复和冷读

- 494清单核验、Mac47 PASS/0失败/0skip：UTC00:59:56–01:00:28。
- 原claim唯一一次resume：01:00:33.469–01:00:34.656，SUCCEEDED/exit0。
- 独立原cold reader：01:00:55.679–01:00:56.171，8档exit0、零写入。
- 准确数量为21 raw / 11 research / 8 articles，不能把21 raw写成21归档。
- 1篇原连续quote、4篇唯一空白映射；3篇保留原owner摘要并标ORIGINAL_BUILDER_SUMMARY / NOT_A_SOURCE_QUOTE，不伪装原文引用。
- 002430原编码tag经原decoder发行人区间及标题compact转换核验身份；8档原body/来源page/采集时间匹配，本批无另一个已发现未覆盖的表示错误。

原receipt与原checkpoint SHA保持不变，原capture/producer/旧失败记录保留；后续capture调用0，不把失败续接计新采集或自然完成。未改现役API/页面、部署0，natural/PIT/production=false、bounded_has_more保留，页面14/完整0不变。M14真实槽读/发布具体批准待答状态保持。
