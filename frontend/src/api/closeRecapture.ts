/** M17 exact saved close-recapture readback. Never uses the historical 1530 route. */
export const CLOSE_RECAPTURE_ROUTE = '/api/v5/manager/close-recapture';
export const DEFAULT_CLOSE_RECAPTURE_QUERY = Object.freeze({
 source_trade_date: '20261012', run_id: 'ca2c344b61334ad28f4b6146117643cd',
});
const MAX_BYTES = 256 * 1024;
const FALSE_FLAGS = ['production_allowed', 'buy_gate_updated', 'orders_sent', 'natural_verified', 'formal_eligibility_verified'];
type JsonObject = Record<string, unknown>;
type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
export interface CloseRecaptureQuery {source_trade_date: string; run_id: string;}
export interface CloseRecaptureResult extends JsonObject {
 schema_version: 'v5.m17.readonly-response.v1'; status: 'READY' | 'PARTIAL';
 source_trade_date: string; plan_trade_date: string; run_id: string;
 execution_kind: 'SIMULATED' | 'OWNER_VERIFIED'; execution_label: 'MANUAL_RECOVERY';
 operation: 'EXISTING_VERIFIED_PRODUCT_REUSE'; captured_at: string; available_at: string;
 candidate_count: number; rows: JsonObject[]; cannot_confirm: string[];
 identity: JsonObject; files: JsonObject; pool: JsonObject; bar_window: JsonObject;
 coverage: JsonObject; source: JsonObject;
}
export interface CloseRecaptureState {
 phase: 'IDLE' | 'LOADING' | 'LOADED' | 'CANNOT_CONFIRM';
 result: CloseRecaptureResult | null; error: string;
}
function check(ok: unknown, reason: string): asserts ok {if (!ok) throw new Error('M17_' + reason);}
function object(value: unknown): value is JsonObject {return !!value && typeof value === 'object' && !Array.isArray(value);}
function strings(value: unknown): value is string[] {return Array.isArray(value) && value.every(x => typeof x === 'string');}
function digest(value: unknown) {return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);}
function date(value: unknown): value is string {
 if (typeof value !== 'string' || !/^\d{8}$/.test(value)) return false;
 const iso = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6)}`;
 const parsed = new Date(iso + 'T00:00:00Z');
 return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === iso;
}
function timestamp(value: unknown): value is string {
 return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)
  && date(value.slice(0, 10).replaceAll('-', '')) && Number(value.slice(11, 13)) < 24
  && Number(value.slice(14, 16)) < 60 && Number(value.slice(17, 19)) < 60 && Number.isFinite(Date.parse(value));
}
function relative(value: unknown) {
 return typeof value === 'string' && !!value && !/[\\:]/.test(value) && value.split('/').every(p => p && p !== '.' && p !== '..');
}
function validQuery(value: unknown): asserts value is CloseRecaptureQuery {
 check(object(value) && Object.keys(value).length === 2 && date(value.source_trade_date)
  && typeof value.run_id === 'string' && /^[0-9a-f]{32}$/.test(value.run_id), 'QUERY');
}
function numberOrNull(value: unknown) {return value === null || (typeof value === 'number' && Number.isFinite(value));}
function validate(value: unknown, expected: CloseRecaptureQuery): CloseRecaptureResult {
 check(object(value) && value.schema_version === 'v5.m17.readonly-response.v1', 'CONTRACT');
 check(value.source_trade_date === expected.source_trade_date && value.run_id === expected.run_id, 'EXACT_REFERENCE');
 check(value.RESEARCH_ONLY === true && FALSE_FLAGS.every(k => value[k] === false)
  && value.received_not_historical_1530 === true && value.execution_label === 'MANUAL_RECOVERY'
  && value.operation === 'EXISTING_VERIFIED_PRODUCT_REUSE'
  && ['SIMULATED', 'OWNER_VERIFIED'].includes(String(value.execution_kind)), 'RESEARCH_BOUNDARY');
 check(['READY', 'PARTIAL'].includes(String(value.status)) && date(value.plan_trade_date)
  && value.plan_trade_date > expected.source_trade_date, 'STATUS_DATES');
 check(timestamp(value.captured_at) && timestamp(value.available_at)
  && Date.parse(value.captured_at) <= Date.parse(value.available_at), 'TIMES');
 const identity = value.identity;
 check(object(identity) && Object.keys(identity).length === 7 && identity.lane === 'manager_close_recapture'
  && identity.target_date === expected.source_trade_date && timestamp(identity.research_cutoff)
  && ['input_sha256', 'code_sha256', 'config_sha256', 'dependency_sha256'].every(k => digest(identity[k])), 'IDENTITY');
 const gaps = value.cannot_confirm;
 check(strings(gaps) && ['MARKET_CLOSE_NOT_CAPTURED_STAGE_WINDOW_ENDS_15_55_05',
  'PYTDX_TURNOVER_CURRENCY_UNIT_UNVERIFIED'].every(gap => gaps.includes(gap)), 'GAPS');
 const files = value.files, prefix = `workbench_research/${expected.source_trade_date}/`;
 check(object(files) && Object.keys(files).length === 4, 'FILES');
 for (const [key, suffix] of Object.entries({artifact: 'close_recapture.json', receipt: 'close_recapture.receipt.json', snapshot: 'inputs/close_recapture_pytdx.json', candidate_overlay: 'close_recapture.candidates.json'})) {
  const file = files[key]; check(object(file) && file.artifact_ref === prefix + suffix && digest(file.sha256), 'FILE_REFERENCE');
 }
 const pool = value.pool, window = value.bar_window, coverage = value.coverage, source = value.source;
 check(object(pool) && pool.owner === 'v3_shared_data' && pool.role === 'HK_CONNECT_D1_TOP100_0_2'
  && pool.trade_date === expected.source_trade_date && pool.row_count === 100
  && typeof pool.run_id === 'string' && !!pool.run_id && date(pool.signal_date) && timestamp(pool.captured_at)
  && ['artifact', 'manifest', 'receipt'].every(k => digest(pool[k + '_sha256']) && relative(pool[k + '_ref'])), 'POOL');
 check(object(window) && window.stage_id === 'STAGE_1545_1555' && window.start_at === '15:46:00' && window.end_before === '15:55:05'
  && timestamp(window.observed_at_min) && timestamp(window.observed_at_max)
  && Date.parse(window.observed_at_min) <= Date.parse(window.observed_at_max)
  && Date.parse(window.observed_at_max) <= Date.parse(value.captured_at), 'BAR_WINDOW');
 check(object(source) && source.provider === 'pytdx_exhq' && source.source_id === 'pytdx' && object(source.source_identity), 'SOURCE');
 const sourceIdentity = source.source_identity;
 check(['provider', 'probe', 'contracts', 'aggregator'].every(k => {const ref = sourceIdentity[k]; return object(ref) && relative(ref.artifact_ref) && digest(ref.sha256);}), 'SOURCE_IDENTITY');
 check(Array.isArray(value.rows) && value.rows.length >= 1 && value.rows.length <= 100 && value.candidate_count === value.rows.length, 'ROW_COUNT');
 check(object(coverage) && coverage.eligible_count === 100 && coverage.observed_count === value.rows.length
  && ['requested_count', 'completed_count', 'no_data_count'].every(k => Number.isInteger(coverage[k]) && Number(coverage[k]) >= 0)
  && coverage.ratio === value.rows.length / 100 && strings(coverage.no_data_symbols), 'COVERAGE');
 const symbols = new Set<string>(); let previousRank = 0;
 for (const row of value.rows) {
  check(object(row) && typeof row.symbol === 'string' && /^HK\.\d{5}$/.test(row.symbol) && !symbols.has(row.symbol)
   && row.source_trade_date === expected.source_trade_date && row.candidate_status === 'OBSERVATION_ONLY'
   && row.turnover_currency === 'UNKNOWN' && row.turnover_unit === 'UNKNOWN'
   && typeof row.name === 'string' && Number.isInteger(row.pool_rank) && Number(row.pool_rank) > previousRank && Number(row.pool_rank) <= 100, 'ROW_IDENTITY');
  check(timestamp(row.observed_at) && timestamp(row.available_at) && Date.parse(row.observed_at) <= Date.parse(row.available_at)
   && Date.parse(row.available_at) <= Date.parse(value.available_at), 'ROW_TIMES');
  check(['pool_score', 'open_price', 'high_price', 'low_price', 'last_price', 'prev_close_price', 'volume', 'turnover'].every(k => numberOrNull(row[k]))
   && (row.bar_count === null || (Number.isInteger(row.bar_count) && Number(row.bar_count) >= 0))
   && ['window_start', 'window_end'].every(k => row[k] === null || typeof row[k] === 'string'), 'ROW_VALUES');
  check(FALSE_FLAGS.every(k => !(k in row) || row[k] === false) && (!('RESEARCH_ONLY' in row) || row.RESEARCH_ONLY === true), 'ROW_BOUNDARY');
  symbols.add(row.symbol); previousRank = Number(row.pool_rank);
 }
 return value as unknown as CloseRecaptureResult;
}
export async function readCloseRecapture(query: CloseRecaptureQuery, fetcher: Fetcher = fetch, signal?: AbortSignal): Promise<CloseRecaptureResult> {
 validQuery(query); const expected = {...query};
 const url = CLOSE_RECAPTURE_ROUTE + '?' + new URLSearchParams({...expected});
 const response = await fetcher(url, {method: 'GET', cache: 'no-store', credentials: 'omit', signal});
 check(response.ok, 'HTTP_' + response.status);
 const length = response.headers.get('content-length');
 check(!length || (/^\d+$/.test(length) && Number(length) <= MAX_BYTES), 'RESPONSE_LIMIT');
 check(response.body, 'EMPTY_RESPONSE');
 const reader = response.body.getReader(), parts: Uint8Array[] = []; let size = 0;
 try {
  while (true) {const part = await reader.read(); if (part.done) break; size += part.value.length;
   if (size > MAX_BYTES) {await reader.cancel(); throw new Error('M17_RESPONSE_LIMIT');} parts.push(part.value);
  }
 } finally {reader.releaseLock();}
 const bytes = new Uint8Array(size); let offset = 0;
 for (const part of parts) {bytes.set(part, offset); offset += part.length;}
 let value: unknown;
 try {value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));} catch {throw new Error('M17_RESPONSE_JSON');}
 return validate(value, expected);
}
export class CloseRecaptureSession {
 private revision = 0; private controller: AbortController | null = null; private closed = false;
 private emit: (state: CloseRecaptureState) => void; private fetcher: Fetcher;
 constructor(emit: (state: CloseRecaptureState) => void, fetcher: Fetcher = fetch) {this.emit = emit; this.fetcher = fetcher;}
 async load(query: CloseRecaptureQuery) {
  if (this.closed) return;
  const revision = ++this.revision; this.controller?.abort(); this.controller = new AbortController();
  this.emit({phase: 'LOADING', result: null, error: ''});
  try {
   const result = await readCloseRecapture(query, this.fetcher, this.controller.signal);
   if (!this.closed && revision === this.revision) this.emit({phase: 'LOADED', result, error: ''});
  } catch (error) {
   if (!this.closed && revision === this.revision) this.emit({phase: 'CANNOT_CONFIRM', result: null, error: error instanceof Error ? error.message : 'M17_READ_FAILED'});
  }
 }
 close() {this.closed = true; this.revision++; this.controller?.abort();}
}
