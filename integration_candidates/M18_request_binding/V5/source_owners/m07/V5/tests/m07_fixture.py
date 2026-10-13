"""Synthetic input producer using unchanged owner contracts, no market data."""
import copy,hashlib,json,sys
from pathlib import Path
OWNER=Path(__file__).resolve().parents[2]/'owner'
sys.path.insert(0,str(OWNER))
from infrastructure.data_store import NativeDataStore,_canonical_bytes,_sha256
from infrastructure.preselection_pool_store import PreselectionPoolStore
from infrastructure.research_store import HourlyResearchStore
from stage_center.input_contracts import a_pool_contract,KNOWN_A_STAGE_POOL_IDS
from stage_center.raw_store import RawStore
from stage_center.contracts import STAGE_BY_ID
from domains.research import build_research_archive

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(_canonical_bytes(value))

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def binding(root):
 return dict(root=str(root),files={str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='.v5-m07-input' and not p.name.startswith('.')})


def make_case(root,count=12,stage='STAGE_0930_0935'):
 date='20261012';day='2026-10-12';spec=STAGE_BY_ID[stage]
 roots={key:root/key for key in ('pool','live','research','morning')}
 for p in roots.values():p.mkdir();(p/'.v5-m07-input').write_bytes(b'v5.m07-input-copy.v1\n')
 codes=[f'{i+1:06}' for i in range(count)]
 pools={}
 pool_store=PreselectionPoolStore(roots['pool'])
 for pool in KNOWN_A_STAGE_POOL_IDS:
  status,producer,role=a_pool_contract(pool)
  signal='20261009' if pool.startswith('a_d1_') else date
  pools[pool]=signal
  payload=dict(schema_version='v3_5.preselection_pool.v1',trade_date=date,target_date=date,signal_date=signal,pool_id=pool,display_name='SYNTHETIC',market='A',status=status if codes else 'VALID_EMPTY',producer_id=producer,source_role=role,source_path='SYNTHETIC',source_sha256='a'*64,rows=[dict(symbol='A.'+c,market='A',pool_id=pool,target_date=date,signal_date=signal,stage_selection_eligible=True) for c in codes],cannot_confirm=[],production_allowed=False,buy_gate_updated=False,orders_sent=False,stage_selection_eligible=True)
  artifact,receipt=pool_store._relative(date,pool)
  write(roots['pool']/artifact,payload)
  write(roots['pool']/receipt,pool_store._receipt(trade_date=date,pool_id=pool,artifact_path=artifact,artifact_sha256=_sha256(payload),payload=payload))
 write(roots['pool']/f'preselection_pools/{date}/manifest.json',{p:_sha256(json.loads((roots['pool']/pool_store._relative(date,p)[0]).read_bytes())) for p in pools})
 start,end=spec.window.split('-');stamp=f'{day}T{end}:00+08:00'
 rows=[dict(batch_index=i+1,code='A.'+c,name='SYNTHETIC',update_time=stamp.replace('T',' ')[:19],last_price=11,open_price=10,high_price=11,low_price=10,prev_close_price=10,turnover=100000000+i*1000000,volume=1000000,bid_price=11,ask_price=11.01,bid_vol=100,ask_vol=100,window_start=f'{day} {start}:00',window_end=stamp.replace('T',' ')[:19],bar_count=5,temporal_cutoff_safe=True) for i,c in enumerate(codes)]
 raw=RawStore(roots['live']).publish(trade_date=date,stage_id=stage,market='A_SHARE',source_id='SYNTHETIC_A_QUOTES',source_status='READY' if rows else 'READY_EMPTY',rows=rows,cannot_confirm=[],source_evidence=['SYNTHETIC_ONLY'],requested_rows=count,missing_symbols=[],window=spec.window,cutoff_at=spec.cutoff)
 source=_source(date,slot='0900',with_stage_evidence=True)
 for field in ('stock_research_timeline','stock_research_daily','research_items'):
  seed=source[field][0];source[field]=[]
  for c in codes:
   item=copy.deepcopy(seed);item['stock_code']=c;item['stock_name']='SYNTHETIC'
   for k in ('dedup_key','item_id','raw_id','evidence_id'):
    if k in item:item[k]+='-'+c
   source[field].append(item)
 source_bytes=_canonical_bytes(source);sha=hashlib.sha256(source_bytes).hexdigest()
 witness=roots['research']/'research/hourly/source'/f'{sha}.json';witness.parent.mkdir(parents=True,exist_ok=True);witness.write_bytes(source_bytes)
 payload=build_research_archive(source,source_input_sha256=sha)
 HourlyResearchStore(roots['research']).publish(payload,slot='0900',mode='LIVE')
 _write_morning(roots['morning'],date)
 # Rewrite the synthetic morning trio with all fixture codes through original hashes.
 morning=json.loads((roots['morning']/f'morning_news/{date}.json').read_bytes())
 morning['stock_mentions']=[dict(stock_code=c,news_quality_score=12.0,intersection_summary='SYNTHETIC') for c in codes];morning['mention_count']=count
 write(roots['morning']/f'morning_news/{date}.json',morning)
 manifest=json.loads((roots['morning']/f'morning_news/{date}.manifest.json').read_bytes());manifest['payload_sha256']=_sha256(morning)
 write(roots['morning']/f'morning_news/{date}.manifest.json',manifest)
 receipt=json.loads((roots['morning']/f'morning_news/{date}.receipt.json').read_bytes());receipt['manifest_sha256']=_sha256(manifest)
 write(roots['morning']/f'morning_news/{date}.receipt.json',receipt)
 latest=json.loads((roots['morning']/'morning_news/latest.json').read_bytes());latest['entries'][date]['payload_sha256']=_sha256(morning);write(roots['morning']/'morning_news/latest.json',latest)
 return dict(schema_version='v5.m07_daily_request.v1',target_date=date,stage_id=stage,cutoff=f'{day}T{spec.cutoff}+08:00',data_kind='SYNTHETIC',trigger='RECORDED_INPUT_REPLAY',natural=False,pool_source_dates=pools,inputs={key:binding(p) for key,p in roots.items()},recording=dict(run_id=raw['run_id'],artifact_sha256=raw['artifact_sha256'],manifest_sha256=raw['manifest_sha256'],receipt_sha256=raw['receipt_sha256'],captured_at=stamp,acquired_at=stamp),expected_generation=None)


def _source(date: str, *, slot: str, with_stage_evidence: bool) -> dict:
    dashed = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    timeline = {
        "stock_code": "000001",
        "stock_name": "平安银行",
        "event_time": f"{dashed}T{slot[:2]}:{slot[2:]}:00+08:00",
        "source_published_at": f"{dashed}T08:31:00+08:00",
        "first_seen_at": f"{dashed}T08:32:00+08:00",
        "last_checked_at": f"{dashed}T{slot[:2]}:{slot[2:]}:00+08:00",
        "source_type": "hourly_research",
        "source_name": "小时研报",
        "source_title": f"银行跟踪 {slot}",
        "source_path": "v4/hourly/source.json",
        "url": "https://example.test/research",
        "theme": "银行",
        "catalyst": "业绩",
        "evidence_sentence": "只读研究证据",
        "evidence_level": "L2_MEDIUM",
        "confidence": "MEDIUM",
        "dedup_key": f"source-{slot}",
    }
    source = {
        "schema_version": "v3_research_lane.v2",
        "trade_date": date,
        "source_manifest": {
            "generated_at": f"{dashed}T{slot[:2]}:{slot[2:]}:00+08:00",
            "hourly_slot": slot,
            # These are source-side provenance fields.  The final hourly
            # payload/receipt SHA is verified independently by HourlyResearchStore.
            "manifest_sha256": "b" * 64,
            "receipt_sha256": "c" * 64,
        },
        "stock_research_timeline": [timeline],
        "stock_research_daily": [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "first_seen_time": f"{dashed}T08:32:00+08:00",
                "last_seen_time": f"{dashed}T{slot[:2]}:{slot[2:]}:00+08:00",
                "research_score": 97,
                "research_status": "REPEATED",
                "evidence_count": 1,
                "source_count": 1,
                "strong_evidence_count": 0,
                "medium_evidence_count": 1,
                "weak_evidence_count": 0,
                "source_types": ["hourly_research"],
                "themes": ["银行"],
                "top_catalysts": ["业绩"],
            }
        ],
        "research_pool_bridge": [],
        "cannot_confirm": [],
    }
    if with_stage_evidence:
        timeline.update(
            {
                "is_new_since_last_slot": True,
                "is_recheck_duplicate": False,
                "evidence_id": "evidence-000001",
            }
        )
        source["research_items"] = [
            {
                "item_id": "item-000001",
                "raw_id": "raw-000001",
                "stock_code": "000001",
                "item_quality": "OK",
                "quality_score": 72.5,
                "quality_score_raw": "72.5",
                "is_new_since_last_slot": True,
                "is_recheck_duplicate": False,
                "source_path": "v4/hourly/source.json",
                "source_title": f"银行跟踪 {slot}",
                "url": "https://example.test/research",
                "cannot_confirm": [],
            }
        ]
    return source

def _write_morning(root: Path, date: str = "20260911") -> None:
    store = NativeDataStore(root)
    payload = {
        "schema_version": "v3_shared_data.morning_news.v1",
        "trade_date": date,
        "source_role": "JIUYANGONGSHE_MORNING_NEWS",
        "articles": [{"article_id": "article-1", "title": "早盘"}],
        "article_count": 1,
        "stock_mentions": [
            {
                "stock_code": "000001",
                "news_quality_score": 12.0,
                "intersection_summary": "早盘明确提及",
            }
        ],
        "mention_count": 1,
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    }
    payload_sha = _sha256(payload)
    manifest = {
        "schema_version": "v3_shared_data.morning_news_manifest.v1",
        "trade_date": date,
        "payload_sha256": payload_sha,
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    }
    receipt = {
        "schema_version": "v3_shared_data.morning_news_receipt.v1",
        "trade_date": date,
        "manifest_sha256": _sha256(manifest),
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    }
    payload_rel = f"morning_news/{date}.json"
    manifest_rel = f"morning_news/{date}.manifest.json"
    receipt_rel = f"morning_news/{date}.receipt.json"
    store._write(payload_rel, payload)
    store._write(manifest_rel, manifest)
    store._write(receipt_rel, receipt)
    store._write(
        "morning_news/latest.json",
        {
            "schema_version": "v3_shared_data.morning_news_latest.v1",
            "entries": {
                date: {
                    "payload_relative": payload_rel,
                    "manifest_relative": manifest_rel,
                    "receipt_relative": receipt_rel,
                    "payload_sha256": payload_sha,
                }
            },
        },
    )
