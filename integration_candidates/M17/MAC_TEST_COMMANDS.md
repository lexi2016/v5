# Independent Mac check for the new standalone integration candidate

Use a fresh isolated checkout at the candidate commit returned with this delivery.
Keep the existing V4/P0 services, source data, credentials, schedules and ports untouched.
Use the existing absolute Python executable with FastAPI already installed; do not
install packages or activate live collectors. The suite uses unittest (not pytest).

From the repository root:

    /absolute/existing/python -I -B integration_candidates/M17/after/V5/tests/test_daily_close_recapture_owner.py

The test file adds only its candidate src path. It resolves the existing repository
vendor root itself. It creates disposable SIMULATED temp input/state/ledger roots
and launches the actual fixed original producer and new reader processes. No old
vendor-only test suite is rerun; the new cases exercise the added adapter, private
ledger lifecycle, request/response binding, unknown/reuse behavior, negative inputs,
source/receipt/pool drift, unchanged six lanes, CLI and Python guard boundaries.

Report interpreter/version, fixed commit, command, start/end times, exit code,
test count, test output SHA256 and any exact failure. Keep raw synthetic payloads
and absolute private runtime paths out of GitHub feedback. A passing result proves
only this SIMULATED engineering unit. Real collection, natural trigger, 1530,
continuous tracking, P0 evening registration and page remain unverified.
