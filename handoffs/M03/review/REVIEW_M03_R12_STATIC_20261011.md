# M03 R12 reader切片静态审查（2026-10-11，冻结）

## 结论

**REWORK：父端subprocess真实接上，但child脚本有确定语法错误，切片尚不能真实运行。再次以单helper覆盖整件旧源码，R11已恢复功能又丢失。** 本轮仅读取/下载/解压/hash/AST/文本差异；未执行产品、child、测试、采集、Mac、patch或浏览器写入。

## 实物

- 原回复：https://chatgpt.com/c/6aca49ea-c2fc-83ec-b79f-64ec937123e8?messageId=e9508117-3d85-4368-a935-174f77049efb
- 实际ZIP名：V5_M03_R12_READER_SLICE_DELIVERY_20261010.zip。
- 本地：/workspace/shared/m03_r12_received_20261011/V5_M03_R12_READER_SLICE_DELIVERY_20261010.zip。
- 4605B；SHA256 7fdb575e4c13e67899355d47e4639586cbbdbb690c96b8c970db3dce39014768，匹配作者值；CRC无错误。
- C=after/V5/src/v5_shadow/us_source_daily.py，1511B/47行，SHA c9b2515928797f2a909f672093785bcde41e5701fd7bc3bff2f79bc27aadf949。
- T=after/V5/tests/test_us_reader_slice.py，390B/13行，SHA fa6e053a32d36d38fa09be5f08c25e0611f947700cd8a42173ed4a2ff2561cf2。
- C/T外层AST可解析且manifest after一致；嵌入child AST不能解析。证据与差异在ZIP同目录STATIC_EVIDENCE_M03_R12.json、R11_R12_SOURCE_STATIC.diff。

## 1. 已实修，须保留

C:11/25–36是真正默认subprocess.run执行，非仅argv/必填callback；使用sys.executable/-I/-B、固定四项参数、stdout/stderr capture和300秒timeout。C:13显式import json修复旧缺名；C:37–46增加非零exit、JSON解析和外层dict检查。意图上已调用原load_owner、ResearchPeripheralStore.read_exact和finally verify/audit。这些不能再说完全没写。

## 2. 立即修复的精确问题

1. **child语法错误，未到loader：** C:18以分号结束字符串，C:19紧接try，最终第一行是“...ResearchPeripheralStore;try:”。Python复合try不能跟在同一行分号后。仅ast.literal_eval提取常量再ast.parse，结果SyntaxError: invalid syntax，line=1，offset=253。这是静态确定错误，不是猜环境、缺checkout或provider。外层py_compile/导入成功也不会发现字符串中的错误。
2. **整个R11再次被覆盖：** C全47行仅有read_cold_snapshot，R11的USSourceRequest/parse_utc/source_paths/collector_argv/run_cold_collector/select_capture/create_binding/persist_binding均消失。切片要在完整R11文件末尾增量加入，或作为独立新模块再导入；不能把切片文件交成旧模块的完整after替换。R11发布新根/争用回退也没有修，只是函数被删掉。
3. **准入未接：** C:16没有import admit_output，C:20直接构造store。原marker及代码/owner根边界未验证。
4. **输出顺序错误：** C:21在try内print，C:22–23之后才verify/audit；应把print移到完整try/finally之后。父端非零退出目前会拒绝结果，这点仍成立，但child“结束验证后才输出”的要求没有实现。
5. **API和类型检查不完整：** child输出{'payload':p}，父端C:45只验外层dict，C:47返回整个envelope。缺payload键、payload为list/数字/字符串均可作为dict返回。若API返回payload，则先确认必须有payload键并验证p为dict或None，再return p；若保留envelope，明确合同并验证内部payload。当前总入口不存在，不能假定调用者自动解包。
6. **timeout只是设置，不是所声称的完整处理：** C:25–36无TimeoutExpired处理；非零异常C:39保留stderr/returncode却丢stdout。应有可识别timeout且带部分stdout/stderr，JSON/type失败也应留诊断。

## 3. 两条“通过”测试根本没有调用reader

T:6–7只assert callable，T:9–10只比较函数名。整个测试零次调用read_cold_snapshot，没有child、原store、fixture或stdout/exit边界，所以嵌入语法错误仍能“2 passed”。它们是存在性检查，不能算真实reader测试或行为stub通过。

作者TEST_LOG记录2 passed in 0.08s，本轮未复跑。日志中Spreadsheet warmup错误与M03无关。原fixture、marker、篡改测试不存在，属NOT_IMPLEMENTED。

## 4. 下一条只需这段精确反馈

R12 SHA已核一致，真实父端subprocess是进展，但child C:18–19拼成“;try:”有SyntaxError（静态解析line1 offset253）；两测试仅callable/函数名，未调用reader。请直接在完整R11 after上增量加reader，恢复被R12覆盖的所有类/helper；child改多行脚本、接admit_output、print放finally之后，父端核payload键及dict/None并处理timeout诊断。测试现在必须实际调用默认reader：用SOURCE原fixture生成真实三件，正例核返回及字节不变，篡改与坏marker必须拒绝。至少对实际bootstrap字符串做AST解析，不能再仅检外层文件。交源码/实际测试增量包；本切片和整个M03均尚未完成。

## 5. 局部云测建议

**不必等整个M03才能测reader，但当前先修确定SyntaxError与准入。** 修后可以把SOURCE V5 wrapper、48件collector_owner和增量R12放私有工作副本，由原152–203离线Proxy fixture在新标记私有数据根写三件，调用read_cold_snapshot默认subprocess，独立fresh child只读。必须禁止真实socket，不调用run_cold_collector。按上述正例/篡改/marker三组记录命令/退出码；通过只计reader局部，不能计稳定snapshot/总入口/SafeRoot发布或Mac通过。本审查未运行该流程。

## 6. 包装仍不成立

manifest before只写字面R11-after，不是前像SHA；runtime仍/dev/null新增和a/mnt/data路径；reverse/runtime仍相同，SHA af2f4230bd64f7668a46266e63a459222c89d8429fd96eebba578b9f6715c1c1。仅改manifest标签没有构成R11→R12 delta，也没有实际往返记录。
