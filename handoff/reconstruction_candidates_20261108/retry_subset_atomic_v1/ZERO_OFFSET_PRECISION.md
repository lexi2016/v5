# Retry upstream guard: real-entry integration regression

Initial investigation baseline: fc9ea68a2432dcfb279745d65819d3d853f5321a.
Integration parent: 07da0f8e38458a1dc4b67266432eb36681dbfd4c.

## Preserve the concurrent upstream repair

The branch advanced while this review was running. Commit 07da0f8 already
repairs the same fractional zero-offset defect in subset_plan.aware(). Its
exact source is retained unchanged; the initially isolated alternative is not
published over it. The existing PRECISION_MANIFEST.json and the new upstream
ZERO_OFFSET_MANIFEST.json and test_zero_offset.py are also retained unchanged.

The defect was reproducible on the initial baseline: a negative one-microsecond
zero offset was parsed as UTC, admitting a true 1799.999999-second cooldown as
1800 seconds. The adopted upstream guard refuses it with
UNSUPPORTED_ZERO_FRACTIONAL_OFFSET. This handoff does not claim that upstream
implementation as an additional new fix by this increment.

## The remaining integration test

test_zero_offset_precision.py contributes one additional regression through
the real existing entrypoint, not another copy of the upstream parser tests.
The fixture pins the actual adopted dependency bytes in its synthetic contract.
It sets available_after one microsecond after the current gate instant, uses
the real dependency loader and preflight, and requires BLOCKED before owner,
gate events or any new ledger entry. Existing fixture files are unchanged.

The upstream four tests already cover parser forms, both retry cooldowns and
representable offsets. Redundant versions of those tests from the isolated
alternative were removed before integration.

## Exact source and authority boundary

- Adopted subset_plan.py SHA256:
  5ca0429a695e83f5f15e8ef7b26ed10764efbd7d466316096a99a9bcb1793c93
- entrypoint and coordinator consume dependencies from separately reviewed
  exact-byte contracts, and the coordinator recalculates under its existing lock.
- TRUSTED_RUNS remains empty. No production dependency pin, old approval,
  reconciliation receipt, owner or schedule is changed or manufactured.
- A newly reviewed production dependency contract is still required to use the
  adopted source in a real run. A source commit alone does not grant it.

## Verification

Run from this directory:

    python3 -B -m unittest test_subset test_precision test_zero_offset test_entrypoint test_zero_offset_precision
    python3 -B -O -m unittest test_subset test_precision test_zero_offset test_entrypoint test_zero_offset_precision

The combination has 51 test methods per mode: existing/upstream coverage plus
one new real-entry regression. These are isolated synthetic checks. They do
not establish deployment, natural triggering, business completion or delivery.
