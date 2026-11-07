# Evening local delivery bundle: public-safe source

This isolated source candidate covers 18:30 local preparation, 18:50 byte
rechecking, and 19:00 local delivery-text checking. It NEVER sends, uploads,
collects, selects, trades, grants BUY eligibility, or formally freezes a next-day
list. A complete local package is not completed business delivery.

## Reproduce synthetic checks

Use Python 3.11+ on Linux, standard library only, in this directory:

    python -B -m unittest discover -v
    python -B -O -m unittest discover -v

Use discovery, not direct `python test_bundle.py`: inherited package/manifest
forgery cases occur after that file's main guard. The tests synthesize two rows
and temporary outputs; they are NOT real market/input tests. CSV injection,
counts, unchanged dates, UNKNOWN preservation, changed inputs/code, corrupted
payloads, idempotent reuse and manifest-field forgery are exercised. Candidate
and emitted package identity both change if code changes.

## Binding and source differences

The original private DATA and ADMISSION references are removed, replaced by
None. `load()` explicitly fails closed with
PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING after the existing pinned-safeio check.
No public registration/configuration interface can grant input admission.
`render()` and the remaining package integrity logic retain source behavior.
`safeio.py` and original synthetic tests are byte-identical. PROVENANCE.json
records original and exported hashes. No original data, package, receipt,
private path, runtime task identity, active lock, or credential is distributed.

The source V2 had a limited isolated integrity review. This changed public
candidate requires independent review before submission. That review cannot
make it a production worker. Private binding restoration would need a new
reviewed candidate and real-input checks, not a caller bypass or modified pins.

## Required resource and shared-lock gate

This candidate does NOT implement the project's shared production lock or
resource admission gate. Exclusive content-addressed local output creation is
NOT a substitute for the shared lock or memory/disk protections. Only the
existing authorized scheduler/orchestrator may enforce those original gates
before any production integration. This package is NOT admitted for that use;
no production scheduling, acquisition/release of shared locks, job dispatch or
resource threshold change occurs here. Never remove, override or weaken those
gates to make this candidate run.

18:30/18:50/19:00 are source-function associations, not proven scheduler events.
The code supplies no actual sending channel. NOT_SENT remains NOT_SENT.
Actual-data scope, chart review, formal freeze, live board refresh, business
acceptance and all natural-trigger acceptance remain NOT VERIFIED here.

This is an incremental source package, not replacement of V4, the original
research panel or any live V5 adapter. Keep prior source history and private
original evidence intact. Upload and remote readback are separate later stages.
