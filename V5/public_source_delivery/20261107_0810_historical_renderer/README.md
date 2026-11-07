# 08:10 historical brief renderer: source-only export

render.py is byte-identical to the reviewed historical renderer. No original
brief, article text, stock list, real input JSON, private path, receipt, database,
credential or output HTML is shipped. The public package has no default private
input binding; CLI requires an explicit input file and matching SHA256. Missing
inputs or digest mismatch refuse rendering; existing output is not overwritten.

Python 3.11+, standard library only:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest -v

Six synthetic tests cover historical/time-label preservation, HTML escaping,
refusal of business/natural/new-selection/buy flags, denominator mismatch,
missing source references, exact CLI input SHA and no overwrite/default input.
Environment variables propagate to CLI subprocess tests. Fixtures contain only
invented text, a non-stock identifier and example.invalid source URL.

This code formats already prepared source-linked historical input. SHA verifies
input bytes, not source authenticity. Source reference lookup rejects missing
references; it does not verify source content or site access. Timing statements
and original timestamps are preserved as supplied, not recomputed. There is no
cutoff/timezone validator in this renderer: the original upstream timing and
source-admission gates remain necessary. Never infer publication timezone,
backfill availability before cutoff, or treat exact-name association as identity
confirmation. Do not describe this renderer as a complete 08:10 source workflow.

The renderer does not send/upload, collect, select, train, trade, register tasks,
check shared production locks or admit resources. Original orchestrator/source/
resource/shared-lock gates must remain in force before integration. This export
is not admitted for production. Browser rendering, actual delivery, production
wiring and natural-trigger/business acceptance remain NOT VERIFIED. Existing
V4, original panel and original historical results are untouched.

PROVENANCE.json records exact source identity. Only new synthetic tests and
public documentation accompany it. Independent source-export review is required
before publication; upload/readback must be documented separately.
