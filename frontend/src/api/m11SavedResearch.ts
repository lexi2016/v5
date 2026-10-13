/** Saved M11 evidence only. This reader never captures, generates or publishes research. */
export const M11_ROUTE = '/api/v5/source-bundle/intraday-research';
export const M11_SLOTS = ['09:25', '09:35', '10:00', '11:30', '14:00', '15:00'] as const;
type Slot = typeof M11_SLOTS[number];
type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
type JsonObject = Record<string, unknown>;
interface ResearchBoundary {
  schema_version: 'v5.m11_saved_research.v1';
  module_id: 'M11_INTRADAY_RESEARCH';
  research_only: true;
  natural_verified: false;
  review_completed: false;
  production_allowed: false;
  buy_gate_updated: false;
  orders_sent: false;
  reason_codes: string[];
  requested_trade_date?: string;
}
export interface ResearchSlot { slot: Slot; status: 'SAVED' | 'WAITING'; }
export interface WaitingResearch extends ResearchBoundary {
  status: 'WAITING';
  slots?: ResearchSlot[];
}
export interface SavedIntradayResearch extends ResearchBoundary {
  status: 'SAVED_RESEARCH_REVIEW_REQUIRED';
  data_kind: 'SYNTHETIC' | 'RECORDED_INPUT_REPLAY' | 'OWNER_RESULT';
  reference: {trade_date: string; run_id: string; commit_sha256: string; operation: 'capture' | 'generate'; slot: Slot};
  evidence_status: 'VERIFIED_PERSISTENCE_ONLY';
  business_status: string;
  research: {intraday_research?: JsonObject; research_review?: JsonObject};
  slots: ResearchSlot[];
}
export type IntradayResearchResult = WaitingResearch | SavedIntradayResearch;
export interface IntradayResearchState {
  phase: 'IDLE' | 'LOADING' | 'LOADED' | 'WAITING' | 'CANNOT_CONFIRM';
  result: IntradayResearchResult | null;
  error: string;
}
function check(ok: unknown, reason: string): asserts ok {
  if (!ok) throw new Error('M11_' + reason);
}
function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function string(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function validSlots(value: unknown, savedSlot?: string): boolean {
  return Array.isArray(value) && value.length === M11_SLOTS.length && value.every((row, index) =>
    object(row) && row.slot === M11_SLOTS[index] && row.status === (row.slot === savedSlot ? 'SAVED' : 'WAITING'));
}
export async function readSavedIntradayResearch(date = '', fetcher: Fetcher = fetch, signal?: AbortSignal): Promise<IntradayResearchResult> {
  check(!date || /^\d{8}$/.test(date), 'DATE');
  const response = await fetcher(M11_ROUTE + (date ? '?trade_date=' + date : ''), {
    method: 'GET', cache: 'no-store', credentials: 'omit', signal,
  });
  check(response.ok, 'HTTP_' + response.status);
  const max = 4 * 1024 * 1024;
  const header = response.headers.get('content-length');
  check(!header || (/^\d+$/.test(header) && Number(header) <= max), 'RESPONSE_LIMIT');
  check(response.body, 'EMPTY_RESPONSE');
  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.length;
      if (size > max) {
        await reader.cancel();
        throw new Error('M11_RESPONSE_LIMIT');
      }
      parts.push(part.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  const value: unknown = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  check(object(value) && value.schema_version === 'v5.m11_saved_research.v1' && value.module_id === 'M11_INTRADAY_RESEARCH', 'CONTRACT');
  check(value.research_only === true && ['natural_verified', 'review_completed', 'production_allowed', 'buy_gate_updated', 'orders_sent'].every(key => value[key] === false), 'RESEARCH_BOUNDARY');
  check(Array.isArray(value.reason_codes) && value.reason_codes.length > 0 && value.reason_codes.every(string), 'REASONS');
  if ('requested_trade_date' in value) {
    check(string(value.requested_trade_date) && /^\d{8}$/.test(value.requested_trade_date) && (!date || value.requested_trade_date === date), 'DATE');
  }
  if (value.status === 'WAITING') {
    check(['reference', 'research', 'display_data', 'data_kind', 'business_status', 'evidence_status'].every(key => !(key in value)), 'WAITING_HAS_CONTENT');
    if ('slots' in value) check(validSlots(value.slots), 'SLOTS');
    return value as unknown as WaitingResearch;
  }
  check(value.status === 'SAVED_RESEARCH_REVIEW_REQUIRED' && string(value.data_kind) && ['SYNTHETIC', 'RECORDED_INPUT_REPLAY', 'OWNER_RESULT'].includes(value.data_kind), 'SAVED_STATE');
  const reference = value.reference;
  check(object(reference) && string(reference.trade_date) && /^\d{8}$/.test(reference.trade_date) && (!date || date === reference.trade_date) &&
    string(reference.run_id) && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(reference.run_id) &&
    string(reference.commit_sha256) && /^[a-f0-9]{64}$/.test(reference.commit_sha256) &&
    (reference.operation === 'capture' || reference.operation === 'generate') && M11_SLOTS.some(slot => reference.slot === slot), 'REFERENCE');
  check(value.evidence_status === 'VERIFIED_PERSISTENCE_ONLY', 'EVIDENCE');
  check(string(value.business_status), 'BUSINESS_STATUS');
  check(object(value.research) && Object.keys(value.research).length > 0 && Object.entries(value.research).every(([key, content]) =>
    ['intraday_research', 'research_review'].includes(key) && object(content)), 'RESEARCH');
  check(validSlots(value.slots, reference.operation === 'capture' ? String(reference.slot) : undefined), 'SLOTS');
  return value as unknown as SavedIntradayResearch;
}
export class SavedIntradayResearchSession {
  private revision = 0;
  private closed = false;
  private controller: AbortController | null = null;
  private emit: (state: IntradayResearchState) => void;
  private fetcher: Fetcher;
  constructor(emit: (state: IntradayResearchState) => void, fetcher: Fetcher = fetch) {
    this.emit = emit;
    this.fetcher = fetcher;
  }
  async load(date = '') {
    if (this.closed) return;
    const revision = ++this.revision;
    this.controller?.abort();
    this.controller = new AbortController();
    this.emit({phase: 'LOADING', result: null, error: ''});
    try {
      const result = await readSavedIntradayResearch(date, this.fetcher, this.controller.signal);
      if (!this.closed && revision === this.revision) this.emit({phase: result.status === 'WAITING' ? 'WAITING' : 'LOADED', result, error: ''});
    } catch (error) {
      if (!this.closed && revision === this.revision) this.emit({phase: 'CANNOT_CONFIRM', result: null, error: error instanceof Error ? error.message : 'M11_READ_FAILED'});
    }
  }
  close() { this.closed = true; this.revision++; this.controller?.abort(); }
}
