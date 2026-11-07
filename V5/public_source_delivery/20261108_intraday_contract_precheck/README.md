# Intraday daily contract precheck: offline, NOT_ADMITTED

Source and tests copied unchanged from reviewed candidate. Only synthetic bytes and synthetic contracts within test code are included. No actual scope1020 contract, monitor list, private path, source data, binding, credentials or unified controller.

Run `python -B -m unittest test_precheck` and `python -B -O -m unittest test_precheck`: 13 synthetic tests. No file/network/collector/scheduler invocation by precheck. Passed structure, dates and byte hashes do NOT grant capture admission.

Source CSV schema/scope equality, generation and input-identity algorithms, trading-calendar provenance, current owner approval, source/resource gates, runtime lock/attempt and scheduler remain unverified. Dates must be independently validated upstream. approved_for_capture always False; no production or natural/business acceptance. The separately blocked controller export is excluded.
