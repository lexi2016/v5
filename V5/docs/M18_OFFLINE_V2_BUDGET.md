# M18 offline v2 resource contract — synthetic candidate

This is a new format alongside unchanged v1. The earlier real `M18_NODE_LIMIT` failure remains a failure. No real-input compatibility claim or new real scan/build is made. This candidate does not change shared digests, API budgets, P0, business eligibility, or owners.

## Fixed caller-pinned profile

`m18.offline.budget.v2.1` is immutable. Its canonical SHA is required by build and Reader; the complete profile is in the manifest and its SHA is in generation identity and every object/response binding. Unknown pins, modified values (including Boolean/integer substitution), and v1 manifests are rejected. The profile is code-defined, not selected from incoming data. Source code must itself be pinned by the caller.

- Every stored object / returned JSON response: strictly less than 16 MiB, at most 200,000 lexical nodes.
- Complete decoded response: at most 1,500,000 lexical nodes across all content chunks, never per-chunk reset.
- Saved result: independently at most 1,500,000 nodes; both inputs together at most 3,000,000.
- Generation object metadata, including base64 envelopes and manifest: at most 500,000 nodes. Response nodes plus that metadata: at most 2,000,000 logical nodes. Saved verification is charged to the separate input budget, not counted as a second stored response.
- Manifest plus all unique stored objects: strictly less than 64 MiB. Canonical complete response and saved input are each strictly less than 64 MiB, but that alone does not guarantee the base64-expanded generation fits.
- Depth at most 64, indexed payload items at most 10,000, generation records including manifest at most 10,000.
- A source string token including JSON quotes and escapes: at most 32 MiB, even if split across content blocks. Keys retain 1,024-byte and non-string scalar tokens 128-byte limits.
- Content blocks remain 256 KiB; detail pages remain 32 references; index storage pages contain at most 512 references. No record/body/gap removal is a budget escape.

Lexical nodes count every JSON value and every object key once, exactly as v1's scanner. This count bounds semantic values as well; it is not bytes or a sum of traversal passes. Ledger tests independently exercise cumulative caps, including caps that a currently valid fixed layout cannot normally reach before a tighter gate fails.

## Parsing and memory behavior

The existing v1 grammar/span scanner is reused with explicit local/response/saved node scope and string-token checks. Standard `json.loads` still determines JSON semantics, with constants rejected, followed by the existing chunked canonical encoder/hash. There is no new streaming JSON semantic implementation.

The saved DOM is validated and released before parsing the response DOM; the response DOM is released before generating content objects. Reader uses one exact-size assembly buffer, converts to immutable bytes and releases the buffer before JSON parsing. The transient conversion still has two full byte copies; this is reduced-residency parsing, not constant-memory streaming. Upstream input bytes and the generation dictionary are still memory residents. RSS acceptance, rather than a claim derived from node counts, decides whether the operation qualifies.

Manifest section summaries point to independently hashed fixed index pages. Reader recomputes the complete index from the fully hash-verified response and compares each page, order, count and entry. It recomputes local/aggregate metadata budgets and actual decoded response node count; self-declared low counts cannot admit a response. The saved-node count is builder evidence committed by the caller-pinned manifest; Reader does not re-open saved source bytes. The builder validates saved raw and canonical semantic SHA separately.

Existing v1 detail/selection/cursor/content mechanics and explicit expected-request verification are reused. Returned schemas are v2; profile is included in the binding. Cursor retains its exact existing fields; manifest and generation pins transitively commit the profile. Caller-held section, indices selection, cursor, offset and chunk index are mandatory for verification, not extracted from a received response.

## Measured resource gates and short-lived execution

`m18_offline_v2_process.run()` accepts only fixed local build/read requests. It spawns a fresh process, loads bounded files there, rejects network/subprocess actions in that worker, and supervises the fixed 90-second wall deadline. It neither invokes owners nor launches a service. The new output directory receives an `ACCEPTED.json` marker only after a successful worker exit and resource checks. Rejection may leave incomplete local files but no accepted marker; there is no automatic retry or CAS/pointer publication.

Resource gates: peak process RSS <=512 MiB, operation CPU <=60 seconds, whole supervised operation wall <=90 seconds. RSS is measured using worker lifetime high-water usage (Darwin bytes / Linux KiB normalized); CPU and wall are measured from before input loading. Unknown platforms fail closed. Core scanners check every 4,096 nodes and string boundary; encoding, parsing, I/O and verification have checkpoints. Parent termination bounds noncooperative wall overruns. Synchronous JSON decoding, canonical encoding and allocation are not preempted by those checkpoints.

**RSS is a measured rejection gate, not hard memory isolation. CPU is checkpoint/final-measurement enforced, not an OS hard cap.** A burst may exceed the budget before rejection. The parent deadline includes spawn/exit overhead and may have scheduling/termination latency. No system settings or permissions are changed. Parent memory is not covered by the worker's 512 MiB gate; requests carry paths/pins, not the large source contents.

Receipts contain peak RSS, CPU/wall, stages and v2 scanner traversals. Traversal counters count completed repeated v2 scans, not logical nodes; a rejected partial scan is not included in these counters; inherited v1 response validation and encoder work are included in CPU/wall but not those scanner counters. No hard real-time or hard memory guarantee is implied.

## Synthetic acceptance

Keep all 30 v1 methods unchanged. New tests cover real exact/over local and source node limits, cumulative ledgers, 16 MiB and 64 MiB boundaries, 32 MiB strings including escape expansion, depth/index limits, canonical Unicode/number semantics, duplicate keys, immutable/pinned profiles, content/index tampering and expected-request substitution. A >1M-node approximately 30MB synthetic fixture is built and read in different new processes, checking every page, every content chunk and final byte SHA.

Separate resource-fault tests use actual allocation, actual CPU work and actual sleeping processes, with fixed unchanged limits. Only worker dispatch is injected for those faults; no clocks, usage readings, product responses or admission results are fabricated. They prove rejection/no accepted marker and parent timeout termination, not OS hard isolation.

This is a local candidate for independent review. Any future real incremental run requires separate authorization and a new isolated directory; never retry by changing limits inside the prior failed run.

## Receipt transport review correction

Return IPC no longer uses `Connection.poll()` followed by blocking pickle `recv()`. It uses a four-byte big-endian length, canonical JSON summary of at most 16 KiB, and one fixed 24-byte `!Qdd` footer. The parent sets its pipe descriptor nonblocking, reads bounded increments with select and the same absolute 90-second deadline, checks declared length before allocating a body, rejects truncation/EOF/I/O errors/trailing bytes, and waits for worker exit within the remaining deadline. On rejection it terminates/kills as necessary and reaps the worker; no accepted marker survives rejection. Pipe EOF alone is never success. Parsing the bounded summary also has a post-parse deadline checkpoint.

Summary keys and primitive types are closed and bounded. The unbounded per-section overview and per-stage telemetry are not returned in IPC: only aggregate NOT_LOADED section/item counts, stage count, scan counters and the existing bounded build/read identities/counts. This changes telemetry, not the payload or any business record. No pickle decoding occurs in the parent return path. An injected fault worker also receives the bounded sender adapter; raw partial-frame injection remains possible only in tests.

Final RSS/CPU sampling occurs after summary compaction, JSON encoding and complete header/body write. RSS uses worker `RUSAGE_SELF.ru_maxrss`; CPU now uses the worker's process-lifetime `process_time()`, which includes spawn imports as well as business work and receipt-body serialization/send. Parent admission uses the footer measurements, not preliminary usage echoed in the summary. The original business ResourceGuard is unchanged.

The final fixed 24-byte footer packing/write, close and interpreter teardown necessarily occur after that sample and are NOT claimed to be included in CPU/RSS. They contain no unbounded user data or pickle serialization. The parent supervises wall time through receipt EOF and worker exit, including this tail. This is an explicitly bounded unmeasured CPU/RSS tail, not a claim of exact whole-process final resource accounting or hard isolation. The small parent-owned acceptance-marker write is outside worker metrics, with deadline checks and rejection cleanup. Scheduler/kernel latency is not a hard real-time guarantee.

New tests distinguish (a) a short observation reproducing the old ready-but-blocked recv defect, (b) short-deadline deterministic protocol tests, and (c) actual unchanged 90-second incomplete-header/body/footer child-process tests with termination/reaping and no marker. The original 51 methods, fixed budget profile and prior resource-stress evidence are retained unchanged. No real-input retry is authorized by this correction.
