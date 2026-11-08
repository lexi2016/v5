"""Synthetic recorded cross-node contracts, original packaged functions, no activation."""
import importlib.util,json,os,pathlib,shutil,tempfile,unittest,copy,subprocess,sys

def add_contract(reg,policy,docs,r):
 policy['panel_freshness']={'schema':'FREEZE_PANEL_FRESHNESS_V1','market':'A_SHARE','timezone':'Asia/Shanghai','calendar_version':'SYNTHETIC_CAL','max_completed_session_lag':0,'max_observation_age_seconds':300000,'max_available_age_seconds':300000}
 docs['market_calendar']={'schema':'MARKET_SESSION_CALENDAR_V1','market':'A_SHARE','timezone':'Asia/Shanghai','version':'SYNTHETIC_CAL','coverage_start':'20261001','coverage_end':'20261110','source_reference':'SYNTHETIC_FIXTURE_NOT_REAL_CALENDAR','sessions':[{'trade_date':d,'close_at':d[:4]+'-'+d[4:6]+'-'+d[6:]+'T15:00:00+08:00'} for d in ['20261001','20261105','20261106','20261109','20261110']]}
 docs['panel_evidence']={'schema':'FREEZE_PANEL_EVIDENCE_V1','panel_identity':r.sha(r.canonical(docs['panel'])),'source_date':reg['source_date'],'calendar_version':'SYNTHETIC_CAL','event_at':'2026-11-06T15:00:00+08:00','observed_at':'2026-11-06T15:01:00+08:00','available_at':'2026-11-06T15:02:00+08:00','source_reference':'SYNTHETIC_PROVIDER_RECEIPT'}
 return reg,policy,docs


class Workflow(unittest.TestCase):
 def test_freeze_delta_jk_assembly_opening(self):
  package=os.environ.get('MORNING_PACKAGE_ROOT',str(pathlib.Path(__file__).resolve().parents[2]))
  if not package:self.skipTest('explicit current packaged source required')
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)/'public';shutil.copytree(package,root);entry=root/'20261108_execution_increment/morning/registered.py'

   spec=importlib.util.spec_from_file_location('workflow_registered',entry);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);safe=m.module('safeio')
   refs={};pids=[];count=[0]
   def persisted(reg,policy,docs,safe):
    count[0]+=1;inputs={}
    docs=copy.deepcopy(docs);parent=None;sections={}
    if 'freeze_parent' in docs:
     del docs['freeze_parent'];parent=refs['06:30:00']
    if reg['node']=='morning-delivery':
     sections={'freeze':refs['07:00:00'],'jk-verify':refs['08:00:00']}
     for name in sections:docs['assembly_sections'][name]['content']={}
    for key,doc in docs.items():
     raw=m.canonical(doc);path=f'probe_{count[0]}_{key}.json';(root/path).write_bytes(raw)
     inputs[key]={'path':path,'bytes':len(raw),'sha256':m.sha(raw)}
    req={'reg':reg,'policy':policy,'inputs':inputs,'parent':parent,'sections':sections}
    path=root/f'request_{count[0]}.json';path.write_bytes(m.canonical(req))
    proc=subprocess.run([sys.executable]+(['-O'] if sys.flags.optimize else [])+[str(pathlib.Path(__file__).resolve()),'--worker',str(root),str(path)],capture_output=True,text=True)
    if proc.returncode not in (0,2):raise RuntimeError(proc.stderr)
    out=json.loads(proc.stdout);pids.append(out['pid'])
    print(json.dumps({k:v for k,v in out.items() if k!='result'}),flush=True)
    if 'error' in out:raise ValueError(out['error'])
    refs[reg['cutoff'][11:19]]=out['ref']
    return out['result']
   symbols=[f'{i:06d}.SZ' for i in range(1,202)];groups=('original','nav_smallk','nav_pullback','nav_breakout')
   panel={'schema':'PAR_SCREEN_DISPLAY_V1','source_date':'20261106','pool_version':'SYNTHETIC_POOL_V1','scope_count':201,'partitions':{'COMPUTED_CURRENT':201},'dedup_selected':0,'dedup_pending':201,'counts':{g:{'after_risk':{'TRUE':0,'FALSE':0,'UNKNOWN':201}} for g in groups},'rows':[{'symbol':s,'name':'SYNTHETIC','owner_outcome':'COMPUTED_CURRENT','source_family':'SYNTHETIC_TEST','actual_date':'20261106','layers':{g:{'after_risk':'UNKNOWN'} for g in groups}} for s in symbols]}
   reg={'node':'freeze','run_id':'SYNTHETIC_WORKFLOW','environment_id':'TEMP','domain':'synthetic','business_date':'20261109','source_date':'20261106','cutoff':'2026-11-09T06:30:00+08:00','inputs':{},'policy':{},'review':{},'owner_identity':'SYNTHETIC_NOT_PRODUCTION_OWNER','output_relative':'unused','adapter_sha256':m.sha(entry.read_bytes())}
   definition={'symbol':symbols[0],'field':'reference','unit':'price','basis':'raw','currency':'CNY','asof':'2026-11-09T06:29:00+08:00'}
   policy={'panel_denominator':201,'semantic_keys':['reference'],'source_ids':['synthetic1','synthetic2'],'key_definitions':{'reference':definition},'semantic_max_age_seconds':{'reference':3600},'freeze_chain':{'schema':'FREEZE_CHAIN_POLICY_V1','version':'TEST_V1','mode':'GENESIS','expected_parent_identity':None}}
   fact={'key':'reference','definition':definition,'value':1,'observed_at':'2026-11-09T06:29:00+08:00','available_at':'2026-11-09T06:29:30+08:00'}
   multi={'sources':{k:{'available_at':fact['available_at'],'facts':[copy.deepcopy(fact)]} for k in policy['source_ids']}}
   docs={'panel':panel,'multi_source':multi,'freeze_changes':{s:'SYNTHETIC genesis' for s in symbols}}
   add_contract(reg,policy,docs,m)
   first=persisted(reg,policy,docs,safe);self.assertFalse(first['formal_freeze']);self.assertEqual(len(first['lineage']['changes']),201)
   reg['cutoff']='2026-11-09T07:00:00+08:00';policy['freeze_chain'].update(mode='DELTA',version='TEST_V2',expected_parent_identity=first['lineage']['identity']);docs['freeze_parent']=first['lineage'];panel['rows'][0]['name']='SYNTHETIC corrected';docs['freeze_changes']={symbols[0]:'Synthetic name correction'}
   docs['panel_evidence']['panel_identity']=m.sha(m.canonical(panel))
   delta=persisted(reg,policy,docs,safe);self.assertEqual(delta['lineage']['parent_identity'],first['lineage']['identity']);self.assertEqual(len(delta['lineage']['changes']),1)
   jkpolicy={'required_comparisons':[{'symbol':'JK_TEST','field':'open','source_ids':['synthetic1','synthetic2']}],'max_observation_age_seconds':60}
   jkpolicy['provider_catalog']={s:{'independence_group':s,'allowed_urls':['https://'+s+'.example.invalid/quote']} for s in ('synthetic1','synthetic2')}
   jkpolicy['required_comparisons'][0]['semantic_contract']={'unit':'index_points','basis':'unadjusted','currency':'JPY','raw_fields':{s:['open'] for s in ('synthetic1','synthetic2')}}
   observations={'source_day':'2026-11-09','records':[{'id':'fixture_'+s,'source_id':s,'source_date':'2026-11-09','symbol':'JK_TEST','field':'open','value':'1','url':'https://'+s+'.example.invalid/quote','unit':'index_points','basis':'unadjusted','currency':'JPY','observed_at':'2026-11-09T07:59:00+08:00','available_at':'2026-11-09T07:59:30+08:00'} for s in ('synthetic1','synthetic2')]}
   jkreg=dict(reg,node='jk-verify',source_date='20261109',cutoff='2026-11-09T08:00:00+08:00');jk=persisted(jkreg,jkpolicy,{'observations':observations},safe);self.assertEqual(jk['status'],'RECONCILED');self.assertFalse(jk['source_admission'])
   sections={}
   for name,content,observed in [('freeze',delta,'07:00:00'),('jk-verify',jk,'08:00:00'),('morning-materials',{'status':'USER_RESEARCH_HANDOFF_PENDING','source':'SYNTHETIC_TEST'},'08:00:00')]:
    stamp='2026-11-09T'+observed+'+08:00';sections[name]={'business_date':'20261109','source_date':'20261106','observed_at':stamp,'available_at':stamp,'status':content['status'],'content':content,'source_reference':'SYNTHETIC_LOCAL:'+name}
   assembly=persisted(dict(reg,node='morning-delivery',cutoff='2026-11-09T08:10:00+08:00'),{'assembly_schema':'MORNING_0810_PREVIEW_V1','section_max_age_seconds':{k:7200 for k in sections}},{'assembly_sections':sections},safe)
   self.assertEqual(assembly['delivery_status'],'NOT_SENT');self.assertFalse(assembly['business_accepted']);self.assertFalse(assembly['formal_freeze']);self.assertEqual(assembly['sections'][0]['content']['lineage']['identity'],delta['lineage']['identity']);self.assertEqual(assembly['sections'][1]['status'],'USER_RESEARCH_HANDOFF_PENDING')
   top={'schema':'DATED_FIXED_REFERENCE_TOP200_V1','source_date':'20261106','pool_version':'SYNTHETIC_POOL_V1','scope_count':201,'rows':[{'symbol':s,'rank':i+1,'actual_date':'20261106','change_pct_display':0} for i,s in enumerate(symbols[:200])]};scope={'schema':'DATED_RESEARCH_POOL_V1','source_date':'20261106','pool_version':'SYNTHETIC_POOL_V1','symbols':symbols}
   opening=persisted(dict(reg,node='opening-prep',cutoff='2026-11-09T08:50:00+08:00'),{'top_schema':top['schema']},{'top':top,'panel':panel,'pool_scope':scope},safe)
   self.assertEqual(len(opening['rows']),200);self.assertTrue(all(x['has_unknown'] for x in opening['rows']));self.assertFalse(opening['monitor_list_frozen']);self.assertEqual(opening['delivery_status'],'NOT_SENT');self.assertEqual(opening['rows'][0]['name'],'SYNTHETIC corrected')
   self.assertEqual(m.TRUSTED_RUNS,());self.assertEqual(m.dispatch('freeze','SYNTHETIC_WORKFLOW','TEMP',None)['status'],'BLOCKED_NO_TRUSTED_REGISTRATION')
   self.assertEqual(len(pids),len(set(pids)))
   frozen_path=root/refs['06:30:00']['path'];before=frozen_path.read_bytes();frozen_path.write_bytes(before+b' ')
   with self.assertRaisesRegex(ValueError,'INPUT_PIN_CHANGED'):
    persisted(reg,policy,docs,safe)
   frozen_path.write_bytes(before)
   evidence_dir=os.environ.get('MORNING_PERSISTENCE_EVIDENCE')
   if evidence_dir:
    evidence=pathlib.Path(evidence_dir)/('evidence_opt' if sys.flags.optimize else 'evidence_normal')
    shutil.copytree(root/'probe_outputs',evidence,dirs_exist_ok=True)
   # Reverse the factual availability without changing early source envelope: refuse.
   multi['sources']['synthetic1']['facts'][0]['available_at']='2026-11-09T07:01:00+08:00'
   with self.assertRaises(ValueError):persisted(reg,policy,docs,safe)
WORKER_SOURCE='"""Isolated synthetic probe only. Does not register, dispatch, send or authorize."""\nimport sys,json,pathlib,importlib.util,os\nroot=pathlib.Path(sys.argv[2]);request=json.loads(pathlib.Path(sys.argv[3]).read_text())\nentry=root/\'20261108_execution_increment/morning/registered.py\'\ns=importlib.util.spec_from_file_location(\'persist_probe\',entry);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);safe=m.module(\'safeio\')\ntry:\n reg=request[\'reg\'];policy=request[\'policy\'];docs={k:m.read(v,safe) for k,v in request[\'inputs\'].items()}\n if request.get(\'parent\'):\n  docs[\'freeze_parent\']=m.read(request[\'parent\'],safe)[\'result\'][\'lineage\']\n for name,ref in request.get(\'sections\',{}).items():\n  result=m.read(ref,safe)[\'result\'];docs[\'assembly_sections\'][name][\'content\']=result;docs[\'assembly_sections\'][name][\'status\']=result[\'status\']\n result=m.calculate(reg,policy,docs,safe)\n report={\'schema\':\'SYNTHETIC_PERSISTENCE_PROBE\',\'result\':result,\'node\':reg[\'node\'],\'cutoff\':reg[\'cutoff\'],\'production_allowed\':False}\n report[\'identity\']=m.sha(m.canonical(report));saved=safe.freeze(root/\'probe_outputs\',report)\n raw=pathlib.Path(saved[\'path\']).read_bytes();ref={\'path\':str(pathlib.Path(saved[\'path\']).relative_to(root)),\'sha256\':m.sha(raw),\'bytes\':len(raw)}\n print(json.dumps({\'pid\':os.getpid(),\'ref\':ref,\'saved\':saved,\'result\':result}))\nexcept ValueError as exc:\n print(json.dumps({\'pid\':os.getpid(),\'error\':str(exc)}));sys.exit(2)\n'
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':exec(WORKER_SOURCE)
 else:unittest.main()

