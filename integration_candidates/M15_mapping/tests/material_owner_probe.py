"""Synthetic original-parser contract probe. Never a production binding."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime/V5/src'))
from v5_shadow.manager_plan import load_owner
load_owner()
from v4.manager_research.workspace_plan import plan_context
from v4.manager_research.workspace_discovery import project_material_discovery
from v4.manager_research.research_evidence import collect_attention_evidence
from datetime import datetime
import copy,json
context=plan_context('20261012',now=datetime.fromisoformat('2026-10-10T01:00:00+00:00'))
source=dict(material_id='SYNTHETIC_ONLY',title='测试甲公司业务公告',verification='OWNER_VERIFIED',
 source_refs=[dict(status='VERIFIED',payload_sha256='a'*64)],published_at='2026-10-09T08:20:00+00:00',
 available_at='2026-10-09T09:00:00+00:00',retrieved_at='2026-10-09T08:30:00+00:00',
 source_row=dict(body_text='测试甲公司与NASDAQ:AVGO签署光模块产品供应合同。'),claim_type='SOURCE_STATEMENT')
master={'HK.00001':dict(name='测试甲公司')};identity=dict(status='OWNER_VERIFIED',source_date=context['market_session'],artifact_sha256='b'*64)
cards=project_material_discovery([source],master,identity,context)
market=dict(status='READY',mapping_eligible=True,captured_at='2026-10-09T20:16:00+00:00',
 source_identity=dict(status='VERIFIED',payload_sha256='c'*64,receipt_sha256='d'*64,manifest_sha256='e'*64),
 raw_industry_up=[dict(label='CPO',status='READY')],raw_individual_up=[dict(symbol='AVGO')],
 research_material_input=dict(complete=True,status='READY'))
def call(cs,mm=market):
 return collect_attention_evidence(market_screen=None,stocks=[],material_cards=cs,themes=[],announcement_observation=None,
 us_market=mm,start=datetime.fromisoformat(context['focus_window_start']),cutoff=datetime.fromisoformat(context['research_cutoff']))
result=call(cards)
print(json.dumps(dict(cards=cards,industry=result.us_industry,individual=result.us_individual,diagnostics=result.us_mapping_diagnostics),ensure_ascii=False))
assert result.us_industry and result.us_individual, 'Expected original body parser to accept both independent synthetic relations'
for field in ('available_at','retrieved_at'):
 bad=copy.deepcopy(cards);bad[0][field]=None;out=call(bad);assert not out.us_industry and not out.us_individual
bad=copy.deepcopy(cards);bad[0]['propositions'][0]['quote']='not the original span';out=call(bad);assert not out.us_industry and not out.us_individual
bad=copy.deepcopy(cards);bad[0]['identity_source']['status']='UNKNOWN';out=call(bad);assert not out.us_industry and not out.us_individual
bad=copy.deepcopy(cards);bad[0]['available_at']='2026-10-11T00:00:00Z';out=call(bad);assert not out.us_industry and not out.us_individual
bad=copy.deepcopy(cards);bad[0]['source_refs'][0]['payload_sha256']='c'*64;out=call(bad);assert not out.us_industry and not out.us_individual
print('PASS original material positive/clock/span/identity/independence probes')
