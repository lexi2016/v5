# M01 R15 独立短审：可做部分隔离测试，默认生产入口仍未实现

审查仅取件、ZIP/摘要/patch字节、AST及原依赖源码对照，未import或运行候选/测试，未修改产品。

## 冻结原件

- 原回复：https://chatgpt.com/c/6aca4d01-136c-83ec-83fd-2cac19e42e50?messageId=3b6981b2-1481-408a-a896-1540999f1498
- Library：libfile_b9019be8f44c819191e0304dfd3a0e27。
- ZIP：/workspace/shared/m01_r15_static_review/downloads/V5_M01_A_SOURCE_R15_CANDIDATE.zip，7476 bytes。
- 实算ZIP SHA256：9e5856d74483da8a2365d97841c6f954295675ded93169e4a6e6c6dd780b6c96。
- a_source_daily.py：6480 bytes，SHA256 b234e625179fddd9debe03fd71de55dd85ebe109d74cb2feb3ca3c569616570c。
- ZIP CRC、源码AST、正向两个hunk与after字节一致。清单已排除自身，五条摘要全部正确。

## 相对R14真正进展

1. bounded_reader:124–137确实新增，两roots入口:139–149确实都传入该封装。create初始pointer及verify_binding_bytes:109磁盘generation_path因此走同一source限制；初始no_symlinks后、reader前判断p.is_relative_to(source)，reader后判断q.is_relative_to(source)。方向正确，不能再说source完全未使用。
2. validate_date、identity、binding_relative、三核心、_make_context均与R14 AST相同；parse_binding除schema升r15外AST相同。六组parser、gid/path/duplicate、精确relative先于reader、全投影比较、expected=current、窄FileNotFound、require_absent及锁内读回全部保留。project把Path→str转换移出validate_path，后者现在只接受原生str。

## 确定缺项，不应写成NOT_RUN

1. 默认生产入口仍未实现：139–146现在要求SafeRoot/reader/no_symlinks/shadow_root/FORMULA_GENERATION_POINTER_NAME五个必填安全外参，比R14多一个。模块全部imports只有标准库。仅业务参数调用必缺参；测试seam不能替代固定原实现的生产路径。
2. 原始词法及上下文不完整：114–122未改变；roots直接Path(...)，没有原始str/Path类型、NUL/反斜线完整检查，没有source.is_dir()。create在构建context后才由core验证日期，未符合先日期再root合同。
3. bounded_reader:126直接Path(pointer)，未做完整原始词法验证；128–129目录追加常量后未再no_symlinks；133–135返回值仅Path(...)后词法包含判断，未执行规范/祖先检查。后续project可拒绝含..或反斜线的返回str，但不能替代读前完整guard。真实reader本身217会拒绝pointer及祖先symlink、257返回resolve()后的path，所以不能把缺少包装层复核直接宣称已证实实际越界读取；目前尤其不能因允许外传任意reader/constant而宣称生产边界完整。

## 可测范围及最小后续

- 可立刻测R15 parser/core，以及显式注入真实原依赖的双roots/bounded-reader路径；NOT_RUN只适用于这些已存在实现。
- harness正控先采用r15 schema；三核心签名仍safe_root首参，避免旧private_root关键字造成假失败。保留R14已正确的诊断适配。
- 默认只传业务参数的入口单独判NOT_IMPLEMENTED，不能用显式注入成功替代默认生产验收。guard负例核reader/lock/write调用次序及旧bytes，不使用任意异常就算通过。
- 原Chat最小修复：内部导入原SafeRoot、read_formula_generation、原常量及composition两函数，提供无安全必填外参的生产双入口；补原始词法/source目录与追加文件、返回路径复核；保留本轮已核parser/core，不重新缩写改写。

## 交付包装仍有缺口

包内仅两个日期tests，无新增入口正控、越source/祖先symlink/旧bytes负测。runtime.patch与reverse.patch仍逐字相同、都是从/dev/null新增；既非R14→R15增量，也非独立逆补丁。REPORT仅一行，无部署/回滚命令及前后源码SHA说明。清单自指已真修，不与以上问题混淆。

静态证据：/workspace/shared/m01_r15_static_review/STATIC_CHECK_RESULTS.json；最小文本差分：同目录R14_TO_R15.diff。
