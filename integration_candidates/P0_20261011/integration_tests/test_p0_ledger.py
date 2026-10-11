"""New combination: 6daed627 dispatcher/assembly with unchanged M07 R3 ledger."""
import hashlib,json,shutil
from pathlib import Path
import pytest
from v5_shadow.run_ledger import MARKER,claim_run,finish_run,read_run,identity_key
from v5_shadow.daily_manager_assembly import product_reference

ROOT=Path(__file__).resolve().parents[2]
LANES=['announcement','us_mapping','rebound','manager_plan','hk_preselection','a_stage']

@pytest.mark.parametrize('order',[LANES,list(reversed(LANES))])
def test_six_lanes_real_persistence_no_overwrite(tmp_path,order):
    (tmp_path/'.v5-daily-run-ledger').write_bytes(MARKER)
    product=tmp_path/'installation-check.txt';product.write_text('ISOLATED FILE INTEGRITY CHECK; NOT MARKET RESULT')
    ref={'path':str(product),'sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'scope':'SYNTHETIC_INSTALLATION_CHECK'}
    saved={};runs=set();keys=set()
    for lane in order:
        identity={'lane':lane,'target_date':'20261011','research_cutoff':'2026-10-11T00:00:00Z','input_sha256':ref['sha256'],'code_sha256':'b'*64,'config_sha256':'c'*64,'dependency_sha256':'d'*64}
        claim=claim_run(tmp_path,identity);assert claim['status']=='CLAIMED'
        assert hashlib.sha256(product.read_bytes()).hexdigest()==ref['sha256']
        state=finish_run(tmp_path,claim,{'status':'SUCCEEDED','product_reference':ref,'readback_verified':True,'retry_safe_without_external_effect':False,'reason_codes':[]})
        assert product_reference({'state':state})==ref
        assert claim_run(tmp_path,identity)['status']=='REUSED_SUCCESS'
        saved[lane]=(identity,state);runs.add(claim['run_id']);keys.add(identity_key(identity))
        for old_identity,old_state in saved.values():assert read_run(tmp_path,old_identity)==old_state
    assert len(runs)==len(keys)==6

def test_actual_saved_m07_product_preserves_same_run(tmp_path):
    original=ROOT/'v5-ledger-r3-local'
    shutil.copytree(original/'ledger',tmp_path/'ledger')
    for name in ['integrity-job','safe-retry-drill']:
        identity=json.loads((original/(name+'-identity.json')).read_text())
        before=read_run(tmp_path/'ledger',identity)
        result=claim_run(tmp_path/'ledger',identity)
        assert result['status']=='REUSED_SUCCESS'
        after=read_run(tmp_path/'ledger',identity)
        assert before==after==result['state']
        reference=product_reference({'state':after})
        assert reference==after['latest_success']['product_reference']
        assert hashlib.sha256(Path(reference['path']).read_bytes()).hexdigest()==reference['sha256']
        assert after['latest_success']['run_id']==before['latest_success']['run_id']
        assert len(after['attempts'])==(1 if name=='integrity-job' else 2)

def test_new_lane_not_implicitly_registered_for_dispatch():
    from v5_shadow.daily_dispatch import LANES as dispatched
    assert set(LANES)-dispatched=={'manager_plan','hk_preselection','a_stage'}
    # Ledger admission is not permission to execute an unregistered owner.
