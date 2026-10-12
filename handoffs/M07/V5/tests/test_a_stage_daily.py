import pytest
from v5_shadow.a_stage_daily import run_a_stage_daily

def receipt():
    return {"status":"VERIFIED","sha256":"a"*64}

def live():
    return {"status":"VERIFIED","sha256":"b"*64,"market":"A_SHARE",
            "data_kind":"RECORDED_INPUT_REPLAY","rows":[],"rows_sha256":"c"*64,
            "source_status":"READY_EMPTY","requested_rows":0,
            "missing_symbols":[],"cannot_confirm":[]}

def test_declared_authority_is_rejected():
    with pytest.raises(ValueError, match="DECLARED"):
        run_a_stage_daily(target_date="20261010",stage_id="STAGE_0930",
            cutoff="09:35:00",pool_input={"status":"VERIFIED","sha256":"a"*64,
            "formal_authority":True},live_input=live(),
            research_input=receipt(),selector=lambda x:x)

def test_special_route_blocked():
    with pytest.raises(ValueError):
        run_a_stage_daily(target_date="20261010",stage_id="STAGE_1545_1555",
            cutoff="15:50:00",pool_input=receipt(),live_input=live(),
            research_input=receipt(),selector=lambda x:x)
