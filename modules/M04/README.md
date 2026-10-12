# M04 captured-input archive owner bridge

This is the existing M04 research/archive module, not a new module. Branch `dev/m04-github-handoff-20261011` was actually created on 2026-10-12 from verified private-v5 baseline `d3ebf33c40d1b5f06e3729b11d5ece0506f34c91`, after all 31 branches were checked and no M04 branch existed. Main, P0, other modules and V4 are unchanged.

## Delivered minimum chain

`source/V5/src/v5_shadow/research_ingest_daily.py` provides explicit `run` and read-only `read` CLI commands. Its default path is the unchanged frozen `archive_builder_v1.run_build` (original collector and full archive owner), unchanged `archive_article_v2.run_import` (original archive store), then independent `archive_reader.read_private` in a fresh process. No callback replacement of these owners and no new algorithm.

The input is an already captured original batch, with the exact existing builder contract: `capture_root`, `capture_files`, `receipt`, `status`; the sole new field is an independently marked private `state_root`. The capture must already have the acquisition marker and complete original same-batch status/pages/recent/summary/receipt evidence. The state marker is `.v5-research-ingest` containing `v5.research-ingest.v1\n`. Capture and state roots must be absolute, nonsymlink, distinct and non-overlapping. No V4 root is inferred or opened.

The original builder enforces current-day binding. Old or incomplete batches are not relabelled current. This command does not acquire data, invoke credentials, run a schedule, publish a preview, or fill missing PIT clocks. Live acquisition remains a separate explicit operation using the original producer and verified independent CLI/selector/source paths. Its old default paths must not be used by a V5 launcher.

## Retry semantics

- Same request and same code identity returns the same immutable successful reference after byte checks and independent cold read, with no new owner run or write.
- An exclusive per-state writer lock rejects concurrent writers. Input/code changes create a different run identity; previous success remains intact if the new attempt fails.
- A fully checkpointed builder result can be resumed by the unchanged import owner, which revalidates all source/receipt/replay bindings.
- Import retries use a new private import root. Failed attempts and original evidence are retained; success is never overwritten.
- An interrupted builder without a complete checkpoint remains blocked by its original exclusive slot guard. It is not silently rerun and its evidence is not overwritten. Recovery needs an explicitly valid fresh captured attempt; no fabricated new capture is created here.
- Private `latest_attempt.json` and `latest_success.json` are distinct. They are not the global preview release pointer. Global expected-generation/CAS publication remains with P0.

## Source provenance

All source baseline bytes come from the original M04 package fixed at V4 `f7cb731c384ee6890a87d16c19a5b5a621779477`. Only the new bridge and its tests are runtime changes. The frozen capsule and original producer bytes/manifests remain unchanged. See SOURCE_FILES.json for each source identity and upload/blob reuse.

The one required frozen producer, blob `6b6d88cdc421a1f561fbbbdada3f33154f3a570f`, is migrated unchanged from https://github.com/lexi2016/v4/blob/f7cb731c384ee6890a87d16c19a5b5a621779477/V5/producers/archive-acquisition-v2/source/ops/run_zsxq_hourly_delta.py . Its two legacy path constants identify an executable and a securities input file; no credentials, local file contents or business payload are included. They are retained only to preserve the receipt-bound producer SHA. Three historical Mac reports and the unused canonical old producer are deliberately excluded from this delivery; none is needed by this offline chain.

The original namespace dependency is the already-declared vendor structural mapping, not a missing canonical discovery. `scripts/test_offline.sh` creates the exact isolated assembly and verifies all 15 dependency SHAs without changing the canonical source or manifest.

## Execution

From repository root, choose the existing verified interpreter, then run:

    PYTHON_BIN=python3 sh modules/M04/scripts/test_offline.sh

The script prints its temporary dependency root and runs only the 14 bridge-focused tests. Set `M04_TEST_SCOPE=all` to run all supplied V5 tests when a full regression is required. It installs nothing. On Mac use the existing approved interpreter path, not a guessed new environment. This is offline synthetic provider input and original owners, not real data acceptance.

After verifying private roots and preparing the JSON request locally:

    PYTHONPATH=modules/M04/source/V5/src "$PYTHON_BIN" -B -m v5_shadow.research_ingest_daily run < request.json > result.json

To cold read only, supply `archive_binding` from the successful result as the JSON input:

    PYTHONPATH=modules/M04/source/V5/src "$PYTHON_BIN" -B -m v5_shadow.research_ingest_daily read < binding.json

No input/body payload is included in GitHub. A future GUI/GET must use only `read`/the original reader; it must never invoke `run`.

## Evidence and open scope

See TEST_REPORT.md and INTEGRATION_REQUEST.md. This completes a bounded offline captured-batch archive bridge, not every M04 lane, natural capture, real-data/PIT qualification, deployment or whole-module acceptance. The 3075 missing retrieval clocks and 175 missing topics remain recorded limitations, not repaired facts.
