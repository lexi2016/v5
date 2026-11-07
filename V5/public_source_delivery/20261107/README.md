# Read-only evening source export

This is an isolated, public-safe source delivery, not a deployment, scheduler,
collector, selector, model, or business acceptance. It preserves the original
four evening report slots (17:00, 18:30, 18:50, 19:00 Asia/Shanghai).
FULL_TIMELINE_MAP.json indexes all 21 original nodes with pinned historical
GitHub source links and exported candidate references. A complete index does not
mean all nodes are implemented or accepted.

## Run synthetic checks

Python 3.11+ on Linux, standard library only:

    python -B -m unittest -v test_public_contract
    python -B -O -m unittest -v test_public_contract

The 17 tests use temporary synthetic objects or no inputs. They do not test
original research data, live services, delivery, or natural scheduler triggers.
Both modes passed during export preparation. A changed export must be retested.

## Deliberate source differences

- `adapter.py`: private deployment/market-data binding, PID observations and
  production-lock locations are omitted. `inspect` and `snapshot` explicitly
  reject use. No caller-configurable replacement admits success.
- `evening.py`: a historical result-count label is replaced with a neutral
  display-only label. Reporter logic and the frozen calendar pins are retained.
- `INPUT_PINS.json` is empty, NOT an approved input registry. Consequently no
  completion evidence can be accepted from this distribution.
- `guard.py` is byte-identical to its source; `V3_PINS.json` identifies this
  distinct public candidate, not the original operational candidate.
- Original data-dependent tests are NOT shipped or claimed as passed here.
  New synthetic tests exercise rejection, pin changes, path confinement,
  no-follow reads, writer exclusion, content-addressed reuse, partial output
  rejection and date/calendar guards. The original candidate remains untouched.

The byte-level provenance is in `PROVENANCE.json`; `MANIFEST.json` covers this
export. There are no private runtime receipts, data, credentials, active locks,
automation instructions or service endpoints. Public holiday-calendar rules
are unchanged and are not research/market-price data.

## Material assembly V2

The material assembly code and its 30 synthetic tests are byte-identical to the
reviewed V2 source. They cover night/morning material slots and immutable candidate
freeze only, not source authorization or research correctness. Private original
receipts, frozen reports, and the local-path build_matrix.py are excluded.
FULL_TIMELINE_MAP.json is a derived public mapping with local-only pins removed
and exported code references rehashed. Its mapping test checks 21 unique nodes
and those hashes; this is not 21 business jobs tested.

    cd handoff/timeline_material_pack_v2_20261107
    python -B -m unittest -v test_material_pack test_races
    python -B -O -m unittest -v test_material_pack test_races

The source V2 independent review passed only isolated security corrections, not
production use. This public export still needs its own final independent review.

## Limits and integration

Do not replace an operational adapter with this export. A future private binding
requires separate source review, version pins and real-input acceptance under
the existing project gates. Missing evidence remains UNKNOWN. Manual/synthetic
checks never prove natural execution, current-day business success or delivery.
Only the original approved environment can establish those facts.

Preparation is not GitHub upload. No branch or deployment is changed by running
these tests. Integrate append-only on the existing development branch, preserving
V4 and history; never force-push, edit access permissions or commit runtime files.

## Cross-cutting recurring obligations

The complete framework index also lists intraday ten-minute collection and
hourly backup. Neither is implemented or triggered by this export. Their current
execution and natural acceptance remain UNKNOWN; the existing scheduler identity,
authorizations, locks and SOP are authoritative. No duplicate alarm, collector or
uploader is created. Seven node-related candidate references do not mean seven
business nodes completed, nor that all 21 nodes or recurring obligations work.
