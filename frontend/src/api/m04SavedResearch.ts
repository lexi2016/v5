/** Exact M04 saved sample, read only. No run, latest, capture, or model selector. */
export const M04_ROUTE='/api/v5/source-bundle/research-intelligence';
const MAX_BYTES=16*1024*1024;
const FLAGS=['natural_verified','historical_pit_claimed','formal_eligibility_verified','production_allowed','buy_gate_updated','orders_sent'];
type JsonObject=Record<string,unknown>;
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
export interface SavedResearchResult {
 schema_version:'v5.m04_saved_research.v1';status:'SAVED_HISTORICAL_SAMPLE';
 article_count:number;missing_retrieved_at:number;missing_available_at:number;pit:'UNKNOWN';
 out_of_sample_record_errors:number;reference:{archive_date:string;source_slot:string;source_run_id:string;batch_fetched_at?:string;source_publication_available_at?:string};
 archive:JsonObject&{articles:JsonObject[]};
}
export interface SavedResearchState {phase:'IDLE'|'LOADING'|'LOADED'|'NOT_CONFIGURED'|'CANNOT_CONFIRM';result:SavedResearchResult|null;error:string;}
function check(ok:unknown,reason:string):asserts ok {if(!ok)throw new Error('M04_'+reason);}
function object(value:unknown):value is Record<string,any>{return !!value&&typeof value==='object'&&!Array.isArray(value);}
export async function readSavedResearch(fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<SavedResearchResult|null>{
 const response=await fetcher(M04_ROUTE,{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'HTTP_'+response.status);
 const sizeHeader=response.headers.get('content-length');
 check(!sizeHeader||(/^\d+$/.test(sizeHeader)&&Number(sizeHeader)<=MAX_BYTES),'RESPONSE_LIMIT');
 check(response.body,'EMPTY_RESPONSE');const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>MAX_BYTES){await reader.cancel();throw new Error('M04_RESPONSE_LIMIT');}parts.push(item.value);}}finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
 let value:any;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('M04_RESPONSE_JSON');}
 check(object(value)&&value.module_id==='M04_RESEARCH_INTELLIGENCE'&&value.research_only===true&&FLAGS.every(k=>value[k]===false),'RESEARCH_BOUNDARY');
 if(value.status==='NOT_CONFIGURED'){check(Array.isArray(value.reason_codes)&&value.reason_codes.includes('M04_SAVED_REFERENCE_NOT_CONFIGURED'),'MISSING_CONTRACT');return null;}
 check(value.schema_version==='v5.m04_saved_research.v1'&&value.status==='SAVED_HISTORICAL_SAMPLE'&&value.data_kind==='RECORDED_INPUT_REPLAY'&&value.coverage_scope==='FIXED_18_ARTICLE_SAMPLE','CONTRACT');
 check(object(value.reference)&&value.reference.archive_date==='20261012'&&value.reference.source_slot==='2100'&&value.reference.source_run_id==='hip-49cb26f7f3a0661bde1d1440'&&value.reference.publication_time_is_not_article_availability===true,'REFERENCE');
 check(value.article_count===18&&value.pit==='UNKNOWN'&&value.missing_retrieved_at===18&&value.missing_available_at===18,'PIT_BOUNDARY');
 check(value.out_of_sample_record_errors===53,'OUT_OF_SAMPLE');
 check(object(value.archive)&&value.archive.archive_date==='20261012'&&value.archive.article_count===18&&Array.isArray(value.archive.articles)&&value.archive.articles.length===18,'ARCHIVE');
 check(['production_allowed','buy_gate_updated','orders_sent'].every(k=>value.archive[k]===false),'ARCHIVE_BOUNDARY');
 value.archive.articles.forEach((row:unknown)=>check(object(row)&&typeof row.article_id==='string'&&row.article_id.length>0&&(!row.retrieved_at||row.retrieved_at==='UNKNOWN')&&(!row.available_at||row.available_at==='UNKNOWN'),'ARTICLE_CLOCKS'));
 return value as SavedResearchResult;
}
export class SavedResearchSession {
 private revision=0;private closed=false;private controller:AbortController|null=null;
 private emit:(state:SavedResearchState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:SavedResearchState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();
  this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readSavedResearch(this.fetcher,this.controller.signal);if(!this.closed&&revision===this.revision)this.emit({phase:result?'LOADED':'NOT_CONFIGURED',result,error:''});}
  catch(error){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',result:null,error:error instanceof Error?error.message:'M04_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
