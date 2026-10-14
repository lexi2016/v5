"""Reuse the fixed owner's synthetic fixture; no real provider or source input."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

package = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
sys.path[:0] = [str(package), str(package / 'tests')]
from test_multi_binding import MultiBindingTests
from research_lane import research_lane

fixture = MultiBindingTests()
fixture.setUp()
try:
    bindings = []
    for name, binding in [('m04-new', fixture.new), ('m04-old', fixture.old)]:
        root = destination / name
        shutil.copytree(binding['root'], root)
        bindings.append(dict(root=str(root), files=binding['files']))
    bundle = dict(schema_version='v5.m04_archive_bindings.v1', bindings=bindings)
    for day in (fixture.c.day, '20200102'):
        value = research_lane(bundle, {'research_date': day})
        assert value['archive_materials']['article_count'] > 0
    info = dict(input_kind='SYNTHETIC', natural_verified=False,
                fixture='M04_capture/tests/test_multi_binding.py',
                fixture_clock='Original synthetic test sets capture window to 23:00; not natural execution',
                dates=[fixture.c.day, '20200102'], archive_binding=bundle,
                package_root=str(package),
                package_manifest_sha256=hashlib.sha256((package / 'RELEASE.json').read_bytes()).hexdigest(),
                python_executable=str(Path(sys.executable).resolve()))
    (destination / 'm04-fixture.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))
    print(json.dumps(info, ensure_ascii=False))
finally:
    fixture.doCleanups()
