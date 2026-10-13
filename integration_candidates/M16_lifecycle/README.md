# M16 isolated lifecycle candidate

## Scope and attribution

Base: `lexi2016/v5`, `dev/m16-github-handoff-20261011`,
`5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a`.
Original M16 Chat: https://chatgpt.com/c/6acb9ad6-5dc8-83ec-b3bd-bd3a447de94a.
P4 scope is fixed by the 2026-10-13 execution plan at
`2a124b87bf64793f8c0226a049ae2ac9700c9b86`.

This is a standalone packaging/startup supplement, not a new job engine.
The original Chat delivered the owner/facade/factory and its source handoff.
The later `5bb1d635` loader repair already made its four-object assembly work.
This delivery adds only `integration_candidates/M16_lifecycle/` and does not
rewrite those files in their original location, P0, shared APIs/UI, other modules,
or running V4. It does not re-import the already validated historical ten rows.

## Existing owner coverage (original delivery; parser patch noted below)

Under `source/fixed-f7cb731c/handoff/v4-running-source-20261005/canonical/`:

- `v4/manager_research/service.py`: `ManagerResearchJobService.__init__`, `get`,
  `ensure`, `retry`, `job`, `cancel`, `ensure_events`, `_run_job`,
  `_run_event_refresh_job`, `_finish_active`, `close` already implement the
  executor pool, deduplication, generation fencing, bounded provider calls,
  cancellation, event-only refresh, and result publication.
- `v4/manager_research/store.py`: `ManagerResearchStore.admit_job`, `write_job`,
  `commit_result`, `read_product`, `cancel_job` own persistence and atomic commit.
- `v4/manager_research/hkex_provider.py`: `HkexOfficialProvider.collect`,
  `collect_events` retain issuer matching, source allowlists, exact cutoff,
  latest-effective-report selection, and separated event collection.
- `v4/manager_research/pdf_parser.py`: pinned private pypdf 6.10.0,
  `extract_pdf_pages`, `extract_pdf_facts`, existing budgets and evidence rules.
- `src/v5_shadow/manager_loader.py`, `manager_factory.py`, `manager_jobs.py`
  are exact copies of the original branch's verified wrappers. No second
  identity, recommendation, worker, store, or strategy implementation exists.

The full fixed source handoff is carried for integrity/provenance and the
owner's lazy imports. M13/M18/workspace routes are not exposed.

## Actual missing pieces repaired

1. `m16_runtime.py` supplies one explicitly started process/app using the existing
   factory, and an immutable-byte observation reader. The reader returns the
   original object unchanged. Its CLI SHA-256 is only file-transport integrity;
   it never invents `raw_artifact_sha256`, `input_source_sha256`, input identity,
   cutoff, source date, PIT evidence, or eligibility. Original contracts validate
   every read. Missing, changed, invalid, wrong-date, or late input fails closed.
2. `m16_router.py` is the original router's seven M16-only paths, with unrelated
   module routes excluded. The function bodies come from the fixed original
   router. Default app configuration rejects mutation; explicit producer opt-in
   is process configuration, never client data. GET never creates a service/job.
3. PDF execution exposed a real packaging gap: the handoff had vendored Python
   but no adjacent runtime dependency manifest/license. This candidate includes
   the existing branch's license byte-for-byte and a **new assembly manifest**
   calculated from the pinned vendor bytes, not a fabricated recovered original.
   The withheld original manifest and its private fields are neither read nor
   recreated. `m16_runtime.closure()` pins the new manifest hash. The unchanged
   parser verifies its vendor tree and license before parsing.

License provenance: original branch
`handoffs/M16/dependency_materials_20261013/pypdf-6.10.0-LICENSE`,
SHA-256 `a97ac230e5f33ef10a5367a850eb01f91f1a0b064e34742c7794d2294557f524`.
Vendor tree SHA-256 `871e199b87bd2d03c9de7819f76494e90876b458ae6b65a580557acf23000da6`.
New assembly manifest SHA-256 `4fa44cbe32992f70cfcec6193e052a9288c87447770694478e2d79c72e3aa210`.
Original source manifest SHA-256 remains
`c8f72f9a64cb2dd0c1f37819156e7d26ec457097d3f2bffad79f2beeebeac2ea`.

## Start with existing dependencies

Use a fresh process and the existing authorized Python with FastAPI/Uvicorn.
No package installation, service manager, daemon, scheduler, credentials, remote
backend, or V4 process is needed. Do not mix this private owner alias with another
M16 source root in the same process. Do not add the donor `v4` path to PYTHONPATH.

From the candidate directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m v5_shadow.m16_runtime \
  --runtime-root /absolute/isolated/v5/m16-runtime
```

This binds loopback `127.0.0.1:8816`. Select another free port with `--port`.
Startup initializes the private runtime directories once. Default operation is
read-only, with no observation binding; reads report CANNOT_CONFIRM instead of
inventing an empty candidate pool. It does not initiate jobs on startup or GET.

Bind an already authorized, original-contract stage observation JSON with both
`--input /absolute/observation.json --input-sha256 <exact-file-sha256>`.
Changing dates or input bytes requires a separately validated binding and process
restart; no HTTP symbol list, URL, document text, or cutoff is accepted.

Only after the operating authority and real-source scope have been verified,
`--enable-producer` allows explicit POST operations to call the original public
providers. It is not authorization to run them. No such production call was
executed for this delivery. Reads remain independent of worker execution.

The original API prefix is retained for compatibility in this independent V5
process; it does not call any V4 server:

- GET `/api/v4/manager/research?date=YYYYMMDD`
- GET `/api/v4/manager/research/status?date=YYYYMMDD`
- POST `/api/v4/manager/research/ensure?date=YYYYMMDD`
- POST `/api/v4/manager/research/retry?date=YYYYMMDD`
- POST `/api/v4/manager/research/events?date=YYYYMMDD`
- GET `/api/v4/manager/research/jobs/{job_id}?date=YYYYMMDD`
- POST `/api/v4/manager/research/jobs/{job_id}/cancel?date=YYYYMMDD`

POST bodies must be empty; cross-origin requests are rejected by the original
same-origin gate. No unrelated workspace, plan, or announcement route is exposed.
P0 integration owns any ordinary V5 route/preview mapping; none is modified here.

## Recovery and rollback

The same runtime root preserves the original jobs, products, commits and receipts.
Fresh-process GET cold-reads the committed product. A persisted RUNNING job is
not evidence of a live worker: original `JOB_OWNER_UNCONFIRMED` remains visible;
GET/ensure/retry do not steal it. Once the previous worker is known stopped,
explicitly cancel that exact job/date, then retry. Cancellation fences late writes.
Do not automatically cancel another process's active job.

A failed commit/receipt leaves the previous committed product readable while
showing FAILED. Retry creates a new generation of the same exact-input job.
Event refresh preserves financial facts and does not recollect PDFs.

For code rollback, stop this isolated candidate process and restore the previous
fixed package/configuration through the existing P0 release owner. Never replace
an imported owner in-process or make old/new writers share a runtime concurrently.
No destructive runtime cleanup or rollback of V4 is required or performed.

## Verification and honest boundaries

Executed with existing Python 3.12.14, FastAPI 0.141.1, HTTPX 0.28.1 and
Uvicorn 0.52.1. No dependencies installed. Run the complete candidate suite:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
```

31/31 PASS, exit 0. It uses the actual pinned classes, original provider/parser,
original state machine/store and in-process ASGI routes. PDF bytes, issuer list,
HTML directory and observations are explicitly SYNTHETIC OFFLINE TEST ONLY.
Network entrypoints are trapped and the suite asserts zero calls. Optional
media/news source failures are injected at their original transport ports.

Coverage includes actual PDF parsing through provider→worker→commit, same-SHA
new-process cold read, GET byte-for-byte no writes, saved/running deduplication,
retry generations, late-result cancellation, event-only refresh, failed-provider
recovery, receipt-failure preservation, cross-instance ownership/fencing,
producer default denial, invalid dates/input/SHA/symlink/body/origin, missing
input, missing financial product, parser byte budget, source URL/cutoff rejection,
original four-object origin, and CLI loopback/lifetime configuration.

Red evidence: missing entrypoint assertion; initial real-PDF run failed on absent
runtime dependency manifest (21 pass, 2 fail, 1 error); added manifest pin test
failed before the pin was added. Final 31 tests all passed after these fixes.
The old loader's 32-test/Mac evidence is retained as previous evidence, not
counted again. The old ten-row historical PARTIAL product is not new production.

Broad repository pytest is NOT_RUN: this current Python reports
`No module named pytest`. No old broader donor failures are claimed fixed.
Native socket server/browser/DOM, Mac execution, preview deployment, real PDF
collection, live provider/network, model calls, natural triggering and complete
M16 business acceptance are NOT_RUN. Real official PDFs and legal candidate/input
binding remain external evidence gaps. Formal/PIT/trading gates remain unchanged.
This is an engineering lifecycle candidate, not full module acceptance.

## Follow-on: prepare a new input from an already-saved M08 stage

`m16_prepare_stage.py` closes the missing input-export boundary. It does not
reconstruct an old manager input from product rows. Historical product input
source digests are not treated as file hashes. A new observation file and its
own byte SHA are prepared from a fully verified M08 saved stage.

The existing M08 `hk_stage_observed.py read --include-artifact` is reused
byte-for-byte, with its 58-file read-only dependency closure from M08 commit
`01f1a6347722081cbbf97b54204bf033e6d01938`. Its read-entry blob remains
`21182642efc71dda9532629597984bce8dfd8ce4`, the same as the previously deployed
observed reader. `M08_READONLY_DEPENDENCY.json` pins every dependency. No M08
producer, selector, importer, source-root modification, network or model is run.
Only the original read verification of a named committed import is invoked.

From this candidate directory, use the existing exact observed-reference JSON
(`v5.hk_stage_observed_reference.v1`) and the existing M08 recorded root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m v5_shadow.m16_prepare_stage \
  --recorded-root /absolute/existing/m08-recorded-root \
  --reference /absolute/existing/exact-m08-reference.json \
  --output-directory /absolute/new/private-m16-preparation
```

The output directory must not already exist, its parent must exist, and it must
be separate from the M08 store and source package. This command only accepts
`HK_CONNECT / STAGE_0935_0940` and the reference's original date/run. It does not
follow latest pointers, choose another date, rescan, fill missing fields, or
accept rows copied from a manager product.

The original reader first verifies import/receipt identities, exact artifact CSV,
manifest and receipt hashes, original envelope/CSV consistency, algorithm/source
identities and safety boundaries. The exporter then preserves the complete
artifact and every complete row, adding only original-contract date/status
aliases and observed-only limitations. Original ranks, source timestamps,
source status, raw-artifact digest, artifact ID, eligibility and gaps are retained.
The original M16 input contract validates the result without constructing a
manager service. Empty rows or missing/late timestamps remain blocked; there is
no fallback to product rows or reconstructed identity.

Outputs are local-only:

- `observation.json`: the new original-contract-compatible input. Its SHA-256
  is printed as `input_file_sha256`, distinct from the original
  `raw_artifact_sha256` source digest and the original CSV file SHA.
- `receipt.json`: final preparation marker, `PREPARED_NOT_RUN`, carrying the
  exact M08 reference/provenance, all three relevant SHA roles, complete row
  count, newly derived M16 contract identity and explicit false job/network/
  model flags. It makes no claim to the missing historical manager input or
  its product identity. An incomplete directory without a receipt is not ready.

Do not upload these private output files automatically. The new identity is
calculated by the original M16 contract from this new input, not supplied by the
caller. Historical/observed-only/PIT-false boundaries are retained.

For separate, authorized read-only service binding, use the printed *new file*
SHA and `observation.json` with the existing runtime entrypoint:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m v5_shadow.m16_runtime \
  --runtime-root /absolute/separate/m16-runtime \
  --input /absolute/new/private-m16-preparation/observation.json \
  --input-sha256 <printed-input_file_sha256> --port 8816
```

Leave producer disabled. This creates no manager job, and does not make the old
product magically match. Actual ensure/provider work is a separate operation.
M08 writes and P0 routing/deployment remain outside this candidate's changes.

Targeted preparation verification (12/12 PASS, exit 0, current cloud Python):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover \
  -s tests -p test_prepare_stage.py -v
```

These tests use a clearly synthetic, hand-serialized saved trio and the actual
unchanged M08 cold reader. They do not run a selector/store publisher or manager
producer. Positive tests verify full row/field preservation, three distinct SHA
roles, original M16 normalization, startup-reader compatibility, command output
and byte-for-byte source preservation. Negative tests cover wrong stage/date,
trio tampering, source-write attempts, existing-output overwrite, symlink,
dependency pin, duplicate JSON, empty stage and missing/post-cutoff timestamps.

The earlier 31 lifecycle tests and their successful Mac run remain separate
baseline evidence, not rerun or added to this round's count. Actual historical
M08 export and read-only service binding on Mac remain pending this fixed
candidate; no new business result, external PDF or production success is claimed.

## PDF layout repair on the 2e49 candidate (2026-10-13)

The candidate now patches only the packaged `pdf_parser.py` and the provider's
`PDF_FACTS_CACHE_VERSION` (1 → 2). The original source locations elsewhere in
V5/V4 are unchanged. `SOURCE_MANIFEST.json` marks these two files
`M16_CANDIDATE_PATCHED_SOURCE`, retaining donor identities under `upstream_source`;
the runtime pins the new manifest. Historical `source/PACKAGE_CHECKS.json` describes the original handoff.
`source/PACKAGE_SHA256.json` is refreshed for its original source file subset;
`CANDIDATE_MANIFEST.json` is the current complete package inventory.

- Accept anchored numeric rows with bilingual/garbled Unicode label suffixes,
  retaining the supplied glyphs verbatim. No numeric search through prose or
  reconstruction/translation of garbled Chinese is performed.
- Recognize exact `Unit: RMB` as yuan, split `first half / year of 2026` periods,
  and `HK$’000` as HKD thousands, while retaining original header excerpts.
- An extra integer is removed as a note only with an explicit Note(s) unit
  header; `fields.note_marker` records it. Wrong column counts, missing period
  or unit, and conflicting revenue/profit/cost labels fail closed.
- `This Reporting Period / Same Period of Last Year` supports an explicit nearby
  reporting year only. The actual HK.01081 page 5 fragment has no year and still
  yields no financial facts. A synthetic added-year variant is separately tested.
- Version 2 invalidates previous zero-fact parses without deleting raw materials
  or version 1 evidence. The cache regression proves recompute once and reuse.

`tests/fixtures/real_pdf_fragments.json` contains exactly four cached extraction
fragments returned by the Mac, including physical PDF page, PDF SHA-256, and
SHA-256 of each original UTF-8 text (no extra final newline). Tests verify all
four hashes and retain every garbled glyph. No PDF was downloaded or re-extracted
for this repair. Sources:

- HK.02583 page 33: https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0921/2026092100448.pdf
- HK.01081 pages 42 and 5: https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0831/2026083100586.pdf
- HK.00376 page 57: https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0924/2026092401829.pdf

The three period-bound fragments yield two financial facts each (six total),
with original amounts, 2026/2025 columns, currencies/units, page locators and
note numbers. This is offline fragment verification, not a claim that the three
whole products are READY. HK.02915 remains unconfirmed; no mapping to HK.00928
has been invented. The existing 10-row production result was not recollected.

Run all candidate tests with the existing environment:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v`
Then Mac may verify the same cached whole documents through the existing service
integration. That separate verification determines final product readiness.
