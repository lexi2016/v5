/** The synthetic fixture must retain legacy None semantics in both Python children. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('M09 fixture pins pandas string inference for its real producer and cold-reader process tree',()=>{
 const probe=`
import assert from 'node:assert/strict';
import childProcess from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
const actual=childProcess.spawnSync;
let observed=false;
childProcess.spawnSync=(command,args,options)=>{
 if(args.includes('V5/tests/export_m09_readonly_fixture.py')){
  observed=true;
  assert.equal(options.env?.PANDAS_FUTURE_INFER_STRING,'0','synthetic fixture must pin legacy string inference in the child environment');
  assert.equal(process.env.PANDAS_FUTURE_INFER_STRING,'1','the Node parent environment must stay unchanged');
 }
 return actual(command,args,options);
};
syncBuiltinESMExports();
await import(${JSON.stringify(new URL('./aCloseReplay.node.mjs',import.meta.url).href)});
assert.equal(observed,true,'the original synthetic exporter must actually be launched');
`;
 const result=spawnSync(process.execPath,['--input-type=module','-e',probe],{
  encoding:'utf8',env:{...process.env,PANDAS_FUTURE_INFER_STRING:'1'},timeout:60000,
 });
 assert.equal(result.status,0,result.stderr+'\n'+result.stdout);
});
