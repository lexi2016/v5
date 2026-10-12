"""New combination: ledger contract with isolated generated fixtures only."""
import hashlib
import pytest
from v5_shadow.run_ledger import MARKER,claim_run,finish_run,read_run,identity_key
from v5_shadow.daily_manager_assembly import product_reference

LANES=['announcement','us_mapping','rebound','manager_plan','hk_preselection','a_stage']

def _identity(ref,lane):
    return {'lane':lane,'target_date':'20261011','research_cutoff':'2026-10-11T00:00:00Z','input_sha256':ref['sha256'],'code_sha256':'b'*64,'config_sha256':'c'*64,'dependency_sha256':'d'*64}

@pytest.mark.parametrize('order',[LANES,list(reversed(LANES))])
def test_six_lanes_real_persistence_no_overwrite(tmp_path,order):
    (tmp_path/'.v5-daily-run-ledger').write_bytes(MARKER)
    product=tmp_path/'installation-check.txt';product.write_text('SYNTHETIC_INSTALLATION_CHECK')
    ref={'path':str(product),'sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'scope':'SYNTHETIC_INSTALLATION_CHECK'}
    saved={}
    for lane in order:
        identity=_identity(ref,lane); claim=claim_run(tmp_path,identity); assert claim['status']=='CLAIMED'
        state=finish_run(tmp_path,claim,{'status':'SUCCEEDED','product_reference':ref,'readback_verified':True,'retry_safe_without_external_effect':False,'reason_codes':[]})
        assert product_reference({'state':state})==ref
        assert claim_run(tmp_path,identity)['status']=='REUSED_SUCCESS'
        saved[lane]=(identity,state)
    for identity,state in saved.values(): assert read_run(tmp_path,identity)==state

def test_actual_saved_m07_product_preserves_same_run(tmp_path):
    (tmp_path/'.v5-daily-run-ledger').write_bytes(MARKER)
    product=tmp_path/'m07-product.txt';product.write_text('SYNTHETIC_M07_COMPATIBILITY_FIXTURE')
    ref={'path':str(product),'sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'scope':'SYNTHETIC_M07_COMPATIBILITY_FIXTURE'}
    identity=_identity(ref,'a_stage')
    claim=claim_run(tmp_path,identity)
    state=finish_run(tmp_path,claim,{'status':'SUCCEEDED','product_reference':ref,'readback_verified':True,'retry_safe_without_external_effect':False,'reason_codes':[]})
    assert claim_run(tmp_path,identity)['status']=='REUSED_SUCCESS'
    assert product_reference({'state':read_run(tmp_path,identity)})==ref

def test_new_lane_not_implicitly_registered_for_dispatch():
    from v5_shadow.daily_dispatch import LANES as dispatched
    assert set(LANES)-dispatched=={'manager_plan','hk_preselection','a_stage'}
