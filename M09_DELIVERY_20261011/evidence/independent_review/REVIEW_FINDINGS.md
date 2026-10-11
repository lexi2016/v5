# Independent M09 frozen-candidate review

Reviewed tree: `/workspace/scratch/a5458cb06b78/m09_work/review_snapshot`.
Requirements: R3 TASK_M09, DELIVERY_CONTRACT, FINAL_SUPPLEMENT_R3,
RUNTIME_INPUT_ADDENDUM_R2, and the implementation plan.

This review changed no candidate files. All market rows in the reproductions
are explicit SYNTHETIC engineering fixtures. No packages were installed.
These observations do not claim real parquet, Mac, live API/UI, or natural
scheduler acceptance.

## Important findings

### IR-01 — P1 — Hard interruption exposes an unfinished publication

Path: `V5/src/v5_shadow/a_close_daily.py`, lines 620–629, 535–538, 481–499.

The head changes before the immutable successful trigger receipt is written.
A process exit at that boundary bypasses the exception restoration block.
The public reader accepts the head without requiring a committed transaction
witness. Retrying the same attempt writes UNKNOWN but leaves the interrupted
generation visible as the current successful result.

`test_crash_after_head_switch_preserves_previous_success` starts a successful
run, launches a real child process for a changed configuration, and exits that
child with code 73 immediately after the real `_activate` completes. Both the
fresh read and the read after retry serve the new generation; the retry says
`INTERRUPTED_ATTEMPT_REQUIRES_NEW_ATTEMPT_ID`.

Recommendation: bind a generation to its creating trigger/request and require
a matching immutable success witness before a public read can serve it. During
an incomplete head transition, serve a verified same-date predecessor with
explicit recovery metadata, or report missing if no predecessor exists. Under
the next date lock, reconcile the interrupted publication and preserve an
auditable recovery receipt. Keep GET free of writes. The root owner proposed
this approach during the review; it is logically sound and needs regression
verification against the retained crash test.

### IR-02 — P1 — Saved calculation and input integrity is not checked on read

Path: `V5/src/v5_shadow/a_close_daily.py`, `_read_run`, lines 457–478.

The reader verifies record JSON and the original store's three output files,
but it never reads `calculation.json`, saved source files, or the admitted
panel. Their hashes are recorded or derivable, but are not enforced after the
initial computation. A saved immutable input can therefore be corrupted while
the ordinary API still reports `read_status=VERIFIED`.

`test_reader_rejects_mutated_calculation_or_input_snapshot` independently
corrupts each of `calculation.json`, `inputs/source/panel.json`,
`inputs/admitted_panel.json`, and `inputs/source/members.txt` in a successful
run. All four reads incorrectly remain VERIFIED.

Recommendation: verify the raw/canonical calculation digest against the
record, its date and execution identity, every referenced saved source digest
and size, the admitted panel digest, and the required pointer/manifest links
using bounded SafeRoot reads. Reject corrupted/missing run evidence on direct
read, cached reuse, publication, and rollback without changing the old head.

### IR-03 — P1 — A running process can attest code it did not execute

Path: `V5/src/v5_shadow/a_close_daily.py`, `_implementation_identity`, lines
412–415.

Identity hashes current on-disk daily/contracts/digests bytes, without binding
them to the implementations already imported into a long-lived process. The
frozen source loader pins its own executing source, but this protection is
missing for the daily implementation and its directly imported helpers.

`test_loaded_daily_code_does_not_claim_changed_on_disk_implementation` copies
the candidate, imports daily in a fresh process, then inserts a mandatory
exception into the on-disk public run entry. The already imported code still
produces a successful review and records the changed file SHA as its executing
daily implementation. Neither the reviewed snapshot nor after is modified.

Recommendation: capture trustworthy executing-module identities at import and
reject source replacement until restart, including daily, contracts and digest
helpers; pin/check the worker launch bytes as well. Continue binding the
separately frozen capsule. In-place deployments must not relabel cached Python
code with new source identities.

### IR-04 — P2 — API raw-review digest is not linked to the hashed record

Path: `V5/src/v5_shadow/a_close_daily_api.py`, `_validate_committed`, lines
60–67.

The raw-review digest receives only hex-format validation. The projector does
not check its equality to the date-specific review entry in the hashed
record's `store_files`. Replacing only `identity.raw_review_sha256` with 64
zeros preserves every currently enforced canonical/record/generation check
and yields VERIFIED output advertising that false raw SHA.

`test_api_rejects_unbound_raw_review_digest` reproduces this using an actual
successful synthetic run returned by the committed reader.

Recommendation: bind the raw-review identity to the exact T review entry in
`record.store_files`, and validate required raw file metadata structure. This
was sent directly to the API owner, who confirmed it and is implementing the
check separately from the pending native-chain/constant checks.

## Preserved RED evidence

- `test_review_findings.py`: 3 tests, 6 assertion failures on the frozen tree.
  Full logs and actual command/time/exit metadata are in
  `independent_review_red.stdout.log`, `independent_review_red.stderr.log`, and
  `independent_review_red.json`.
- `test_api_raw_digest.py`: 1 test, 1 assertion failure on the frozen tree.
  Full logs and metadata are in `independent_api_digest_red.stdout.log`,
  `independent_api_digest_red.stderr.log`, and
  `independent_api_digest_red.json`.

These expected RED assertions are concrete candidate failures, not passed
acceptance tests. The scripts accept `M09_REVIEW_SNAPSHOT` to select a separately
fixed candidate for subsequent GREEN verification. Known pending worker-root
binding and complete native-chain checks were intentionally not duplicated.
