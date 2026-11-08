"""Same-basis next-session provider. No scheduling, native calls, or asset writes.

The existing serial owner must inject a resource gate and run latest109 with the
returned prior_component_state. A verified upstream daily source contract is
mandatory; this adapter cannot turn unchecked raw quotes into admission.
"""
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from decimal import Decimal

ROOT = Path('/workspace/scratch/2d97ff6ac292')
OLD = ROOT/'handoff/panel109_nov5_increment_20261105/engine'
STEP = ROOT/'handoff/cloud_v5_daily_pipeline_20261102/r4_state_step/cloud_step.py'
PINS = {
    STEP: '8aed22a3c5d10710a1c2ddd53acf5e3770058f82e5ae64b32e1ba4a8319b7dc1',
    OLD/'bootstrap841.py': 'f56e8d26b8716605a75a75f92befdef812ca49ad8fb1c2491a92f877825df7e3',
    OLD/'prior4734.py': '03a8829e455f18c906e385fbf2e95b545e0f85f21d1de6c88f378a633403e265',
    ROOT/'handoff/unified_candidate_20261102/source.py': '5f5932db843a723e976dbea26bd79e05b1a2f494228ed2462fd5403c1d6ffe35',
}
FLAGS = dict.fromkeys(('source_admission','selection_admission','production_allowed',
                      'research_consumption_allowed','historical_PIT','volume_absolute_eligibility'), False)
LATEST_PINS = {'producer.py':'3b0d1685d4652133826dfa32148a4adfadabd6932d1dfb2ff2882fe91ab0bfaf','native_adapter.py':'751da7c1e9525244af51d165c6d2975a445c9ced097ec206b545b12632bb8a0c','foundation':'fbd79452e084c474edf87b7c320fb69827bb1453d1d31c6f3d42e4d4bf087bce','score':'8a6e0529114cc25973a41c7a5a0ba0fc0b209bb23005192b7d4becd9ec765191'}
BASIS_KEYS = ('price_coordinate','event_sha256','volume_contract_sha256')

def need(ok, reason):
    if not ok: raise ValueError(reason)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False).encode()

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()

def checked(ref, limit=16*1024**2):
    need(type(ref) is dict and {'path','bytes','sha256'} <= set(ref), 'REF_FIELDS')
    p = Path(ref['path']); p = p if p.is_absolute() else ROOT/p
    need(p == p.resolve() and p.is_relative_to(ROOT) and not p.is_symlink(), 'REF_PATH')
    before = p.stat(); need(0 < before.st_size == ref['bytes'] <= limit, 'REF_SIZE')
    data = p.read_bytes(); after = p.stat()
    need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) ==
         (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns), 'REF_CHANGED')
    need(len(data) == ref['bytes'] and hashlib.sha256(data).hexdigest() == ref['sha256'], 'REF_SHA')
    return data

def load(path, name):
    need(PINS.get(path) is not None and hashlib.sha256(path.read_bytes()).hexdigest() == PINS[path], 'CODE_PIN')
    spec = importlib.util.spec_from_file_location(name,path)
    m = importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def modules():
    sys.path.insert(0,str(ROOT/'handoff/unified_candidate_20261102'))
    return load(STEP,'continuous_original51_step'), load(ROOT/'handoff/unified_candidate_20261102/source.py','continuous_original_source')

def read_bundle(ref):
    raw = checked(ref, 2*1024**2)
    # Bounded decompression; a compressed bomb cannot become an unbounded read.
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f: data=f.read(4*1024**2+1)
    need(len(data)<=4*1024**2,'BUNDLE_EXPANSION_LIMIT')
    bundle=json.loads(data);state=bundle['state51'];day=bundle['daily51'];component=bundle['component109']
    need(bundle['schema'] in ('NOV5_MINIMUM_CONTINUATION_BUNDLE_V1','SAME_BASIS_CONTINUATION_BUNDLE_V1'), 'BUNDLE_SCHEMA')
    need(re.fullmatch(r'[0-9]{6}\.(SZ|SH|BJ)',bundle['symbol']) is not None,'BUNDLE_SYMBOL')
    need(type(bundle['asof']) is str and re.fullmatch(r'[0-9]{8}',bundle['asof']) is not None,'BUNDLE_ASOF_TYPE')
    date=int(bundle['asof']);datetime.date(date//10000,date//100%100,date%100)
    for value in (state['first_date'],state['last_date'],day['trade_date'],day['ohlcv']['trade_date']):
        need(type(value) is int and len(str(value))==8,'BUNDLE_DATE_TYPE');datetime.date(value//10000,value//100%100,value%100)
    need(state['first_date']<=date,'BUNDLE_DATE_RANGE')
    need(state['symbol']==component['symbol']==bundle['symbol'] and state['last_date']==day['trade_date']==date and component['last_date']==str(date),'BUNDLE_IDENTITY')
    need(day['ohlcv']['trade_date']==date and len(day['values'])==51 and len(day['drawings'])==22,'DAY51_22')
    need(state['last_daily_sha256']==digest(day) and state['state_sha256']==digest({k:v for k,v in state.items() if k!='state_sha256'}),'BUNDLE_STATE_HASH')
    need(component.get('schema')=='ORIGINAL109_LATEST_COMPONENT_STATE_V1' and component.get('original_pins')==LATEST_PINS,'COMPONENT_SCHEMA_PINS')
    need(type(state['count']) is int and type(component['count']) is int and state['count']==component['count'] and state['count']>0,'BUNDLE_COUNT')
    need(all(bundle.get(k) is False for k in FLAGS),'BUNDLE_NOT_GLOBAL_ADMISSION')
    return bundle

def append_day(rows,day,source,symbol):
    previous=rows[-1]
    bridge={'trade_date':int(previous['event_date']),'ohlcv':{'trade_date':int(previous['event_date']),
            **{k:previous[k] for k in ('open','high','low','close')},'vol':previous['volume']}}
    row=source.normalize([bridge,day],symbol)[-1];row['raw_row_index']=len(rows)
    return rows+[row]

class SeedHistory:
    """Read Nov5 seed references only, never bootstrap51 or evaluate native.

    Lazily initialized original adapters are used only for their raw readers.
    Later days carry parent-continuation references, not copies of full history.
    """
    def __init__(self,gate):
        self.gate=gate;self.existing=None;self.bootstrap=None
        self.step,self.source=modules()
    def __call__(self,bundle):
        self.gate();symbol=bundle['symbol'];history=bundle['history_refs']
        need(bundle['schema']=='NOV5_MINIMUM_CONTINUATION_BUNDLE_V1' and bundle['asof']=='20261105','SEED_SCHEMA_AND_DATE')
        if 'oct30_catalog_ref' in history:
            if self.existing is None:
                m=load(OLD/'prior4734.py','continuous_seed_prior')
                registry=ROOT/'handoff/panel_today4734_day_registry_20261104/DAY_REGISTRY.jsonl'
                prior={r['symbol']:r for r in map(json.loads,registry.read_bytes().splitlines())}
                self.existing=m.Provider(prior,{},None,self.gate)
            rows,_=self.existing.prior_rows(symbol)
            need(history['oct30_catalog_ref']==PINS_CATALOG,'SEED_CATALOG_IDENTITY')
            need(history['oct30_source_binding']==self.existing.catalog['symbols'][symbol] and history['nov2_nov3']==self.existing.days[symbol] and history['nov4_state_asset_ref']==self.existing.prior[symbol]['parquet_ref'],'SEED_ALL_HISTORY_REFS')
            rows=append_day(rows,bundle['daily51'],self.source,symbol)
        else:
            if self.bootstrap is None:
                m=load(OLD/'bootstrap841.py','continuous_seed_bootstrap')
                pin=history.get('nov5_raw')
                if pin is None:
                    # Shared Nov5 raw index fixed by the sealed seed catalog.
                    pin={'path':'handoff/panel109_nov5_increment_20261105/sources/FIXED5575_RAW_CANDIDATE.json','bytes':8362658,'sha256':'6c529a23c454f3a63f88a9a0ce8b0556dd821dd1b60e397a6d61d6ebb223654d'}
                raws={r['symbol']:r for r in json.loads(checked(pin))['rows']}
                self.bootstrap=m.Provider(raws,None,self.gate)
            if history['kind']=='TDX_RAW_DAY_PLUS_ACTUAL_APPEND_PLUS_NOV5_EVENTS':
                bars,refs,_=self.bootstrap._tdx_bars(symbol)
                for k,v in refs.items(): need(history[k]==v,'SEED_TDX_REF_IDENTITY:'+k)
            elif history['kind']=='SINA_SAME_PROVIDER_RAW_AND_FACTORS_NOV5':
                old_source=json.loads(checked(history['prior_authoritative_source']))
                bars,refs,_=self.bootstrap._sina_bars(symbol,old_source)
                for k,v in refs.items():need(history[k]==v,'SEED_SINA_REF_IDENTITY:'+k)
            else:raise ValueError('SEED_SOURCE_KIND')
            e=self.step.engine();normalized=e.json_ready(e.normalize(bars))
            rows=self.source.normalize([{'trade_date':r['trade_date'],'ohlcv':r} for r in normalized],symbol)
        # Historical original51 columns are unnecessary for latest109.
        for row in rows:row.pop('original_values',None)
        rows[-1]['original_values']={k:bundle['daily51']['values'].get(k) for k in ('MA60','白线','黄线','一级买点','二级买点','卖点')}
        return rows

PINS_CATALOG={'path':'handoff/unified_candidate_20261102/SOURCE_BINDINGS_V2.json','bytes':12801327,'sha256':'71854c8985db863fc0c4f1c54da8c89a68b1dab1fad0144a72b3477a1648166e'}

class Provider:
    def __init__(self, gate, seed_history=None):
        self.gate=gate;self.step,self.source=modules();self.seed_history=seed_history or SeedHistory(gate)
    def prefix(self,bundle,seen=None):
        seen=set() if seen is None else seen
        self.gate();history=bundle['history_refs']
        if bundle['schema']=='NOV5_MINIMUM_CONTINUATION_BUNDLE_V1':rows=self.seed_history(bundle)
        else:
            pin=history['parent_continuation_ref'];key=pin['sha256']
            need(key not in seen and len(seen)<366,'CONTINUATION_CYCLE_OR_DEPTH');seen.add(key)
            parent=read_bundle(pin)
            need(parent['symbol']==bundle['symbol'] and int(parent['asof'])<int(bundle['asof']),'PARENT_IDENTITY')
            rows=append_day(self.prefix(parent,seen),bundle['daily51'],self.source,bundle['symbol'])
        need(len(rows)==bundle['state51']['count'] and rows[-1]['event_date']==bundle['asof'],'PREFIX_COUNT_DATE')
        for k in ('open','high','low','close'):
            need(Decimal(str(rows[-1][k]))==Decimal(str(bundle['daily51']['ohlcv'][k])),'PREFIX_LAST_PRICE')
        need(Decimal(str(rows[-1]['volume']))==Decimal(str(bundle['daily51']['ohlcv']['vol'])),'PREFIX_LAST_VOLUME')
        self.gate();return rows
    def prepare(self, prior_ref, input_ref, expected_input_sha256):
        """Input SHA must come from independent source review, not self-approval.

        input_ref pins a SAME_SOURCE_NEXT_SESSION_INPUT_V1 contract containing
        a pinned formula_bar_ref in the exact saved state volume/basis units.
        A missing-bar contract returns RETAINED; no step or prefix read occurs.
        """
        self.gate();need(input_ref['sha256']==expected_input_sha256,'EXTERNAL_INPUT_PIN')
        facts=json.loads(checked(input_ref));prior=read_bundle(prior_ref);state=prior['state51']
        need(facts['schema']=='SAME_SOURCE_NEXT_SESSION_INPUT_V1','INPUT_SCHEMA')
        need(facts['prior_continuation_ref']==prior_ref and facts['symbol']==prior['symbol'],'INPUT_PRIOR_IDENTITY')
        target=facts['target_date'];observation=facts['observation_date'];self.step.valid_date(target,'TARGET_DATE');self.step.valid_date(observation,'OBSERVATION_DATE')
        calendar=state['binding']['date_contract']['open_dates']
        need(target>int(prior['asof']),'NO_REPLAY_OR_REDATE')
        need(calendar==sorted(set(calendar)) and target in calendar,'VERIFIED_CALENDAR_TARGET')
        i=calendar.index(target);need(i>0 and i+1<len(calendar) and calendar[i+1]==observation,'NEXT_OBSERVATION_SESSION')
        if facts['status']=='VERIFIED_NO_VALID_BAR':
            need(facts.get('no_bar_evidence_ref') is not None,'NO_BAR_EVIDENCE_REQUIRED');checked(facts['no_bar_evidence_ref'])
            return {'status':'RETAINED_NO_VALID_BAR','symbol':prior['symbol'],'event_date':prior['asof'],'requested_date':str(target),'prior_continuation_ref':prior_ref,'input_ref':input_ref,'original51_step_calls':0,**FLAGS}
        need(facts['status']=='VERIFIED_SAME_BASIS_BAR','SOURCE_REVIEW_STATUS')
        need(calendar[i-1]==int(prior['asof']),'STATE_GAP_REQUIRES_REVIEWED_RECOVERY')
        need(facts['basis']=={k:state['binding'].get(k) for k in BASIS_KEYS},'SOURCE_BASIS_CHANGED_REBUILD_REQUIRED')
        need(facts['effective_price_or_volume_change'] is False,'EVENT_REBUILD_REQUIRED')
        need(facts.get('source_evidence_refs') and type(facts['source_evidence_refs']) is list,'SOURCE_EVIDENCE_REQUIRED')
        for pin in facts['source_evidence_refs']:checked(pin)
        bar=json.loads(checked(facts['formula_bar_ref'],128*1024))
        need(bar.get('symbol')==prior['symbol'] and bar['trade_date']==target,'BAR_IDENTITY')
        need(Decimal(str(facts['prior_close_same_basis']))==Decimal(str(prior['daily51']['ohlcv']['close'])),'PRIOR_CLOSE_BOUNDARY')
        for k in ('open','high','low','close','vol'):
            need(type(bar[k]) is str and Decimal(bar[k]).is_finite() and Decimal(bar[k])>0,'POSITIVE_FORMULA_BAR')
        need(Decimal(bar['low'])<=min(Decimal(bar['open']),Decimal(bar['close']))<=max(Decimal(bar['open']),Decimal(bar['close']))<=Decimal(bar['high']),'BAR_ENVELOPE')
        rows=self.prefix(prior);before=digest(prior);state_bytes=canonical(state)
        self.gate();day,newstate=self.step.step(state,bar,state['binding'],verified_state_bytes=state_bytes,expected_state_sha256=hashlib.sha256(state_bytes).hexdigest());self.gate()
        need(digest(prior)==before,'PRIOR_MUTATED')
        rows=append_day(rows,day,self.source,prior['symbol'])
        return {'status':'PREPARED_ONE_SESSION','symbol':prior['symbol'],'rows':rows,
                'context':{'symbol':prior['symbol'],'currency':'CNY','asof':str(target),'observation_date':str(observation),'prefix_complete':True},
                'daily':day,'state':newstate,'prior_component_state':prior['component109'],
                'history_refs':{'kind':'SAME_BASIS_PARENT_CONTINUATION','parent_continuation_ref':prior_ref,'input_ref':input_ref},
                'provenance':{'prior_date':int(prior['asof']),'target_date':target,'original51_step_calls':1,'historical51_rows_recomputed':0,'historical109_rows_evaluated':0,'full_history_copied':False,'source_input_ref':input_ref},**FLAGS}

def continuation(prepared,component_state):
    need(prepared['status']=='PREPARED_ONE_SESSION','PREPARED_STATUS')
    need(component_state.get('schema')=='ORIGINAL109_LATEST_COMPONENT_STATE_V1' and component_state.get('original_pins')==LATEST_PINS,'NEW_COMPONENT_PINS')
    need(component_state['symbol']==prepared['symbol'] and component_state['last_date']==prepared['context']['asof'] and component_state['count']==prepared['state']['count'],'NEW_COMPONENT_IDENTITY')
    return {'schema':'SAME_BASIS_CONTINUATION_BUNDLE_V1','symbol':prepared['symbol'],'asof':prepared['context']['asof'],
            'daily51':prepared['daily'],'state51':prepared['state'],'component109':component_state,
            'history_refs':prepared['history_refs'],'provenance':prepared['provenance'],'full_history_copied':False,**FLAGS}
