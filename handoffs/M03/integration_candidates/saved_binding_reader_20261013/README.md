# M03 exact saved-binding reader

Original runtime: lexi2016/v5@efeaeb8fc04474b1f38ebda98b35953b580049df, `handoffs/M03/integration_candidates/market_snapshot_20261013`. This new adapter does not modify that runtime, producer, owner, or any request/data. Copying it beside the original is unnecessary: it locates the original runtime using the unchanged local request and verifies the fixed runtime source bytes before importing them.

Run with existing POSIX Python: `python -I -B V5/src/v5_shadow/us_source_saved.py --request LOCAL_READ_ENVELOPE.json`.

The local envelope must contain exactly:
- `request_file`: absolute path of the existing full original request JSON
- `expected_request_sha256`: SHA256 of the ORIGINAL REQUEST FILE BYTES (whitespace included)
- `expected_binding_sha256`: SHA256 of the existing binding file bytes
- `expected_source_sha256`: exactly the original `payload`, `receipt`, `manifest` raw SHA256 values

Do not put `action` in this standalone envelope. The optional P0 dispatcher adds `action=read` outside these four fields and removes it before calling the adapter.

The reader separately derives `request_identity_sha256` using the unchanged R14 canonical convention. That canonical digest is the existing binding basename. A formatted request's raw file SHA differs from its canonical binding identity. Neither original request nor binding is rewritten. In particular, `allow_network_capture=true` remains part of the original identity: this read-only code path grants no capture permission and never calls run_us_source or a producer.

A fresh child verifies the exact fixed runtime closure, compiles only verified source bytes (including the original fresh-reader child, ignoring valid/poisoned pyc and unlisted dependency shadows), admits original marked snapshot/binding roots, reads the exact binding, and invokes original `_verify_binding`. This rechecks original request/capture/cutoff/status/safety identities, snapshot triplet SHA and original `ResearchPeripheralStore` reader. Missing/corrupt inputs are errors with no fallback, initialization, lock creation, repair, copying, production writes, or network.

The public result exposes dates/cutoff, capture identity, original statuses, quote/theme counts, SHA anchors, and false safety flags. It does not expose local request paths, owner/code/data roots, provider URLs, or the original full request. Readback is not a new natural capture and does not upgrade trading eligibility.

Exit 0: verified read-only public result on stdout. Exit 2: SOURCE_REJECTED and original error information on stderr. Read success is not publication success. The P0 one-card publication patch is a separate candidate and must retain every non-M03 card and route with generation CAS.

## Tests

Copy the new test into an isolated copy of the unchanged original candidate's V5/tests and the adapter into V5/src/v5_shadow, then use its existing test fixture and environment:
`M03_FIXED_SOURCE=$RUNTIME PYTHONPATH=$RUNTIME/V5/src:$RUNTIME/V5/tests python -B -m unittest -v test_us_source_saved`.
12/12 passed using actual original quote-only synthetic producer/store/binding/cold reader. No real provider, Mac production data, or page publication was executed here. All actual test sources, clocks, and Proxy responses are explicitly synthetic. No Mac private request or paths are committed.

Route compatibility correction: see p0_integration/route_compatibility_fix/README.md for the exact e18 increment. The full P0 candidate now preserves the complete 15-route deployed inventory while rejecting unknown paths.
