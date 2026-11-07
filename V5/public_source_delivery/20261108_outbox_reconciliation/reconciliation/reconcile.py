"""Internal read-only evidence classifier; no retry, source IO or lock capability.
Caller must independently verify immutable evidence pins and exact unit-to-attempt
scope. No live caller is bound here. Missing evidence is never zero execution.
"""
import copy

TRUSTED_RUNS = {}

def classify(scope, attempts, *, verify):
    """verify verifies EACH full evidence record against trusted original receipts.
    This callback is a boundary precondition, NOT a production authorization.
    Caller supplies a frozen full scope, not a subset guessed from missing files.
    Completed is original independently reviewed terminal, not SUCCESS filename.
    """
    if type(scope) is not list or not scope or any(type(x) is not str or not x for x in scope) or len(scope)!=len(set(scope)):
        raise ValueError('FULL_UNIQUE_SCOPE_REQUIRED')
    if type(attempts) is not list or not callable(verify):raise ValueError('EVIDENCE_INTERFACE')
    observed={s:[] for s in scope}; identities=set()
    for a0 in attempts:
        a=copy.deepcopy(a0)
        if type(a) is not dict or set(a)!={'attempt_id','units','binding','review','review_ref','terminal_ref'}:
            raise ValueError('ATTEMPT_SCHEMA')
        aid=a['attempt_id'];units=a['units'];r=a['review']
        if type(aid) is not str or not aid or aid in identities:raise ValueError('DUPLICATE_ATTEMPT')
        identities.add(aid)
        if type(units) is not list or not units or len(units)!=len(set(units)) or any(u not in observed for u in units):raise ValueError('EXACT_SCOPE_REQUIRED')
        # Never consume a status without independently pin/review/scope verification.
        valid = verify(copy.deepcopy(a)) is True
        outcome='UNKNOWN';reason='UNVERIFIED_EVIDENCE'
        if valid and type(r) is dict and r.get('status')=='PASS_ATTEMPT_RECONCILIATION' and r.get('reviewer_role')=='independent_reviewer' and r.get('binding')==a['binding'] and r.get('attempt_id')==aid:
            if r.get('outcome')=='completed' and a['terminal_ref'] is not None:
                # verifier must additionally call original success(), validate terminal
                # scope/identity and unchanged pins, not just review text.
                outcome='SUCCESS_REVIEW_VERIFIED';reason='EXACT_ORIGINAL_TERMINAL_REVIEW'
            elif r.get('outcome')=='known_not_executed' and type(r.get('executed_units')) is int and r['executed_units']==0:
                outcome='KNOWN_ZERO_EXECUTION';reason='WHOLE_ATTEMPT_ZERO_ONLY'
            else:reason='PARTIAL_OR_UNKNOWN_REMAINS_UNKNOWN'
        for u in units:observed[u].append({'attempt_id':aid,'classification':outcome,'reason':reason,'review_ref':a['review_ref'],'terminal_ref':a['terminal_ref']})
    rows=[]
    for unit,ev in observed.items():
        classes=[x['classification'] for x in ev]
        # Any unresolved attempt blocks interpreting this unit as fully reconciled.
        if not ev or 'UNKNOWN' in classes:status='UNKNOWN'
        elif classes.count('SUCCESS_REVIEW_VERIFIED')>1:status='UNKNOWN' # duplicate-success conflict
        elif 'SUCCESS_REVIEW_VERIFIED' in classes:status='SUCCESS_REVIEW_VERIFIED'
        else:status='KNOWN_ZERO_EXECUTION'
        rows.append({'unit':unit,'status':status,'evidence':ev,'retry_allowed':False,'release_allowed':False})
    return {'schema':'READ_ONLY_UNIT_RECONCILIATION_CANDIDATE_V1','rows':rows,
            'counts':{k:sum(r['status']==k for r in rows) for k in ('SUCCESS_REVIEW_VERIFIED','KNOWN_ZERO_EXECUTION','UNKNOWN')},
            'execution_permitted':False,'retry_allowed':False,'release_allowed':False,
            'natural_verified':False,'production_bound':False}

def dispatch(run_id):
    # No implicit way to turn caller assertions into an original owner capability.
    raise ValueError('BLOCKED_VERIFIED_OWNER_SCOPE_BINDING_NOT_REGISTERED')
