# M17 guarded real default collector path

This increment corrects the intentional SIMULATED-only limit of ef2d2a0d4a87fc96e90a1d91f106267ca24c2b97.
The previous candidate and its 17-test/Mac evidence are preserved unchanged in
integration_candidates/M17 and in their fixed commits. No old 17 cases or old four
vendor controls are rerun in this increment. This candidate is a separate complete
runnable after tree; the two-file forward patch applies on the ef2d candidate.

## Original real interfaces are present

The fixed 24-file owner closure already includes:
- ops/materialize_manager_close_discovery.py::recapture_close_minutes
- scripts/live_acquisition/pytdx_exhq.py::collect_pytdx_exhq_minute
- scripts/live_acquisition/pytdx_exhq_probe.py::_connect_first_available and collect_payload
- the existing TdxExHq_API call, original 64-code bounded batches and aggregation

The external installed pytdx package is an existing-runtime dependency, not a
missing owner algorithm. This cloud runner has no PyTDX installed. Nothing is
installed here; absent runtime evidence correctly blocks real execution.

## Complete default call, gated by concrete binding

Use execution_kind=OWNER_VERIFIED with config.real_binding containing exactly:
active_capture_mode, pytdx_python, pytdx_python_sha256, pytdx_exhq_sha256,
provider_root, state_root, universe_root.

- active_capture_mode must explicitly be PYTDX_LATE_OBSERVATION.
- state_root and universe_root must exactly match the outer config, exist as
  distinct absolute non-symlink roots, and never overlap the frozen owner root.
- The private real state root marker .v5-m17-close-root must contain
  v5.m17.close.v1 followed by newline. Simulated roots use the different existing
  marker v5.m17.simulated-close.v1; the modes cannot cross-write these roots.
- provider_root is exactly owner_root/upstreams/v3_shared_data, already verified
  by the 24-file source manifest; no arbitrary provider module or callback.
- pytdx_python is the explicitly selected existing absolute interpreter. Its
  actual executable bytes must match pytdx_python_sha256. Symlinked virtualenv
  interpreters are accepted only after resolving and hashing the actual binary.
- A fixed read-only/no-network runtime probe under that interpreter checks
  pytdx.exhq availability and verifies its module bytes against pytdx_exhq_sha256.
  This pins the binary and PyTDX entry module, not every installed transitive
  library or the operating system. No credential or environment-secret read.
- research_cutoff is the real request time, cannot be in the future, and is not
  injected as the capture clock. Simulated clock/quote fields are rejected in a
  real request. Natural verification remains false until separate evidence exists.

With a valid binding and runtime, the producer calls the ORIGINAL
recapture_close_minutes without any clock or pytdx_collector injection. Its
original default collect_pytdx_exhq_minute runs. The only transport wrapper admits
exactly the bound interpreter and -m scripts.live_acquisition.pytdx_exhq_probe,
original source date/STAGE_1545_1555, shell=False and original bounded timeouts.
It passes only a minimal safe environment and the frozen provider PYTHONPATH;
it does not inherit HOME, credentials or unrelated environment values.

Missing binding, invalid roots/fingerprints, missing PyTDX or runtime fingerprint
drift produce explicit BLOCKED/INPUT_MISSING before collection. Real requests are
no longer permanently blocked merely because they are real.

The real worker budget permits the original executor's 420-second maximum;
the original collector keeps its 64-code batches and 180-second per-batch cap.
The previous 120-second simulated-only ceiling is not reused for real operation.
No original window/qualification/PIT logic is changed. The owner still enforces
current/previous HK_CONNECT full session and same-day >=15:55:05; source/plan and
actual captured_at/available_at remain separate. No collector runs for GET.

## Unknown outcome, readback, and safety

Lost worker, subprocess timeout, signal death or start uncertainty retain the
original RUNNING ledger claim. A narrow internal BaseException sentinel prevents
the frozen collector's broad except Exception from downgrading a lost real probe
to a confirmed FAILED receipt. No automatic retry is enabled.

Producer -> new reader -> external D1 pool -> four byte hashes -> five-field
finish -> read_run is unchanged. PARTIAL, OBSERVATION_ONLY, non-final-close and
currency/unit UNKNOWN remain visible. The new reader process performs no runtime
collector preflight, accepts no child process, and keeps no-network/no-write guards.
Producer itself also keeps network guards; only its explicitly bound fixed probe
child may use the existing original network API when real execution is authorized.
These are Python/code-level guards, not a claim of an OS sandbox or new OS grants.

## What was actually tested

Only the new gate/real-default-path suite was executed. Its test-only isolated
harness substitutes TdxExHq_API at the network boundary while retaining original
collector, probe, batching, aggregation, actual current owner clock, producer,
independent reader and ledger logic. It proves 64+36 calls over 100 synthetic
rows, guarded binding checks, explicit unavailable-runtime blocking, and no false
terminal failure on transport timeout. All such outputs are
SYNTHETIC_NETWORK_BOUNDARY evidence, never real market or natural-run evidence.

No real probe connection, installation, credential access, permission change,
P0/V4 mutation, page deployment, or scheduler activation occurred.

## Mac incremental command

In a fresh isolated checkout at this increment's returned commit, use the existing
Python that already contains FastAPI:

    /absolute/existing/python -I -B integration_candidates/M17_REAL/after/V5/tests/test_daily_close_recapture_real_binding.py

Do not run the old 17-test file again. It is included byte-identically only for its
fixture helper, not imported as a test suite. The runtime-unavailable case may
skip if PyTDX is already installed; synthetic boundary cases still exercise the
real default path without a network request. Report pass/fail/skip separately.

## Remaining integration, not concealed as completion

Actual Mac interpreter/PyTDX fingerprints, private real output root, exact D1 pool
root and verified active capture mode must be explicitly bound before any real
execution. P0's independent evening dispatch/tick registration and approved slot
remain the sole integrator's work; never use the morning default. No request to
perform real collection is implied by this candidate's publication.

1530 still has deferred-import/runtime assembly and real-input gaps described by
the prior M17 integration request. Continuous tracking, real-source acceptance,
page publication and natural triggers are not established by either unit's tests.
