#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="V5/src:V5/vendor/research_review_baseline${PYTHONPATH:+:$PYTHONPATH}"
python -B -m pytest -q -p no:cacheprovider V5/tests/m11
