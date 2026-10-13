# M18 original request preparation and saved binding

This independent candidate extends the original M18 branch. It does not replace the P0 live tree. `V5/` contains the full fixed P0 V5 source tree from c7b815c065da83bd2db2b3023be4607ce9f194ec plus only the new preparation module and its tests. The eight files on M18 HEAD 0b3495b5ded5c0a6a132de1b10108c4d7ff761f6 have identical Git blob identities in that baseline. No source owner, algorithm, daily dispatcher, API, UI, V4 or existing artifact is modified.

## Entry and original contract

`V5/src/v5_shadow/manager_request_preparation.py` provides:

- `template(spec)`: completes the original read controls only. The caller must provide the original explicit `target_date`, actual nonfuture `now`, `inputs` roots/file SHA-256 maps, `rebound` (possibly null), and existing marked `manager_output_root`. Original optional announcement/rebound/membership/archive/native bindings are supported unchanged. It does not scan, copy, mint or re-date upstream references.
- `prepare(request)`: verifies original input file pins, invokes only `run_manager_plan(action='read', view='dynamic')` with a disposable empty plan root, and rereads all input pins. The original pinned owner performs its ordinary source/admission checks. An existing saved plan cannot masquerade as current input availability. Nothing is written to the input roots or real manager output root.
- `bind_saved(request, {run_id, plan_sha256})`: two separate original-owner read subprocesses must return the expected saved run, plan SHA, input identity and same-run attempt. A newer latest run causes refusal; it is never silently substituted. The original historical view remains available through the original request's view/cutoff. No refresh or API publication is invoked.

All three lanes must be complete before `manager_template` is returned. A genuine original consumed empty announcement or original US VALID_EMPTY is retained; absent products, mismatched dates/runs/SHA, rejected source sessions, or pending rebound are not empty success. A READY_WITH_GAPS rebound remains visible in the original reference and conservatively keeps preparation WAITING. The new code does not turn the existing 690 pending rows into a formal screen. M06 is not a substitute for the M13/M14/M15 references.

`manager_request` is always null: this read probe cannot grant a refresh authorization or bypass the original assembler/dispatcher. When complete, its `manager_template` is in the original schema for the existing `assemble_manager_request`; the existing 08:45–09:00 HK dispatcher must check the actual window and seal the actual cutoff. No old target12 reference is relabeled as target14. Future cutoff is refused by the original validator. Prepared is not executed, business accepted, natural, historical/PIT verified, published, or browser acknowledged.

## Mac one-time assembly (isolated only)

1. Fetch/check out this exact candidate commit on the authorized M18 development branch into an isolated V5 directory. Use only `integration_candidates/M18_request_binding/`; do not overlay the active P0/V4 tree or copy a moving branch HEAD over production.
2. Keep the original dependency bounds in `V5/pyproject.toml` (Python >=3.14, pandas >=2.3,<3, pyarrow >=21,<25). Use the existing authorized compatible environment. Do not install or expand credentials/permissions to pass. If unavailable, record locked-environment validation NOT_RUN. The cloud checks below do not establish that lock.
3. From the candidate root, with that interpreter, set `PYTHONPATH=V5/src:V5/tests` and run `python -B -m unittest test_manager_request_preparation test_manager_plan test_daily_manager_assembly test_m18_daily_publication`. These are isolated synthetic tests only. Keep the detailed broader baseline findings in verification.json separate.
4. Prepare a private original-schema request JSON using real root/file pins already saved by their original owners. Paths and hashes must be local to the Mac, not copied from a cloud fixture. The output root must already be the approved original V5 manager root with its existing `.v5-manager-plan-root` marker. Do not create a new live root or run owners to satisfy this step.
5. Once read-only use of the real inputs is in scope, run `python -I -B V5/src/v5_shadow/manager_request_preparation.py --request /absolute/private/request.json`. Output is JSON on stdout, not an installed bundle. Exit 2 is an expected WAITING_SOURCES result. Exit 0 is PREPARED_READ_ONLY, not execution approval. An explicit operator may save stdout to a new private file; never overwrite a current bundle blindly. This delivery itself has NOT run real inputs.
6. To bind an already saved manager result, supply `--saved-reference /absolute/private/saved-reference.json` with exactly its original `run_id` and `plan_sha256`. Output SAVED_READBACK_MATCHED proves the cold identity only; `three_lane_accepted` separately reflects original source admission. Failure is an error and never triggers refresh/retry/collection.
7. P0's single integration owner can consume the returned original template and existing saved binding through its already-fixed daily/API publication path after the real window and source conditions are met. This candidate does not modify those shared files or enable scheduling/daily opt-in.

Stop/rollback: do not invoke the CLI, or remove the isolated candidate from the next integration batch. No daemon, launchd job, current pointer or server has been installed. No live rollback is needed for this code-only delivery.

## Verification boundaries

New tests use temporary synthetic files. They cover missing inputs, SHA refusal, explicit date preservation, a refresh input forced to read-only, fresh preview despite a saved old plan, same-run saved cold binding, wrong-run refusal, CLI no writes and exit 2, original valid-empty projection, pending nonempty, cross-date, mismatched run, invalid empty-with-rows and missing fields. Original owner cold save/read is exercised only against synthetic temporary roots.

See verification.json for exact executed commands and limitations. Real provider/model/owner production, live manager save, actual current-day sources, HTTP/DOM, Mac deployment, browser ACK, PIT, formal qualification, natural run and complete-module acceptance are NOT_RUN. No network collection or trading is introduced.
