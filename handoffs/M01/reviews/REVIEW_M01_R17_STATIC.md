# M01 R17 实物静态核验

2026-10-11 11:43 UTC，仅下载/清单/CRC/SHA/静态差分，未运行候选或测试。

- user ecb0beb5-1353-4dea-867e-0575d2c9a1c2：11:41:45.195Z
- assistant 43897d3f-41c1-4fc2-aa47-fe6a04899c23：11:42:00.611002Z–11:42:06.384061Z
- ZIP6753B，6文件，CRC通过；SHA91c79646be97c97d6a4b55430fe40e211ae8cd2708ed43ab762f6bacd5e37e05
- Library libfile_b9941035d840819193dba097ed60e0ab

结论：不接受、不投入Mac运行。已保留R15_vs_R17.diff。按父要求暂停M01，不反复催。

恢复：project、create_binding、锁内require_absent、最终读回/expected比较、FIELDS/对象字段检查及真实NUL判断。SHA清单正确排除自身，5项均核合。

新旧阻断：

1. 整个bounded_reader删除；create入口91–97使用裸reader；source只用于93–94重叠检查，不限制generation_pointer或返回path。
2. read入口99–103仅no_symlinks(source)、shadow_root(private)、SafeRoot，未检查marker、source/private重叠，随后用裸reader。source没有参与读取路径准入。
3. 两公开入口仍必传SafeRoot/reader/no_symlinks/shadow_root/pointer_name，pointer_name未使用，全部imports仍标准库，无真实默认依赖装配。
4. project36–44和parse_binding52–69都没有generation_id字符串/64hex校验；project41对任何返回path先str，丢失原始类型拒绝。
5. schema40/64改为r17，违反保留R15 schema/身份要求。
6. 根与pointer完整原始类型/词法、source已存在目录、目录追加pointer后的symlink/containment、reader返回path祖先检查仍无。
7. 源码4951B/103行；测试232B仍只有两个日期。REPORT92B仅NOT_RUN，没有实际执行日志。
8. runtime.patch与reverse.patch完全同字节，各5684B；均new file /dev/null，仍非R15→R17真实增量与独立逆向patch。清单哈希自洽不能弥补补丁方向错误。

完整原Chat：https://chatgpt.com/c/6aca4d01-136c-83ec-83fd-2cac19e42e50?messageId=43897d3f-41c1-4fc2-aa47-fe6a04899c23

