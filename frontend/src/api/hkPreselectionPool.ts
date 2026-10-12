/** Read one configured M06 committed pool. Never selects a date, generates or publishes. */
export const HK_PRESELECTION_ROUTE = '/api/v5/source-bundle/hk-preselection';
const MAX_BYTES = 16 * 1024 * 1024;
const TRADING_FLAGS = ['production_allowed', 'buy_gate_updated', 'orders_sent'];
const RESEARCH_FLAGS = [...TRADING_FLAGS, 'natural_verified', 'formal_eligibility_verified'];
const POOL_ID = 'hkconnect_d1_top100';
type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
type JsonObject = Record<string, unknown>;

export interface HkPreselectionRow extends JsonObject {
 symbol: string;
 pool_rank: number;
}
export interface HkPreselectionArtifact extends JsonObject {
 rows: HkPreselectionRow[];
 source_run_id: string;
 source_sha256: string;
 source_manifest_sha256: string;
 source_receipt_sha256: string;
 status: string;
}
export interface HkCommittedReference extends JsonObject {
 target_date: string;
 signal_date: string;
 eligibility_source_date: string;
 research_cutoff: string;
 execution_mode: string;
 computation_sha256: string;
 artifact_sha256: string;
 artifact_relative: string;
}
export interface HkPreselectionResult {
 artifact: HkPreselectionArtifact;
 committed_reference: HkCommittedReference;
 model_weights_reverified: false;
 fixture_only: boolean;
}
export interface HkNotConfigured {
 status: 'NOT_CONFIGURED';
 module_id: 'M06_HK_PRESELECTION';
 reason_codes: ['M06_REFERENCE_NOT_CONFIGURED'];
}
export interface HkPreselectionState {
 phase: 'IDLE' | 'LOADING' | 'LOADED' | 'NOT_CONFIGURED' | 'CANNOT_CONFIRM';
 result: HkPreselectionResult | null;
 error: string;
}
function check(ok: unknown, reason: string): asserts ok {
 if (!ok) throw new Error('M06_' + reason);
}
function object(value: unknown): value is JsonObject {
 return !!value && typeof value === 'object' && !Array.isArray(value);
}
function digest(value: unknown): value is string {
 return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
}
function date(value: unknown): value is string {
 if (typeof value !== 'string' || !/^\d{8}$/.test(value)) return false;
 const iso = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
 const parsed = new Date(iso + 'T00:00:00Z');
 return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === iso;
}
function relative(value: unknown): value is string {
 return typeof value === 'string' && !!value && !value.includes('\\') && !value.includes(':')
  && value.split('/').every(part => part !== '' && part !== '.' && part !== '..');
}
function boundary(value: JsonObject, research = false) {
 check((research ? RESEARCH_FLAGS : TRADING_FLAGS).every(key => value[key] === false), 'RESEARCH_BOUNDARY');
 check(!research || (value.research_only === true && value.model_weights_reverified === false), 'RESEARCH_BOUNDARY');
 // Original artifact/row extensions must not silently promote the research claim.
 for (const key of ['natural_verified', 'formal_eligibility_verified', 'model_weights_reverified']) {
  check(!(key in value) || value[key] === false, 'RESEARCH_BOUNDARY');
 }
 check(!('research_only' in value) || value.research_only === true, 'RESEARCH_BOUNDARY');
}
function validate(value: unknown): HkPreselectionResult | HkNotConfigured {
 check(object(value), 'CONTRACT');
 boundary(value, true);
 if (value.status === 'NOT_CONFIGURED') {
  check(value.module_id === 'M06_HK_PRESELECTION' && Array.isArray(value.reason_codes)
   && value.reason_codes.length === 1 && value.reason_codes[0] === 'M06_REFERENCE_NOT_CONFIGURED'
   && !('artifact' in value) && !('committed_reference' in value), 'NOT_CONFIGURED_CONTRACT');
  return value as unknown as HkNotConfigured;
 }
 const artifact = value.artifact, reference = value.committed_reference;
 check(object(artifact) && object(reference), 'CONTRACT');
 boundary(reference, true);
 boundary(artifact);
 check(reference.schema_version === 'v5.hk_preselection_committed_reference.v1'
  && reference.owner === 'M06' && reference.market === 'HK' && reference.status === 'COMMITTED'
  && reference.business_status === 'STRICT_0_2_READY' && reference.data_kind === 'VERIFIED_SOURCE_SNAPSHOT', 'REFERENCE_IDENTITY');
 check(typeof value.fixture_only === 'boolean' && reference.fixture_only === value.fixture_only, 'FIXTURE_IDENTITY');
 check(date(reference.target_date) && date(reference.signal_date) && date(reference.eligibility_source_date)
  && reference.signal_date < reference.target_date && reference.eligibility_source_date <= reference.target_date, 'DATES');
 check(typeof reference.research_cutoff === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(reference.research_cutoff)
  && Number.isFinite(Date.parse(reference.research_cutoff)), 'CUTOFF');
 check(['NATURAL', 'MANUAL_RECOVERY', 'RECORDED_INPUT_REPLAY'].includes(String(reference.execution_mode)), 'EXECUTION_MODE');
 check(['computation_sha256', 'request_sha256', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256'].every(key => digest(reference[key])), 'REFERENCE_DIGEST');
 const prefix = `hk_preselection/${reference.target_date}/objects/${reference.computation_sha256}`;
 for (const name of ['artifact', 'manifest', 'receipt']) {
  check(reference[name + '_relative'] === `${prefix}/${name}.json`, 'REFERENCE_PATH');
 }
 for (const name of ['producer', 'reader']) {
  const entry = reference[name + '_reference'];
  check(object(entry) && digest(entry.sha256)
   && entry.relative === `${prefix}/${name === 'reader' ? 'strict_reader' : 'producer'}_receipt.json`, 'REFERENCE_IDENTITY');
 }
 const computation = reference.computation_identity;
 check(object(computation) && computation.lane === 'hk_preselection' && computation.target_date === reference.target_date
  && computation.research_cutoff === reference.research_cutoff
  && ['input_sha256', 'code_sha256', 'config_sha256', 'dependency_sha256'].every(key => digest(computation[key])), 'COMPUTATION_IDENTITY');
 check(artifact.schema_version === 'v3_5.preselection_pool.v1' && artifact.market === 'HK'
  && artifact.pool_id === POOL_ID && artifact.status === 'STRICT_0_2_READY'
  && artifact.producer_id === 'v3_shared_hk_0_2_consumer_v1' && artifact.source_role === 'SHARED_VERIFIED_HK_0_2'
  && artifact.trade_date === reference.target_date && artifact.target_date === reference.target_date
  && artifact.signal_date === reference.signal_date && artifact.source_row_count === 100, 'ARTIFACT_IDENTITY');
 const source = reference.verified_source_reference;
 check(object(source) && source.role === 'HK_CONNECT_D1_TOP100_0_2'
  && typeof source.run_id === 'string' && source.run_id.length > 0 && relative(source.artifact_relative)
  && ['artifact_sha256', 'manifest_sha256', 'receipt_sha256'].every(key => digest(source[key])), 'SOURCE_IDENTITY');
 const projections: Record<string, string> = { run_id: 'source_run_id', artifact_sha256: 'source_sha256', manifest_sha256: 'source_manifest_sha256', receipt_sha256: 'source_receipt_sha256', artifact_relative: 'source_path' };
 check(Object.entries(projections).every(([input, output]) => source[input] === artifact[output]), 'SOURCE_IDENTITY');
 check(Array.isArray(artifact.rows) && artifact.rows.length === 100, 'ROW_COUNT');
 const symbols = new Set<string>();
 artifact.rows.forEach((row: unknown, index: number) => {
  check(object(row), 'ROW_CONTRACT');
  boundary(row);
  check(typeof row.symbol === 'string' && /^HK\.\d{5}$/.test(row.symbol) && !symbols.has(row.symbol)
   && row.market === 'HK' && row.pool_id === POOL_ID && row.pool_rank === index + 1
   && (!('rank' in row) || Number(row.rank) === index + 1), 'ROW_IDENTITY');
  const code = String(row.code_norm || row.code || '').trim().toUpperCase().replace(/^HK\./, '');
  check(row.symbol === 'HK.' + code && row.target_date === reference.target_date
   && row.trade_date === reference.target_date && row.signal_date === reference.signal_date
   && row.selected_strategy === 'prob_active' && row.d1_freshness_status === 'PASS'
   && row.recommendation_status === 'WATCH_ONLY', 'ROW_CONTRACT');
  check((typeof row.score_prob_active === 'string' && row.score_prob_active.trim() !== ''
   || typeof row.score_prob_active === 'number') && Number.isFinite(Number(row.score_prob_active))
   && typeof row.pool_score === 'number' && row.pool_score >= 0 && row.pool_score <= 1
   && Number(row.score_prob_active) === row.pool_score, 'ROW_SCORE');
  symbols.add(row.symbol);
 });
 // Return the original object and row order. SHA verification belongs to the cold reader.
 return value as unknown as HkPreselectionResult;
}
export async function readHkPreselectionPool(fetcher: Fetcher = fetch, signal?: AbortSignal): Promise<HkPreselectionResult | HkNotConfigured> {
 const response = await fetcher(HK_PRESELECTION_ROUTE, { method: 'GET', cache: 'no-store', credentials: 'omit', signal });
 check(response.ok, 'HTTP_' + response.status);
 const advertised = response.headers.get('content-length');
 check(!advertised || (/^\d+$/.test(advertised) && Number(advertised) <= MAX_BYTES), 'RESPONSE_LIMIT');
 check(response.body, 'EMPTY_RESPONSE');
 const reader = response.body.getReader(), parts: Uint8Array[] = [];
 let size = 0;
 try {
  while (true) {
   const item = await reader.read();
   if (item.done) break;
   size += item.value.length;
   if (size > MAX_BYTES) { await reader.cancel(); throw new Error('M06_RESPONSE_LIMIT'); }
   parts.push(item.value);
  }
 } finally { reader.releaseLock(); }
 const bytes = new Uint8Array(size);
 let offset = 0;
 for (const part of parts) { bytes.set(part, offset); offset += part.length; }
 let value: unknown;
 try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
 catch { throw new Error('M06_RESPONSE_JSON'); }
 return validate(value);
}
export class HkPreselectionSession {
 private revision = 0;
 private controller: AbortController | null = null;
 private closed = false;
 private emit: (state: HkPreselectionState) => void;
 private fetcher: Fetcher;
 constructor(emit: (state: HkPreselectionState) => void, fetcher: Fetcher = fetch) { this.emit = emit; this.fetcher = fetcher; }
 async load() {
  if (this.closed) return;
  const revision = ++this.revision;
  this.controller?.abort();
  this.controller = new AbortController();
  this.emit({ phase: 'LOADING', result: null, error: '' });
  try {
   const result = await readHkPreselectionPool(this.fetcher, this.controller.signal);
   if (revision !== this.revision || this.closed) return;
   if ('status' in result) this.emit({ phase: 'NOT_CONFIGURED', result: null, error: result.reason_codes.join(' · ') });
   else this.emit({ phase: 'LOADED', result, error: '' });
  } catch (error) {
   if (revision === this.revision && !this.closed) this.emit({ phase: 'CANNOT_CONFIRM', result: null, error: error instanceof Error ? error.message : 'M06_READ_FAILED' });
  }
 }
 close() { this.closed = true; this.revision++; this.controller?.abort(); }
}
