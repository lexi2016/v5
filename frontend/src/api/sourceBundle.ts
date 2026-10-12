/** Independent read-only source status. Never starts an owner or reuses M18 state. */
export const SOURCE_ROUTE = '/api/v5/source-bundle/status';
const MODULES = ['M01_A_MARKET','M02_HK_MARKET','M03_US_MARKET','M05_A_PRESELECTION'];
const OWNERS = ['m01_a_source','m02_hk_source','m03_us_source','m05_a_preselection'];
const FLAGS = ['natural_verified','formal_eligibility_verified','production_allowed','buy_gate_updated','orders_sent'];
const MAX_BYTES = 16 * 1024 * 1024;
export interface SourceRow { module_id:string; owner_entry:string; status:string; error?:string; error_type?:string; owner_result?:Record<string,unknown>; }
export interface SourceResult { schema_version:string; status:string; observed_at:string; request_sha256:string; data_kind:string; modules:SourceRow[]; }
export interface SourceState { phase:'IDLE'|'LOADING'|'LOADED'|'CANNOT_CONFIRM'; result:SourceResult|null; error:string; }
type Fetcher = (url:string,init?:RequestInit)=>Promise<Response>;
function check(ok:unknown,reason:string):asserts ok { if(!ok)throw new Error('SOURCE_'+reason); }
function object(value:unknown):value is Record<string,any> { return !!value&&typeof value==='object'&&!Array.isArray(value); }
export async function readSourceBundle(fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<SourceResult> {
 const response=await fetcher(SOURCE_ROUTE,{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'HTTP_'+response.status);
 const advertised=response.headers.get('content-length');
 check(!advertised||(/^\d+$/.test(advertised)&&Number(advertised)<=MAX_BYTES),'RESPONSE_LIMIT');
 check(response.body,'EMPTY_RESPONSE');
 const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try { while(true) { const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>MAX_BYTES){await reader.cancel();throw new Error('SOURCE_RESPONSE_LIMIT');}parts.push(item.value); } }
 finally {reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
 let value:any;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('SOURCE_RESPONSE_JSON');}
 check(object(value)&&value.schema_version==='v5.source_bundle.result.v1'&&value.status==='SOURCE_BUNDLE_ATTEMPTED','CONTRACT');
 check(typeof value.observed_at==='string'&&Number.isFinite(Date.parse(value.observed_at))&&/^[0-9a-f]{64}$/.test(value.request_sha256),'IDENTITY');
 check(['SYNTHETIC','RECORDED_INPUT_REPLAY'].includes(value.data_kind)&&FLAGS.every(k=>value[k]===false),'RESEARCH_BOUNDARY');
 check(Array.isArray(value.modules)&&value.modules.length===4,'MODULES');
 value.modules.forEach((row:unknown,i:number)=>{check(object(row)&&row.module_id===MODULES[i]&&row.owner_entry===OWNERS[i]&&typeof row.status==='string'&&row.status.length>0&&FLAGS.every(k=>row[k]===false),'MODULE_CONTRACT');});
 return value as SourceResult;
}
export class SourceBundleSession {
 private revision=0;private controller:AbortController|null=null;private closed=false;
 private emit:(state:SourceState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:SourceState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();
  this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readSourceBundle(this.fetcher,this.controller.signal);if(revision===this.revision&&!this.closed)this.emit({phase:'LOADED',result,error:''});}
  catch(error){if(revision===this.revision&&!this.closed)this.emit({phase:'CANNOT_CONFIRM',result:null,error:error instanceof Error?error.message:'SOURCE_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
