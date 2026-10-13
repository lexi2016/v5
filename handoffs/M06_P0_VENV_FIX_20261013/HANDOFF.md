# M06 pinned venv launch repair

Parent: `1ad98175e582ccc39e350341f97f5c9f9a97fa4e`. The Mac's actual `SYMLINK_REJECTED` and dependency probes were read from `handoffs/P0/feedback/mac-211fe3-m06-daily-20261013/`. Historical 21+9 Mac passes remain historical; they were not rerun here.

## Narrow change

Only `p0_hk_preselection.py` and the P0 `m06_daily_worker.py` change executable behavior. The unchanged original M06 owner, model, reader and ledgers remain fixed. An explicitly registered venv may launch its executable symlink while separately pinning the resolved executable. Source/input/output roots, venv root/bin directory, pyvenv.cfg and real binary retain the existing strict no-symlink checks.

For a venv, `python_executable` is the actual launch path, with canonical parent but an unresolved final leaf. `python_sha256` remains the existing real binary SHA256. Add this exact optional object to the private M06 registration:

```json
"python_venv": {
  "root": "<EXISTING_CANONICAL_VENV_ROOT>",
  "realpath": "<EXISTING_RESOLVED_BINARY_PATH>",
  "pyvenv_cfg_sha256": "<RAW_PYVENV_CFG_SHA256>",
  "symlink_sha256": "<SHA256_OF_OS_READLINK_TEXT_UTF8>"
}
```

The launch path must be directly in root/bin, its parent must not be a symlink, its final leaf must be a symlink, and its exact link text and final resolved binary must match the pins. The target must be a regular executable with the pinned bytes. A bare symlink without this explicit venv object is still rejected. Ordinary non-symlink Python registration keeps its existing shape.

Each subprocess must report the exact launch path, final realpath, venv prefix and a distinct base prefix. Before and after execution, and when finishing/reusing a P0 binding, the bridge rechecks file identities (including inode/device/timestamps), binary hash, cfg hash and link hash. Even a same-byte launch replacement cannot silently finish the previous binding. The observed interpreter identity participates only in P0 dependency identity; it does not alter the original M06 computation/dependency identity.

## Read-only pin collection in the existing Mac venv

Keep the current Mac environment. Do not install packages, recreate the venv, copy an interpreter, modify permissions, or resolve python_executable's final leaf. Run this using the already verified existing HK02 launch path. It prints fields only, without writing a config or invoking M06:

```sh
"$EXISTING_HK02_PYTHON" -I -B - <<'PY'
import hashlib,json,os,sys
from pathlib import Path
launch=Path(sys.executable).parent.resolve()/Path(sys.executable).name
root=Path(sys.prefix).resolve();real=launch.resolve(strict=True)
assert launch.parent==root/'bin' and launch.is_symlink()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(real.read_bytes())=='95fb891ec36d4022bdf62172f9d3c757fb3c7b1669a274cacc87fe261a535b7e'
print(json.dumps(dict(python_executable=str(launch),python_sha256=sha(real.read_bytes()),
  python_venv=dict(root=str(root),realpath=str(real),
    pyvenv_cfg_sha256=sha((root/'pyvenv.cfg').read_bytes()),
    symlink_sha256=sha(os.readlink(launch).encode()))),indent=2))
PY
```

Keep these actual paths in the private task config, not GitHub. The disabled template has been corrected to distinguish launch and binary paths. Do not use the old template's realpath placeholder as the venv launch.

## Focused validation

New command, from repository root, using an existing interpreter:

```sh
PYTHONPATH=V5/src:V5/tests "$EXISTING_HK02_PYTHON" -B -m unittest test_m06_python_launch
```

Cloud result: 14/14 PASS, 19.084 seconds, exit 0. The tests create a disposable synthetic pyvenv.cfg/symlink/sentinel metadata layout using the current Python; no pip or dependency installation occurs. They invoke real subprocesses and the fixed original M06 inspect, original owner and fresh reader on synthetic CSV inputs. They also cover bad binary/config/link pins, wrong realpath/prefix, out-of-root launch, forbidden input/venv-directory symlinks, missing executable permission and replacement during execution. No real model/provider is used.

Mac need only run these new interpreter-focused tests, verify this 147-entry closure, and perform the already authorized private registration/inspection using the retained existing venv. Do not repeat the old 21/85/M17 suites as this repair's evidence.

For the prepared existing-pool request, preserve original dates, eight source hashes, ten asset hashes and original M06 cutoff/identity. Compare inspection's M06 identity to the exact identity recorded in the Mac feedback before allowing a controlled tick. A mismatch remains blocked; do not alter cutoff or dependencies to manufacture a new success. The old past completion cutoff is valid only for that existing-pool contract, never for generation.

No real Mac admission, recomputation, natural scheduling or deployment is claimed by this fix. Keep the prepared runtime disabled until the existing Mac task's controlled admission is verified. Source closure SHA256: `dae57f54bedc7632b4beafa9cd29fb2158db83162ac3d7bacdace2bf9fe1a1e4`.
