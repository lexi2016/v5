"""Synthetic owner-shaped 206k-node M14 section; no private data or owner execution."""
import copy,json
from v5_shadow import m18_offline_v2 as m
from v5_shadow.digests import canonical_bytes


def fixture():
    import test_m18_v2_rebound_projection as test
    import test_m18_v2_disk_pages as base
    row = {'adjustment_consistency': 'PANEL_RAW_NO_ADJUSTMENT',
     'amount_hkd': 1,
     'background20_status': 1,
     'classification': None,
     'close': 1,
     'close_position_0_low_1_high': 1,
     'code': 1,
     'connect_eligibility': 'VERIFIED_TARGET_UNIVERSE',
     'continuous_strength_highvolume_risk': False,
     'current_volume': 1,
     'day_positive_close_gt_prev_close': 1,
     'high_volume_ratio_ge_1_5': 1,
     'history_adjustment': 'NONE',
     'history_raw_error': None,
     'history_raw_status': 'SHARED_PANEL_READY',
     'history_source': 'V4_SHARED_HK_0_2_PANEL_AUTHORITY',
     'history_status': 1,
     'history_unknown_reasons': 1,
     'membership_source': {'exchange': 'HK_CONNECT', 'owner': 1, 'payload_sha256': 1, 'source_date': 1},
     'name': 1,
     'near_failed_gate': 1,
     'near_failed_value': 1,
     'near_gate_gap_ratio': 1,
     'near_gate_gap_value': 1,
     'near_gate_value': 1,
     'near_two_gate_one_missing': 1,
     'oversold_close_le_80pct_prior60_high': 1,
     'oversold_cutoff_80pct_prior60_high': 1,
     'oversold_flag': 1,
     'oversold_rebound_watch': 1,
     'pct_change': 1,
     'prev_close': 1,
     'previous20_mean_volume_background': 1,
     'previous20_session_count': 1,
     'previous5_mean_volume': 1,
     'previous5_session_count': 1,
     'prior60_session_count': 1,
     'prior60_session_high': 1,
     'qualification_status': 'RESEARCH_ONLY_CANDIDATE',
     'rebound_close_vs_low_pct': 1,
     'rebound_ge_3pct': 1,
     'recent_3_session_return_pct': None,
     'recent_5_session_return_pct': None,
     'research_boundary': 'RESEARCH_ONLY; no buy/sell/order conclusion',
     'source_refs': [{'manifest_path': 1,
                      'manifest_sha256': 1,
                      'owner': 1,
                      'payload_path': 1,
                      'payload_sha256': 1},
                     {'manifest_path': 1,
                      'manifest_sha256': 1,
                      'owner': 1,
                      'payload_path': 1,
                      'payload_sha256': 1}],
     'strict_two_gate_oversold_5dvolume': 1,
     'target_monday': 1,
     'update_time': None,
     'verified_session': 1,
     'volume_flag_5d_ge_1_5': 1,
     'volume_ratio_20d_background': 1,
     'volume_ratio_5d': 1,
     'volume_ratio_current_to_previous20_mean_background': 1,
     'volume_ratio_current_to_previous5_mean': 1}
    row.pop('verified_session');row['observed_session']=20261009
    row.pop('amount_hkd');row['amount_native']=100
    row.update(code='00001',name='SYNTHETIC',qualification_status='UNVERIFIED_RESEARCH_OBSERVATION',
        target_monday=20261012,connect_eligibility='UNVERIFIED',volume_source='SYNTHETIC',
        volume_unit_status='NOT_PROVEN',volume_scale_applied=1)
    source=dict(owner='SYNTHETIC',payload_path='/synthetic/private/path',payload_sha256='a'*64,
        manifest_path='/synthetic/private/manifest',manifest_sha256='b'*64)
    row['source_refs']=[source,dict(source),dict(owner='SYNTHETIC',artifact_path='/synthetic/private/artifact',
        artifact_sha256='c'*64,manifest_path='/synthetic/private/manifest',manifest_sha256='d'*64)]
    for key in ('research_priority_method','research_priority_rank','reason_for_group'):
        row[key]=None if key=='research_priority_rank' else 'SYNTHETIC'
    # Keep the original key shape while bringing each row close to actual 4 KiB.
    row['name'] += 'X'*max(0,4180-len(canonical_bytes(row)))
    groups={group:[dict(row,code=f'{group[:1]}{i:05}') for i in range(count)]
        for group,count in zip(test.GROUPS,(214,286,34,159,0))}
    for entry in groups['pending']:
        for key in ('research_priority_method','research_priority_rank','reason_for_group'):entry.pop(key)
    for entry in groups['excluded']:
        entry.pop('research_priority_rank');entry.pop('reason_for_group')
        entry.update(screen_decision='EXCLUDED',exclusion_reason_code='SYNTHETIC',reason_for_exclusion='SYNTHETIC')
    raw,identity,bundle=test.fixture(groups)
    payload=json.loads(raw)['payload'];del payload['plan_product']
    native=dict(schema_version='v3_shared_data.hk02_native_observation.v1',scope='NEW_INCREMENT_ONLY',
        requested_through_date='20261009',requested_after_date='20261008',selected_dates=['20261009'],
        session_finality='NOT_ATTESTED_BY_PROVIDER',owner_source_sha256='e'*64,
        read_started_at='2026-10-10T00:00:00+00:00',read_completed_at='2026-10-10T00:01:00+00:00',
        fields=dict(trade=dict(native_field='trade_v',byte_offset=24,storage_type='uint32_le',
            scale_applied=1,unit=None,unit_status='NOT_PROVEN')),
        source_files=[dict(source_relative=f'vipdoc/ds/lday/71#{i:05}.day',size_bytes=32000,
            selected_rows=1,sha256='f'*64) for i in range(693)])
    observation=payload[test.SECTION]['research_observation']
    observation['native_evidence']['native_observation']=native
    observation['authority']=dict(panel_witness=dict(native_observation=native),security_master={})
    saved=dict(run_id=base.RUN,target_trade_date=payload['target_trade_date'],
        input_identity=payload['input_identity'],workspace=copy.deepcopy(payload))
    saved['sha256']=m.sha(canonical_bytes(saved));saved_raw=canonical_bytes(saved)
    payload['plan_product']=dict(consumed=True,run_id=base.RUN,sha256=saved['sha256'])
    raw=canonical_bytes(dict(payload=payload,readback=dict(run_id=base.RUN,
        plan_sha256=saved['sha256'],input_identity=payload['input_identity'])))
    identity=dict(run_id=base.RUN,target_date=payload['target_trade_date'],
        input_identity=payload['input_identity'],plan_sha256=saved['sha256'],
        raw_sha256=m.sha(saved_raw),response_sha256=m.sha(raw))
    bundle=m.build(raw,saved_raw,identity,expected_profile=m.PROFILE_SHA256)
    return raw,identity,bundle
