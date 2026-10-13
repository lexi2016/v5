# M06 generated result preview — composed deployment

Status: **DEPLOYED_HTTP_AND_DOM_VERIFIED_VISUAL_UNAVAILABLE**. Preview remains on loopback port 54780.

Actual composed product, not the whole P0 branch HEAD:
- Backend: `287de959ac160f6ae2792ca1f9684b4c86750012` unchanged.
- Frontend base and all other existing product files: `287de959ac160f6ae2792ca1f9684b4c86750012`.
- Only `frontend/src/components/HkPreselectionPool.vue` is overlaid from `0332c6b36157fe703c99fc1e1fc2c0e1f1b57a78`; the two new tests are also taken from that commit.
- Generation product provenance: `4e05bd422d1f6bdedb7bff8b2faf5218fac9e58a`. This backend version was not deployed by this UI task.
- Fixed result publication: `d6726881b5c4fc29c2753d45283968ea69bbb48f212d0bc8879efd233577580b`.

Three-file code/test closure SHA256: `8d5757dba7ce5b1fbdcfd37cfbe0731cff561413467ab805e43d431a014f54a8`. File hashes are in closure.json. Direct comparison with the retained live base confirmed the component is the only changed existing product source file.

## Checks and deployment

Only the new Node text checks (2 PASS), new Vue spec (5 PASS) and necessary build ran; all exit 0. Commands and UTC times are in checks.json. No old test suites, model generation, pool reuse execution or natural scheduler ran. Initial tool transport failed before starting checks; those checks then ran once successfully.

The initial deployment harness queried M17 without required date/run parameters and stopped before any service change. It was corrected to compare the existing explicit M17 run/date, then the single deployment completed at UTC 02:17:19.896359–02:17:23.142474.

A new isolated source API (PID 55204, port 65413) serves the unchanged 287de959 backend with only the prepared M06 binding changed. The old API at 64303, old configuration and old dist remain intact. Preview PID 40161 was checked by listener, command, cwd and served old index before it alone was stopped. New preview PID 55214 serves the composed dist on 54780 and proxies M06/source routes to 65413. Manager proxy remains 63668.

The deployed GET returned the entire exact committed reference and all 100 original artifact rows. M08/M09/M10/status responses remained equal, M17 retained its exact saved run semantics, and M18 run `46596b03c2ab4e29b1219fd2e5eb698f` retained its descriptor. Protected V4, manager and other preview listener PIDs were unchanged.

All 19 deployed static files were fetched and byte-compared with the new local dist. dist-manifest.json uses sorted compact JSON plus one newline; its SHA256 is `a40b3b982ecc5cd9d8786e03f18bb681d82536c8626058da249989ff2caa3c12`. deployment.json also records the deterministic local dist ZIP hash and size; no private configs, model or input data are included in that archive or this feedback.

## DOM versus visual evidence

One Mac Chrome capability attempt returned `Transport closed`. It was not retried. **No browser screenshot or visual acceptance is claimed.**

The exact fixed Vue SFC was rendered in jsdom against the real deployed HTTP endpoint. Two actual reads confirmed all 100 rows and rendered fields in original order, the new publication identity, FROZEN_MODEL_PRODUCER / producer-verified text, reader-no-reverification text, and retained formal/PIT/natural boundaries. Refresh cleared rows and the previous producer claim before restoring the same result. The separately fetched dist bytes match the build. This establishes HTTP and DOM behavior, not Chrome layout/visual rendering.

After DOM access, all **149 protected files** still matched pre-deployment SHA256/size/mtime. The generated P0 UUID `4c8295528ca7450daf2dc48b014f0af5` and M06 UUID `1112ecbd4b95467799eaee153520f2f0` each retain exactly one SUCCEEDED attempt and unchanged ledger hashes. No owner/generator/provider action was invoked; serving used the fixed original read-only projection and saved-reference readers. Runtime model-call profiling was not attached to the API server, so this does not invent a new profiler count.

## Rollback and limitations

Old source API/config/build remain available. A task-local rollback script verifies the current preview identity, then restores 287de959 frontend with source origin 64303 on the same 54780 port; it was prepared but not executed. The new result and both ledgers are retained regardless of preview binding.

The previous generation's one unidentified blocked external process/shell attempt remains an explicit evidence limitation. This deployment does not resolve it. Model generation success does not establish natural scheduling, PIT correctness, formal eligibility, trading readiness or overall 18-module/P0–P5 acceptance. No V4/M18 product change, acquisition, trade or natural-scheduler enablement occurred.
