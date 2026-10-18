"""New save/publish/HTTP assembly; synthetic empty-owner inputs, real code/stores."""
import json,hashlib,threading
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "V5" / "tests"))
import test_manager_current_recovery as recovery_fixture
from v5_shadow.manager_plan import run_manager_plan,publish_workspace_read,ROUTE
from v5_shadow.daily_owner_adapters import run_manager_daily
from v5_shadow.module_api import create_module_server
from v5_shadow.module_artifacts import activate_generation
from v5_shadow.run_ledger import MARKER

@pytest.fixture
def setup():
    fixture=recovery_fixture.ManagerCurrentRecoveryTests();fixture.setUp()
    root=fixture.root
    api=root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:manager\n')
    ledger=root/'ledger';ledger.mkdir();(ledger/'.v5-daily-run-ledger').write_bytes(MARKER)
    cfg={'schema_version':'v5.module_api.v1','module_id':'manager','release_id':'p0-integration-synthetic','data_root':str(api),'routes':[ROUTE]}
    try:yield fixture,cfg,ledger
    finally:fixture.doCleanups()

def head(cfg):return (Path(cfg['data_root'])/'active.json').read_bytes()
def generation(cfg):return json.loads(head(cfg))['generation_sha256']
def publish(f,cfg,saved,expected):
    product=saved['payload']['plan_product']
    return publish_workspace_read(dict(f.request,action='read'),cfg,expected_generation=expected,expected_run_id=product['run_id'],expected_plan_sha256=product['sha256'])

def test_actual_daily_save_publish_http_reuse_and_changed_request(setup):
    f,cfg,ledger=setup
    f.request.update(now='2026-10-09T08:45:00+08:00')
    binding={'code_sha256':'a'*64,'config_sha256':'b'*64,'dependency_sha256':'c'*64}
    with patch('v5_shadow.daily_owner_adapters.datetime') as clock:
        clock.now.return_value=datetime(2026,10,9,2,tzinfo=timezone.utc)
        first=run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':None})
        assert first['status']=='BLOCKED' # partial empty-owner plan, not business success
        product=first['result']['payload']['plan_product'];old_head=head(cfg)
        again=run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':generation(cfg)})
        assert again['status']=='RETRY_BLOCKED' and head(cfg)==old_head
        assert len(again['state']['attempts'])==1
        server=create_module_server(cfg);server.daemon_threads=True;server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
        before=f.snapshot()
        try:
            for _ in range(2):
                with urlopen('http://127.0.0.1:'+str(server.server_port)+ROUTE+'?date=20261009&view=auto') as response:
                    body=json.load(response)
                    assert body['plan_product']['run_id']==product['run_id']
                    assert body['plan_product']['sha256']==product['sha256']
                    assert response.headers['X-V5-Workspace-Access']=='READ_ONLY'
            assert f.snapshot()==before
        finally:
            server.shutdown();server.server_close();server_thread.join(timeout=2)
            assert not server_thread.is_alive(), 'TEST_HTTP_SERVER_THREAD_LEAK'
        f.request['now']='2026-10-09T08:46:00+08:00'
        second=run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':generation(cfg)})
        assert second['result']['payload']['plan_product']['run_id']!=product['run_id']
        assert second['publication']['previous_generation']==json.loads(old_head)['generation_sha256']
        evidence=Path(__file__).resolve().parents[1]/'evidence/publication-chain-receipt.json'
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps({'fixture_kind':'SYNTHETIC_EMPTY_OWNER_INPUTS','saved_plan':product,
            'first_publication':first['publication'],'http_product':body['plan_product'],
            'repeated_request_status':again['status'],'changed_cutoff_product':second['result']['payload']['plan_product'],
            'second_publication':second['publication'],'GET_files_unchanged':True,'business_status':'BLOCKED','natural_verified':False},indent=2))

def test_wrong_run_sha_cas_and_bad_input_preserve_old_generation(setup):
    f,cfg,ledger=setup
    saved=run_manager_plan(f.request);pub=publish(f,cfg,saved,None);old=head(cfg)
    read=dict(f.request,action='read');p=saved['payload']['plan_product']
    with pytest.raises(ValueError,match='SAVED_RUN_NOT_CONSUMED'):
        publish_workspace_read(read,cfg,expected_generation=generation(cfg),expected_run_id='0'*32)
    with pytest.raises(ValueError,match='SAVED_PLAN_SHA_NOT_CONSUMED'):
        publish_workspace_read(read,cfg,expected_generation=generation(cfg),expected_run_id=p['run_id'],expected_plan_sha256='0'*64)
    with pytest.raises(ValueError,match='GENERATION_CONFLICT'):publish(f,cfg,saved,None)
    assert head(cfg)==old
    broken=dict(read);broken['inputs']={**read['inputs'],'manager':{'root':str(f.root/'absent'),'files':{}}}
    with pytest.raises(Exception):publish_workspace_read(broken,cfg,expected_generation=generation(cfg),expected_run_id=p['run_id'])
    assert head(cfg)==old

def test_manager_generation_rollback_does_not_touch_other_module(setup):
    f,cfg,ledger=setup
    first=run_manager_plan(f.request);publish(f,cfg,first,None);old=generation(cfg)
    # Change explicit request cutoff, not fabricated market input.
    f.request['now']='2026-10-09T08:45:00+08:00'
    second=run_manager_plan(f.request);publish(f,cfg,second,old);new=generation(cfg)
    other=f.root/'other-module';other.mkdir();(other/'sentinel').write_bytes(b'HEALTHY_OTHER_MODULE')
    before=(other/'sentinel').read_bytes()
    activate_generation(cfg,old,expected_generation=new)
    assert generation(cfg)==old and (other/'sentinel').read_bytes()==before

def test_latest_changed_rejects_prior_expected_run_before_activation(setup):
    f,cfg,ledger=setup
    first=run_manager_plan(f.request);publish(f,cfg,first,None);old=head(cfg)
    f.request['now']='2026-10-09T08:45:00+08:00'
    second=run_manager_plan(f.request)
    assert first['readback']['run_id']!=second['readback']['run_id']
    with pytest.raises(ValueError,match='SAVED_RUN_NOT_CONSUMED'):
        publish(f,cfg,first,generation(cfg))
    assert head(cfg)==old

def test_publication_conflict_preserves_old_head_and_unknown_attempt(setup):
    f,cfg,ledger=setup
    f.request.update(now='2026-10-09T08:45:00+08:00')
    binding={'code_sha256':'a'*64,'config_sha256':'b'*64,'dependency_sha256':'c'*64}
    with patch('v5_shadow.daily_owner_adapters.datetime') as clock:
        clock.now.return_value=datetime(2026,10,9,2,tzinfo=timezone.utc)
        first=run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':None});old=head(cfg)
        f.request['now']='2026-10-09T08:46:00+08:00'
        with pytest.raises(ValueError,match='GENERATION_CONFLICT'):
            run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':None})
        assert head(cfg)==old
        again=run_manager_daily(f.request,ledger,binding,publication={'config':cfg,'expected_generation':generation(cfg)})
        assert again['status']=='IN_PROGRESS_OR_OUTCOME_UNKNOWN'
        assert len(again['state']['attempts'])==1
        assert head(cfg)==old

def test_tick_retains_publication_receipt_and_stable_config_identity(setup):
    from v5_shadow.daily_tick import tick
    f,cfg,ledger=setup
    f.request['now']='2026-10-09T08:45:00+08:00'
    bundles=f.root/'bundles';bundles.mkdir()
    (bundles/'.v5-daily-bundles').write_bytes(b'v5.daily-bundles.v1\n')
    (bundles/'20261009.json').write_text(json.dumps({'target_date':'20261009','jobs':[],'manager_request':f.request}))
    config={'enabled':True,'bundle_root':str(bundles),'ledger_root':str(ledger),'manager_publication':cfg}
    with patch('v5_shadow.daily_tick.datetime') as tick_clock,patch('v5_shadow.daily_owner_adapters.datetime') as owner_clock,patch('v5_shadow.daily_dispatch.datetime') as dispatch_clock:
        tick_clock.now.return_value=owner_clock.now.return_value=dispatch_clock.now.return_value=datetime(2026,10,9,0,50,tzinfo=timezone.utc)
        first=tick(config);old=head(cfg);second=tick(config)
    assert first['manager']['status']=='BLOCKED'
    assert first['manager']['publication']['generation_sha256']==json.loads(old)['generation_sha256']
    assert first['manager']['state']['attempts'][-1]['product_reference']['transport_publication']==first['manager']['publication']
    assert second['manager']['status']=='RETRY_BLOCKED' and len(second['manager']['state']['attempts'])==1
    assert head(cfg)==old
