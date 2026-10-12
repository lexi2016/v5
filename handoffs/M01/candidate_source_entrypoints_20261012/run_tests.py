"""Run only this candidate's offline suite with byte-preserved donor imports."""
from pathlib import Path
import argparse
import sys
import unittest

BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=(BASE / 'source' if (BASE / 'source').is_dir() else BASE.parent / 'source'))
parser.add_argument('--candidate', type=Path, default=BASE / 'after/V5/src/v5_shadow/a_source_daily.py')
parser.add_argument('--require-parquet', action='store_true')
args = parser.parse_args()
source = args.source.resolve()
sys.path[:0] = [str(source / 'V5/src'), str(source / 'handoff/v4-running-source-20261005/canonical')]
import v5_shadow
v5_shadow.__path__.insert(0, str(args.candidate.resolve().parent))
if args.require_parquet:
    import pyarrow.parquet
suite = unittest.defaultTestLoader.discover(str(BASE / 'after/V5/tests'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
