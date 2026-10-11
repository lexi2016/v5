# M03｜US行情来源：完整固定原源与最新候选交接

私有仓库`lexi2016/v5`；独立分支`dev/m03-github-handoff-20261011`；共同main基线`2489ea1e04a26a9e2f318f498ac3f5f8c970fe48`。
原Chat：https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8 。继续该会话，不新开M03。
按交接消息中的固定commit读取本目录，分支名不能代替不可变身份。

## 阅读顺序
1. [STATIC_TASK.md](STATIC_TASK.md)：下一次完整默认链/reader返修。
2. [当前R13静态审查](review/REVIEW_M03_R13_HANDOFF_STATIC_20261011.md)。最新是R13 reader切片，不是R9，也不是完整M03。
3. [source/V5](source/V5)与[source/collector_owner](source/collector_owner)：原SOURCE的63份Git原件全部保留，完整可读，原[source/SOURCE_MANIFEST.json](source/SOURCE_MANIFEST.json)给出每件commit、原路径、Git blob/SHA/bytes。
4. [PUBLICATION_SCOPE.json](PUBLICATION_SCOPE.json)：76件原始字节和4份派生文档，总80件。未上传任何ZIP或运行日志。

## 准确来源
- 原SOURCE：163761B，SHA256`4d5cc792923aed31bc0867ff8abbca85b1cb6fbdabd882a3581c827bb91e4d45`，69件中63原源＋原manifest保留，5份旧入口/任务说明由本次派生文档代替。
- V5 wrapper/helper/test基线F=`f7cb731c384ee6890a87d16c19a5b5a621779477`。
- 原descriptor SHA`34f45318dd89132a496ac0edf98147455b41d9ea926198d83ce1bd8810c20d8b`固定owner=`164c010c7eaa1659db9bfed0ff5f123c7a39eefc`。48件owner按runtime相对布局完整保留，逐bytes/SHA与descriptor核合，不换成最新同名文件。
- `V5/vendor/us_mapping_baseline/infrastructure/http_transport.py`是原transport测试直接加载的共享HTTP代码，不含M15映射算法。slot/executor及两份来源测试是M03原接线参考，不是完整调度发行物。

## 候选严格分开
- [candidate_r9_historical_rejected](candidate_r9_historical_rejected)：R9历史binding/总入口参考，ZIP SHA`8374c79b5eced12b4a40507439ec827a390afeaf5eaf4a4106144e76a0eac4ab`。仍缺真实默认执行、同源snapshot等。
- [candidate_r11_historical_rejected](candidate_r11_historical_rejected)：R11完整after参考，ZIP SHA`a771029a5ea97ac98fb53d85ef826c022fe7fcc7e4b75505d3f9a73c8e796fa5`。含恢复的请求类/helper和cold collector，但无完整run_us_source/reader。
- [candidate_r13_latest_incomplete](candidate_r13_latest_incomplete)：最新R13，ZIP SHA`f731e6edca95ba8da171ad47f81728eaad2e21a7d9a55d947af97aeaec96ba4f`。reader源码2122B/SHA`78cff69c77097aa45507596becf78b762498ca966a18438101340c15a9a14334`；测试350B/SHA`005ed686d064531adda8d3e857afca7a1a8f773b3e965840374cec3f7beb0f99`。
每版只保留两份完整源码/测试及原作者manifest。所有日志排除；各版正反patch逐字相同且非正确增量路径，均排除并在范围中留SHA/原因。原manifest的R9-after/R11-after标签不是准确前像SHA。

R13同路径`us_source_daily.py`仅reader两函数，直接覆盖R11会丢类/helper。各版在本交接保持独立，没有自动合并，没有放进任何根级runtime。R13修复子脚本SyntaxError与输出次序是实有进展，不能再退回旧错误描述；也不能把AST或存在性测试当真实reader执行通过。

## 源码已经齐备的部分和实际缺口
原`cloud_us_collector.verify/load_owner`不调用git；48件已物化原源可用于新的离线fixture。只有旧assemble脚本/旧test setUp依赖git show的164c历史对象，不能据此说默认入口代码无法完成。见[历史静态装配指导](reference/M03_SOURCE_TEMP_ASSEMBLY_GUIDE_20261011.md)，其中版本称呼/ZIP交付应按本GitHub入口更新。

完整run_us_source、source→稳定同源snapshot、SafeRoot/跨进程锁发布、幂等争用/失败保成功和独立引用重验仍缺完整实现/验证。Python/POSIX/zoneinfo和真实provider/运行现场仍需实际核；原slot完整调度闭包不在此树。
本次只核字节/来源与静态结构，未执行候选、测试、子进程、真实采集、Mac、API/页面、自然运行或部署。材料数不计代码完成。

## 后续
所有代码工作继续GitHub；原Chat提交完整累积候选、真实测试源码、准确前后像/正反diff和固定commit。保留source、历史候选和review；不要用reader切片覆盖整件模块。不能读固定文件时给真实工具/路径/错误，不凭路径猜实现。
不改原owner/PIN/guard、V4、main、其他模块，不采集/交易或扩大凭据权限。shared scheduler/gateway/UI只提精确集成请求。候选交独审和Mac隔离验收，不凭本次材料发布部署。
