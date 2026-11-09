# Evening original-review-time containment

Source baseline: `fc9ea68a2432dcfb279745d65819d3d853f5321a`.
Nodes: `evening-prepare` (18:30), `evening-check` (18:50),
`evening-delivery` (19:00), all `Asia/Shanghai`.

## Reproduced defect

The previous `_receipt` compared all receipt members except `checked_at` with
the expected core. It then treated that excluded local timestamp as evidence
for the stage time gate. Keeping the proof unchanged while editing a freeze
receipt from 18:00 to 18:40, or a verification receipt from 18:49:59 to 18:55,
was accepted at 19:00. Creating a new receipt also used the current registered
clock rather than the original independent-review event time.

Both edits and the fabricated-original-time creation are reproduced by three
failing regression tests on the baseline, in ordinary and optimized Python.
The separate delivery sender quarantine remained in place; no send occurred.

## Current behavior and call map

`execution.run` still resolves only its private `REGISTRY` and checks the exact
controlled-chain code pin. For a controlled binding it calls
`controlled_chain.run`. After binding, action and clock checks, that call now
returns `BLOCKED` with
`INDEPENDENT_REVIEW_TIME_AUTHORITY_UNBOUND_NO_FORMAL_RECEIPT`, before entering
the owner context or reading/writing package files. The private `_package` and
`_receipt` boundaries enforce the same containment.

No runtime flag, project-domain string, local hash or newly supplied callback
can grant the missing authority. The unsafe local timestamp gate was removed.
Existing receipts, outbox state and locks are not changed or migrated.

Legacy local exports through `execution._run_local` remain available with their
existing source/owner checks and `formal_freeze=False`, `sent=False`,
`natural_verified=False`, `business_accepted=False`. The nine existing tests
for that path still pass. This patch does not grant a production registration,
formal preparation, delivery, natural-trigger or business acceptance.

## What must be recovered before lifting containment

The original owner and independent reviewer must identify and verify:

1. An original review event bound to the exact manifest/package digest, stage,
   business date, run/task/environment, reviewer and authority identities.
2. Its original event timestamp and timezone, obtained from an independently
   authenticated event source, not the current clock, owner statement or a
   mutable local receipt. The event must prove the relevant 18:30/18:50 gate.
3. A verified read interface and authority root for that event, including how
   correction, revocation, replacement and rollback are detected. A checksum
   of a self-written file provides byte identity only.
4. The pre-existing original delivery/outbox identity and an independent
   consume-once or equivalent no-replay authority for real delivery. The
   separate `ANTI_ROLLBACK_AUTHORITY_UNBOUND_NO_SEND` gate stays unchanged.

Those are missing contract/evidence requirements, not a newly created trust
service. Do not invent identifiers, insert approved booleans, restore an old
local timestamp, or create a new empty ledger to satisfy them. Once actual
authority is recovered, a separately reviewed implementation can replace this
containment. Historical receipts require explicit reconciliation, not automatic
migration or re-dating.

## Validation

From this directory:

```sh
python3 -B -m unittest -v test_execution test_review_time_quarantine
python3 -B -O -m unittest -v test_execution test_review_time_quarantine
```

Both run 14 tests successfully, all isolated/synthetic. The unchanged
`terminal17_alert_v1/test_delivery_quarantine_selfcontained.py` suite also runs
8 tests successfully in both modes and verifies the actual consumer digest.
The shared sender/outbox modules and their pins were not changed.

## Rollback

This change is a deliberate safety containment. Do not roll back it to enable
formal preparation while original review-time authority is missing. If source
rollback is required, retain the empty live registry and existing no-send gate;
do not delete or rewrite package files, outbox state, attempt records or locks.
