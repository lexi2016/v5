"""Print only SYNTHETIC test projection, never reads a user data root."""
import json
from pathlib import Path
import sys
import tempfile
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from fixtures.hk_close_readonly_factory import create_fixture
from v5_shadow.m10_readonly import BINDING,ROUTE,read_record
with tempfile.TemporaryDirectory(prefix='m10-ui-synthetic-') as temp:
    binding,_=create_fixture(Path(temp).resolve()/'runs')
    config=dict(module_id='source_bundle',release_id='synthetic',routes=[ROUTE]);config[BINDING]=binding
    print(json.dumps(read_record(config,{})[0]['payload']))
