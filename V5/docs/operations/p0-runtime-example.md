# P0 read-only runtime example

This is a single-module, read-only lifecycle example. It does **not** start the full V5 frontend, daily scheduler, providers, or production pipeline. It never calls a producer. The research day route reads only an exact published record; an absent record remains unavailable. The date catalog lists only exact research-day products present in the immutable source-bundle store.

## Requirements

- Python `>=3.14`, matching `V5/pyproject.toml` and the checked-in lockfile.
- Install only the checked-in locked environment: `uv sync --project V5 --frozen`.
- No API keys, credentials, provider packages, or V4 runtime are needed for this read-only example.

## Prepare a user-owned, non-symlink root

Choose an existing user-owned parent directory on your machine. Do not use a path containing symlinked ancestors (on macOS, `/tmp` may resolve through a symlink). Replace the example root below with your real absolute path.

```bash
ROOT="/absolute/path/you-own/v5-runtime-home"
python - "$ROOT" "$PWD/V5/examples/p0_runtime_config.json" <<'PY'
import json, os, sys
from pathlib import Path

root = Path(sys.argv[1])
template = Path(sys.argv[2])
if not root.is_absolute() or ".." in root.parts or root == Path(root.anchor):
    raise SystemExit("ROOT must be a non-root absolute path without '..'")
for part in (root, *root.parents):
    if part.is_symlink():
        raise SystemExit("SYMLINK_REJECTED: " + str(part))
root.mkdir(parents=True, exist_ok=True)
data_root = root / "module-data"
runtime_root = root / "runtime"
data_root.mkdir(exist_ok=True)
runtime_root.mkdir(exist_ok=True)
for path in (data_root, runtime_root):
    if path.is_symlink():
        raise SystemExit("SYMLINK_REJECTED: " + str(path))
marker = data_root / ".v5-module-root"
expected = b"v5.module-root.v1:source_bundle\n"
if marker.exists():
    if marker.is_symlink() or not marker.is_file() or marker.read_bytes() != expected:
        raise SystemExit("MODULE_ROOT_IDENTITY: refusing to overwrite existing marker")
else:
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(expected)
        stream.flush()
        os.fsync(stream.fileno())
raw = template.read_text()
raw = raw.replace("/REPLACE_WITH_ABSOLUTE_USER_OWNED_PATH", str(root))
config = json.loads(raw)
out = root / "p0_runtime_config.json"
if out.exists():
    if out.is_symlink() or not out.is_file() or out.read_text() != json.dumps(config, indent=2) + "\n":
        raise SystemExit("CONFIG_EXISTS_DIFFERENT: refusing to overwrite")
else:
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(config, indent=2) + "\n")
print(out)
print("module_data_root=" + str(data_root))
print("runtime_root=" + str(runtime_root))
PY
```

The `composition` field is a required absolute path in the current lifecycle configuration contract. The current `main_runtime` lifecycle validates its presence but does not load or compose that file; this example does not claim full multi-module composition.

## Validate, start, inspect, stop

Run from the repository root:

```bash
uv run --project V5 --frozen python -I -B V5/run_shadow.py runtime validate --config "$ROOT/p0_runtime_config.json"
uv run --project V5 --frozen python -I -B V5/run_shadow.py runtime start --config "$ROOT/p0_runtime_config.json"
uv run --project V5 --frozen python -I -B V5/run_shadow.py runtime status --config "$ROOT/p0_runtime_config.json"
uv run --project V5 --frozen python -I -B V5/run_shadow.py runtime stop --config "$ROOT/p0_runtime_config.json"
```

The start path waits for the child process's bounded `READY` handshake, then probes `/__v5/module-health` and checks PID, port, module ID, release ID and config SHA before writing the runtime identity. This is process/service readiness only; it does **not** establish data-source readiness, natural scheduler execution, research correctness or V4 parity.

## Expected no-data behavior

- `GET /api/v1/runs/date-list` lists only exact research-day products already published to this source-bundle root. If none exist, it returns `NOT_MATERIALIZED` with an empty `dates` array; it does not invent today's date or use an hourly/latest product.
- `GET /api/v3/research/day?archive_date=YYYYMMDD` cold-reads that exact saved response. If absent, the module returns `503 CANNOT_CONFIRM / MODULE_RESULT_NOT_AVAILABLE`, not a fake empty day product.
- `POST` to these read-only module routes is rejected.
- This example has no `m04_research_lane_binding` or source producer configured; a missing research lane stays `NOT_MATERIALIZED`.

## Boundaries

No V4 process or data root is read or modified. Do not enable `daily`, add provider bindings, or treat a health response as successful data collection without a separately reviewed configuration and evidence.
