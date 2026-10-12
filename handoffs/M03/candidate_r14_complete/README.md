# M03 R14 complete cumulative candidate

This candidate implements the default US source chain in one complete module. It preserves R11's request and helper names and integrates R13's multiline fresh-process reader. It does not replace the module with a reader slice.

## Scope and fixed dependencies

- Base branch commit: `91b799d04ee42e2a5bacec035eacdafa8ef65ad7` on `dev/m03-github-handoff-20261011`.
- Original source: `../source`, all 63 files checked by bytes, SHA256 and Git blob. The descriptor pins all 48 owner files at `164c010c7eaa1659db9bfed0ff5f123c7a39eefc`.
- Only the five files under `after/V5` are new or changed. No owner, descriptor, PIN, transport guard, historical source, reference, review, V4, other module, gateway, scheduler or preview file is changed.
- POSIX Python with the original `SafeRoot` and `zoneinfo` support is required. Linux Python 3.12.14 was tested; Mac is a separate acceptance step.

## Runtime contract

Public entry: `run_us_source(USSourceRequest(...))`. The original nine request fields are retained. Additional optional fields default to safe read/reuse operation:

- `allow_network_capture=False`
- `capture_root=None`
- `allow_late_post_close=False`
- `development_dates_file=None`

The entry starts a fresh owner worker. Original `load_owner`, descriptor validation, module-origin auditing, store validation and calendar/window rules remain in use. Collection and reading use separate fresh `sys.executable -I -B` children. Low-level binding helpers run inside this pinned worker; consumers should call the public entry rather than import owner modules into the caller.

Qualified existing source is reused without collection. Only a genuinely absent exact source may reach the explicit collection gate. A malformed or rejected existing source is not silently replaced by a collection attempt. New collection writes to `capture_root`, not to `source_root` or the immutable snapshot. The original CLI supports a session date equal to the requested artifact date; a new-collection request with different dates is refused rather than collecting the wrong session. Existing target-date sources may still be read when their explicit session identity matches.

All source, capture, snapshot, binding and code/owner roots must be absolute, symlink-free and mutually disjoint. Private data roots use the original initializer and marker admission. Existing unmarked roots are rejected, never marked retroactively. A source that is absent stays absent when collection is disabled.

**`snapshot_root` identifies one immutable complete three-file generation, including the original manifest bytes.** Supply a different, disjoint snapshot root for a later date, capture, changed source, or changed manifest. Do not use one snapshot root as a rolling daily store. The binding root may hold multiple immutable request bindings. Concurrent identical requests reuse the same verified binding. Conflicting snapshot bytes and binding contents fail closed. Failed work does not overwrite an older successful binding.

The chain takes stable original payload/receipt/manifest bytes, independently reads their source contract, copies exactly those bytes through original `SafeRoot.write_bytes(require_absent=True)`, and runs the original store reader in a fresh child against that same snapshot. It checks the selected capture is unique, session/phase/date/cutoff agree, and the snapshot is eligible. Physical SHA256 values refer to the snapshot that was actually read. An initial READY source changing to a valid CANNOT_CONFIRM source is rejected before freezing the rejected snapshot. Every reused or newly published binding is reread from disk and its references and original-reader result are independently revalidated. Publication uses the original persistent kernel locks and atomic no-replace IO with fsync and temporary-file cleanup. The orchestrator import-time SHA is checked before execution and on exit to reject an in-process disk version change.

Statuses are explicit:

- `VALIDATED_SOURCE_BINDING`: verified source; `source_status` distinguishes READY from valid empty READY_EMPTY; capture identity retains historical/late information; safety flags remain false.
- `SOURCE_MISSING`: capture is not enabled, or collector returned zero but no original source exists.
- `NOT_DUE`: original calendar/window or PRE_OPEN quote-not-due condition.
- `SOURCE_REJECTED`: an original readable source is not eligible.
- `COLLECTOR_FAILED`: nonzero collector result, with original stdout/stderr/returncode.
- Integrity, identity, IO and child execution/JSON/type/timeout failures raise their diagnostics; they are not converted to absence.

A valid historical research-only source uses the original historical paths and reader. New historical collection additionally requires the original development date allowlist. A valid late source can be reused read-only; `allow_late_post_close` controls the original new-collection CLI. No test clock, synthetic provider or custom fixture is wired into the production default.

## Isolated assembly and tests

From a checkout of this fixed candidate commit, make a new disposable code directory outside any data root. Copy the complete `handoffs/M03/source/V5` into it, then overlay `after/V5`. Leave `handoffs/M03/source/collector_owner` untouched. Set `M03_FIXED_SOURCE` to the absolute `handoffs/M03/source` directory and run:

```sh
M03_FIXED_SOURCE="$CHECKOUT/handoffs/M03/source" python3 -B "$WORK/V5/tests/run_m03_offline_suite.py"
```

The runner executes every original collector and transport test body unchanged, substituting only the old git-show assembler setup with the already published 48-file owner. The new fixture extracts the exact original synthetic Proxy/Direct/socket-audit producer script from the fixed source test. Extended variants alter only test clock/provider seams. No real socket, real capture, credentials or orders are used.

`TEST_REPORT.md` distinguishes actual offline results from work not run. Scheduler/API/UI consumption is specified separately in `INTEGRATION_REQUEST.md`; this candidate does not modify or deploy them.

## Exact patch and rollback

`MANIFEST.json` gives every before/after SHA256, byte length, Git blob and fixed source path. The before tree is an explicit assembly baseline: R11 complete module and test plus R13 reader test. It is not a claim that those three paths formed one old runtime commit. R13's reader implementation is separately recorded as the algorithm source.

For a disposable tree containing this exact before assembly, run `git apply --check runtime.patch`, then `git apply runtime.patch`. The genuine reverse patch is `reverse.patch`; check and apply it to restore exact before bytes and remove the newly added test helpers. Forward and reverse were applied and checked byte-for-byte in isolation. Never apply either patch blindly to a different runtime baseline. For a clean isolated tree made from the original source, overlaying the five complete after files is sufficient and avoids inventing an old runtime baseline.
