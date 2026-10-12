# Existing Mac isolated acceptance

Use the original development branch at the fixed resulting commit supplied by the parent, in an isolated worktree. Do not run against active V4 or change preview/54780, accounts, credentials, security settings, owners, manifests, or models. Use the existing Python/dependencies only.

## One-command module suite

From the repository root:

```sh
python3 V5/tools/run_m02_isolated.py
```

The harness verifies all 72 original source handoff SHA256 values before copying them into a disposable temporary tree. It overlays only this candidate and runs the supported module/regression suite. It does not import or install the absent manager business module. To reproduce the full-discovery boundary, `python3 V5/tools/run_m02_isolated.py --all` also exposes the two retained manager-reference import failures.

## Default three-owner positive control with local frozen assets

The parent already located a local frozen asset root and verified it through the unchanged original loader. Do not upload that root, model, panel, names, or private path. Supply that verified local root in the environment for this single test run:

```sh
M02_REAL_ASSET_ROOT="<verified local asset root>" python3 V5/tools/run_m02_isolated.py
```

`test_all_three_original_readers_with_real_frozen_assets` now runs without mocking any of the three readers/loaders or changing PINs. It creates original-owner synthetic membership/native fixtures in temporary roots, binds the local unchanged real panel/model/name assets, commits and independently reads back. The fixture target/reference dates are 20261009/20261008 and the original HK calendar is used. A newer panel is permitted only for reference identity; all PIT, historical and formal eligibility fields remain False. No future acquisition, future real data, scoring, inference, model deserialization, external transmission, or asset mutation is needed.

`test_all_three_unmodified_readers_roundtrip` remains a separate optional test for a complete caller-supplied request JSON; without such a request it is explicitly skipped. Do not count that skipped test as passed.

## Build a complete request for already available original source outputs

In an isolated V5 overlay, use `V5/tools/prepare_m02_request.py` with:
- `--asset-root` the verified local frozen root
- `--membership-binding` a local JSON containing the exact original `{root, files}` seven-file mapping
- `--native-binding` a local original native `{root, files}` mapping
- `--private-root` an existing empty private output root initialized with the marker specified in README
- Explicit `--target-date`, `--signal-date`, `--eligibility-source-date`, and timezone-aware `--cutoff`

The tool only reads these inputs and prints request JSON. Redirect it to a file inside the isolated acceptance directory, then run the suite with `M02_REAL_FIXTURE_REQUEST="<local request JSON>"`. Do not commit that JSON: it contains local paths. Missing real source bindings are an acceptance-input gap, not a reason to fabricate them or block source implementation.

Acceptance evidence must distinguish source unit/negative tests, original-owner synthetic fixtures, real frozen asset smoke, complete real-source request, and natural/production runs. The latter two are not established by a synthetic fixture. Preserve source SHA, private binding/receipt identity and flags, and report actual skips/failures.
