# Derived from pinned original; only date plumbing and schema changed. No ranking/filter changes.
import csv
import hashlib
import io
import json
import math
import os
import re
import stat
from contextlib import contextmanager
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
FLAGS = dict(no_buy=True, production_allowed=False, source_admission=False, selection_admission=False, business_admission=False, full_universe_certified=False, historical_PIT=False, main_four_group_results_changed=False)

def need(ok, message):
    if not ok:
        raise ValueError(message)

def numeric(v):
    return type(v) in (int, float) and math.isfinite(v)

def same(a, b):
    return type(a) is type(b) and (a == b or (type(a) is float and math.isnan(a) and math.isnan(b)))

def rank_row(row, target_date):
    symbol = row.get('symbol')
    need(type(symbol) is str and re.fullmatch('\\d{6}\\.(SH|SZ|BJ)', symbol), 'SYMBOL')
    need(type(row.get('source_date')) is int and row['source_date'] == target_date, 'SOURCE_DATE')
    state = row.get('status')
    need(state in ('RAW_OHLCV_VALID_NOT_ADMITTED', 'EXPLICIT_ZERO_BAR_NO_VALID_OHLCV'), 'UNKNOWN_SOURCE_STATUS')
    base = dict(symbol=symbol, source_date=target_date, actual_date=target_date, rank=None, rank_eligibility='UNKNOWN', change_pct_decimal=None, change_pct_display=None, reason=None, **FLAGS)
    block = row['original_block']
    if state == 'EXPLICIT_ZERO_BAR_NO_VALID_OHLCV':
        base.update(actual_date=None, reason=state)
        return base
    bar = row['bar']
    need(all((same(bar[k], block[k]) for k in ('open', 'high', 'low', 'close', 'amount'))), 'RAW_BAR_JOIN')
    need(same(row['reference_previous'], block['previous']), 'RAW_PREVIOUS_JOIN')
    need(same(row['native_volume'], block['native_volume']), 'RAW_VOLUME_JOIN')
    need((bar.get('year'), bar.get('month'), bar.get('day')) == (target_date // 10000, target_date // 100 % 100, target_date % 100), 'BAR_DATE')
    fields = ('open', 'high', 'low', 'close', 'previous', 'native_volume')
    if not all((numeric(block[k]) and block[k] > 0 for k in fields)):
        base['reason'] = 'NONPOSITIVE_OR_NONFINITE_REQUIRED_RAW_VALUE'
        return base
    if not (block['high'] >= max((block[k] for k in ('open', 'low', 'close'))) and block['low'] <= min((block[k] for k in ('open', 'high', 'close')))):
        base['reason'] = 'INVALID_RAW_OHLC_ENVELOPE'
        return base
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        change = (Decimal(str(block['close'])) / Decimal(str(block['previous'])) - 1) * 100
        display = str(change.quantize(Decimal('.01')))
    off = block['md1_byte_offset']
    need(type(off) is int and off >= 0, 'OFFSET')
    base.update(rank_eligibility='RANKABLE_FIXED_REFERENCE_RESEARCH_ONLY', reason=None, raw_close=str(block['close']), reference_previous=str(block['previous']), open=str(block['open']), high=str(block['high']), low=str(block['low']), native_volume=str(block['native_volume']), amount_raw=str(block['amount']), change_pct_decimal=str(change), change_pct_display=display, volume_vendor_unit_certification='UNCONFIRMED', amount_display_currency_certified=False, lineage=dict(md1_member=block['md1_member'], cod_member=block['cod_member'], md1_byte_offset=off, reference_byte_offset=off + 4, close_byte_offset=off + 36, cod_record_index=block['cod_record_index'], seq=block['seq']))
    return base

def project_rows(rows, symbols, target_date):
    need(type(rows) is list and type(symbols) is list, 'ARRAY_SCOPE')
    need(len(symbols) == len(set(symbols)), 'DUPLICATE_SCOPE')
    by = {r['symbol']: r for r in rows}
    need(len(rows) == len(by) == len(symbols) and set(by) == set(symbols), 'EXACT_FULL_SCOPE')
    scope = [rank_row(by[s], target_date) for s in symbols]
    ranked = [r for r in scope if r['rank_eligibility'] != 'UNKNOWN']
    ranked.sort(key=lambda r: (Decimal(r['change_pct_decimal']).copy_negate(), r['symbol']))
    for i, r in enumerate(ranked, 1):
        r['rank'] = i
    return dict(schema='DATED_FIXED_REFERENCE_TOP200_V1', status='READY_PENDING_INDEPENDENT_REVIEW', source_date=target_date, scope_count=len(scope), valid_rank_count=len(ranked), unknown_count=len(scope) - len(ranked), top_count=min(200, len(ranked)), rows=ranked[:200], unknown=[r for r in scope if r['rank_eligibility'] == 'UNKNOWN'], scope_rows=scope, rank_rule='Decimal precision28 ROUND_HALF_EVEN; (G4 close/G4 previous-1)*100 descending, symbol ascending tie-break', scope_label='Existing fixed5575 mixed-source research identity reference; not certified exchange-wide ordinary-A universe', numerical_four_group_filter_applied=False, score_or_action_filter_applied=False, formula_calls=0, native_calls=0, parquet_reads=0, market_requests=0, **FLAGS)
