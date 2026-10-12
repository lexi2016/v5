import pytest
from V5.src.v5_shadow.hk_preselection_verified import run_verified_hk_preselection

def test_missing_identity_rejected():
    with pytest.raises(ValueError):
        run_verified_hk_preselection({'schema_version':'v5.hk_preselection_verified_request.v1','target_date':'20261008','signal_date':'20261007','eligibility_source_date':'20260930','research_cutoff':'x','data_kind':'SOURCE_SNAPSHOT','input_root':'.','files':{'x':'0'*64},'expected_source':{}})
