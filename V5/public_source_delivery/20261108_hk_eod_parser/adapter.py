"""Offline Eastmoney daily parser. Never exports original READY snapshot schema.
No network, scheduling, store, lock mutation or production activation path.
"""
import datetime as dt
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, parse_qs


def number(text, positive=False):
    try:
        n = Decimal(text)
        if not n.is_finite() or n < 0 or (positive and n == 0):
            raise ValueError('INVALID_NUMBER')
        return str(n)
    except (InvalidOperation, TypeError):
        raise ValueError('INVALID_NUMBER')


def adapt(raw_by_code, scope, trade_date, requested_codes, request_receipts):
    """raw_by_code contains bytes from saved responses; scope is official union.
    Only explicit requested subset may be emitted. No auto scope expansion.
    Documentation units are not independently certified units.
    """
    day = dt.date.fromisoformat(trade_date)
    if day.isoformat() != trade_date:
        raise ValueError('INVALID_DATE')
    requested = list(requested_codes)
    if not requested or len(requested) != len(set(requested)):
        raise ValueError('INVALID_REQUESTED_SCOPE')
    if scope.get('source_date') != trade_date or scope.get('complete_structural_check') is not True:
        raise ValueError('SCOPE_DATE_OR_COMPLETENESS_UNKNOWN')
    entries = scope.get('rows', [])
    if not isinstance(entries, list) or not entries:
        raise ValueError('EMPTY_SCOPE')
    mapping = {}
    for r in entries:
        c = r.get('code')
        if not isinstance(c, str) or not re.fullmatch(r'\d{5}', c) or c in mapping:
            raise ValueError('INVALID_SCOPE_IDENTITY')
        mapping[c] = r
    if any(c not in mapping for c in requested) or set(raw_by_code) - set(requested):
        raise ValueError('SCOPE_EXPANSION_REJECTED')
    rows, failures, hashes = [], [], {}
    for c in requested:
        raw = raw_by_code.get(c)
        if raw is None:
            failures.append({'code':c,'status':'UNKNOWN','reason':'RESPONSE_MISSING'})
            continue
        try:
            if not isinstance(raw, bytes):
                raise ValueError('RAW_BYTES_REQUIRED')
            hashes[c] = hashlib.sha256(raw).hexdigest()
            receipt = request_receipts.get(c, {})
            url = urlsplit(receipt.get('url', ''))
            query = parse_qs(url.query)
            expected = {'secid':['116.'+c], 'klt':['101'], 'fqt':['0'], 'fields2':['f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61']}
            if url.scheme != 'https' or url.hostname != 'push2his.eastmoney.com' or url.path != '/api/qt/stock/kline/get' or any(query.get(k)!=v for k,v in expected.items()) or receipt.get('sha256') != hashes[c] or receipt.get('status') != 200:
                raise ValueError('SOURCE_REQUEST_PROVENANCE_MISMATCH')
            if not query.get('beg') or not query.get('end') or not query['beg'][0] <= day.strftime('%Y%m%d') <= query['end'][0]:
                raise ValueError('SOURCE_REQUEST_DATE_RANGE_MISMATCH')
            j = json.loads(raw)
            d = j.get('data')
            if type(j.get('rc')) is not int or j['rc'] != 0 or not isinstance(d,dict):
                raise ValueError('VENDOR_FAILURE')
            if d.get('code') != c or d.get('market') != 116:
                raise ValueError('VENDOR_IDENTITY_MISMATCH')
            bars = d.get('klines')
            if not isinstance(bars,list):
                raise ValueError('BARS_MISSING')
            chosen = [b.split(',') for b in bars if isinstance(b,str) and b.split(',')[0] == trade_date]
            if len(chosen) != 1:
                raise ValueError('TARGET_DATE_MISSING_OR_DUPLICATE')
            v = chosen[0]
            if len(v) != 11:
                raise ValueError('BAR_SCHEMA_MISMATCH')
            values = dict(zip(['open','close','high','low','volume','amount'], [number(x, i<4) for i,x in enumerate(v[1:7])]))
            if Decimal(values['volume']) != Decimal(values['volume']).to_integral_value():
                raise ValueError('NONINTEGER_VOLUME')
            o,cl,hi,lo=[Decimal(values[k]) for k in ['open','close','high','low']]
            if not lo <= min(o,cl) <= max(o,cl) <= hi:
                raise ValueError('OHLC_ORDER_INVALID')
            rows.append({'code':'HK.'+c,'trade_date':trade_date,'security_type':mapping[c].get('security_type','UNKNOWN'), 'type_source':mapping[c].get('type_source','UNKNOWN'),'vendor_name':d.get('name'),**values,'pre_close':None,'pre_close_status':'UNKNOWN_NOT_INFERRED_FROM_PREKPRICE','adjustment':'UNADJUSTED_REQUEST_CONTRACT_NOT_RESPONSE_ATTESTED','units':{'price':'HKD_DOCUMENTED','volume':'SHARES_DOCUMENTED','amount':'HKD_DOCUMENTED'},'unit_equivalence':'UNKNOWN','source':'EASTMONEY_SAVED_DAILY_RESPONSE','source_sha256':hashes[c]})
        except (ValueError,TypeError,KeyError,AttributeError) as e:
            failures.append({'code':c,'status':'UNKNOWN','reason':str(e)})
    return {'schema_version':'candidate.hk_eod_research.v1','status':'PARTIAL_UNKNOWN' if failures else 'PARSED_NOT_ADMITTED','trade_date':trade_date,'rows':rows,'failures':failures,'requested_count':len(requested),'parsed_count':len(rows),'official_scope_count':len(mapping),'source_hashes':hashes,'production_allowed':False,'buy_gate_updated':False,'orders_sent':False,'natural_verified':False,'original_contract_export_allowed':False,'gates':{'original_minimum_rows':600,'original_full_coverage_required':1.0,'resource_gate':'UNKNOWN_NOT_EXECUTED','lock_gate':'NOT_ACQUIRED_OFFLINE','futu_scope_equivalence':'UNKNOWN','futu_price_unit_equivalence':'UNKNOWN','cas_event':'UNKNOWN','independent_review':'PENDING'}}
