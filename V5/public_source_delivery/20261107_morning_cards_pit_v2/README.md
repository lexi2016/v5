# Morning card point-in-time correction: public component delta

This supersedes the API/view PIT behavior in the earlier public morning-source-
card batch; that historical batch is preserved. It is not a live deployment.
Only two revised source components, synthetic tests and provenance are included.
No source text, original card, real rank/stock data, original notice/timestamp,
private binding/path, database, credential or runtime receipt is distributed.

Both original revised components require ranking_provenance.source == G4,
historical_PIT strictly false, and source_admission strictly false. Missing or
changed flags reject the record. Numeric zero is NOT a substitute for false.
The view explicitly states: 事后复盘，非盘前已知 (post-hoc review, not preopen-known).
This label does not prove source authenticity, identity or temporal eligibility;
flags authorize no source admission. Original-source metadata must still be
verified by the original upstream workflow.

Private exact-record/source dates and pins remain unset; API fails closed.
Default view loader refuses without network access and the absent exact-date
binding rejects even caller-supplied results. Original date/scope/hash/size and
resource-callback/bounded-local-lock mechanisms remain. Do not bypass these
bindings for production. Restoring real inputs needs separate review and tests.

Reproduce with Python 3.11+ Linux and existing Node, standard libraries only:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest -v
    node --test pit-view.test.mjs

Four Python tests (including strict-flag subcases) and three fake-DOM tests use
only synthetic input. Temporary test-only bindings exercise the PIT gate; they
are not production registration interfaces. The JS test imports a synthetic
in-memory date-bound copy; the exported file itself stays unbound and unchanged.
No browser or real source has been tested in this public package.

Shared production locks, resource limits and source/timing review remain the
original orchestrator's responsibilities. Local component locking does not
replace them. No owner, scheduler, collector, send/upload, trade, or service
cutover is introduced. Identity/facts, browser, live wiring, business completion
and natural triggers remain NOT VERIFIED. Preserve V4 and historical evidence.
