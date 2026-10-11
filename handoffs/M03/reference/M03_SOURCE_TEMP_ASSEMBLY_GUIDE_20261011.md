# M03：用已附 SOURCE 做临时装配的最小指导（未执行）

针对原Chat 2026-10-11T01:15:08Z回复。现有材料足够编写默认cold入口、原store适配及定向测试；“没有完整Git checkout”会阻断原组装脚本的git show和部分历史test setUp，不会阻断源码实现、确定性diff或从已物化48件owner建立冷loader。是否能运行须按下面实际环境能力逐项核验；本指导没有运行bootstrap、产品或测试，也不提供PASS日志。

## 1. ZIP实际布局，不再等新的源码包
SOURCE ZIP SHA256：4d5cc792923aed31bc0867ff8abbca85b1cb6fbdabd882a3581c827bb91e4d45。
ZIP共69项，含63件真实源文件和6件说明/manifest；SOURCE_MANIFEST.json列63件，已经逐件核bytes/SHA。根级直接是：
- V5/src/v5_shadow/：cloud_us_collector.py、cloud_transport.py、composition.py、contracts.py、digests.py、__init__.py
- V5/contracts/cloud_us_collector_sources.json
- V5/tests/test_cloud_us_collector.py、test_cloud_transport.py
- V5/tools/cloud_preview/assemble_us_collector.py
- collector_owner/：48件冻结运行闭包，已按descriptor runtime path摆好，含contracts/us_equity_calendar_2026.json
- handoff/.../canonical/：slot/executor及历史测试参考；不是本轮默认collector必须导入的完整调度运行时

在可写临时目录 W 解压，保留原件；复制成 W/work。W/work/V5/src 是V5导入根，W/work/collector_owner就是owner_root。不要把owner拼成canonical目录、不要把所有文件扁平化。R8包的after/V5/...两件叠加到独立before/after候选副本，不能覆盖原SOURCE以伪造来源SHA。

代码/owner保持 W/work 下；本次私有数据放 W/data 下的source、capture、snapshot、binding独立根，避免位于V5 BASE或owner_root内部/祖先。用原initialize_output/admit_output与shadow_root准入，数据source和稳定snapshot不得混同源码目录。

## 2. 不需要git的cold loader定位
原assemble_us_collector.py:10–12通过git show取48件，所以该脚本确实需要对应Git对象。**本ZIP已经提供了它本应组装出的collector_owner/**，不要在新定向fixture里重复依赖该脚本。

原cloud_us_collector.verify(root):17–37只读descriptor及磁盘文件，不调用git；load_owner(root):97–105也不调用git。它负责安装PinnedFinder及导入冻结ops/infrastructure/contracts，不依赖pip安装这些私有包。

原测试的冷进程模式（test_cloud_us_collector.py:15–21）可直接按如下形状写进新增实现/fixture。以下是调用示例文本，本审查未执行：

python -I -B -c 'import sys; sys.path.insert(0, sys.argv[1]); from v5_shadow.cloud_us_collector import main; raise SystemExit(main(["--owner-root", sys.argv[2], "--check-only"]))' "$W/work/V5/src" "$W/work/collector_owner"

实现中用subprocess.run([sys.executable,"-I","-B","-c",bootstrap,str(v5_src),str(owner_root),...],...)，保留超时、stdout/stderr和真实returncode。**-I会忽略PYTHONPATH**，所以固定路径应由受控bootstrap显式sys.path.insert，不是只设置环境变量。不要先import任何ops/infrastructure/contracts再load_owner；也不要拿ambient模块顶替PIN闭包。

真正collector默认runner用新的cold child调用原main，argv按已给owner-root/allow-network-capture/--/data-root/trade-date/capture-phase。root初始化单独走--init-data-root。网络采集和Mac仍保持NOT_RUN，不能为了验证runner去擅自执行真实采集。

默认reader用另一个cold child：
1. 插入固定V5/src；
2. 从v5_shadow.cloud_us_collector导入load_owner、verify、audit_modules；load_owner(Path(owner_root))；
3. from infrastructure.research_peripheral_store import ResearchPeripheralStore；
4. ResearchPeripheralStore(admitted_snapshot_root).read_exact(date,"external_finance")；
5. 在finally保留verify(owner_root)/audit_modules。
不要在已load_owner的同一child再次调用main，它会再次load_owner而触发FRESH_PROCESS_REQUIRED。reader的payload、三件物理SHA和后续binding必须指向同一个经稳定复制/准入的snapshot。

## 3. 离线fixture已经有可复用原例
原test_cloud_us_collector.py:152–203是成功离线RSS+quote→原producer→真实ResearchPeripheralStore读回的源码：
- :158–160装冷loader；
- :161为fixture固定clock；
- :164–177提供合成Proxy响应并禁止Direct；
- :178–180用audit hook拒绝真实socket；
- :183通过原cloud_transport.run_original_us_cli的transport_options测试接缝；
- :184–190调用真实reader并比较三文件前后字节；
- :203明确三件JSON。

可在**新增M03测试**中复用这段fixture构建逻辑，把owner_root设为已核W/work/collector_owner，避免原test class的setUpClass:12重新调用git assembler。不要修改冻结owner字节，不把合成clock/transport带进生产默认runner，不用假store替代原reader。

需要补的M03部分是：将fixture生成的原三件交给实际run_us_source入口，验证stable snapshot、binding、reuse/缺失/错身份/不可覆盖/读回篡改。fixture存在不等于这些代码已经写好。直接跑原整份test_cloud_us_collector而失败于git setUp，应如实写“原setUp未跑”，不能推广成“loader/reader无法实现”。

## 4. 真正的环境前提与目前未提供的材料
静态扫描本轮V5 wrapper和48件owner，所需运行库为Python标准库及包内私有模块；未见M03 collector链要求pandas、numpy、sklearn等第三方包。不能套用M06依赖阻断M03。

仍须实际确认而不可假设的能力：
- 兼容包内现代Python语法/API的解释器；POSIX/macOS/Linux，fcntl、O_NOFOLLOW、O_DIRECTORY、dir_fd、fsync、硬链接/内核锁可用；不支持时保留原PLATFORM_UNSUPPORTED，不降级安全IO。
- 可启动subprocess，允许本轮可写临时目录；不能据“无Git”推断这两项缺失。若真禁用，给准确命令、退出码/异常。
- zoneinfo能取得America/New_York、Asia/Shanghai时区数据。若缺，给实际ZoneInfoNotFoundError；本指导不擅自安装。
- 新测试可以用unittest标准库；若沿用pytest命令，需要pytest实际可用。缺pytest不阻止写测试源码。
- Git固定对象仅为原assemble脚本/原历史test setUp所需；已解压48件可供新增离线fixture。整个原scheduler/runtime catalog/dispatcher及真实slot状态不在此包完整范围，历史slot测试不能声称独立可跑。
- 真实provider网络、真实时钟数据、Mac活动目录/服务与自然接续证据仍未提供；这些是现场运行NOT_RUN项，不是默认函数、snapshot逻辑和after/diff未实现的理由。

不要为了补环境关闭PIN、fresh-process、root/IO/transport保护或修改共享源码。

## 5. 当次可交而不伪报完成的成果
完成私有after源码和真实合同测试；对R8 before与after逐件hash，用difflib生成标准a/V5/...到b/V5/...正反diff（无需Git checkout），包内写适用前像与before/after SHA。可执行的部分记录原始命令/退出码；不能执行的准确标NOT_RUN并给具体限制。代码未实现应单列UNIMPLEMENTED，不能把它混写成环境NOT_RUN，也不必把“写完整after”绑定为“全部PASS日志”。

本补件仅解决临时材料装配和真实依赖定位，不再次扩大业务范围；未实施或运行上述步骤。

