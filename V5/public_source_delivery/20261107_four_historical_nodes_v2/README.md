# Four historical node views: public component increment

Includes the cumulative read-only API/router and four component views:
announcement annotation, 08:50 cross-table, Hong Kong historical close reference,
and 15:00 post-close retrospective. These are not four completed business nodes.

Private dates, event symbol, annotation dates, exact CAS-event key and input
bindings are unset. API, router/default loader and each standalone view refuse
missing bindings. No real article, quote, stock row, original notice, database,
user path, credential, active lock or runtime receipt is shipped. Historical
literal date/count/symbol labels are generalized, not relabelled as current data.

Original scope, date-equality, source hash/size, strict false qualification,
PIT=false, no-buy, resource-callback and bounded local-lock checks remain.
Post-close ranking is explicitly not preopen-known or a 15:00 capture. HK
continuous close is not final CAS: actual final time remains UNKNOWN, not fixed
16:10 or a news timestamp. Annotation never rewrites the original name/risk
rules or confirms full-market announcements. Original pinned annotation executable
is intentionally not distributed; absent binding prevents dynamic import.
Restoring that closure or real input requires fresh source review and tests.

Reproduce (Python 3.11+ Linux, existing Node, standard libraries):

    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest -v
    node --test views.test.mjs

Six Python tests use temporary synthetic JSON bindings to check unbound refusal,
HK unknown-final retention/rejection, resource refusal, strict PIT/no-buy and
post-close qualification. Three Node fake-DOM tests check unbound components,
router UNKNOWN and synthetic post-close warning/qualification. Synthetic copies
are test-only; no production binding or network is activated. Dynamic announcement
code, real content correctness, browser rendering and complete view integration
are NOT tested here. This small public test set is not the original full suite.

Original shared production lock, resource thresholds and source/timing admission
remain the original authorized orchestrator's responsibility; component-local
locks do not replace them. No capture, owner, scheduler, trade, send/upload or
production cutover is added. Identity, facts, browser, live service, business
completion and natural acceptance remain NOT VERIFIED. Preserve V4 and prior
source versions. PROVENANCE records each source hash and deliberate differences.
Only manifest allowlisted files are candidates for upload; exclude caches and
private audit material. Independent review is required before submission.

## V2 binding completeness correction
All nodes now require valid, consistent record/source date bindings and complete pinned input roles before resource acquisition or input reads. HK nodes require a nonempty final-field binding and the explicitly present field; an absent field is an error, whereas an explicitly null field remains historical UNKNOWN. Announcement nodes require a nonempty symbol and valid nonempty ISO-date list before any dynamic code load. Pin descriptors require path, byte count, and SHA256. This does not grant private-source admission or production eligibility. Synthetic coverage: 11 Python tests in each mode and 3 fake-DOM tests. Earlier V1 candidate and test evidence are retained separately; no browser, production or natural acceptance.
