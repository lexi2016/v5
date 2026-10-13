/** Immutable M15 reads only. Neither loading nor paging starts an owner. */
export const M15_ROUTE='/api/v5/source-bundle/us-mapping-saved';
export type M15Lane='seed'|'industry'|'individual';
export type Reference={run_id:string;sha256:string;target_date:string};
export type Overview={schema_version:string;target_date:string;reference:Reference;mode:string;seed_status:string;seed_run_id:string;seed_artifact_sha256:string;seed_source_status:string;seed_coverage:unknown;seed_coverage_diagnostics?:{status?:string;scope?:string;reason_codes?:string[];[key:string]:unknown}|null;seed_coverage_scope?:unknown;seed_recovery_evaluation?:unknown;seed_execution_kind?:string|null;seed_gaps:unknown;us_session_date:string|null;target_date_eligibility:string;material_status:string|null;material_reasons:unknown;material_input:unknown;material_coverage:unknown;lanes:Record<M15Lane,number|null>;page_size:number;[key:string]:unknown};
export type Page={schema_version:string;target_date:string;reference:Reference;lane:M15Lane;offset:number;total:number;rows:unknown[];next_offset:number|null;[key:string]:unknown};
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
function check(value:unknown,message:string):asserts value {if(!value)throw new Error(message);}
function object(v:unknown):v is Record<string,any>{return !!v&&typeof v==='object'&&!Array.isArray(v);}
function reference(value:unknown,date:string):asserts value is Reference {check(object(value)&&value.target_date===date&&/^[0-9a-f]{32}$/.test(value.run_id)&&/^[0-9a-f]{64}$/.test(value.sha256),'M15_REFERENCE');}
async function request(query:Record<string,string>,fetcher:Fetcher,signal?:AbortSignal):Promise<any>{
 const response=await fetcher(M15_ROUTE+'?'+new URLSearchParams(query),{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'M15_HTTP_'+response.status);check(response.body,'M15_EMPTY_BODY');
 const reader=response.body.getReader();let size=0;const parts:Uint8Array[]=[];
 try{for(;;){const part=await reader.read();if(part.done)break;size+=part.value.length;check(size<=16*1024*1024,'M15_RESPONSE_LIMIT');parts.push(part.value);}}
 finally{await reader.cancel();reader.releaseLock();}
 const bytes=new Uint8Array(size);let at=0;for(const part of parts){bytes.set(part,at);at+=part.length;}
 const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 check(object(value)&&value.target_date===query.date,'M15_DATE_MISMATCH');reference(value.reference,query.date);
 check(value.RESEARCH_ONLY===true&&['formal_eligible','natural_verified','full_market_coverage','production_allowed','buy_gate_updated','orders_sent'].every(k=>value[k]===false),'M15_BOUNDARY');
 return value;
}
export async function readM15(date:string,fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<Overview>{
 check(/^\d{8}$/.test(date),'M15_DATE');const value=await request({date},fetcher,signal);
 check(value.schema_version==='v5.m15.public.v1'&&object(value.lanes)&&value.page_size===50,'M15_OVERVIEW');
 for(const lane of ['seed','industry','individual'])check(value.lanes[lane]===null||Number.isSafeInteger(value.lanes[lane])&&value.lanes[lane]>=0,'M15_COUNT');
 return value as Overview;
}
export async function readM15Page(overview:Overview,lane:M15Lane,offset:number,fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<Page>{
 check(['seed','industry','individual'].includes(lane)&&Number.isSafeInteger(offset)&&offset>=0&&offset%50===0,'M15_PAGE_REQUEST');
 const value=await request({date:overview.target_date,run_id:overview.reference.run_id,lane,offset:String(offset)},fetcher,signal);
 check(value.schema_version==='v5.m15.page.v1'&&value.reference.run_id===overview.reference.run_id&&value.reference.sha256===overview.reference.sha256,'M15_PAGE_IDENTITY');
 check(value.lane===lane&&value.offset===offset&&value.total===overview.lanes[lane]&&Array.isArray(value.rows)&&value.rows.length<=50,'M15_PAGE_CONTRACT');
 check(value.rows.length===Math.min(50,Math.max(0,value.total-offset))&&value.next_offset===(offset+50<value.total?offset+50:null),'M15_PAGE_SEQUENCE');
 return value as Page;
}
