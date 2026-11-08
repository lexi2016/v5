# 09:15 synthetic input validator V2

Standalone rewrite candidate, NOT recovered original a0915.py or a production collector. Original source and fixed pins remain untouched. No production registry, dispatch, gate, lock, source, formula or schedule is changed. No network or filesystem operation exists in candidate.py.

## Scope / source
V79 archived fixture A0915_RECORDED_DISPLAY_INPUT_V1 supplies the text-only structure and evidence for scope mismatch rejection, missing scope rows, unavailable 09:25 input, and source admission remaining UNKNOWN. Exact original reader/output semantics have not been recovered. This new module is not a drop-in replacement and no original acceptance transfers to it.

## Changes against V1
- Missing, malformed and wrong-type timestamps raise RejectedInput with stable code rather than incidental KeyError/TypeError.
- Wrong date/schema/market, empty or duplicate scope, cross-date timestamps, precise cutoff boundary, UTC equivalents and unexpected fields covered by regression tests.
- Returns detached recorded_input and input_canonical_sha256. This digest is of explicitly canonicalized parsed JSON, NOT original file bytes.
- Freshness admission always UNKNOWN and FRESHNESS_CONTRACT_UNKNOWN always blocks, even if input is before cutoff. A midnight record is not labelled timely.
- Production/business/natural acceptance always false, source calls zero. Real inputs rejected.

New conservative candidate semantics remain explicit: 09:15:00 Shanghai cutoff, same-day times, available>=observed, no duplicate rows, exact typed text structure, no unknown fields. These are NOT proven original business semantics. No lower freshness bound or real source qualification is invented.

## Test / provenance
The V2 tests ran against V1 first: 37 tests including inherited repetitions, 2 failures and 6 errors; preserved RED_V2.log. Removed redundant inherited repetition before final suite; 25 distinct tests pass in normal and -O modes. Run `python -m unittest -v` and `python -O -m unittest -v` in this directory. This is the full isolated candidate suite, not the full production project suite or actual 09:15 owner integration.

## Registration and rollback
REGISTRATION_PROPOSAL.json inventories the candidate for project bookkeeping only. It is NOT a production job registration and does not modify the empty original REGISTRY. Rollback: stop referencing this isolated version. V1 and historical original evidence are retained.

## Still blocked
Missing original exact reader; legitimate real source, quote/units contract, monitoring scope, timing/freshness definition, approved owner/resource and scheduler integration. These require explicit evidence and review before connecting any replacement. GitHub upload not performed; this package contains only code, synthetic tests and audit docs. No real stock observations or credentials.
