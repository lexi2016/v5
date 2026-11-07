# Intraday read-only API and original M11 timing predicate: source export

These are isolated source candidates, not production integrations or complete
intraday monitoring. No sampling, source collection, ten-minute jobs, trading,
activation, source admission, model run or natural-trigger execution is added.

## Intraday API

Private input pins and real historical date/count bindings have been removed.
The unmodified load/create_server paths fail closed after the unchanged safeio
code SHA gate. The original contract membership, date, source-admission and
no-carry-forward checks remain in code but are not exercised against real data
in this distribution. No public source registration interface was added.

The current route remains HTTP 409 BLOCKED_CURRENT_BINDING_UNKNOWN with no
historical fallback and no current rows. This is verified using a synthetic-only
HTTP harness, NOT evidence that any production endpoint is now running. The
original private candidate's current409 is historical manual evidence and is not
shipped. Unmodified public CLI cannot start without a separately reviewed binding.

Tests synthesize two non-market records and patch the loader ONLY inside test
harnesses. synthetic_cli.py is clearly test-only, not an approved input adapter.
Never use synthetic payloads as research records or current-day evidence.

From intraday/ (Python 3.11+ Linux, standard library):

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest discover -v

The environment variables also apply to spawned Python CLI test processes;
parent-only -B/-O flags do not propagate to those subprocesses.

13 tests cover synthetic HTTP status/history/current rejection, Host/Origin
restrictions, no mutations, wrong routes, idle/slow/trickled request lifetime,
and missing-binding refusal. Imported create_server does not itself impose total
service lifetime; the tested bounded total lifetime is the CLI watchdog path.
Absolute per-request limits remain separate. This is not a hard realtime proof.
Expected client/deadline disconnects may produce default BrokenPipe logging;
clean stderr and longer-lived production suitability are NOT claimed.

## M11 timing subfunction

source_time_gate.py is byte-identical to the reviewed wrapper. The two original
predicate functions are included as an exact source excerpt for AST comparison,
not the complete owner. ORIGINAL_SOURCE.json pins the public historical GitHub
source. test_source_time_gate.py changes only its reference filename to the
minimal excerpt. No source data or private binding is needed for this predicate.

From source_time_gate/:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest discover -v

9 synthetic tests cover timing-only partition and original AST equality.
On-time is NOT source validity, correct trading day, semantic approval or
production admission. Late is classified before missing remaining timestamps by
the preserved original predicate; late records must stay timing-rejected or
quarantined, never interpreted as metadata-valid. Input records remain retained.
M11's original capture slots are not ten-minute collection; no owner is run here.

## Shared boundaries

No private historical payload, runtime receipt, task ID, lock, credential,
private path or account configuration is included. Shared production/resource
gates still belong to the original authorized orchestrator. Neither local HTTP
socket bookkeeping nor safe local reads replace that shared production lock.
No production admission, browser rendering, current activation, real bucket,
collector binding, live dispatch or natural-trigger acceptance is established.

PROVENANCE.json records changed and unchanged source hashes. Original reviewed
candidates remain intact. This public candidate needs its own limited independent
review before submission; source review is not business acceptance. Prior public
source batches and V4 are preserved, with no deployment/permission change.
