'use strict';
// Project-owned wrapper only. Vendor decoder must be supplied locally, never fetched/evaluated as SDK.
const fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const DECODER_SHA='0effc9a3924b63f8c7f10c6ac4ed8b2654599ebc3ec762348bf96a42f056f48a';
const LIMITS=Object.freeze({raw:8*1024*1024,decoder:64*1024,rows:100000,output:32*1024*1024,timeout:3000});
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function decode(raw,symbol,decoder){
 if(typeof symbol!=='string'||!/^\d{6}\.(SZ|SH|BJ)$/.test(symbol))throw Error('SYMBOL');
 if(!Buffer.isBuffer(raw)||raw.length===0||raw.length>8*1024*1024)throw Error('RAW_SIZE_TYPE');
 if(!Buffer.isBuffer(decoder)||decoder.length>LIMITS.decoder||hash(decoder)!==DECODER_SHA)throw Error('DECODER_PIN');
 const text=raw.toString('utf8'); if(!Buffer.from(text).equals(raw))throw Error('RAW_ENCODING');
 const parts=text.split('/*');
 if(parts.length>2||(parts.length===2&&!/^[A-Za-z0-9+/=\s]*\*\/\s*$/.test(parts[1])))throw Error('COMMENT_CONTENT');
 const tx=symbol.slice(7).toLowerCase()+symbol.slice(0,6);
 const m=new RegExp('^var KLC_K2_'+tx+'="([A-Za-z0-9+/]+)";?\\s*$').exec(parts[0]);
 if(!m)throw Error('RAW_ENVELOPE');
 const context=vm.createContext({encoded:m[1]},{codeGeneration:{strings:false,wasm:false}});
 const output=new vm.Script('(()=>{const r='+decoder.toString('utf8').trim()+'(encoded);if(!Array.isArray(r)||r.length>'+LIMITS.rows+')throw Error("ROWS");const s=JSON.stringify(r);if(s.length>'+LIMITS.output+')throw Error("OUTPUT_SIZE");return s;})()').runInContext(context,{timeout:3000});
 if(typeof output!=='string'||Buffer.byteLength(output)>LIMITS.output)throw Error('OUTPUT_SIZE');
 const rows=JSON.parse(output);validateRows(rows);
 // Preserve original rows/units/optional fields. No target-day invention or admission/factor logic here.
 return rows;
}
function writeRowsExclusive(out,rows){
 const encoded=JSON.stringify(rows)+'\n';
 if(Buffer.byteLength(encoded)>LIMITS.output)throw Error('OUTPUT_SIZE');
 fs.writeFileSync(out,encoded,{flag:'wx'});
}
function validateRows(rows){
 if(!Array.isArray(rows)||!rows.length||rows.length>LIMITS.rows)throw Error('ROWS');
 let previous='';for(const row of rows){
  if(!row||typeof row.date!=='string'||!/^\d{4}-\d\d-\d\dT00:00:00\.000Z$/.test(row.date)||!Number.isFinite(Date.parse(row.date))||new Date(row.date).toISOString()!==row.date||row.date<=previous)throw Error('DATE');
  previous=row.date;
  for(const key of ['open','high','low','close','volume'])if(typeof row[key]!=='number'||!Number.isFinite(row[key]))throw Error('FIELD_'+key);
  for(const key of ['open','high','low','close','volume','amount','postVol','postAmt'])if(key in row && (typeof row[key]!=='number'||!Number.isFinite(row[key])||row[key]<0))throw Error('VALUE_'+key);
  if(row.low>Math.min(row.open,row.close)||row.high<Math.max(row.open,row.close)||row.low>row.high)throw Error('OHLC');
 }

 return rows;
}
function readBoundedRegular(file,limit){
 const before=fs.lstatSync(file);if(!before.isFile()||before.isSymbolicLink())throw Error('FILE_TYPE');
 if(before.size===0||before.size>limit)throw Error('FILE_SIZE');
 if(typeof fs.constants.O_NOFOLLOW!=='number')throw Error('NOFOLLOW_UNAVAILABLE');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{
  const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.dev!==before.dev||stat.ino!==before.ino)throw Error('FILE_CHANGED');
  if(stat.size===0||stat.size>limit)throw Error('FILE_SIZE');
  const chunks=[];let total=0;
  while(true){const buf=Buffer.alloc(Math.min(65536,limit+1-total));const n=fs.readSync(fd,buf,0,buf.length,null);if(!n)break;total+=n;if(total>limit)throw Error('FILE_SIZE');chunks.push(buf.subarray(0,n));}
  const after=fs.fstatSync(fd);if(total!==stat.size||after.size!==stat.size||after.mtimeMs!==stat.mtimeMs||after.ctimeMs!==stat.ctimeMs)throw Error('FILE_CHANGED');
  return Buffer.concat(chunks,total);
 }finally{fs.closeSync(fd);}
}
module.exports={decode,DECODER_SHA,writeRowsExclusive,validateRows,readBoundedRegular,LIMITS};
if(require.main===module){
 if(process.argv.length!==6)throw Error('USAGE: node --max-old-space-size=96 adapter.cjs SYMBOL RAW DECODER NEW_OUTPUT');
 const [symbol,raw,decoder,out]=process.argv.slice(2);
 const rows=decode(readBoundedRegular(raw,LIMITS.raw),symbol,readBoundedRegular(decoder,LIMITS.decoder));
 writeRowsExclusive(out,rows);
 console.log(JSON.stringify({symbol,rows:rows.length,last:rows.at(-1).date,production_admission:false}));
}
