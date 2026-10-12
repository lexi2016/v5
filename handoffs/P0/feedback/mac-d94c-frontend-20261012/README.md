# Mac isolated frontend build — d94cfc

Fixed candidate: `d94cfc86111dc33a76e651e15fb6668dcefa849c`.
Branch: `dev/p0-frontend-integration-20261012`.

## Result: product typecheck PASS, Vite build PASS

Read candidate START_HERE.md and SOURCE_MANIFEST.json first. Materialized all 133 tracked files in a new task-only directory: 130 frontend source/config/lock/retained-test files plus two notes and inherited README. 129 source files reused only after exact Git blob matching against this candidate; four files fetched at the fixed commit. All **133/133 blobs verified before and after build**, unchanged. Four excluded private-path tests were not recovered or copied.

Existing node_modules were copied into the isolated candidate rather than shared for writes. No npm install, upgrade or registry download was needed. Checked 244 installed package versions against candidate package-lock: zero version mismatches (version check, not a fresh-install integrity attestation).
- Node v24.19.0; npm 11.17.0
- TypeScript 5.9.3; vue-tsc 3.3.8
- Vite 7.3.6; Vitest 4.1.10; Vue 3.5.40

## Actual commands / UTC times / exits

CWD=`<ISOLATED_CANDIDATE>/frontend`. NODE/NPM represent existing binaries; private absolute paths redacted. HOME/TMPDIR/npm cache directed to task evidence, update/audit/fund notices disabled.

| Executed command | UTC start → end, 2026-10-12 | Exit |
|---|---|---|
| `$NODE --version` | 04:58:34.732276 → 04:58:34.744042 | 0 |
| `$NPM --version` | 04:58:34.744302 → 04:58:34.822183 | 0 |
| `$NODE node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.cloud-product.json` | 04:58:34.822509 → 04:58:36.485557 | **0** |
| `$NPM run build` (package script: vite build) | 04:58:36.485893 → 04:58:38.562297 | **0** |

Product typecheck stdout/stderr empty. Build stderr empty; Vite reported 120 modules transformed and built in 822ms. No failures or warnings observed in these commands.

## Local build artifacts

11 files generated (three HTML, five JS, three CSS). Referenced /assets files exist in dist. HTML entry identities:

| Relative path | Bytes | Title | SHA256 |
|---|---:|---|---|
| dist/index.html | 836 | V3.5 | 1bd1b74f21ff3469aab3c8dd13284e45752604ad0c8e5f6c2f3829a086a5e199 |
| dist/daily-research-command/index.html | 504 | V5 云端隔离预览 | b068de1d29bb04f861c31c67064071fc6f5b914b0d39ab7a6a070df3f9d7b751 |
| dist/manager-selection/index.html | 579 | 经理选股工作台 · V4 | 1fdd8b71a5f5a96a7abfda18dfc80c2cb7657de343993bbee64338a92c65a5d7 |

The complete relative artifact SHA256 list remains in local build-artifacts.json. Generated bundles were not uploaded or deployed. Existing V3.5/V4 titles are preserved and demonstrate this is a buildable source base, **not a completed new V5 main UI**.

## Scope / next handoff

PASS applies only to the product configuration typecheck and production bundle generation for this fixed source identity. Default npm run typecheck (includes retained tests), npm test/Vitest, browser behavior, APIs/business results, service startup, live deployment and full 18-module/P0–P5 acceptance are **NOT_RUN**. No old private tests/fixtures were invented or restored. This is not an all-tests-passed claim.

No source edits, frontend work-root writes, main changes, V4 port changes, service startup or deployment. Build/cache outputs confined to the new isolation directory. The source base can now be handed to the original P0 author for actual V5 main-entry integration; that integration remains unverified.

This minimal sanitized execution receipt is appended to this independent frontend branch using fresh HEAD/base plus expected-SHA CAS, preserving concurrent changes.
