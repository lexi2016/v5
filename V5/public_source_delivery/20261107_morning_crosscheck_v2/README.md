# 06:30 source crosscheck: public-safe source candidate

This is a limited row-date/source/owner/state consistency substep, not complete
morning semantic source validation. It does not collect, select, trade, grant
source/selection admission, formally freeze the next day, or implement a scheduler.
A consistent pinned snapshot may still have stale or UNKNOWN rows.

## Reproduce checks

Python 3.11+ on Linux, standard library only, from this directory:

    python -B -m unittest -v test_crosscheck
    python -B -O -m unittest -v test_crosscheck
    python -B -m unittest discover -v
    python -B -O -m unittest discover -v

The first two commands cover all 18 original synthetic tests. Discovery also
runs two public missing-binding checks (20 total). Do not directly run
`python test_crosscheck.py`: its original main guard precedes EntryTests and
would omit five tests. These cases synthesize two rows and mocked load/freeze
failures. They do not establish real source identity, current-day market data,
production integration or natural execution.

## Public export differences

Private DATA and ADMISSION path/hash/size constants are removed and replaced
with None. After its unchanged pinned safeio check, `load()` fails closed with
PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING. There is no public input registry or
CLI bypass. Raw audit, schema/date/count/owner checks and nonzero failure exit
semantics are preserved. safeio.py and the 18-test source are byte-identical.
PROVENANCE.json records original and public-candidate hashes.

The CLI deliberately exits 3 without audit/freeze or a saved-success receipt
while binding is absent. Inconsistency exits 2 before freeze; input/schema or
readback exceptions exit 3. Even an authorized original runtime's exit 0 means
only snapshot consistency and local byte readback, never business completion.
Restoring private bindings requires a new reviewed candidate, exact original
source pins and actual-input verification. Never weaken those checks.

## Unverified and excluded

No real research data, runtime receipts, active locks, private paths, account
configuration or credentials are included. Complete semantic crosscheck,
formal freeze, live board/delivery and natural-trigger acceptance remain
NOT VERIFIED. The source V2 passed a limited isolated review; this modified
public candidate separately requires review before publication.

This code does not acquire the project's shared production lock or enforce its
resource gate. Those must remain under the original authorized orchestrator;
local freeze integrity is not a substitute. No production admission, new task,
resource-threshold change or existing-job modification is authorized by this
export. Preserve V4, original data, failure history and original gate semantics.
