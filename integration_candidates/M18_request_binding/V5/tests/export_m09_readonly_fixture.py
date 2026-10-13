"""Emit one SYNTHETIC original-owner replay for frontend contract tests only."""
import json
from pathlib import Path
import sys
import tempfile
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from fixtures.a_close_replay_factory import create_fixture
from v5_shadow.m09_readonly import BINDING,ROUTE,read_record
with tempfile.TemporaryDirectory(prefix='m09-browser-synthetic-') as temp:
    binding,_=create_fixture(Path(temp).resolve()/'fixture')
    config=dict(module_id='source_bundle',release_id='m09-frontend-synthetic',routes=[ROUTE],**{BINDING:binding})
    record,_=read_record(config,{})
    print(json.dumps(record['payload'],ensure_ascii=False,allow_nan=False))
