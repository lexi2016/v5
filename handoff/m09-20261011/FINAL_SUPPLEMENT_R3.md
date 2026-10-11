# M09 R3 本轮最终增补

R3为本轮唯一最终提交附件。R2包完整保留，不再作为本轮发送版本；原52份源码、原Mac输入包都不改变字节或版本。

新增 `M09_A_PANEL_STOCK_MENTIONS_SUPPLEMENT_20261011.zip`：14163字节，6成员；SHA-256 `482cd87266a1ea36cd9c045cffac2432229791b79b843dfc8a600baa15e730ba`。云端独立核CRC、5项manifest及3份来源源码SHA全部通过；ReviewView与review.ts两份重叠文件和主Mac包逐字节一致，活动release仍为hk-dated-name-20261011-r2。

现已补齐：

- `apps/web/src/views/ReviewView.vue`：3441字节，SHA `cb1f4f19d9b8100d0caf86a5563990a90b627fdb72699b9ccbe499b1e9542c71`
- `apps/web/src/components/review/AshareReviewPanel.vue`：25639字节，SHA `f9deaf8d15a3273d3237458b083b847a72f6dcda86824d37731103c13d6672bf`
- `apps/web/src/contracts/review.ts`：10012字节，SHA `079adf7971e346a8da5d40c49bc3c1fdfb2307aaf6ed70df5ed4d9312699c507`

A面板仅直接import外部Vue computed和上述内部类型，无直接内部子组件，类型文件无内部import。原页读面从 `current.market_reviews.A` 传入，面板消费 `model_review.market_summary`、`model_review.board_rows`、`model_review.anchor_role_rows`、情景/观察池/close_chain/质量缺口等。这里是源文件/依赖存在证明，不是已经浏览器运行或渲染验收。其他市场组件不用为本次M09补件递归收集。

正确的 `close_review_sources/20261009/bilibili/transcript_stockdict/stock_mentions.json` 已于Mac逐一检查：V3.5 producer root及V4 API root均不存在。两个状态均MISSING，SHA与available_at均null，不能捏造值。检查时间仅是取件时间。该补件修正R2较浅路径的查询范围；并未把视频输入升级为齐备，也没有重跑视频链。

装配：先按ASSEMBLY解原源码与主Mac输入，再把小ZIP解到一个新的supplement目录。ZIP内顶层为 `M09_SUPPLEMENT/`；核14163字节/上述SHA/CRC和其MANIFEST的5项。源码仅作活动读面参考，按相对路径查看，不直接覆盖V4或原F，也不执行任何产品脚本。

从现在起R2正文中“待补AshareReviewPanel/正确stock_mentions”的两句话只代表旧版时点，已由本R3状态替代。其他真限制完全保留：真实历史T输入存在缺值，源REBUILD_REQUIRED/PARTIAL、PIT/最终available_at未知、Mac依赖超V5声明上界，API/producer根不一致、V5 M09发布配置未建立、GitHub新私库固定身份待建。它们不能成为倒要输出或停止整个编码的理由；按任务书完成候选并精确分层验证。
