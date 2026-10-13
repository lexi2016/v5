# M04 Mac 测试窄修前后原回执

本目录从 Mac 普通消息 msg_0b47eb1b0178a3a6016ace538c4dd087d1bc1d2617613246f1 精确提取两段 JSON，各保留末尾一个换行；转存者未重跑测试。
- prior-failure.json：6,279 bytes，SHA-256 af64331774c519de4677ac9f530e32ab358086e1c0261582c0d87f3904f5fee0。
- success.json：6,032 bytes，SHA-256 241f61bf310d48974c80dff90fab5646631725aa9f4b8d0018a3e3cc69ab2928。

原9736bf2e807b2aa22e2541a4375b182e1ddceb24：8 PASS / 2 FAIL / 11 ERROR；测试生成的shebang直接使用含空格sys.executable，合成CLI无法启动，相关下游断言未达到。失败历史不删除。

固定8266c6ed9606b0912328670c7411743a85af5727：Mac22/22 PASS、0 FAIL/ERROR/SKIP，exit0；482 Git blob/481 manifest、测试后清单一致。仅测试夹具、report、log、RELEASE四文件变化，业务与原owner字节不变。

Python3.14.6满足最低版本，但既有pandas3.0.5和pyarrow25.0.1超声明上限；完整锁依赖NOT_RUN，未安装或放宽依赖。旧18篇/原scope suite未重跑，真实provider/network、原生页面/部署及自然未验，不计全模块完成。

原stderr 38,555 bytes（SHA-256 e56a17f1a2cbcec499cb083e17c97f42d5c64b69c6360a5fd45d4f4c1ace5dbf）仍保留于Mac，未完整回传，未上传本目录。本件不声称包含完整stderr。

研报候选已在P0 d3c52b4f08cbe6af9f69326461109004ac36c95c精确绑定新M04版本；真实归档/DOM/发布正在另行验收，结果未到，不在本件宣称通过。
