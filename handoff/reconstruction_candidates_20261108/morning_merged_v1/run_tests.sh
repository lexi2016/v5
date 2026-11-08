#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$BASE/isolated/handoff/morning_registered_execution_v2_20261107"
export JK_ENTRY="$PWD/registered.py"
python -m unittest test_jk test_assembly test_bundle test_combined_dispatch
python -O -m unittest test_jk test_assembly test_bundle test_combined_dispatch
