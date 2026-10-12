/** Read only, bounded access to one already-saved M18 run. No live/workspace fallback. */
export const M18_ROUTE = '/api/v4/manager/m18/v2';
const RESPONSE_BYTES = 256 * 1024;
const IDENTITY_KEYS = ['run_id', 'target_date', 'plan_sha256', 'raw_sha256', 'response_sha256', 'input_identity'] as const;
export type Identity = Record<typeof IDENTITY_KEYS[number], string>;
export interface Descriptor { schema_version: string; identity: Identity; run_id: string; target_date: string; generation_id: string; profile_sha256: string; pages_route: string; status: string; generated_at: string; }
export interface Binding { identity: Identity; generation_id: string; profile_sha256: string; manifest_sha256: string; }
export interface SectionMeta { kind: string; total: number; loaded_count: number; not_loaded_count: number; state: string; }
export interface Overview extends Binding { schema: string; content_chunks: number; sections: Record<string, SectionMeta>; }
export interface SavedEntry { index: number; kind: string; offset: number; bytes: number; sha256: string; value_state: 'LOADED' | 'NOT_LOADED'; value?: unknown; reason?: string; }
export const REBOUND_GROUPS = ['strict','near','pending','excluded','screen_unresolved'] as const;
export type ReboundGroup = typeof REBOUND_GROUPS[number];
export interface ReboundMetadata { source_section_sha256: string; group_counts: Record<ReboundGroup,number>; source: Record<string,unknown>; observation: Record<string,unknown>; }
export interface AnnouncementMetadata { status: unknown; plan_cutoff: unknown; gaps: unknown; source_section_sha256: string; reference_count: number; products: Record<string,unknown>[]; }
export interface SectionPage extends Binding { schema: string; projection?: 'announcement_references' | 'rebound_references'; announcement?: AnnouncementMetadata; rebound?: ReboundMetadata; group?: ReboundGroup; section: string; selection: null; cursor: string | null; offset: number; matched_total: number; not_loaded_count: number; remaining_entries: number; entries: SavedEntry[]; next_cursor: string | null; }
type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;
function check(condition: unknown, code: string): asserts condition { if (!condition) throw new Error('M18_' + code); }
function object(value: unknown): value is Record<string, any> { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function digest(value: unknown): value is string { return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value); }
function integer(value: unknown, low = 0, high = 10000): value is number { return Number.isInteger(value) && Number(value) >= low && Number(value) <= high; }
function identity(value: unknown): asserts value is Identity {
 check(object(value) && Object.keys(value).length === IDENTITY_KEYS.length, 'IDENTITY');
 for (const key of IDENTITY_KEYS) check(typeof value[key] === 'string' && (key === 'run_id' ? /^[0-9a-f]{32}$/ : key === 'target_date' ? /^\d{8}$/ : /^[0-9a-f]{64}$/).test(value[key]), 'IDENTITY');
}
function binding(value: unknown, expected: Descriptor, manifest?: string): asserts value is Binding & Record<string, any> {
 check(object(value), 'BINDING'); identity(value.identity);
 check(IDENTITY_KEYS.every(key => value.identity[key] === expected.identity[key]) && value.generation_id === expected.generation_id && value.profile_sha256 === expected.profile_sha256, 'BINDING');
 check(digest(value.manifest_sha256) && (!manifest || value.manifest_sha256 === manifest), 'BINDING');
}
async function boundedJson(response: Response): Promise<any> {
 const advertised = response.headers.get('content-length');
 check(!advertised || (/^\d+$/.test(advertised) && Number(advertised) <= RESPONSE_BYTES), 'RESPONSE_LIMIT');
 check(response.body, 'EMPTY_RESPONSE');
 const reader = response.body.getReader(); const parts: Uint8Array[] = []; let size = 0;
 try { while (true) { const item = await reader.read(); if (item.done) break; size += item.value.length; if (size > RESPONSE_BYTES) { await reader.cancel(); throw new Error('M18_RESPONSE_LIMIT'); } parts.push(item.value); } }
 finally { reader.releaseLock(); }
 const bytes = new Uint8Array(size); let offset = 0; for (const part of parts) { bytes.set(part, offset); offset += part.length; }
 let value: any; try { value = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes)); } catch { throw new Error('M18_RESPONSE_JSON'); }
 if (!response.ok) { const reasons = Array.isArray(value?.reason_codes) ? value.reason_codes.filter((code: unknown) => typeof code === 'string' && /^[A-Z0-9_]{1,100}$/.test(code)).join(',') : ''; throw new Error(`M18_HTTP_${response.status}${reasons ? ': ' + reasons : ''}`); }
 return value;
}
export class M18SavedClient {
 private fetcher: Fetcher;
 constructor(fetcher: Fetcher = (url, options) => fetch(url, options)) { this.fetcher = fetcher; }
 private async get(path: string, query: Record<string,string>, signal?: AbortSignal) { return boundedJson(await this.fetcher(M18_ROUTE + path + '?' + new URLSearchParams(query), {method:'GET', cache:'no-store', credentials:'same-origin', signal})); }
 async descriptor(run: string, signal?: AbortSignal): Promise<Descriptor> {
  check(/^[0-9a-f]{32}$/.test(run), 'RUN_ID'); const value = await this.get('', {run_id:run}, signal);
  check(object(value) && value.schema_version === 'v5.m18.v2.descriptor.v1' && value.status === 'READY', 'DESCRIPTOR_NOT_READY'); identity(value.identity);
  check(value.run_id === run && value.identity.run_id === run && value.target_date === value.identity.target_date && value.pages_route === M18_ROUTE + '/pages' && digest(value.generation_id) && digest(value.profile_sha256) && typeof value.generated_at === 'string' && Number.isFinite(Date.parse(value.generated_at)), 'DESCRIPTOR');
  return value as Descriptor;
 }
 async overview(expected: Descriptor, signal?: AbortSignal): Promise<Overview> {
  const value = await this.get('/overview', {run_id:expected.run_id, generation_id:expected.generation_id}, signal); binding(value,expected);
  check(value.schema === 'v5.m18.offline.v2.overview' && integer(value.content_chunks,1,256) && object(value.sections) && Object.keys(value.sections).length <= 10000, 'OVERVIEW');
  for (const row of Object.values(value.sections)) check(object(row) && typeof row.kind === 'string' && integer(row.total) && row.loaded_count === 0 && row.not_loaded_count === row.total && row.state === 'NOT_LOADED', 'OVERVIEW');
  return value as Overview;
 }
 async section(expected: Descriptor, overview: Overview, section: string, cursor: string | null = null, offset = 0, signal?: AbortSignal, group: ReboundGroup = 'strict'): Promise<SectionPage> {
  const projected = section === 'announcement_reviewed_analysis', rebound = section === 'rebound_research_observation';
  check(Object.hasOwn(overview.sections,section) && section.length <= 1024 && integer(offset) && (rebound || offset % 32 === 0) && (cursor === null ? offset === 0 : cursor.length <= 8192 && offset > 0), 'SECTION_REQUEST');
  if (rebound) check(REBOUND_GROUPS.includes(group), 'REBOUND_GROUP');
  const query: Record<string,string> = {run_id:expected.run_id, generation_id:expected.generation_id, section}; if (cursor !== null) query.cursor=cursor; if (projected) query.projection='announcement_references'; if (rebound) {query.projection='rebound_references';query.group=group;}
  const value = await this.get('/sections',query,signal); binding(value,expected,overview.manifest_sha256);
  if (projected) check(value.projection === 'announcement_references' && object(value.announcement) && digest(value.announcement.source_section_sha256) && integer(value.announcement.reference_count) && Array.isArray(value.announcement.products) && value.announcement.products.every(object), 'ANNOUNCEMENT_PROJECTION');
  else if (rebound) check(value.projection === 'rebound_references' && value.group === group && object(value.rebound) && digest(value.rebound.source_section_sha256) && object(value.rebound.group_counts) && Object.keys(value.rebound.group_counts).length === REBOUND_GROUPS.length && REBOUND_GROUPS.every(key=>integer(value.rebound.group_counts[key])) && object(value.rebound.source) && object(value.rebound.observation), 'REBOUND_PROJECTION');
  else check(!Object.hasOwn(value,'projection') && !Object.hasOwn(value,'announcement') && !Object.hasOwn(value,'rebound') && !Object.hasOwn(value,'group'), 'SECTION_PROJECTION');
  const total = projected ? value.announcement.reference_count : rebound ? value.rebound.group_counts[group] : overview.sections[section].total;
  check(value.schema === 'v5.m18.offline.v2.detail' && value.section === section && value.selection === null && value.cursor === cursor && value.offset === offset && value.matched_total === total && Array.isArray(value.entries) && value.entries.length <= 32 && integer(value.remaining_entries) && integer(value.not_loaded_count) && (value.next_cursor === null || (typeof value.next_cursor === 'string' && value.next_cursor.length <= 8192)), 'SECTION_PAGE');
  for (const [position, entry] of value.entries.entries()) check(object(entry) && entry.index === offset + position && typeof entry.kind === 'string' && integer(entry.offset,0,64*1024*1024) && integer(entry.bytes,1,64*1024*1024) && digest(entry.sha256) && (entry.value_state === 'LOADED' ? Object.hasOwn(entry,'value') : entry.value_state === 'NOT_LOADED' && !Object.hasOwn(entry,'value')), 'SECTION_ENTRY');
  const pageCountValid = rebound ? (total === 0 ? offset === 0 && value.entries.length === 0 : offset < total && value.entries.length > 0 && value.entries.length <= Math.min(32,total-offset)) : value.entries.length === Math.min(32,total-offset);
  check(pageCountValid && value.remaining_entries === value.matched_total-offset-value.entries.length && value.not_loaded_count === value.matched_total-value.entries.filter((entry: SavedEntry) => entry.value_state === 'LOADED').length && (value.remaining_entries > 0) === (value.next_cursor !== null), 'SECTION_COUNTS');
  return value as SectionPage;
 }
}
export function chooseSection(sections: Record<string, SectionMeta>): string { return ['announcement_reviewed_analysis','summary','stocks','cards','candidates','focus_stocks','status','gaps'].find(key => Object.hasOwn(sections,key)) ?? Object.keys(sections)[0] ?? ''; }
export function entryPresentation(entry: SavedEntry): {state:string; value?:unknown; reason?:string} { return entry.value_state === 'LOADED' ? {state:'LOADED',value:entry.value} : {state:'NOT_LOADED',reason:entry.reason ?? 'NOT_LOADED'}; }

export interface SavedRunState { phase: 'IDLE' | 'LOADING' | 'LOADED' | 'CANNOT_CONFIRM'; descriptor: Descriptor | null; overview: Overview | null; section: string; group?: ReboundGroup; page: SectionPage | null; error: string; canPrevious: boolean; }
/** Latest-request wins; navigation never combines runs or retains rows after a failure. */
export class SavedRunSession {
 state: SavedRunState = {phase:'IDLE',descriptor:null,overview:null,section:'',page:null,error:'',canPrevious:false};
 private client: Pick<M18SavedClient,'descriptor'|'overview'|'section'>;
 private changed: (state: SavedRunState) => void;
 private serial=0; private abort: AbortController | null=null;
 private history: {cursor:string|null;offset:number}[]=[]; private position=0;
 constructor(client: Pick<M18SavedClient,'descriptor'|'overview'|'section'> = new M18SavedClient(), changed: (state:SavedRunState)=>void = () => {}) { this.client=client; this.changed=changed; }
 private set(patch: Partial<SavedRunState>) { this.state={...this.state,...patch}; this.changed(this.state); }
 private begin() { this.abort?.abort(); this.abort=new AbortController(); const serial=++this.serial; this.set({phase:'LOADING',page:null,error:''}); return {serial,signal:this.abort.signal}; }
 private failure(error:unknown,serial:number) { if(serial===this.serial) this.set({phase:'CANNOT_CONFIRM',page:null,error:error instanceof Error ? error.message : 'M18_UNAVAILABLE'}); }
 async load(run:string) {
  const {serial,signal}=this.begin(); this.history=[];this.position=0;this.set({descriptor:null,overview:null,section:'',group:undefined,canPrevious:false});
  try {
   const descriptor=await this.client.descriptor(run,signal); if(serial!==this.serial)return;
   const overview=await this.client.overview(descriptor,signal); if(serial!==this.serial)return;
   const section=chooseSection(overview.sections); this.set({descriptor,overview,section});
   const page=section ? await this.client.section(descriptor,overview,section,null,0,signal) : null; if(serial!==this.serial)return;
   this.history=[{cursor:null,offset:0}];this.set({page,phase:'LOADED'});
  } catch(error) { this.failure(error,serial); }
 }
 async select(section:string,group:ReboundGroup='strict') { this.set({group:section==='rebound_research_observation'?group:undefined});this.history=[{cursor:null,offset:0}];this.position=0;await this.pageAt(section,0); }
 private async pageAt(section:string,position:number) {
  const {descriptor,overview,group}=this.state; const request=this.history[position]; if(!descriptor||!overview||!request)return;
  const {serial,signal}=this.begin();this.set({section,canPrevious:position>0});
  try { const page=await this.client.section(descriptor,overview,section,request.cursor,request.offset,signal,group); if(serial!==this.serial)return;this.position=position;this.set({page,phase:'LOADED'}); }
  catch(error) { this.failure(error,serial); }
 }
 async next() { const page=this.state.page;if(this.state.phase==='LOADING'||!page?.next_cursor)return;this.history=this.history.slice(0,this.position+1);this.history.push({cursor:page.next_cursor,offset:page.offset+page.entries.length});await this.pageAt(this.state.section,this.position+1); }
 async previous() { if(this.state.phase==='LOADING'||this.position<1)return;await this.pageAt(this.state.section,this.position-1); }
 close() { this.abort?.abort();this.serial++; }
}
