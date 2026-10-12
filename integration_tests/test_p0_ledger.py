"""New combination: ledger contract with isolated generated fixtures only."""
import hashlib
from pathlib import Path
import pytest
from v5_shadow.run_ledger import MARKER,claim_run,finish_run,read_run,identity_key
from v5_shadow.daily_manager_assembly import product_reference

LANES=['announcement','us_mapping','rebound','manager_plan','hk_preselection','a_stage']

@pytest.mark.parametrize('order',[LANES,list(reversed(LANES))])
def test_six_lanes_real_persistence_no_overwrite(tmp_path,order):
    (tmp_path/'.v5-daily-run-ledger').write_bytes(MARKER)
    product=tmp_path/'installation-check.txt';product.write_text('ISOLATED FIXTURE')
    ref={'path':str(product),'sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'scope':'SYNTHETIC_INSTALLATION_CHECK'}
    saved={};runs=set();keys=set()
    for lane in order:
        identity={'lane':lane,'target_date':'20261011','research_cutoff':'2026-10-11T00:00:00Z','input_sha256':ref['sha256'],'code_sha256':'b'*64,'config_sha256':'c'*64,'dependency_sha256':'d'*64}
        claim=claim_run(tmp_path,identity);assert claim['status']=='CLAIMED'
        state=finish_run(tmp_path,claim,{'status':'SUCCEEDED','product_reference':ref,'readback_verified':True,'retry_safe_without_external_effect':False,'reason_codes':[]})
        assert product_reference({'state':state})==ref
        assert claim_run(tmp_path,identity)['status']=='REUSED_SUCCESS'
        saved[lane]=(identity,state);runs.add(claim['run_id']);keys.add(identity_key(identity))
        for old_identity,old_state in saved.values(): assert read_run(tmp_path,old_identity)==old_state
    assert len(runs)==len(keys)==6

def test_actual_saved_m07_product_preserves_same_run(tmp_path):
    product=tmp_path/'m07-product.txt';product.write_text('PORTABLE M07 SHAPE FIXTURE')
    ref={'path':str(product),'sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'scope':'SYNTHETIC_M07_COMPATIBILITY_FIXTURE'}
    identity={'lane':'a_stage','target_date':'20261011','research_cutoff':'2026-10-11T00:00:00Z','input_sha256':ref['sha256'],'code_sha256':'b'*64,'config_sha256':'c'*64,'dependency_sha256':'d'*64}
    claim=claim_run(tmp_path,identity);state=finish_run(tmp_path,claim,{'status':'SUCCEEDED','product_reference':ref,'readback_verified':True,'retry_safe_without_external_effect':False,'reason_codes':[]})
    assert claim_run(tmp_path,identity)['status']=='REUSED_SUCCESS'
    assert product_reference({'state':read_run(tmp_path,identity)})==ref

def test_new_lane_not_implicitly_registered_for_dispatch():
    from v5_shadow.daily_dispatch import LANES as dispatched
    assert set(LANES)-dispatched=={'manager_plan','hk_preselection','a_stage'}
