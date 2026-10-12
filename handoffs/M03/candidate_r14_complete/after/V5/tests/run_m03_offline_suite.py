"""Run all M03 source tests with the published frozen owner, without git show.

M03_FIXED_SOURCE must point to the complete handoff source directory.
Only the old assembler-dependent setUpClass is substituted; every original
collector/transport test body is run unchanged. This is test-only code.
"""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from m03_fixture import OWNER
import test_cloud_us_collector


@classmethod
def materialized_owner(cls):
    cls.temporary = tempfile.TemporaryDirectory(prefix='m03-original-suite-')
    cls.addClassCleanup(cls.temporary.cleanup)
    cls.root = Path(cls.temporary.name)
    cls.owner = OWNER


test_cloud_us_collector.CloudUSCollectorTests.setUpClass = materialized_owner
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
