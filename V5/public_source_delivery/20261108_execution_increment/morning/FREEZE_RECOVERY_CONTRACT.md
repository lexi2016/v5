# 06:30 freeze recovery guard contract — 2026-11-09

Baseline: `fc9ea68a2432dcfb279745d65819d3d853f5321a`.

## Scope and status

This change adds a **new structural input contract**, not a recovered exchange
calendar or recovered production freeze authority. The public `TRUSTED_RUNS`
registry stays empty. No scheduler, owner, lock, writer, source credential,
production activation, V4 code or formula is changed.

Two baseline reproductions are distinct:

1. Removing the November 6 session from a supplied calendar allowed November 5
   source data with a fresh November 6 observation receipt to receive session
   lag zero. Envelope coverage dates did not prove every intervening day was
   represented.
2. The pure lineage builder could construct two different parentless GENESIS
   previews. This proves absence of unique-chain registration in that helper;
   it does **not** prove that a production chain was written twice. Existing
   results already declared `formal_freeze=false`.

## New required structural input

`reg.inputs.calendar_coverage` must be a normal pinned input reference (path,
byte length and SHA-256). `verify()` therefore includes it in the existing PIT
input binding and exact reviewed registration contract. The decoded document
has these exact top-level fields:

| Field | Contract |
| --- | --- |
| `schema` | `MARKET_CALENDAR_COVERAGE_V1` |
| `calendar_identity` | SHA-256 of the existing canonical `market_calendar` document |
| `market`, `timezone`, `version` | Exact equality with that calendar |
| `coverage_start`, `coverage_end` | Exact calendar bounds, YYYYMMDD |
| `days` | Exactly one ordered row for **every civil date**, inclusive |

Every day row has exactly `date`, `state`, and `source_reference`. `state` is
explicitly `OPEN` or `CLOSED`. An omitted, duplicate, reordered, `UNKNOWN`, or
unreferenced day is refused. The set of `OPEN` dates must equal the existing
session dates exactly. A declared temporary closure can therefore be represented
without assuming that weekdays must be open. The code never fills omitted days
from weekday heuristics.

**Structural agreement is not authority.** A caller can still lie consistently
in two documents. Production requires independently admitted exchange-calendar
provenance and temporary-closure information available by the relevant cutoff.
A self-hash, `source_reference` string or local file alone proves none of these.
The output explicitly retains `source_admission=false` and
`calendar_authority=REQUIRES_EXISTING_INDEPENDENT_REVIEW`.

## Production chain boundary

Until the original authority is recovered and reviewed, production `freeze`
dispatch returns `BLOCKED_FREEZE_AUTHORITY_NOT_BOUND` **before** gate start,
module/input loading, owner-guard acquisition, lineage construction or output
writing. A caller-provided approval object or local head file does not alter
this result. Direct production calculation returns the same blocked result.
The pure lineage helper requires the explicit `synthetic` domain.

The missing production requirements remain:

- Exchange-calendar and temporary-closure admission.
- A trusted chain head identified by the original owner/system.
- Explicit authorization for the first GENESIS of that chain.
- Atomic unique chain registration/CAS against that trusted head, with a
  conflict/reconciliation contract and anti-rollback authority.

No local-file CAS has been invented or presented as recovered authority. No
automatic fallback from a missing parent/head to GENESIS is provided. Synthetic
historical previews retain their previous lineage content and non-authoritative
status; they do not acquire production uniqueness semantics.

## Existing callers and migration

The current call path is `dispatch()` → `verify()` → original owner guard →
`calculate()` → `validate_freeze_panel_freshness()` / `build_freeze_lineage()`.
Direct synthetic tests also call the latter helpers. Existing empty production
registration is preserved.

Synthetic fixtures now include `calendar_coverage`; tests that intentionally
change sessions must keep this structural fixture coherent when testing a later
guard. A separate regression deliberately removes a session while retaining its
explicit OPEN day to test the missing-session bug.

A reviewed future production binding must update the adapter byte pin, include
the new coverage input in PIT and review identities, and implement/recover the
four authorities above. Merely repinning this file is insufficient and does not
remove the explicit production block. The original frozen source pins and old
review receipts must remain available as historical evidence.

## Verification

Run from this directory with `MORNING_PACKAGE_ROOT` pointing to the complete
`V5/public_source_delivery` package and `USER_INGESTION_SOURCE` pointing to its
existing `20261108_night_control/night_handoff.py`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest discover -v -p 'test_*.py'
```

These are isolated synthetic/replay tests. They do not establish current
deployment, natural triggering, production input admission or delivery.
