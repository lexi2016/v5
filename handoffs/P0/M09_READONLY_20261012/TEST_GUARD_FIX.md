# M09 Mac acceptance: test-only optional-PyArrow correction

## Verified cause

Feedback commit `57050f34b2229f096c994377a5086a063d8a7f23` records 26 Python passes and one failure at `assert 'pyarrow' not in sys.modules`, after the actual original cold read had succeeded. The same fixed candidate passed the real 20261012 GET/original-projection comparison, all 41 Node tests, component DOM tests, product typecheck and build. It was not deployed.

The failing assertion confused dependency initialization with source preparation. pandas 2.3.3 normally imports an installed PyArrow package to inspect its version in its [official compatibility module](https://github.com/pandas-dev/pandas/blob/v2.3.3/pandas/compat/pyarrow.py). An import alone is not a producer or source-Parquet operation. The required historical typed-row validator uses pandas; no runtime defect is demonstrated by this test failure.

## Minimal change

Only `V5/tests/test_m09_readonly_api.py` changes executable code. Product API, worker, frozen owner closure, frontend, build inputs, reference bindings and every saved result remain byte-identical to candidate `65b3bea261a3a48d6a4ea481420e743dc84e8ec6`.

The corrected single test:

- Allows normal pandas/optional PyArrow initialization, with no requirement that PyArrow be absent.
- Retains explicit blocking sentinels for original producer/module access and adds root initialization and raw source-Parquet preparation entrypoints.
- Installs an operation audit guard for file writes/mutations, network operations and child-process creation during the reader invocation.
- Executes 13 negative controls before reading: nine blocked production/preparation/initialization functions, one blocked original producer-module load, one blocked temporary file write, one blocked loopback connection and one blocked child process. Each must be rejected before its side effect.
- Clears the control counters, runs the actual unchanged cold worker, requires zero guarded attempts, compares the full original review, and verifies the whole temporary source/run tree is unchanged.

The guard is test-only; it does not alter any system permission, security setting, installed dependency or product behavior.

## Targeted cloud evidence

The corrected test passes with the current existing Python/pandas environment. An additional test-only mutation disables the audit hook in the subprocess harness; that mutant fails exactly with `GUARD_DID_NOT_BLOCK:file_write`. Its only possible write target is a disposable synthetic fixture root. This establishes that the side-effect test is not vacuous.

The cloud does not have installed PyArrow. Supported Mac compatibility still needs the single test below, rather than treating the cloud result as a Mac pass. No complete suite, frontend rebuild, real source collection or historical producer rerun was performed for this correction.

## Mac: rerun only the previously failing item

From the isolated checkout of the exact correction commit, using the existing Python 3.14.6/pandas 2.3.3/PyArrow 24.0.0 and a non-symlink task-owned TMPDIR, run this one command. It verifies the checkout and runs only the named test:

```sh
TMPDIR="<TASK_OWNED_NON_SYMLINK_TEMP>" <EXISTING_PYTHON_3.14.6> -I -B -c "import sys,unittest; from pathlib import Path; sys.path[:0]=['V5/src','V5/tests']; from run_m09_readonly_acceptance import verify_checkout; verify_checkout(Path.cwd(),sys.argv[1]); suite=unittest.defaultTestLoader.loadTestsFromName('test_m09_readonly_api.M09ReadOnlyAPITests.test_cold_worker_cannot_call_owner_producer_or_source_preparation'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==1 and not result.skipped else 1)" <EXACT_CORRECTION_COMMIT>
```

Return the exact checkout commit, exit code, `1 PASS / 0 skip` or precise failure, actual Python/pandas/PyArrow versions, and confirmation that runtime/frontend source hashes still match the previously tested candidate. Keep the original failed feedback intact. A successful retry resolves only this failed test; the prior real GET/Node/DOM/typecheck/build results belong to unchanged product bytes and must be referenced as such. Preview activation remains a separate, explicitly verified action.
