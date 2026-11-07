# Shared Par / SQLite metadata components: public-safe V11.4 source export

This is a partial component source export, not a standalone workbench or a new
replacement panel. It shares original read-only Par projections and indexes
references; it does not duplicate raw Par history or invent missing data.
No real SQLite, Par payload, catalog-binding, INPUTS file, user result,
runtime receipt, credential, active lock or private workspace path is included.

## Components and missing bindings

- js/shared-par-store.mjs retains versioned in-flight deduplication and no stale
  fallback. Its only source change is the relative import query suffix.
- js/par-screen-data.mjs retains original validation/count/filter functions.
  The private loader is deliberately omitted and replaced with unconditional
  PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING; allowed source dates are empty.
  These validator-only functions do not grant source admission.
- js/timeline-module-view.mjs is byte-identical UI source for one independently
  mounted node view. It reads a supplied store and does not start a node job.
  It is not a complete page, and no browser render of this export was tested.
- python/database.py retains the original SQLite schema, reference tables,
  selected/pending views, immutable build and read-only summary logic. PINS is
  None. Default connect/build/summary refuse missing private binding. Explicit
  temporary test DB connections remain mode=ro, query_only and trusted_schema=off.
- python/catalog_api.py retains version validation, bounded local lock and the
  resource-gate callbacks. Private directory/binding are unset, and get refuses
  absent binding after the gate. No input-registration API or bypass is added.

The original fixed-scope/version literals in source are contract constants, not
bundled data or proof that any actual rows are present. Original selectors,
formulas, labels, source gates and qualification logic are not changed.

## Reproduce synthetic tests

Python 3.11+ Linux and existing Node (standard libraries only):

    cd python
    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest -v
    cd ../js
    node --test public.test.mjs

Seven Python tests run in each mode: missing bindings, resource refusal,
version refusal, bounded locking and a temporary synthetic SQLite schema with
read-only access. Three JS tests cover default refusal, UNKNOWN/no-buy validator
semantics, and concurrent shared reads/retry without stale fallback. The latter
copies source into a temporary directory and injects a TEST-ONLY date binding;
original export source remains unchanged. A synthetic count of 21 concurrent
consumers does NOT mean 21 business jobs executed or completed. No synthetic
fixture may substitute for real research input.

The node view source is included for preservation but not browser-verified here.
No full server, live catalog HTTP route, cutover, staging or deployment script is
shipped. Original full-suite/live-input results are not claimed for this export.

## Gates, scope and acceptance

The SQLite builder retains the original 256 MiB disk / 1 GiB MemAvailable checks,
nonblocking build lock, exact input verification and no-overwrite publication.
The catalog retains its 95-second local lock and supplied resource gate checks.
These local locks do not replace the original project's shared production lock.
Restore and enforce original source/resource/shared-lock gates through the
already authorized orchestrator before any integration. This public candidate
is NOT admitted for that integration; never lower gates to get a startup.

Original V11.4 staging was blocked by memory protection; it was not started.
That historical condition is not a fresh memory measurement. Public export
preparation does not alter it or authorize bypass. Browser verification,
production integration, actual shared database service, natural triggers and
business acceptance remain NOT VERIFIED. No claim that all 21 framework nodes
are implemented is made. Preserve V4, original Par and prior failure evidence.

PROVENANCE.json records source and candidate hashes. Private binding restoration
requires a new reviewed candidate, original source pins and real-input tests.
The public-source bundle itself requires independent review before upload.
