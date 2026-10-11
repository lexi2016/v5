# M09 同版小补件

增补主包 libfile_aa3fb8314fd88191aaa9dac51e058111。活动版本 hk-dated-name-20261011-r2，T=20261009。

ReviewView.vue 通过 ../components/review/AshareReviewPanel.vue 导入A股面板，传入 current.market_reviews.A。面板只依赖外部Vue computed及内部 ../../contracts/review 类型，无直接内部子组件；类型文件无内部import。3个源文件均原字节保留，路径和SHA见SOURCE_SUMMARY.json。ReviewView仅用于进口/prop来源证明，不递归带入其余市场面板。

在已核V3.5和V4两个data_root精确检查 close_review_sources/20261009/bilibili/transcript_stockdict/stock_mentions.json，均不存在。该正确路径补查更正了前包少一层目录的检查范围；不能宣称视频数据已齐。无available_at可提供，未以mtime代替。未重复current_asr_pointer检查。

本包仅输入补取，不运行业务、测试、部署，不修改任何产品或权限。
