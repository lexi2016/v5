# HK EOD transport V2: unbound source candidate

Source adapter and transport are unchanged from reviewed candidate. Public tests contain only generated synthetic responses and temporary checkpoints. Test identifiers/dates are changed to 00001/00002 and 2030-01-02; no actual responses, source lists, bindings, credentials, production locks or unified controller are included.

Run `python -B -m unittest test_transport` and `python -B -O -m unittest test_transport`: 15 synthetic tests. Network opener is mocked. The low-level https_get does contain real HTTP capability but is never called against a live network by tests. run_live always refuses, TRUSTED_LIVE_REGISTRY remains empty, and isolated engine receives mocks only.

Checkpoint budget is 2 MiB, not a changed production memory gate. Atomic isolated writes and test.lock do not certify original production owner, durable writer, resource gate or lock identity. Crash-time HTTP intent remains UNKNOWN; no exactly-once network claim. Candidate must not use shared production directories.

pre_close, Futu scope/unit equivalence, CAS and full eligible scope remain UNKNOWN. No original READY export, production activation, natural or business acceptance. The separately blocked unified controller export remains excluded.
