"""Synthetic 17:00 report-to-outbox preparation. No sender or production binding.
Original terminal nodes.py owns state/approval review; this module never calls it.
A pinned report is input evidence, NOT independently verified business success.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import types
from zoneinfo import ZoneInfo
REGISTRY = {}
PIN = '50a7fee95e2b24911ee3c205b5e402316a764e7d7d1ece2a634bb78552ac5891'
KEYS = ('task_id','node','environment_id','binding_version','authorization_ref','channel','destination','input_sha256','code_version','data_date','run_id','output_root')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(doc): return json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def _outbox():
    path=Path(__file__).with_name('outbox.py');raw=path.read_bytes()
    if sha(raw)!=PIN: raise ValueError('DEPENDENCY_CHANGED')
    module=types.ModuleType('terminal_outbox');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

def assemble(raw, expected_sha, date, identity):
    if sha(raw)!=expected_sha: raise ValueError('REPORT_CHANGED')
    r=json.loads(raw)
    if r.get('schema')!='RETRY_TERMINAL_NODE_V1' or r.get('node')!='terminal-1700': raise ValueError('REPORT_TYPE')
    if r.get('target_date')!=date or not identity or r.get('identity')!=identity: raise ValueError('REPORT_IDENTITY')
    when=dt.datetime.fromisoformat(r['checked_at'])
    if when.utcoffset() is None: raise ValueError('AWARE_CLOCK_REQUIRED')
    local=when.astimezone(ZoneInfo('Asia/Shanghai'))
    if local.strftime('%Y%m%d')!=date or local.time()<dt.time(17): raise ValueError('TERMINAL_DATE_TIME_GATE')
    known={'COMPLETED_REVIEW_VERIFIED','UNKNOWN_RECONCILIATION_REQUIRED','NOT_RUN','BLOCKED'}
    status=r.get('status') if r.get('status') in known else 'UNKNOWN'
    return {'schema':'SYNTHETIC_TERMINAL_ALERT_V1','node':'1700','data_date':date,
        'report_sha256':expected_sha,'identity':identity,'reported_generation_status':status,
        'generation_independently_verified':False,'alert_required':status!='COMPLETED_REVIEW_VERIFIED',
        'reason':r.get('reason'),'browser_acceptance':'UNKNOWN','delivery_status':'UNKNOWN',
        'business_accepted':False,'natural_verified':False}

def prepare(key, raw):
    if key not in REGISTRY: raise ValueError('NO_SYNTHETIC_BINDING')
    b=REGISTRY[key]
    if b.get('domain')!='synthetic': raise ValueError('PRODUCTION_BLOCKED')
    c=b['outbox_config']
    if {k:c[k] for k in KEYS}!=b['identity'] or c['node']!='1700' or c['destination']!='SYNTHETIC_NO_RECIPIENT': raise ValueError('OUTBOX_BINDING_CHANGED')
    if c['input_sha256']!=b['report_sha256']: raise ValueError('INPUT_BINDING_CHANGED')
    alert=assemble(raw,b['report_sha256'],c['data_date'],b['report_identity'])
    outbox=_outbox();outbox.REGISTRY={'synthetic':c}
    # Deliberately only preparation. No attempt, reconcile, sender or owner execution.
    item=outbox.prepare('synthetic',canonical(alert).decode())
    return {'status':'SYNTHETIC_PREPARATION_ONLY','alert':alert,'outbox':item,
            'delivery_state':item['state'],'sent_in_this_call':False,
            'delivery_verified':False,'natural_verified':False,'business_accepted':False}


# New explicit contract; the legacy synthetic prepare() above remains unchanged.
DELIVERY_BRIDGE_SHA = 'a9369a26d5ca8f016f62d3484db543687b7afdc68de7ef1f14371fd7b0d38ca0'


def _delivery_bridge():
    path = Path(__file__).with_name('controlled_delivery.py')
    raw = path.read_bytes()
    if sha(raw) != DELIVERY_BRIDGE_SHA:
        raise ValueError('DELIVERY_BRIDGE_CHANGED')
    module = types.ModuleType('terminal_controlled_delivery')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def run(registration_id, action='prepare'):
    """Registered 17:00 report -> unchanged outbox -> explicit delivery proof.

    The original terminal owner still creates/reviews RETRY_TERMINAL_NODE_V1.
    This adapter reads its pinned report and independent review callback; it
    cannot manufacture that owner, source contract or recipient registration.
    """
    if registration_id not in REGISTRY:
        return dict(status='BLOCKED', reason='NO_REVIEWED_OWNER_BINDING',
                    delivery_state='NOT_ATTEMPTED', sent_in_this_call=False,
                    delivery_verified=False, natural_verified=False, business_accepted=False)
    bridge = _delivery_bridge()
    binding = REGISTRY[registration_id]
    try:
        bridge.validate_binding(binding, 'TERMINAL_ALERT_BINDING_V2')
        if action not in ('prepare', 'deliver', 'reconcile'):
            raise ValueError('DELIVERY_ACTION')
        if not callable(binding.get('review_report')):
            raise ValueError('MISSING_INDEPENDENT_REPORT_REVIEW')
        io = bridge.safeio()

        def load_reviewed():
            now = bridge.clock_gate(binding, '1700', allow_later=action == 'reconcile')
            raw = bridge.checked_pin(io, binding['input_root'], binding['report'])
            report = json.loads(raw)
            item = assemble(raw, binding['report']['sha256'], binding['run_date'],
                            binding['report_identity'])
            if dt.datetime.fromisoformat(report['checked_at']) > now:
                raise ValueError('REPORT_FROM_FUTURE')
            proof = binding['review_report'](
                report=json.loads(raw), report_sha256=binding['report']['sha256'])
            expected = dict(schema='TERMINAL_REPORT_REVIEW_V2', status='VERIFIED',
                            report_sha256=binding['report']['sha256'],
                            report_identity=binding['report_identity'],
                            target_date=binding['run_date'],
                            source_contract_ref=binding['source_contract_ref'])
            if (not isinstance(proof, dict) or any(proof.get(k) != v for k, v in expected.items())
                    or not bridge.text_identity(proof.get('reviewer_id'))
                    or proof['reviewer_id'] == binding['owner_id']
                    or not bridge.text_identity(proof.get('evidence_ref'))
                    or type(proof.get('generation_independently_verified')) is not bool):
                raise ValueError('INDEPENDENT_REPORT_REVIEW_MISMATCH')
            item.update(schema='TERMINAL_ALERT_V2', evidence_domain=binding['domain'],
                        source_contract_ref=binding['source_contract_ref'], report_review=proof,
                        generation_independently_verified=proof['generation_independently_verified'])
            item['alert_required'] = (item['reported_generation_status'] != 'COMPLETED_REVIEW_VERIFIED'
                                      or not proof['generation_independently_verified'])
            return item

        with binding['owner_context']():
            bridge.original_gate(binding)
            item = load_reviewed()
        frozen_alert = bridge.canonical(item)

        def preflight():
            # Called again while the original outbox holds the original owner.
            if bridge.canonical(load_reviewed()) != frozen_alert:
                raise ValueError('REPORT_REVIEW_CHANGED')

        version = bridge.sha(bridge.canonical(dict(
            adapter=sha(Path(__file__).read_bytes()), bridge=DELIVERY_BRIDGE_SHA,
            outbox=PIN, safeio=bridge.SAFEIO_SHA)))
        result = bridge.dispatch(binding, node='1700', input_sha256=binding['report']['sha256'],
                                 code_version=version, payload=item, preflight=preflight, action=action)
        return result | {'node': 'terminal-1700', 'alert': item}
    except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
        return bridge.blocked(type(error).__name__ + ':' + str(error), node='terminal-1700')
    except OSError as error:
        return dict(status='UNKNOWN_RECONCILIATION_REQUIRED', node='terminal-1700',
                    reason=type(error).__name__, delivery_state='UNKNOWN', sent_in_this_call=None,
                    delivery_verified=False, natural_verified=False, business_accepted=False)
