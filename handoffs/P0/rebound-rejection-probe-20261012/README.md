# One-shot M14 worker rejection diagnostic

Product remains the fixed aa42f4 candidate. The first real strict request failed with only the generic API error because the acceptance wrapper omitted the worker's already-returned error code. Measured319799296-byte peak is below512MiB; do not attribute the failure to RSS.

This diagnostic does exactly one original supervised `kind=rebound`, `group=strict` read using the retained config binding, in a fresh child. It prints only status/error/resource/footer/exit/reap, source fingerprints and before/after data hash/mtime equality. No payload/stock text or private path is printed. No API server, trace, oracle, build, new budget, cache or data write.

```sh
PYTHONPATH=<AA42_FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B \
  <THIS_FIXED_CHECKOUT>/V5/tests/m18_projection_rejection_probe.py \
  <RETAINED_SAVED_VIEW_CONFIG>
```

Expected product source fingerprints:
- module_api.py:3abf88a9d345cd7990d7b73a61eea619f235b12e6956e39c84aec9f8953fd313
- m18_v2_read_process.py:5a2e37ec3b65094facbfa5d3f3f074664988f6ce11ea411b9d24edf6140bd2ef

A diagnostic exit0 means the child was reaped and data was unchanged, not that the page succeeded. Read `status` and exact `error`. Run once; retain the current accepted announcement preview and user's browser untouched. This is not a product fix or permission to deploy aa42.

The diagnostic wraps only `_m18_disk_reader` and `_m18_semantic_value` inside the original worker to report a caught exception's type, safe M18 code, and terminal function/line on stderr. It rethrows unchanged. This also distinguishes an original ValueError from the worker's generic `M18_V2_WORKER_FAILED`; it does not expose locals, full traceback, exception payload text or paths and does not retain a Reader between requests. stdout remains the existing worker receipt summary. Product source fingerprints stay unchanged.

Cloud synthetic smoke: valid binding produced OK, then a separate deliberately wrong manifest pin produced original `ValueError: M18_MANIFEST_HASH` at the reader boundary and the unchanged outer `M18_V2_WORKER_FAILED` receipt; both exited0/reaped and retained all fixture hashes/mtimes. These are two test fixtures, not a second real Mac diagnosis. No real cause is inferred from them.
