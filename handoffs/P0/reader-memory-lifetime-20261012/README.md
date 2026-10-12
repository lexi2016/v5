# M18 owned encoded-buffer lifetime repair

This is a narrow backend candidate for the real b2a gaps HTTP409. Frontend files,
API schemas, profile/identity validation, global budgets and existing disk
artifacts are unchanged. It is not yet a claim that the real Mac gaps request
or the complete V5 business flow has passed.

## Confirmed failure and ownership cause

The real no-trace independent-service report at
`7f89dd428fd2fbe7c5ee68776cc1f58ca4aa6fc1` identified
`M18_V2_RESOURCE_PEAK_RSS_BYTES` at `Reader.__init__ -> parse -> checkpoint`.
Its peak was 542,490,624 bytes against the unchanged 536,870,912-byte limit,
after successful descriptor, overview and summary requests. This was the
product's independent API, not an in-process oracle and not a Vue failure.

`_m18_disk_reader` exclusively owns a temporary Bundle loaded from disk.
The Reader's local bundle/get references retained all encoded content objects
while allocating and validating the full JSON DOM. These encoded objects were
already completely verified and copied into the assembly buffer. The retained
objects therefore added a large unnecessary concurrently-live representation
at precisely the failing parse stage. No permanent Reader-reference leak has
been established; this repair reduces peak live ownership and allocation churn.

## Minimal change

- `Reader(..., consume_content=False)` keeps its default reusable caller-owned
  Bundle behavior unchanged.
- Only `_m18_disk_reader` passes `consume_content=True` for its private temporary
  Bundle. After **all** content chunks pass original object hash, identity,
  descriptor, size, chunk hash and order checks and are copied into assembly,
  it releases the verified encoded content objects together, before full JSON
  parsing. Index objects remain available for the original index validation.
- The opt-in destructively consumes the in-memory Bundle; a later validation
  failure can also leave it consumed. It must not be used with a shared Bundle.
- Full-response hash, JSON validation, response/section/index checks and all
  counters still execute. Every GET still opens and verifies the saved files.
  No disk writes, publication, cache, new worker pool, Guard reset, global
  budget increase or suppression of a resource failure is introduced.

The complete tree inherits the previous frontend and all later feedback.
Runtime remains `python -m v5_shadow.module_api`; config and frontend commands
remain those in `handoffs/P0/saved-result-page-20261012/README.md`.

## Actual cloud verification

Existing Python3.12.14/pytest9.1.1, Linux; no dependencies installed.
The ownership test was run RED before the new option existed. Final product
regression command:

```sh
PYTHONPATH=V5/src:V5/tests "$PYTHON" -m pytest -q \
  V5/tests/test_m18_v2_reader_lifetime.py \
  V5/tests/test_m18_v2_semantic_pages.py \
  V5/tests/test_m18_v2_disk_pages.py \
  V5/tests/test_m18_v2_module_api_binding.py \
  V5/tests/test_m18_v2_http_bridge.py \
  V5/tests/test_m18_v2_publication_bridge.py \
  V5/tests/test_module_api.py V5/tests/test_module_artifacts.py \
  V5/tests/test_m18_offline_v2.py
```

Result: **75 passed, 55 subtests passed**, exit0 (53.52s). The tightened final
ownership assertion additionally passed **3 tests, 3 subtests**: content remains
owned throughout chunk parsing and is absent before the response DOM parse;
index objects remain; default behavior/counts/pages are identical; tampered,
missing and extra objects still reject. Existing disk mutation, binding,
HTTP, publication/CAS and synthetic frontend-client regressions are included.

### Large repeated-request measurement

The real generated synthetic corpus has a 28,647,597-byte response,
37,913,404-byte saved input, 1,103,793 response lexical nodes and a 38,940,915-byte
stored generation. The original fixed budgets are used without mocking RSS,
CPU, time, Reader output or validation. Fixture preparation is separate from
GET, and the API is a separate OS process with no oracle retained in it.

In one service lifetime, ten sequential requests read overview, summary, gaps,
gaps next page, materials, empty, summary, gaps, materials and overview.
All ten returned200 and bundle/publication hashes+mtimes remained unchanged.
The request sequences exceed90 seconds in total while each request creates its
own original Guard; this is not a cached Reader with a reset timer.

- Original b2a peak: **208,236,544 bytes**.
- Final batch-release candidate peak: **175,996,928 bytes**.
- Reduction: **32,239,616 bytes**, about15.5%; final peak stayed stable across
  repeated requests. This is measured Linux synthetic evidence, not a promise
  of the exact Darwin/real-data peak.

Two intermediate probes were rejected rather than shipped: interleaved
per-chunk release rose to276,320,256 bytes on repeated calls; putting that probe
in a fixed reader thread reached232,955,904. The candidate includes neither
behavior. Full measured request counters are in `RESOURCE_EVIDENCE.json`.

Reproduction uses the committed synthetic-only helper:

```sh
PYTHONPATH=V5/src:V5/tests "$PYTHON" V5/tests/m18_semantic_memory_probe.py \
  prepare "$NEW_SYNTHETIC_ROOT"
PYTHONPATH=V5/src "$PYTHON" V5/tests/m18_semantic_memory_probe.py \
  sequence "$NEW_SYNTHETIC_ROOT" "$PWD/V5/src"
```

`NEW_SYNTHETIC_ROOT` must not already exist. A baseline comparison can point
sequence's last argument at a separate complete b2a checkout's `V5/src`.
No production input or fixture is required or uploaded.

## One focused Mac acceptance still required

Start a **fresh** independent API process from this fixed complete candidate,
using the retained saved-view local config and unchanged real artifacts.
Do not reuse a process whose high-water RSS has already exceeded the budget.
Repeat descriptor → overview → summary → gaps page0 → gaps page1 → materials
and the original small status/empty sections, then repeat the read sequence
and optionally existing content pages0/1. Record process peak RSS, exact
identities, same source bytes/counts/cursors, and before/after artifact hashes
and mtimes. Do not lift limits or swallow a failure.

Mac's b2a Node12/Vue1/product typecheck/build pass remains applicable only to
its unchanged frontend source. No frontend files change here, so this repair
does not require repeating the full frontend build. Real gaps acceptance,
Darwin repeated-request resource evidence and browser acceptance for this
candidate are **NOT_RUN here**. The repository-wide suite was not run; the
cloud environment does not provide the full Python3.14/pyarrow runtime.
