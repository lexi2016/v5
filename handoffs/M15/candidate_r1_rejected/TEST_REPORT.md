# V5 M15 test report

Command:
```
PYTHONPATH=V5/src pytest -q V5/tests/test_daily_us_owner.py V5/tests/test_us_mapping_scope.py V5/tests/test_us_mapping_daily.py
```

See test.log for stdout/stderr.

The candidate change adds only owner ledger_run_id input validation.
No real Mac data, production source closure, or natural run was executed.
