import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from test_default_owner_chain import binding


def test_cli_explicit_read_is_real_owner_zero_write(tmp_path):
    b=binding(tmp_path)
    data={k:str(v) for k,v in dataclasses.asdict(b).items()}
    raw=json.dumps(data).encode();path=tmp_path/'binding.json';path.write_bytes(raw)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=subprocess.run([sys.executable,'-B','-m','v5_shadow.m11','--binding-file',str(path),'--binding-sha256',hashlib.sha256(raw).hexdigest(),'read','--date','2026-10-12'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['intraday_research']['missing_slots']==['09:25','09:35','10:00','11:30','14:00','15:00']
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
