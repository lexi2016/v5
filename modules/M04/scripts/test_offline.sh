#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
V5="$HERE/source/V5"
CANONICAL="$HERE/source/handoff/v4-running-source-20261005/canonical"
PYTHON_BIN=${PYTHON_BIN:-python3}
OWNER_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/m04-owner-layout.XXXXXX")
cp -R "$CANONICAL/." "$OWNER_ROOT/"
cp "$V5/vendor/archive_builder_baseline/domains/_research_hourly_parts/_namespace.py" "$OWNER_ROOT/domains/_research_hourly_parts/_namespace.py"
export V5 V5_ARCHIVE_PRODUCER_SOURCE_ROOT="$OWNER_ROOT"
export PYTHONPATH="$V5/src:$V5/tests" PYTHONDONTWRITEBYTECODE=1
"$PYTHON_BIN" -B - <<'PY'
import os,json,hashlib,platform,sys
from pathlib import Path
v5=Path(os.environ['V5']); root=Path(os.environ['V5_ARCHIVE_PRODUCER_SOURCE_ROOT'])
items=json.loads((v5/'producers/archive-acquisition-v2/manifest.json').read_bytes())['test_dependency_sha256']
assert len(items)==15
for name,digest in items.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('15 dependency SHAs MATCHED; offline structural mapping, not Mac source acceptance')
print('Python:',sys.version,'Platform:',platform.platform())
print('Isolated dependency root:',root)
PY
if [ "${M04_TEST_SCOPE:-targeted}" = all ]; then
  "$PYTHON_BIN" -B -m unittest discover -s "$V5/tests" -v
else
  "$PYTHON_BIN" -B -m unittest test_research_ingest_daily -v
fi
