# M14 bounded history source recovery candidate

## Execute the canary first

This package adds an independent, explicit research-only capture command. It does not change the running source API or preview, run an owner, publish a repair, or write any V4 asset. It reuses the frozen original PyTDX connector and raw decoder source. Real provider availability is **NOT_RUN** until the Mac executes the canary.

The initial scope is **HK.00001, HK.02825, HK.03469**, one request per code, **category=4 / market=71 / start=0 / count=120**, one connection, no retry, no fallback host. The source is the existing 119.97.142.130:7721. The existing Mac Python 3.13.12 / pytdx 1.72 environment can run this standalone capture; no installation is requested. This does not bypass the original owner's separate Python 3.14 runtime check.

The original collector is pinned at SHA256 `fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd`, its manifest at `057a2c453ae562bc94564829dd8f78aba2b303bb7182a0b493fde9d4bedbafcd`. Only its unchanged `_canonical`, `_clock`, `_connect` AST functions are loaded. The original six-bar collector is not run or replaced. The bounded request extension is this candidate's contribution. The SDK method takes offset/count, not start/end dates; the primary SDK source confirms that signature: [pytdx exhq](https://github.com/rainx/pytdx/blob/master/pytdx/exhq.py). The untracked Mac count128 implementation is not included or used.

## Prepare the actual task from existing bound inputs

Use the original inspected owner `V5` directory as `V5_ROOT`, the current source API config as `SOURCE_API_CONFIG`, and the original existing V5 HK02 asset root as `HK02_ASSET_ROOT`. The asset root is the directory containing `panel_latest.json`, not the `.day` directory and not the M14 result root. `TASK_JSON` must be a new path inside the Mac task evidence directory. Do not put private roots or raw rows on GitHub.

The following is offline. It rechecks the original four-reference reader, exact dates, bound panel bytes and current parent pointer, uses the existing native calendar, and writes only the bounded canary task. It does not call a producer.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$V5_ROOT/src" "$PY_M14" -B - "$SOURCE_API_CONFIG" "$HK02_ASSET_ROOT" "$TASK_JSON" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
from v5_shadow import rebound_owner as owner, rebound_panel_repair as repair
from v5_shadow.composition import no_symlinks
from v5_shadow.digests import canonical_bytes

config = owner._json(no_symlinks(sys.argv[1]).read_bytes())
binding = config['m14_rebound_binding']
artifact = owner.read_rebound_owner(binding['private_root'], binding['reference'])
request = artifact['request']
assert (request['target_date'], request['signal_date']) == ('20261014','20261013')
asset = no_symlinks(sys.argv[2])
prefix = 'assets/hk_0_2/'
manifest_rel = request['paths']['panel_manifest'].removeprefix(prefix)
panel_rel = request['paths']['panel'].removeprefix(prefix)
pointer_raw = repair._read(asset,'panel_latest.json')
assert owner._json(pointer_raw)['manifest_relative'] == manifest_rel, 'PARENT_POINTER_CHANGED'
manifest_sha = hashlib.sha256(repair._read(asset,manifest_rel)).hexdigest()
panel_sha = owner._file(asset,panel_rel)['sha256']
assert manifest_sha == request['files'][request['paths']['panel_manifest']]
assert panel_sha == request['files'][request['paths']['panel']]
codes = ['HK.00001','HK.02825','HK.03469']
keys = [dict(code=code,date=day) for code in codes for day in ['20261005','20261006','20261007']]
keys += [dict(code=code,date='20261012') for code in codes[1:]]
window = repair._history_window(request['signal_date'])
assert all(key['date'] in window['prior60'] for key in keys)
task = dict(schema_version='v5.m14_history_capture_task.v1', target_date=request['target_date'],
 signal_date=request['signal_date'], canary_codes=codes, keys=keys,
 expected_panel_sha256=panel_sha, original_reference=binding['reference'],
 parent_binding=dict(parent_pointer_sha256=hashlib.sha256(pointer_raw).hexdigest(),
 parent_manifest_relative=manifest_rel,parent_manifest_sha256=manifest_sha,
 parent_panel_relative=panel_rel,parent_panel_sha256=panel_sha))
output = no_symlinks(Path(sys.argv[3]).absolute())
with output.open('xb') as stream:
 stream.write(canonical_bytes(task)); stream.flush(); os.fsync(stream.fileno())
print(json.dumps(dict(status='BOUNDED_TASK_PREPARED_OFFLINE',code_count=3,key_count=len(keys),
 task_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),calendar_sha256=window['calendar_sha256'])))
PY
```

The dates/codes above come from the completed Mac missing-key audit. If its parent pointer has since changed, stop and rebind the actual saved original revision in the existing V5 private workspace; do not silently replace the reference with latest or manufacture a capture time. This initial task tests 11 known missing keys only. It is not a full-pool repair task or a declaration that other dates are complete.

## Exact canary commands

`CANDIDATE` is this folder. `PLAN_DIR` and `CAPTURE_DIR` must be two different, previously absent directories under the existing private task directory. Use physical paths: the no-follow boundary rejects symlink components, including a symlinked `/tmp` alias. The source and output paths never come from an HTTP client.

```sh
V5_HISTORY_TEST_BASELINE_ROOT="$V5_ROOT" PYTHONDONTWRITEBYTECODE=1 "$PY_M14" -B -m unittest discover -s "$CANDIDATE/capture/tests" -v

"$PY_M14" -I -B "$CANDIDATE/capture/v5_shadow/rebound_history_capture.py" plan \
  --task "$TASK_JSON" --baseline-root "$V5_ROOT" --output-dir "$PLAN_DIR"

PLAN_SHA=$("$PY_M14" -I -B -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$PLAN_DIR/plan.json")

"$PY_M14" -I -B "$CANDIDATE/capture/v5_shadow/rebound_history_capture.py" capture \
  --plan "$PLAN_DIR/plan.json" --plan-sha256 "$PLAN_SHA" \
  --baseline-root "$V5_ROOT" --output-dir "$CAPTURE_DIR"
```

Only the last command contacts the existing source. Each native response record has its exact request, request SHA, whole SDK-decoded source rows, response SHA, returned count and actual request-start/response-acquired/request-finished times. These are SDK response rows, not alleged TCP wire bytes. Connection/query errors receive create-once private receipts. The original source rows are not scaled, filled, filtered, re-dated, or merged into a panel. Future rows remain present and explicitly block the existing decoder; no later row is silently dropped to make an old signal pass. A successful request does not prove all keys exist or that units match.

The result provides `sources=[{relative,sha256,record_pointer}]` directly consumable by the existing `rebound_raw_repair.decode_raw_repair`. Keep all original receipts locally. Report only status, query counts, returned date range/counts, exact requested-key coverage, error codes, raw-file hashes and protected-input unchanged hashes. `repair_ready`, `formal_eligibility_verified`, `natural_verified`, production/buy/order flags stay false.

No full-pool loop is enabled in this canary. Successful source availability is the evidence needed before selecting the subsequent bounded recovery task; failure must be returned with the real receipt, without alternate hosts, retries or invented rows.

## Optional existing-witness owner connection, not active in the canary

`optional-owner/` contains a two-file exact-preimage candidate: complete `rebound_owner.py` after-image and focused tests, plus the existing hash-checking apply helper and patch. The only product-file preimage is `dc1b68715ba38a97a1df029a1934dab58b84b7f7486cb60b2a75a4d71491aa15`, which the Mac confirmed equals its original 884548 owner checkout, saved manifest and running copy. This matches the P0 c7b/386d source; it does not claim 884548 is available as a GitHub commit.

The optional branch adds explicit `panel_receipt`, `repair_parent_manifest`, `repair_parent_panel` roles. It SHA-binds child/parent/receipt, invokes the **existing** `read_repaired_panel_witness`, and substitutes only that verified panel-witness function inside the isolated worker. Original calculator/calendar/strict-near-pending-excluded-unresolved arithmetic, raw decoder and panel-repair implementation stay unchanged. The new roles cannot mix in a daily supplement. Existing five/eight-role requests and old four-field saved references remain compatible. Additional repair/raw implementation hashes are bound only for new repaired requests, preserving old identity key sets. The cutoff is checked as an aware instant, including equivalent UTC/HK representations.

All original `BLOCKERS`, research downgrade, units/finality/target-membership unknowns and `CANNOT_CONFIRM` formal status remain. Adding authentic missing rows must not be described as formal approval. A new repair uses its real preparation time and a new suitable request cutoff. It cannot change the already saved result or backdate data into its cutoff.

**Do not apply or execute this optional owner path for the canary.** It is provided to remove the actual repaired-manifest consumer gap once a real receipt and the existing independently supplied `OwnerRepairAuthority` binding exist. The existing repair wrapper still supplies publication, parent preservation, source/capture identity and row-lineage verification; no new publisher or formal protocol is introduced. Its real Parquet/worker integration is NOT_RUN here and must be tested in the existing Mac environment before any actual owner execution or binding change.

## Verification

- Standalone capture candidate: **18 passed**, existing raw decoder used in synthetic compatibility tests; no network. Packaged bytes independently rerun by the integrator: **18 passed**.
- Optional-owner request, context, old-reference, raw-decoder and saved-page regression: **71 passed, 105 subtests passed**, exit 0.
- Original algorithm, raw decoder, repair implementation, capsule sources and API/page files were not edited by this package.
- Real provider capture, real repaired Parquet worker, owner run, active API binding and deployment: **NOT_RUN**. Cloud environment has no pyarrow; no dependency was installed to disguise this limitation.
- Changes are confined to this integration candidate directory on the original M14 development branch. V4 and the deployed fac269 page remain untouched.

Detailed capture contract and fixed source identities: [capture/README.md](capture/README.md). Optional owner before/after hashes: [optional-owner/verification.json](optional-owner/verification.json). Test outputs: [evidence](evidence).
