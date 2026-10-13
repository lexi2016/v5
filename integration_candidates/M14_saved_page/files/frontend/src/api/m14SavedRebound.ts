/** Independent M14 owner saved research. GET only; never starts computation or a manager run. */
export const M14_SAVED_REBOUND_ROUTE = '/api/v5/source-bundle/rebound-saved';
export const M14_REBOUND_GROUPS = ['strict', 'near', 'pending', 'excluded', 'screen_unresolved'] as const;
export type M14ReboundGroup = typeof M14_REBOUND_GROUPS[number];
type JsonObject = Record<string, unknown>;
type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
const REFERENCE_KEYS = ['run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256'] as const;
export type M14SavedReference = Record<typeof REFERENCE_KEYS[number], string>;
interface ResearchBoundary {
 research_only: true; production_allowed: false; buy_gate_updated: false; orders_sent: false;
 natural_verified: false; formal_eligibility_verified: false;
}
interface M14Envelope extends ResearchBoundary {schema_version: 'v5.m14.saved_rebound.v1'; source_kind: 'M14_OWNER';}
export interface M14SavedWaiting extends M14Envelope {status: 'WAITING'; reason_codes: string[];}
export interface M14SavedEntry {index: number; kind: string; bytes: number; sha256: string; projection_sha256?: string; value_state: 'LOADED' | 'NOT_LOADED'; value?: unknown; reason?: 'ITEM_BYTES_LIMIT';}
export interface M14SavedRebound extends M14Envelope {
 status: 'SAVED_RESEARCH'; reference: M14SavedReference; target_date: string; signal_date: string;
 data_kind: 'SYNTHETIC' | 'RECORDED_INPUT_REPLAY'; execution_kind: string; projection: 'rebound_references'; group: M14ReboundGroup;
 rebound: {source_section_sha256: string; group_counts: Record<M14ReboundGroup, number>; source: JsonObject; observation: JsonObject};
 cursor: string | null; offset: number; limit: 32; matched_total: number; loaded_count: number;
 not_loaded_count: number; remaining_entries: number; entries: M14SavedEntry[]; next_cursor: string | null;
}
export type M14SavedResult = M14SavedWaiting | M14SavedRebound;
export interface M14SavedQuery {group?: M14ReboundGroup; cursor?: string | null; reference?: M14SavedReference;}
export interface M14SavedState {phase: 'IDLE' | 'LOADING' | 'WAITING' | 'LOADED' | 'CANNOT_CONFIRM'; result: M14SavedResult | null; error: string; group: M14ReboundGroup; canPrevious: boolean;}
const MAX_RESPONSE = 256 * 1024, MAX_ITEM = 16 * 1024, MAX_VALUES = 128 * 1024;
const FALSE_FLAGS = ['production_allowed', 'buy_gate_updated', 'orders_sent', 'natural_verified', 'formal_eligibility_verified'];
const COVERAGE_FIELDS = ['input_candidate_count', 'history_complete_count', 'history_pending_count', 'strict_count', 'near_candidate_count', 'near_count', 'selected_count', 'panel_row_count', 'panel_code_count', 'excluded_count', 'screen_unresolved_count', 'row_accounted_count'];
function check(ok: unknown, code: string): asserts ok {if (!ok) throw new Error('M14_' + code);}
function object(value: unknown): value is JsonObject {return value !== null && typeof value === 'object' && !Array.isArray(value);}
function integer(value: unknown): value is number {return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;}
function digest(value: unknown): value is string {return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);}
function text(value: unknown): value is string {return typeof value === 'string' && value.trim().length > 0 && value.length <= 2048;}
function strings(value: unknown): value is string[] {return Array.isArray(value) && value.length <= 10000 && value.every(text);}
function date(value: unknown): value is string {
 if (typeof value !== 'string' || !/^\d{8}$/.test(value)) return false;
 const iso = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6)}`;
 const parsed = new Date(iso + 'T00:00:00Z');
 return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === iso;
}
function reference(value: unknown): value is M14SavedReference {
 return object(value) && Object.keys(value).length === 4 && typeof value.run_id === 'string' && /^[a-f0-9]{32}$/.test(value.run_id) && REFERENCE_KEYS.slice(1).every(key => digest(value[key]));
}
function sameReference(a: M14SavedReference, b: M14SavedReference): boolean {return REFERENCE_KEYS.every(key => a[key] === b[key]);}
function cursor(value: unknown): value is string {return typeof value === 'string' && value.length <= 4096 && /^[A-Za-z0-9_-]+={0,2}$/.test(value);}
function boundary(value: unknown): asserts value is JsonObject {check(object(value) && value.research_only === true && FALSE_FLAGS.every(key => value[key] === false), 'RESEARCH_BOUNDARY');}
function nestedBoundary(value: unknown, depth = 0): void {
 check(depth <= 32, 'RESPONSE_DEPTH');
 if (Array.isArray(value)) {for (const item of value) nestedBoundary(item, depth + 1); return;}
 if (!object(value)) return;
 for (const [key, item] of Object.entries(value)) {
  check(!/(^path$|_path$|^root$|_root$|^__proto__$|^constructor$|^prototype$)/i.test(key), 'UNSAFE_FIELD');
  if (FALSE_FLAGS.includes(key)) check(item === false, 'NESTED_BOUNDARY');
  if (key === 'research_only') check(item === true, 'NESTED_BOUNDARY');
  nestedBoundary(item, depth + 1);
 }
}
function validate(value: unknown, query: M14SavedQuery): M14SavedResult {
 boundary(value);
 check(value.schema_version === 'v5.m14.saved_rebound.v1' && value.source_kind === 'M14_OWNER', 'CONTRACT');
 nestedBoundary(value);
 if (value.status === 'WAITING') {
  check(!query.reference && value.reason_codes instanceof Array && value.reason_codes.length === 1 && value.reason_codes[0] === 'M14_SAVED_REFERENCE_NOT_CONFIGURED', 'WAITING');
  const allowed = ['schema_version', 'status', 'source_kind', 'reason_codes', 'research_only', ...FALSE_FLAGS];
  check(Object.keys(value).every(key => allowed.includes(key)), 'WAITING_CONTENT');
  return value as unknown as M14SavedWaiting;
 }
 check(value.status === 'SAVED_RESEARCH' && ['SYNTHETIC', 'RECORDED_INPUT_REPLAY'].includes(String(value.data_kind)) && typeof value.data_kind === 'string' && text(value.execution_kind), 'CLASSIFICATION');
 check(reference(value.reference) && (!query.reference || sameReference(value.reference, query.reference)), 'REFERENCE');
 check(date(value.target_date) && date(value.signal_date) && value.signal_date < value.target_date, 'DATE');
 const group = query.group ?? 'pending', meta = value.rebound;
 check(value.projection === 'rebound_references' && value.group === group && object(meta) && digest(meta.source_section_sha256) && object(meta.group_counts), 'PROJECTION');
 check(Object.keys(meta.group_counts).length === 5 && M14_REBOUND_GROUPS.every(key => integer((meta.group_counts as JsonObject)[key]) && Number((meta.group_counts as JsonObject)[key]) <= 10000), 'GROUP_COUNTS');
 const source = meta.source, observation = meta.observation;
 boundary(source); boundary(observation);
 check(source.status === 'CANNOT_CONFIRM' && source.eligible_screen === null && source.source_run_id === value.reference.run_id && reference(source.binding_reference) && sameReference(source.binding_reference, value.reference) && source.scope === 'INDEPENDENT_SAVED_M14_OWNER_RESEARCH' && strings(source.reason_codes), 'SOURCE');
 check(observation.status === 'CANNOT_CONFIRM' && typeof observation.original_computation_status === 'string' && ['READY', 'READY_WITH_GAPS', 'CANNOT_CONFIRM'].includes(observation.original_computation_status) && observation.main_screen_ready === false && strings(observation.gaps), 'OBSERVATION');
 check((!Object.hasOwn(observation, 'target_trade_date') || ((typeof observation.target_trade_date === 'string' || typeof observation.target_trade_date === 'number') && String(observation.target_trade_date) === value.target_date)) && (!Object.hasOwn(observation, 'observed_session') || ((typeof observation.observed_session === 'string' || typeof observation.observed_session === 'number') && String(observation.observed_session) === value.signal_date)), 'OBSERVATION_DATE');
 check(object(observation.coverage) && Object.entries(observation.coverage).every(([key, count]) => COVERAGE_FIELDS.includes(key) && integer(count)) && object(observation.native_evidence), 'COVERAGE');
 const total = meta.group_counts[group];
 check(integer(value.offset) && integer(total) && value.matched_total === total && value.limit === 32 && value.cursor === (query.cursor ?? null) && (value.cursor === null ? value.offset === 0 : value.offset > 0), 'PAGE');
 check(Array.isArray(value.entries) && value.entries.length <= Math.min(32, total - value.offset) && (total === 0 ? value.offset === 0 && value.entries.length === 0 : value.offset < total && value.entries.length > 0), 'PAGE');
 let loaded = 0, loadedBytes = 0;
 for (const [position, entry] of value.entries.entries()) {
  check(object(entry) && entry.index === value.offset + position && !Object.hasOwn(entry, 'offset') && typeof entry.kind === 'string' && ['object', 'scalar'].includes(entry.kind) && integer(entry.bytes) && entry.bytes > 0 && digest(entry.sha256), 'ENTRY');
  if (entry.value_state === 'LOADED') {
   check(Object.hasOwn(entry, 'value') && digest(entry.projection_sha256) && !Object.hasOwn(entry, 'reason'), 'ENTRY');
   const kind = object(entry.value) ? 'object' : 'scalar';
   check(kind === entry.kind, 'ENTRY_KIND');
   const bytes = new TextEncoder().encode(JSON.stringify(entry.value)).length;
   check(bytes <= MAX_ITEM && entry.bytes <= MAX_ITEM, 'ENTRY_LIMIT');
   loaded++; loadedBytes += Math.max(bytes, entry.bytes); check(loadedBytes <= MAX_VALUES, 'VALUES_LIMIT');
  } else check(entry.value_state === 'NOT_LOADED' && !Object.hasOwn(entry, 'value') && !Object.hasOwn(entry, 'projection_sha256') && entry.reason === 'ITEM_BYTES_LIMIT' && entry.bytes > MAX_ITEM, 'ENTRY');
 }
 check(value.loaded_count === loaded && value.not_loaded_count === total - loaded && value.remaining_entries === total - value.offset - value.entries.length && (value.next_cursor === null || cursor(value.next_cursor)) && (Number(value.remaining_entries) > 0) === (value.next_cursor !== null) && (value.next_cursor === null || value.next_cursor !== value.cursor), 'PAGE_COUNTS');
 return value as unknown as M14SavedRebound;
}
export async function readSavedRebound(query: M14SavedQuery = {}, fetcher: Fetcher = fetch, signal?: AbortSignal): Promise<M14SavedResult> {
 check(query !== null && typeof query === 'object' && !Array.isArray(query) && Object.keys(query).every(key => ['group', 'cursor', 'reference'].includes(key)), 'QUERY');
 const group = query.group ?? 'pending';
 check(M14_REBOUND_GROUPS.includes(group), 'QUERY');
 check(query.reference === undefined || reference(query.reference), 'QUERY_REFERENCE');
 check(query.cursor === undefined || query.cursor === null || (cursor(query.cursor) && query.reference !== undefined), 'QUERY_CURSOR');
 // Copy before awaiting: a caller cannot change the expected identity mid-request.
 const expected: M14SavedQuery = {group, cursor: query.cursor ?? null, ...(query.reference ? {reference: {...query.reference}} : {})};
 const params = new URLSearchParams({group: expected.group!});
 if (expected.cursor) params.set('cursor', expected.cursor);
 if (expected.reference) for (const key of REFERENCE_KEYS) params.set(key, expected.reference[key]);
 const response = await fetcher(M14_SAVED_REBOUND_ROUTE + '?' + params.toString(), {method: 'GET', cache: 'no-store', credentials: 'omit', redirect: 'error', signal});
 check(response.ok, 'HTTP_' + response.status);
 const advertised = response.headers.get('content-length');
 check(!advertised || (/^\d+$/.test(advertised) && Number(advertised) <= MAX_RESPONSE), 'RESPONSE_LIMIT');
 check(response.body, 'EMPTY_RESPONSE');
 const reader = response.body.getReader(), parts: Uint8Array[] = [];
 let size = 0;
 try {while (true) {const part = await reader.read(); if (part.done) break; size += part.value.length; if (size > MAX_RESPONSE) {await reader.cancel(); throw new Error('M14_RESPONSE_LIMIT');} parts.push(part.value);}}
 finally {reader.releaseLock();}
 const bytes = new Uint8Array(size); let offset = 0;
 for (const part of parts) {bytes.set(part, offset); offset += part.length;}
 let value: unknown;
 try {value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));} catch {throw new Error('M14_RESPONSE_JSON');}
 return validate(value, expected);
}
/** One pinned M14 owner per browsing session; reload explicitly re-reads the configured binding. */
export class SavedReboundSession {
 private revision = 0; private closed = false; private controller: AbortController | null = null;
 private pinned: M14SavedReference | null = null;
 private history: {cursor: string | null; offset: number}[] = [{cursor: null, offset: 0}]; private position = 0;
 private state: M14SavedState = {phase: 'IDLE', result: null, error: '', group: 'pending', canPrevious: false};
 private emit: (state: M14SavedState) => void; private fetcher: Fetcher;
 constructor(emit: (state: M14SavedState) => void, fetcher: Fetcher = fetch) {this.emit = emit; this.fetcher = fetcher;}
 private publish(state: M14SavedState) {this.state = state; this.emit(state);}
 private async page(group: M14ReboundGroup, position: number) {
  if (this.closed) return;
  const request = this.history[position]; if (!request) return;
  const revision = ++this.revision; this.controller?.abort(); this.controller = new AbortController();
  const query = {group, cursor: request.cursor, ...(this.pinned ? {reference: {...this.pinned}} : {})};
  this.publish({phase: 'LOADING', result: null, error: '', group, canPrevious: false});
  try {
   const result = await readSavedRebound(query, this.fetcher, this.controller.signal);
   if (this.closed || revision !== this.revision) return;
   if (result.status === 'SAVED_RESEARCH') {
    check(result.offset === request.offset, 'PAGE_OFFSET');
    this.pinned = {...result.reference};
   }
   this.position = position;
   this.publish({phase: result.status === 'WAITING' ? 'WAITING' : 'LOADED', result, error: '', group, canPrevious: position > 0});
  } catch (error) {
   if (!this.closed && revision === this.revision) this.publish({phase: 'CANNOT_CONFIRM', result: null, error: error instanceof Error && /^M14_[A-Z0-9_]+$/.test(error.message) ? error.message : 'M14_READ_FAILED', group, canPrevious: false});
  }
 }
 async load(group: M14ReboundGroup = 'pending') {if (this.closed) return; this.pinned = null; this.history = [{cursor: null, offset: 0}]; this.position = 0; await this.page(group, 0);}
 async select(group: M14ReboundGroup) {if (this.closed) return; this.history = [{cursor: null, offset: 0}]; this.position = 0; await this.page(group, 0);}
 async next() {
  const result = this.state.result;
  if (this.closed || this.state.phase !== 'LOADED' || result?.status !== 'SAVED_RESEARCH' || !result.next_cursor) return;
  this.history = this.history.slice(0, this.position + 1); this.history.push({cursor: result.next_cursor, offset: result.offset + result.entries.length});
  await this.page(this.state.group, this.position + 1);
 }
 async previous() {if (this.closed || this.state.phase !== 'LOADED' || this.position < 1) return; await this.page(this.state.group, this.position - 1);}
 close() {this.closed = true; this.revision++; this.controller?.abort();}
}
