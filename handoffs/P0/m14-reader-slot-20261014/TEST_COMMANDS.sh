#!/bin/sh
# Reproducible forms of the actual commands. Set existing compatible PYTHON,
# CANDIDATE and STAGE explicitly; all work belongs in an isolated runtime copy.
set -eu
: "${CANDIDATE:?candidate directory required}"
: "${STAGE:?isolated P0 runtime root required}"
: "${PYTHON:?existing Python executable required}"
"$PYTHON" -I -B "$CANDIDATE/tests/test_m14_reader_slot.py" "$STAGE"
PYTHONPATH="$STAGE/V5/src:$STAGE/V5/tests" "$PYTHON" -B -m unittest -v test_m14_saved_rebound test_module_api
# RED used the identical test command with the frozen 94c1 file staged.
# GREEN used the 64357836 after file. Do not run this script against a live tree.
