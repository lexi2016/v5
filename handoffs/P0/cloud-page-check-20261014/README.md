# Cloud page check: HTTP / component DOM passed, real browser blocked

Runtime source fixed at `afddbdf75b86f3669b9329e1bffdd77c03bb3c7c` on
`dev/v5-main-integration-20261012`. This increment adds opt-in checks and receipts;
it changes no production frontend, API, algorithm, dependency or live configuration.

## Actual browser capability

The environment has Chromium `151.0.7922.173` and Playwright. An actual launch with
`chromiumSandbox: true` failed before any page could load. The installed
`/usr/lib/chromium/chrome-sandbox` has owner `nobody`, mode `4755`; Chromium rejects
that configuration. A read-only capability probe also reported
`unshare: cannot open /proc/self/uid_map: Read-only file system`.
The complete launch failure is in `evidence/browser-capability.txt`.

No permissions, helper ownership, user namespace settings or sandbox policy were
changed. No `--no-sandbox` fallback was used. The available tool catalog exposed no
separate browser/computer connector. Browser screenshots, browser console,
browser navigation, layout and visual acceptance are **NOT_RUN**, not passed.
A platform environment with a functioning browser sandbox is still required for
that acceptance. The `.dom.html` files below are serialized jsdom component DOM,
explicitly labelled **not screenshots**; they contain no browser-rendered pixels.

## Independent preview and input provenance

The active preview addresses apply only inside this current cloud environment:

- UI: `http://127.0.0.1:4177/`
- M04 new sample: `http://127.0.0.1:4177/?view=research&date=20261014`
- M04 old sample: `http://127.0.0.1:4177/?view=research&date=20200102`
- Source API: `127.0.0.1:4191`; manager read API: `127.0.0.1:4192`.

These are not externally published URLs and will not reach this preview from a
user's own computer via its localhost. No tunnel or live deployment was created.
The preview HTML alone has an injected banner: **SYNTHETIC 合成样例 · 非真实行情／非生产结果／非 Mac 验收**.
Production HTML and source remain unchanged. `fixture-info.json` records the exact
M17 date/run to enter in its visible form; it is a newly generated synthetic run.

M04 uses the fixed package's existing `tests/test_multi_binding.py` synthetic
fixtures, with RELEASE SHA256
`2bafef714a5d35352d54ff8a4d2dde0898fb1fb2ce48e71b3a0eafc4108828de`.
The fixture's provider is a local synthetic executable, not a real collector;
its existing mocked capture-window clock is recorded. Old and new archives are
copied into private marked preview roots and read through the unchanged original
reader. Original-v1 unknown timestamps/run remain unknown.

M17 uses `V5/tests/test_daily_close_recapture_owner.py::fixture` and the original
producer, then reads its saved artifacts through the actual read-only API.
`execution_kind=SIMULATED`, `natural_verified=false` remain visible. M18 uses the
original offline bundle builder and reader with synthetic fixture bytes, published
only into this task's private preview directory. It does not run the real manager
algorithm or prove a business result.

## Results, with layers kept separate

| Layer | Actual result | Limit |
|---|---|---|
| Real HTTP through Vite loopback proxy | 17 request checks passed | Not browser interaction |
| Built JS/CSS assets | 18 assets HTTP 200, exact bytes matched build output | Not browser execution of those assets |
| Vue components under jsdom with real HTTP | 3 scenarios passed | Not rendered layout, screenshots or actual navigation |
| Saved source files | 42 SHA256 and mtime values unchanged after HTTP and DOM; independently rechecked | Synthetic preview roots only |
| Real Chromium | Launch blocked | Page load / screenshots / browser console NOT_RUN |

The scenarios verify:

- Manager sections and source disclosure open under component events; materials
  page 1 and page 2 retain exact run, generation, manifest and identity. Pages
  1–64 of 70 are covered; the final 6 entries are not claimed tested here. A wrong
  run returns `503 CANNOT_CONFIRM` and clears old rows. The research link's href is
  checked; actual browser following of that link is not claimed.
- M04 list and full original body; exact new → old → missing date changes;
  missing date does not fall back. Explicit latest shows the actual source date
  and its difference from the selected date. Old source evidence remains UNKNOWN.
- M17 starts unconfirmed for its unmatched default reference, accepts the exact
  synthetic date/run entered in the form, shows all 100 original rows and
  SIMULATED identity, then clears both table and loaded identity on a wrong run.
  Wrong date, missing query and non-GET refusal are also checked over HTTP.

DOM transport recorded **20 requests: 14×200, 3×409, 3×503**. The 409s are unmatched
M17 references; two 503s are the unconfigured source status and wrong manager run.
One M04 request returned 503 during concurrent checks, then the same exact URL
returned 200 through the existing bounded retry. Its response reason body was not
captured, so shared-reader contention is only an inference, not a verified cause.
This is not a zero-request-error result. Component console errors were empty;
the real browser console was never reached. Raw request evidence is retained.

## Remaining real-input and browser gaps

No lawful original old-18/new-8 M04 archive copy exists in the independent cloud
checkout. The fixed old sample requires these exact files (pins are unchanged in
`V5/src/v5_shadow/m04_readonly.py`):

- `manifest.json` — `b3018c40ba6ffb88f1eec00a48448b5f3414fd55f067fb39a7518febb012fb52`
- `research/archives/20261012.json` — `3fdf8ce89eefc4e6c39b03201e56dd3a4aaaefca125c5b3ae787228fa7bb21af`
- `receipts/research/archives/20261012.json` — `8b62a83a0dcc85879734af21a309a7e464ff0cbabbad6e68271b4d11a9766ecd`

The new real sample additionally needs its original complete archive binding and
pinned members. The real M17 state/universe/ledger binding and exact saved product
are likewise absent; the synthetic reference is not a replacement for that
evidence. No new acquisition was attempted. Prior Mac 54 PASS and old18/new8
receipts remain historical only; see the previous cloud-isolation handoff.

No browser acceptance is claimed until the platform supplies a working sandboxed
browser. No Mac/Windows, V4, credentials, security configuration, live deployment
or trading action was involved. V4 remained at
`615d1ce5417ed65ca2c8b736435c5d4596b79b19` with clean status.

## Reproduction

`scripts/prepare_m04.py` takes the fixed M04 package root and a **new empty** preview
directory, using its approved capture fixture interpreter. `scripts/prepare_api.py`
takes the V5 checkout and that directory, using the locked P0 interpreter.
Start the original `V5/src/v5_shadow/module_process.py` with the generated
`source-config.json` and `manager-config.json` on loopback ports 4191 and 4192.
Build frontend assets and serve with the existing Vite preview proxy environment
`V5_SOURCE_API_ORIGIN=http://127.0.0.1:4191` and
`V5_MODULE_API_ORIGIN=http://127.0.0.1:4192`, on loopback port 4177.
Apply the synthetic banner to the copied preview output only.

Run `scripts/check_http.py <preview-directory> <evidence-directory>` with the
locked P0 Python. For the optional DOM checks from `frontend/`:

```sh
V5_PAGE_CHECK_FIXTURE=/absolute/preview/fixture-info.json \
V5_PAGE_CHECK_ORIGIN=http://127.0.0.1:4177 \
V5_PAGE_CHECK_EVIDENCE=/absolute/evidence \
  ./node_modules/.bin/vitest run tests/cloud-page-check.spec.ts
```

The test is skipped by default without these explicit environment variables.
`FILES.json` hashes complete scripts, test and evidence. Evidence preparation is
not counted as production code completion or full browser acceptance.
