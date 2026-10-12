"""Synthetic recipe derived from original test_store_backed_producer fixture.

No member/PIT or natural-run attestation is fabricated.
"""
from pathlib import Path
import subprocess
import sys
from v5_shadow.hk_close_daily import prepare_owner_capsule


def create_fixture(root, *, with_model=True, with_stages=True, close_offset=0, stage_mode="ready"):
    root=Path(root)
    script=r'''
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from infrastructure.hkconnect_close_store import CloseSnapshotStore
from infrastructure.preselection_pool_store import PreselectionPoolStore
from stage_center.selection import SelectionStore,select_hk_four_lane
from domains.close_review import _REVIEW_STAGE_IDS
root=Path(sys.argv[2]);date='20260730'
flags=dict(production_allowed=False,buy_gate_updated=False,orders_sent=False)
rows=[dict(trade_date=date,code=f'HK.{i:05d}',name=f'SYNTHETIC {i}',close=100+i+int(sys.argv[5]),pre_close=100,amount=i) for i in range(1,601)]
snapshot=dict(schema_version='v3_5.hkconnect_close_snapshot.v1',trade_date=date,status='READY',source_mode='SYNTHETIC_OFFLINE_FIXTURE',source_input_sha256='e'*64,universe_count=600,same_date_row_count=600,coverage_ratio=1.0,rows=rows,**flags)
CloseSnapshotStore(root).import_snapshot(snapshot)
if sys.argv[3]=='True':
    model=[dict(market='HK',symbol=f'HK.{i:05d}',stock_name=f'SYNTHETIC {i}',pool_id='hkconnect_d1_top100',pool_rank=i,target_date=date,recommendation_status='WATCH_ONLY') for i in range(1,101)]
    PreselectionPoolStore(root).materialize(dict(schema_version='v3_5.preselection_pool.v1',trade_date=date,pool_id='hkconnect_d1_top100',display_name='Synthetic HK D-1 Top100',market='HK',status='STRICT_0_2_READY',producer_id='synthetic.test',source_role='SHARED_VERIFIED_HK_0_2',source_path='fixture/hk.json',source_sha256='f'*64,rows=model,cannot_confirm=[],**flags))
if sys.argv[4]=='True':
    for offset,stage in enumerate(_REVIEW_STAGE_IDS):
        row=dict(code=f'HK.{600-offset:05d}',name='SYNTHETIC',pct_chg=1.0,last_price=101.0,open_price=100.0,high_price=101.0,low_price=100.0,prev_close=100.0,turnover=1000.0,volume_ratio=1.0)
        envelope=select_hk_four_lane([] if sys.argv[6]=='empty' else [row],date,stage,f'{offset+1:064x}',source_evidence=('fixture=SYNTHETIC_OFFLINE',))
        if sys.argv[6]=='partial':
            envelope['selection_status']='PARTIAL_WITH_ROWS';envelope['cannot_confirm']=['SYNTHETIC_SOURCE_GAP']
        SelectionStore(root/'stages').publish(envelope,market='HK_CONNECT')
'''
    with prepare_owner_capsule() as capsule:
        subprocess.run([sys.executable,'-I','-S','-B','-c',script,str(capsule),str(root),str(with_model),str(with_stages),str(close_offset),stage_mode],check=True,capture_output=True,text=True)
    return root
