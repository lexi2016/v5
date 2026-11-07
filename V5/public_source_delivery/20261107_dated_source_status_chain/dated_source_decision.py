"""Dated pure source decision, reuses frozen V3 functions without running V3.
No capture, locks, writes, owner/formula execution or automatic admission.
Caller must bind physical source delta/review before consuming the result.
"""
import ast, hashlib, json, math, re, types
from pathlib import Path
ROOT=None;SOURCE=None;SOURCE_SHA=None

def need(ok,reason):
    if not ok: raise ValueError(reason)

def decision_context(reader, calendar_ref, cap, functions):
    """All date bindings are per-context, never shared mutable module globals.
    `reader` is the existing checked portable reader; `cap` and original functions
    are supplied by the existing isolated V3 owner, not a replacement IO stack.
    """
    need(isinstance(ROOT,Path) and ROOT.is_absolute() and isinstance(SOURCE,str) and bool(SOURCE) and isinstance(SOURCE_SHA,str) and len(SOURCE_SHA)==64,'NO_APPROVED_PRIVATE_BINDING')
    relative=Path(SOURCE);path=ROOT/relative
    need(not relative.is_absolute() and '..' not in relative.parts and not ROOT.is_symlink() and not any((ROOT/Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)) and path.resolve().is_relative_to(ROOT.resolve()),'SOURCE_PATH')
    calendar=json.loads(reader.checked(calendar_ref))
    need(calendar.get('status')=='VERIFIED_CURRENT_SESSION_CALENDAR' and calendar.get('reviewer_role')=='independent_reviewer','CURRENT_CALENDAR_REVIEW')
    p,d,n=(calendar.get(k) for k in ('prior_date','target_date','observation_date'))
    need(all(type(x)is int for x in (p,d,n)),'DATE_TYPES')
    for value in (p,d,n): cap.portable.date_value(value)
    need(p<d<n,'SOURCE_DATES')
    need(bool(calendar.get('evidence_refs')),'CALENDAR_EVIDENCE_REQUIRED')
    for pin in calendar['evidence_refs']: reader.checked(pin)
    raw=(ROOT/SOURCE).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'V3_SOURCE_PIN')
    tree=ast.parse(raw)
    names={'valid_events','history_family','decide'}
    nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names]
    need({x.name for x in nodes}==names and len(nodes)==3,'V3_FUNCTION_SET')
    ns={'need':need,'cap':cap,'P':p,'D':d,'N':n,'math':math,'re':re,'hashlib':hashlib,'BASIS':('price_coordinate','event_sha256','volume_contract_sha256')}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/SOURCE)+'::dated_pure_functions','exec'),ns)
    def decide(selection,row,bundle,validated_event_rows,expected_count):
        # No caller-provided truncated "effective" subset: the full decoded rows
        # are validated by unchanged V3 code and filtered with bound dates here.
        effective=ns['valid_events'](validated_event_rows,expected_count)
        facts,bar=ns['decide'](selection,row,bundle,effective,functions)
        facts['date_binding']={'calendar_ref':dict(calendar_ref),'prior_date':p,'target_date':d,'observation_date':n,'v3_source_sha256':SOURCE_SHA}
        facts['not_source_admission']=True
        return facts,bar
    return decide
