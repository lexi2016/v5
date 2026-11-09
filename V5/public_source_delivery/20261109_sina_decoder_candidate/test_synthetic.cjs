'use strict';
// Self-authored synthetic tests. No vendor implementation or market fixtures.
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {decode,DECODER_SHA,writeRowsExclusive}=require('./adapter.cjs');
assert.equal(typeof decode,'function');assert.equal(decode.length,3);
assert.match(DECODER_SHA,/^[a-f0-9]{64}$/);
const fake=Buffer.from('synthetic-not-a-decoder');
const raw=Buffer.from('var KLC_K2_sz000001="A";');
const tests=[
 ['invalid_symbol',()=>decode(raw,'000001;evil',fake),/SYMBOL/],
 ['raw_wrong_type',()=>decode('not-buffer','000001.SZ',fake),/RAW_SIZE_TYPE/],
 ['raw_empty',()=>decode(Buffer.alloc(0),'000001.SZ',fake),/RAW_SIZE_TYPE/],
 ['raw_oversize',()=>decode(Buffer.alloc(8*1024*1024+1),'000001.SZ',fake),/RAW_SIZE_TYPE/],
 ['decoder_wrong_type',()=>decode(raw,'000001.SZ','bad'),/DECODER_PIN/],
 ['decoder_pin_mismatch',()=>decode(raw,'000001.SZ',fake),/DECODER_PIN/]
];
for(const [name,fn,error]of tests)assert.throws(fn,error,name);
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'sina-wrapper-synthetic-'));
try{
 const file=path.join(dir,'output.json');const rows=[{synthetic:true,date:'2000-01-01T00:00:00.000Z',close:1}];
 writeRowsExclusive(file,rows);assert.deepStrictEqual(JSON.parse(fs.readFileSync(file)),rows);
 const before=fs.readFileSync(file);assert.throws(()=>writeRowsExclusive(file,[{replacement:true}]),{code:'EEXIST'});assert.deepStrictEqual(fs.readFileSync(file),before);
}finally{fs.rmSync(dir,{recursive:true});}
console.log(JSON.stringify({status:'PASS',scope:'synthetic interface, rejection before vendor execution, exclusive output only',rejection_cases:tests.length,vendor_decode_exercised:false,real_market_verification:false,production_admission:false}));
