# Mac paired reader-boundary diagnostic — 2026-10-12

Fixed candidate: `5bbbc92b02ea6eb42d77f0b8f4396c4908eb8567`.
Product/frontend remain the 4c8606 candidate; this run uses the candidate's diagnostic script without product edits.
This is diagnosis, not acceptance of P0, the full 18 modules, or P0–P5.

## Executed command and outcome

Private absolute paths replaced with role placeholders:

```sh
<existing-python> -B <candidate>/V5/tests/m18_reader_boundary_probe.py --config <retained-saved-view-config>
```

Python 3.14.6, Darwin, GIL enabled. Started UTC 2026-10-12T10:49:36.067911+00:00; ended UTC 2026-10-12T10:49:59.211334+00:00.
Actual diagnostic command exit: 0; stderr empty. Exit 0 means diagnostic_complete, not that the HTTP sequence passed.

Two fresh API service processes ran sequentially. Each requested descriptor → overview → summary → gaps once, stopping on its first non-200.

| Arm | Descriptor | Overview | Summary | Gaps | Final child peak RSS bytes |
| --- | --- | --- | --- | --- | --- | --- |
| ordinary | 200 / 804 B | 200 / 6638 B | 200 / 1321 B | 409 / 90 B | 542801920 |
| fixed_thread | 200 / 804 B | 200 / 6638 B | 200 / 1321 B | 409 / 90 B | 543375360 |

Both failed with original guard code `M18_V2_RESOURCE_PEAK_RSS_BYTES`, over the unchanged 536870912-byte budget.
Ordinary guard usage: peak_rss_bytes=542785536, cpu_seconds=2.727812, wall_seconds=2.7299939160002396, scan_nodes=1122085, scan_bytes=71203343.
Fixed-thread guard usage: peak_rss_bytes=543375360, cpu_seconds=2.682734, wall_seconds=2.6904079999949317, scan_nodes=1122085, scan_bytes=71203343.
The final sampled peak and failure-boundary peak are separate measurements.

## Boundary observations

Ordinary semantic thread native IDs: 2774658, 2774786, 2774875. Fixed-thread semantic calls all used native ID 2774948.
Both arms reported live_readers=0 at every semantic entry. Nevertheless, current RSS before later requests stayed elevated:
ordinary 32931840 → 270565376 → 388055040 bytes; fixed-thread 33636352 → 272547840 → 390119424 bytes.

Both arms used consume_content=true. Encoded objects decreased from 133 / 42291625 bytes at reader entry to 16 index objects / 1583408 bytes at response parse entry. The release path was reached.
Response JSON-loaded current RSS grew across requests: ordinary 318750720 → 431849472 → 542785536; fixed-thread 319635456 → 432390144 → 543375360 bytes.

Keeping a persistent semantic thread did not avoid the failure for this fixture and sequence. The weak-reference observations do not establish an allocator root cause or prove the absence of every other retained object.

## Scope and preservation

Both owned child services stopped. Saved-data hashes and mtimes were unchanged across 141 files. No product edits, forced GC, budget changes, cross-request reader cache, oracle, real acquisition, trading, frontend build, or deployment occurred.
No unrelated service was stopped. No payloads, local config, credentials, or private absolute paths are included.
Full original metadata-only script output, including HTTP status and guard error boundaries, is in `boundary-diagnostic.jsonl`.
