# V5 P0 前端源码装配底座

独立分支：dev/p0-frontend-integration-20261012。从干净原始提交2489ea1e04a26a9e2f318f498ac3f5f8c970fe48继承，保留原README。完整逐路径donor、固定commit、Git blob及bytes见[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)。

## 源码范围

frontend/有130件原字节源码、构建配置、锁文件及保留测试。参考134路径中4件含个人机器路径的旧测试未复制（清单见下）。底座由e9固定canonical源、6da已发表overlay、834原依赖及两份新安全源提交机械映射而成，没有编写/修改产品逻辑。

7件补充取3e64e816a84b22dc5f0f4640766fb5b0d06ed8e1；app_shell/types.ts与useAppShell.ts取41afab656086d51c68572322bff7716f9e5ac815的现时原字节，未倒退为旧canonical版。其余文件保留明确固定来源，不能据此宣称整树等同当前Mac全部工作文件。

## 构建入口与验证边界

在frontend/：
- npm run build：vite build。
- 产品源码类型检查：vue-tsc --noEmit -p tsconfig.cloud-product.json。
- npm run typecheck：默认vue-tsc --noEmit，会包含保留测试。
- npm test：vitest run；部分原测试依赖未复制的本机fixture，不能假造补齐或承诺全套通过。

三HTML入口已具备：index.html、daily-research-command/index.html、manager-selection/index.html；各脚本和挂载节点与main一致。仅做相对import路径存在性及原字节身份核对。package-lock原字节保留，构建配置依赖vitest/config，需沿已有完整开发依赖；publisher没有安装依赖。

**NOT_RUN**：本次没有build、typecheck、test、启动服务或部署。下步交现有Mac在独立候选目录构建实测，再由原P0 Chat接入UI。材料文件数不代表功能验收。

## 未复制的4件原测试

- frontend/src/api/managerWorkspace.announcementReview.spec.ts
- frontend/src/manager-selection/__tests__/workspaceAfterReadback.spec.ts
- frontend/src/manager-selection/catalystObservationPanel.runtime.spec.ts
- frontend/src/views/ManagerSelectionView.spec.ts

未修改这些原测试、未传入其私人路径值，也没有用同内容改路径替代。原source/long-running上传分支、P0 Chat开发分支、main和V4均未改变。
