"""Synthetic offline controls; original owners execute without injected callbacks."""
import json
import shutil
from pathlib import Path

import pytest
import v5_shadow.hk_close_daily as daily


def test_run_directory_identity_rejected(tmp_path):
    daily.HKCloseReviewStore(tmp_path).publish('one', {'review': {}}, {'generation': 'g1'})
    shutil.copytree(tmp_path/'one', tmp_path/'other')
    with pytest.raises(ValueError, match='IDENTITY'):
        daily.HKCloseReviewReader(tmp_path).read('other')


def test_receipt_payload_identity_rejected(tmp_path):
    daily.HKCloseReviewStore(tmp_path).publish('one', {'review': {}}, {'generation': 'g1'})
    path=tmp_path/'one'/'receipt.json'; value=json.loads(path.read_text());value['payload_sha256']='0'*64;path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='RECEIPT'):
        daily.HKCloseReviewReader(tmp_path).read('one')


def test_generation_cas_preserves_success(tmp_path):
    store=daily.HKCloseReviewStore(tmp_path)
    first=store.publish('one', {'x':1}, {'generation':'g1'}, expected_generation=None)
    with pytest.raises(ValueError, match='GENERATION_CAS'):
        store.publish('two', {'x':2}, {'generation':'g2'}, expected_generation='stale')
    assert daily.HKCloseReviewReader(tmp_path).read_latest()['x']==1


def test_default_owner_closure_is_frozen():
    assert hasattr(daily, 'prepare_owner_capsule'), 'default chain has no fixed owner closure'


@pytest.mark.parametrize('run_id',['../escape','/absolute','.','a/b'])
def test_unsafe_run_id_rejected(tmp_path,run_id):
    with pytest.raises(ValueError,match='RUN_ID'):
        daily.HKCloseReviewStore(tmp_path).publish(run_id,{}, {})


def test_real_default_owners_save_and_cold_read(tmp_path):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input')
    before={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
    result=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=tmp_path/'runs',stage_selection_root=data/'stages')
    assert result['review']['row_counts']=={'hkconnect_universe':600,'close_top20':20,'model_0_2':100,'stage_rows':7}
    assert result['review']['stage_union']['hit_count']==7
    assert result['data_kind']=='RECORDED_INPUT_REPLAY'
    assert result['natural_admission']=='UNVERIFIED'
    assert 'M02_MEMBERSHIP_PIT_UNVERIFIED' in result['cannot_confirm']
    assert result==daily.HKCloseReviewReader(tmp_path/'runs').read(result['run_id'])
    assert before=={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
    first={str(p.relative_to(tmp_path/'runs')):p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    again=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=tmp_path/'runs',stage_selection_root=data/'stages')
    assert again==result
    assert first=={str(p.relative_to(tmp_path/'runs')):p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}


def test_missing_inputs_preserve_top20_as_partial(tmp_path):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input',with_model=False,with_stages=False)
    result=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=tmp_path/'runs')
    assert len(result['review']['close_top20'])==20
    assert result['review']['models']['0.2_prob_active']['hit_count'] is None
    assert len(result['review']['missing_stages'])==7
    assert result['input_evidence']['model']['payload']=={}


def test_default_missing_close_never_collects(tmp_path):
    with pytest.raises(ValueError,match='M10_CLOSE_INPUT'):
        daily.build_default_hk_close_review(data_root=tmp_path/'absent',trade_date='20260730',run_root=tmp_path/'runs')
    assert not (tmp_path/'absent').exists()
    assert not (tmp_path/'runs'/'latest_success.json').exists()
    assert len(list((tmp_path/'runs'/'attempts').glob('*.json')))==1


def test_pointer_write_failure_is_not_a_committed_run_and_retry_recovers(tmp_path,monkeypatch):
    store=daily.HKCloseReviewStore(tmp_path)
    store.publish('one',{'x':1},{'generation':'g1'})
    old=daily.HKCloseReviewReader(tmp_path).latest_identity()['generation']
    real=daily._write
    def fail(path,value):
        if Path(path).name=='latest_success.json': raise OSError('synthetic disk fault')
        return real(path,value)
    monkeypatch.setattr(daily,'_write',fail)
    with pytest.raises(OSError): store.publish('two',{'x':2},{'generation':'g2'},expected_generation=old)
    assert daily.HKCloseReviewReader(tmp_path).read_latest()=={'x':1}
    with pytest.raises(ValueError,match='NOT_COMMITTED'): daily.HKCloseReviewReader(tmp_path).read('two')
    monkeypatch.setattr(daily,'_write',real)
    store.publish('two',{'x':2},{'generation':'g2'},expected_generation=old)
    assert daily.HKCloseReviewReader(tmp_path).read_latest()=={'x':2}


def test_default_native_and_generation_cas_leave_latest(tmp_path):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input')
    runs=tmp_path/'runs'
    first=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=runs,stage_selection_root=data/'stages')
    newer=create_fixture(tmp_path/'changed',close_offset=1)
    generation=daily.HKCloseReviewReader(runs).latest_identity()['generation']
    with pytest.raises(ValueError,match='GENERATION_CAS'):
        daily.build_default_hk_close_review(data_root=newer,trade_date='20260730',run_root=runs,stage_selection_root=newer/'stages')
    with pytest.raises(ValueError,match='NATIVE_CAS'):
        daily.build_default_hk_close_review(data_root=newer,trade_date='20260730',run_root=runs,stage_selection_root=newer/'stages',expected_generation=generation,expected_native_sha256='0'*64)
    assert daily.HKCloseReviewReader(runs).read_latest()==first
    second=daily.build_default_hk_close_review(data_root=newer,trade_date='20260730',run_root=runs,stage_selection_root=newer/'stages',expected_generation=generation,expected_native_sha256=daily._digest(first['review']))
    assert second['run_id']!=first['run_id']
    assert daily.HKCloseReviewReader(runs).read(first['run_id'])==first


def test_partial_projection_does_not_claim_missing_hits(tmp_path):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input',with_model=False,with_stages=False)
    runs=tmp_path/'runs'
    daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=runs)
    projection=daily.read_hk_close_projection(runs)
    assert len(projection['review']['close_top20'])==20
    assert all(r['model_0_2_hit'] is None and r['stage_union_hit'] is None and r['classification']=='CANNOT_CONFIRM' for r in projection['review']['top20_attribution'])


@pytest.mark.parametrize('part',['model','stage'])
def test_invalid_optional_evidence_keeps_top20(tmp_path,part):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input')
    path=data/('preselection_pools/20260730/manifest.json' if part=='model' else 'stages/selection_latest.json')
    path.write_text('{invalid')
    result=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=tmp_path/'runs',stage_selection_root=data/'stages')
    assert len(result['review']['close_top20'])==20
    assert result['cannot_confirm']


@pytest.mark.parametrize('mode',['partial','empty'])
def test_original_stage_status_and_reason_survive(tmp_path,mode):
    from m10_fixture import create_fixture
    data=create_fixture(tmp_path/'input',stage_mode=mode)
    runs=tmp_path/'runs'
    result=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=runs,stage_selection_root=data/'stages')
    view=daily.read_hk_close_projection(runs)
    assert len(view['review']['close_top20'])==20
    if mode=='partial':
        assert any('SYNTHETIC_SOURCE_GAP' in reason for reason in result['cannot_confirm'])
        assert view['review']['stage_union']['hit_count'] is None
        assert all(row['classification']=='CANNOT_CONFIRM' for row in view['review']['top20_attribution'])
    else:
        assert result['review']['missing_stages']==[]
        assert result['review']['stage_union']['selected_count']==0
        assert all(metric['source_status']=='READY_EMPTY' for metric in view['review']['stages'].values())


def test_read_has_no_filesystem_side_effects(tmp_path):
    absent=tmp_path/'absent'
    with pytest.raises(FileNotFoundError): daily.HKCloseReviewReader(absent).read('missing')
    assert not absent.exists()
    daily.HKCloseReviewStore(tmp_path/'runs').publish('one',{'x':1},{})
    before={str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}
    daily.HKCloseReviewReader(tmp_path/'runs').read_latest()
    assert before=={str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}


def test_frozen_source_tamper_rejected(tmp_path,monkeypatch):
    import v5_shadow.hk_close_owner as owner
    root=tmp_path/'repo'
    shutil.copytree(owner.REPOSITORY/'handoffs',root/'handoffs')
    shutil.copytree(owner.REPOSITORY/'integration_candidates',root/'integration_candidates')
    source=root/'handoffs/M10/handoff/v4-running-source-20261005/canonical/ops/build_close_review.py'
    source.write_text(source.read_text()+'\n# tampered synthetic test copy\n')
    monkeypatch.setattr(owner,'REPOSITORY',root)
    with pytest.raises(ValueError,match='SOURCE_SHA'):
        with owner.prepare_owner_capsule(): pass


def test_input_and_run_roots_cannot_overlap(tmp_path):
    data=tmp_path/'input';data.mkdir()
    with pytest.raises(ValueError,match='ROOT_OVERLAP'):
        daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=data/'runs')
    assert list(data.iterdir())==[]


def test_orphan_cannot_change_parent_after_other_success(tmp_path,monkeypatch):
    store=daily.HKCloseReviewStore(tmp_path)
    store.publish('one',{'x':1},{})
    old=daily.HKCloseReviewReader(tmp_path).latest_identity()['generation']
    real=daily._write
    def fail(path,value):
        if Path(path).name=='latest_success.json': raise OSError('synthetic pointer fault')
        return real(path,value)
    monkeypatch.setattr(daily,'_write',fail)
    with pytest.raises(OSError): store.publish('orphan',{'x':2},{},expected_generation=old)
    monkeypatch.setattr(daily,'_write',real)
    store.publish('three',{'x':3},{},expected_generation=old)
    current=daily.HKCloseReviewReader(tmp_path).latest_identity()['generation']
    with pytest.raises(ValueError,match='ORPHAN_PARENT_CAS'):
        store.publish('orphan',{'x':2},{},expected_generation=current)
    assert daily.HKCloseReviewReader(tmp_path).read_latest()=={'x':3}


def test_default_owner_pointer_failure_retries_without_rebuilding(tmp_path,monkeypatch):
    from m10_fixture import create_fixture
    import v5_shadow.hk_close_owner as owner
    data=create_fixture(tmp_path/'input');runs=tmp_path/'runs'
    real_write=daily._write
    def fail(path,value):
        if Path(path).name=='latest_success.json': raise OSError('synthetic pointer fault')
        return real_write(path,value)
    monkeypatch.setattr(daily,'_write',fail)
    with pytest.raises(OSError):
        daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=runs,stage_selection_root=data/'stages')
    monkeypatch.setattr(daily,'_write',real_write)
    original_run=owner.run_owner
    def inspect_only(action,*args,**kwargs):
        assert action=='inspect', 'orphan recovery must not recalculate'
        return original_run(action,*args,**kwargs)
    monkeypatch.setattr(owner,'run_owner',inspect_only)
    result=daily.build_default_hk_close_review(data_root=data,trade_date='20260730',run_root=runs,stage_selection_root=data/'stages')
    assert daily.HKCloseReviewReader(runs).read_latest()==result


def test_internal_temp_symlink_alias_is_canonicalized(tmp_path,monkeypatch):
    # macOS /tmp and /var may be OS-provided symlink aliases. Resolve only
    # internally created temporary roots; user input symlinks remain rejected.
    import v5_shadow.hk_close_owner as owner
    original=owner.tempfile.TemporaryDirectory
    real=tmp_path/'real-temp';real.mkdir();alias=tmp_path/'temp-alias';alias.symlink_to(real,target_is_directory=True)
    def aliased_temp(*args,**kwargs):
        return original(*args,dir=alias,**kwargs)
    monkeypatch.setattr(owner.tempfile,'TemporaryDirectory',aliased_temp)
    with owner.prepare_owner_capsule() as capsule:
        assert capsule.is_relative_to(real)
        assert (capsule/'ops/build_close_review.py').is_file()
