'use strict';
// Project-owned wrapper only. Vendor decoder must be supplied locally, never fetched/evaluated as SDK.
const fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const DECODER_SHA='0effc9a3924b63f8c7f10c6ac4ed8b2654599ebc3ec762348bf96a42f056f48a';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function decode(raw,symbol,decoder){
 if(typeof symbol!=='string'||!/^\d{6}\.(SZ|SH|BJ)$/.test(symbol))throw Error('SYMBOL');
 if(!Buffer.isBuffer(raw)||raw.length===0||raw.length>8*1024*1024)throw Error('RAW_SIZE_TYPE');
 if(!Buffer.isBuffer(decoder)||hash(decoder)!==DECODER_SHA)throw Error('DECODER_PIN');
 const text=raw.toString('utf8'); if(!Buffer.from(text).equals(raw))throw Error('RAW_ENCODING');
 const parts=text.split('/*');
 if(parts.length>2||(parts.length===2&&!/^[A-Za-z0-9+/=\s]*\*\/\s*$/.test(parts[1])))throw Error('COMMENT_CONTENT');
 const tx=symbol.slice(7).toLowerCase()+symbol.slice(0,6);
 const m=new RegExp('^var KLC_K2_'+tx+'="([A-Za-z0-9+/]+)";?\\s*$').exec(parts[0]);
 if(!m)throw Error('RAW_ENVELOPE');
 const context=vm.createContext({encoded:m[1]},{codeGeneration:{strings:false,wasm:false}});
 const output=new vm.Script('JSON.stringify('+decoder.toString('utf8').trim()+'(encoded))').runInContext(context,{timeout:3000});
 const rows=JSON.parse(output); if(!Array.isArray(rows)||!rows.length)throw Error('ROWS');
 let previous='';for(const row of rows){
  if(!row||typeof row.date!=='string'||!/^\d{4}-\d\d-\d\dT00:00:00\.000Z$/.test(row.date)||!Number.isFinite(Date.parse(row.date))||new Date(row.date).toISOString()!==row.date||row.date<=previous)throw Error('DATE');
  previous=row.date;
  for(const key of ['open','high','low','close','volume'])if(typeof row[key]!=='number'||!Number.isFinite(row[key]))throw Error('FIELD_'+key);
 }
 // Preserve original rows/units/optional fields. No target-day invention or admission/factor logic here.
 return rows;
}
function writeRowsExclusive(out,rows){
 fs.writeFileSync(out,JSON.stringify(rows)+'\n',{flag:'wx'});
}
module.exports={decode,DECODER_SHA,writeRowsExclusive};
if(require.main===module){
 if(process.argv.length!==6)throw Error('USAGE: node --max-old-space-size=96 adapter.cjs SYMBOL RAW DECODER NEW_OUTPUT');
 const [symbol,raw,decoder,out]=process.argv.slice(2);
 const rows=decode(fs.readFileSync(raw),symbol,fs.readFileSync(decoder));
 writeRowsExclusive(out,rows);
 console.log(JSON.stringify({symbol,rows:rows.length,last:rows.at(-1).date,production_admission:false}));
}
