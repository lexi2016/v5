# One paired, read-only Reader boundary diagnosis

Purpose: fixed `4c8606044b6004025998cff3cb0ebe5f3a5c4ed0` still failed the real Mac third semantic read. Its prior synthetic RSS reduction is **not** real acceptance. This commit only adds the external test script and this note. Product source, all frontend files, budgets and persisted data are unchanged.

## Run once on the existing Mac environment

Use the fixed checkout's source and existing Python. Keep the existing retained config unchanged:

```sh
PYTHONPATH=<FIXED_CHECKOUT>/V5/src <EXISTING_PYTHON> -B \
  <FIXED_CHECKOUT>/V5/tests/m18_reader_boundary_probe.py \
  --config <RETAINED_SAVED_VIEW_CONFIG> > <LOCAL_EVIDENCE>/boundary-diagnostic.jsonl
```

The script checks the exact two `4c8606` product source SHA256 values before starting. It launches and stops two fresh independent API subprocesses sequentially:

1. `ordinary`: original HTTP request-thread lifetime.
2. `fixed_thread`: the sole counterfactual routes each semantic call through one persistent read thread. Each request still rereads disk and constructs a new Reader and its original Guard. No Reader/cache reuse, forced GC, allocator environment changes or increased budgets.

Each child receives only descriptor, overview, summary and gaps first page once, stopping that arm at its first non-200. The process exits after both arms, not an acceptance loop. Its final `diagnostic_complete` means evidence collected, not product PASS. No UI/build/test repetition.

## Recorded facts

At Reader/response-parse/semantic boundaries only: current RSS from existing `ps`, service `RUSAGE_SELF` peak RSS, native thread ID, thread count, weak-reference live Reader count, GC counters, effective `consume_content`, remaining encoded object bytes, Python/GIL/platform and pinned source hashes. Original resource exceptions propagate; their fixed ContractError codes/usage are recorded. No tracing, tracemalloc, heap walk, forced collection, payload content, credential or private path logging.

Both arms verify successful response identity/generation/profile/manifest pins; parent snapshot compares persisted bundle/publication hashes and mtimes. Those paths/hash maps are retained only in memory, and output contains only equality and file count. There is no oracle Reader in the API or verifier process.

Interpretation: old Reader count zero with elevated pre-request RSS indicates retained process allocations, not proof of an application-reference leak. Fixed-thread success/stable RSS would specifically support controlling thread lifetime; a failed or similar fixed-thread arm would refute that candidate. Do not ship a threading change based only on Linux synthetic results.

Cloud probe validation: Python syntax and both subprocess arms exercised against the existing explicitly synthetic 28.65 MB fixture. Real Darwin result remains pending.
