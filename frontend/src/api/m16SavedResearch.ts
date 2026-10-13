/** Saved M16 public research only. Never starts a provider, job or ensure operation. */
export const M16_ROUTE = '/api/v5/source-bundle/manager-public-research';
const MAX_BYTES = 4 * 1024 * 1024;
type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
type JsonObject = Record<string, unknown>;
interface PublicResearchBoundary {
  schema_version: 'v5.m16_saved_public_research.v1';
  module_id: 'M16_PUBLIC_RESEARCH';
  mode: 'READ_ONLY_SAVED_RESULT';
  read_only: true;
  can_execute: false;
  research_only: true;
  natural_verified: false;
  production_allowed: false;
  buy_gate_updated: false;
  orders_sent: false;
  reason_codes: string[];
  requested_trade_date?: string;
}
export interface UnavailablePublicResearch extends PublicResearchBoundary {
  status: 'WAITING' | 'CANNOT_CONFIRM';
}
export interface SavedPublicResearch extends PublicResearchBoundary {
  status: 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED';
  data_kind: 'SYNTHETIC' | 'RECORDED_INPUT_REPLAY' | 'OWNER_RESULT';
  evidence_status: 'VERIFIED_PERSISTENCE_ONLY';
  business_status: string;
  reference: {
    trade_date: string;
    input_identity: string;
    job_id: string;
    generation: string;
    attempt: number;
    commit_sha256: string;
    commit_file_sha256: string;
    product_sha256: string;
    job_sha256: string;
    receipt_sha256: string;
  };
  product: JsonObject & {status: string; rows?: JsonObject[]};
  job: JsonObject;
  receipt: JsonObject;
}
export type PublicResearchResult = UnavailablePublicResearch | SavedPublicResearch;
export interface PublicResearchState {
  phase: 'IDLE' | 'LOADING' | 'LOADED' | 'WAITING' | 'CANNOT_CONFIRM';
  result: PublicResearchResult | null;
  error: string;
}
function check(ok: unknown, reason: string): asserts ok {
  if (!ok) throw new Error('M16_' + reason);
}
function object(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function string(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function date(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{8}$/.test(value)) return false;
  const iso = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
  const parsed = new Date(iso + 'T00:00:00Z');
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === iso;
}
function digest(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
}
export async function readSavedPublicResearch(tradeDate = '', fetcher: Fetcher = fetch, signal?: AbortSignal): Promise<PublicResearchResult> {
  check(!tradeDate || date(tradeDate), 'DATE');
  const response = await fetcher(M16_ROUTE + (tradeDate ? '?trade_date=' + tradeDate : ''), {
    method: 'GET', cache: 'no-store', credentials: 'omit', signal,
  });
  check(response.ok, 'HTTP_' + response.status);
  const advertised = response.headers.get('content-length');
  check(!advertised || (/^\d+$/.test(advertised) && Number(advertised) <= MAX_BYTES), 'RESPONSE_LIMIT');
  check(response.body, 'EMPTY_RESPONSE');
  const reader = response.body.getReader(), parts: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.length;
      if (size > MAX_BYTES) {await reader.cancel(); throw new Error('M16_RESPONSE_LIMIT');}
      parts.push(part.value);
    }
  } finally {reader.releaseLock();}
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {bytes.set(part, offset); offset += part.length;}
  let value: unknown;
  try {value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));}
  catch {throw new Error('M16_RESPONSE_JSON');}
  check(object(value) && value.schema_version === 'v5.m16_saved_public_research.v1' && value.module_id === 'M16_PUBLIC_RESEARCH', 'CONTRACT');
  check(value.mode === 'READ_ONLY_SAVED_RESULT' && value.read_only === true && value.research_only === true &&
    ['can_execute', 'natural_verified', 'production_allowed', 'buy_gate_updated', 'orders_sent'].every(key => value[key] === false), 'RESEARCH_BOUNDARY');
  check(Array.isArray(value.reason_codes) && value.reason_codes.length > 0 && value.reason_codes.every(string), 'REASONS');
  if ('requested_trade_date' in value) check(date(value.requested_trade_date) && (!tradeDate || value.requested_trade_date === tradeDate), 'DATE');
  if (value.status === 'WAITING' || value.status === 'CANNOT_CONFIRM') {
    check(['reference', 'product', 'job', 'receipt', 'display_data', 'data_kind', 'business_status', 'evidence_status'].every(key => !(key in value)), 'UNAVAILABLE_HAS_CONTENT');
    return value as unknown as UnavailablePublicResearch;
  }
  check(value.status === 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED' && string(value.data_kind) && ['SYNTHETIC', 'RECORDED_INPUT_REPLAY', 'OWNER_RESULT'].includes(value.data_kind), 'SAVED_STATE');
  const reference = value.reference;
  check(object(reference) && date(reference.trade_date) && (!tradeDate || reference.trade_date === tradeDate) &&
    (!value.requested_trade_date || value.requested_trade_date === reference.trade_date) && string(reference.job_id) && string(reference.generation) &&
    typeof reference.attempt === 'number' && Number.isSafeInteger(reference.attempt) && reference.attempt > 0 &&
    ['input_identity', 'commit_sha256', 'commit_file_sha256', 'product_sha256', 'job_sha256', 'receipt_sha256'].every(key => digest(reference[key])), 'REFERENCE');
  check(value.evidence_status === 'VERIFIED_PERSISTENCE_ONLY', 'EVIDENCE');
  check(string(value.business_status), 'BUSINESS_STATUS');
  check(object(value.product) && value.product.status === value.business_status &&
    (!('rows' in value.product) || (Array.isArray(value.product.rows) && value.product.rows.every(object))), 'PRODUCT');
  check(object(value.job) && object(value.receipt), 'SAVED_RECORDS');
  // Persistence digest verification belongs to the backend cold reader. Preserve
  // its original business records rather than inferring a successful research run.
  return value as unknown as SavedPublicResearch;
}
export class SavedPublicResearchSession {
  private revision = 0;
  private closed = false;
  private controller: AbortController | null = null;
  private emit: (state: PublicResearchState) => void;
  private fetcher: Fetcher;
  constructor(emit: (state: PublicResearchState) => void, fetcher: Fetcher = fetch) {this.emit = emit; this.fetcher = fetcher;}
  async load(date = '') {
    if (this.closed) return;
    const revision = ++this.revision;
    this.controller?.abort();
    this.controller = new AbortController();
    this.emit({phase: 'LOADING', result: null, error: ''});
    try {
      const result = await readSavedPublicResearch(date, this.fetcher, this.controller.signal);
      if (!this.closed && revision === this.revision) this.emit({phase: result.status === 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED' ? 'LOADED' : result.status, result, error: ''});
    } catch (error) {
      if (!this.closed && revision === this.revision) this.emit({phase: 'CANNOT_CONFIRM', result: null, error: error instanceof Error ? error.message : 'M16_READ_FAILED'});
    }
  }
  close() {this.closed = true; this.revision++; this.controller?.abort();}
}
