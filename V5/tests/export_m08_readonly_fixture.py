import json,sys,tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from fixtures.hk_stage_observed_factory import create_fixture
from v5_shadow.m08_readonly import read_record,BINDING,ROUTE
with tempfile.TemporaryDirectory() as tmp:
 binding,expected=create_fixture(Path(tmp)/'fixture')
 config=dict(module_id='source_bundle',release_id='m08-fixture',routes=[ROUTE],**{BINDING:binding})
 catalog=read_record(config,{})[0]['payload'];results=[]
 for ref in binding['references']:
  query=dict(date=ref['target_date'],stage=ref['stage_id'],run_id=ref['run_id'],import_sha256=ref['import_sha256'])
  results.append(read_record(config,query)[0]['payload'])
 print(json.dumps(dict(catalog=catalog,results=results)))
