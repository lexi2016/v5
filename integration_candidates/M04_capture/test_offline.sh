#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
export PYTHONDONTWRITEBYTECODE=1
"$PYTHON_BIN" -B -c "import sys;sys.path.insert(0,sys.argv[1]);import capture_runtime;capture_runtime.verify_sources();print('RELEASE hashes MATCHED')" "$HERE"
"$PYTHON_BIN" -B -m unittest discover -s "$HERE/tests" -v
