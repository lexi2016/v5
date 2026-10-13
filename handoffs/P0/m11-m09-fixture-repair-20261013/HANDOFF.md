# Narrow M09 synthetic-fixture environment repair

## Root cause and preserved boundary

Mac feedback `347bbc10ca344ad96e47bdadb3715cecfefd29ce` passed all 117 M11/Python acceptance cases but stopped the Node suite when the inherited M09 synthetic fixture raised `M09_ADMITTED_FRAME_TEXT`. Its second input row intentionally has `tdx_industry_code=None`. The frozen historical validator accepts None or strings, and correctly refuses a floating-point NaN in a text field.

The M09 fixture factory, frozen validator, historical snapshot code and original Node fixture test were all byte-identical before and after M11. This is an inherited fixture-environment compatibility issue, not an M11 strategy change. Cloud pandas 2.2.3 retains None in the default object column. The pandas 3 default string-inference behavior converts missing text to NaN, as described in the [official migration guide](https://pandas.pydata.org/docs/user_guide/migration-3-strings.html). The [official 3.0 configuration implementation](https://raw.githubusercontent.com/pandas-dev/pandas/v3.0.0/pandas/core/config_init.py) supports PANDAS_FUTURE_INFER_STRING=0. The exact existing Mac version/option scalar probe is recorded separately when returned; the Mac refusal itself is already fixed-commit evidence.

The only existing-file edit passes that compatibility setting in the M09 synthetic exporter's subprocess environment. It propagates to both the original producer and the separate original cold reader. The Node parent and all other module fixtures keep their environment. No production runtime, frozen-owner bytes, actual saved data, source rows or existing assertions change. This does not certify arbitrary production M09 data under a changed pandas version.

The new regression observes the actual exporter spawn, requires the child setting to be 0 even when the Node parent has 1, and then forwards to the real original exporter/producer/cold reader and executes its unchanged contract tests. It does not stub a successful owner or delete conditional cases. The original None, empty strings and numeric NaN remain in the fixture.

## Exact two-test-file overlay

Apply only the two files in SOURCE_CLOSURE.json to the existing isolated M11 acceptance tree. Both have deploy=false. Keep the 74 runtime files from M11 `490529f549324fb435af56d5f728672ad6390b72` unchanged. No Python117 repeat is needed because no Python/product file changed.

With the existing Mac Python and Node paths, run from candidate/frontend:

    PYTHON=<EXISTING_MAC_PYTHON> PATH=<EXISTING_NODE_BIN>:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 TMPDIR=<ISOLATED_TASK_TMP> node --test tests/aCloseReplay.node.mjs tests/m09FixtureEnvironment.node.mjs tests/m11SavedResearch.node.mjs

Expected: all 26 top-level cases register and pass. This explicitly includes all seven previously unregistered conditional M09 cases. Do not call the earlier 115/116 run a full-suite pass.

After that passes, continue the previously unreached M11/M04/M12 Vue DOM checks, typecheck, build and read-only preview checks from the original M11 handoff. No dependency install, production configuration change, M11 acquisition service or real data binding is part of this repair. Keep absent M11 evidence WAITING.

Cloud: regression RED then GREEN; narrow 26/26 and full Node 124/124 passed. The latter adds one new environment regression to the original 123 cases. Mac repair acceptance remains pending until its own receipt.
