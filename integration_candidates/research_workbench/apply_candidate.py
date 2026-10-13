"""Apply only this candidate's exact changes to an explicitly supplied isolated V5 checkout.
Never invoke against the active release or V4. Emits changed-file hashes for review.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent

def once(s,old,new):
 if '\r\n' in s:
  old=old.replace('\r\n','\n').replace('\n','\r\n');new=new.replace('\r\n','\n').replace('\n','\r\n')
 if s.count(old)!=1:raise ValueError('PREIMAGE_ANCHOR_COUNT:'+old[:90])
 return s.replace(old,new,1)

def transforms(files):
 out=dict(files)
 main='frontend/src/main.ts'
 out[main]=once(out[main],"const app = view === 'legacy' ? import('./App.vue') : import('./views/SavedManagerResultView.vue');", "const app = view === 'research' ? import('./research-workbench/Root.vue')\n  : view === 'legacy' ? import('./App.vue') : import('./views/SavedManagerResultView.vue');")
 vite='frontend/vite.config.ts'
 out[vite]=once(out[vite],"if (sourceTarget) {","if (sourceTarget) {\n proxy['/api/v5/research/lane'] = readonlyProxy(sourceTarget);\n proxy['/api/v5/research/wechat/materials'] = readonlyProxy(sourceTarget);")
 view='frontend/src/views/SavedManagerResultView.vue'
 out[view]=once(out[view],'<button type="button" disabled>研报决策台 · 未接入</button>','<a class="entry-nav-link" href="?view=research">研报决策台</a>')
 api='V5/src/v5_shadow/module_api.py';s=out[api]
 s=once(s,"    exact_keys(value, keys)","    if isinstance(value, dict) and 'm04_research_lane_binding' in value:\n        keys += ('m04_research_lane_binding',)\n    exact_keys(value, keys)\n    if 'm04_research_lane_binding' in value:\n        from .research_workbench_readonly import validate_binding\n        validate_binding(value)")
 anchor="            heavy = heavy or (config['module_id']=='source_bundle' and parsed.path==M17_ROUTE)"
 s=once(s,anchor,anchor+"\n            research_path = config['module_id']=='source_bundle' and parsed.path in ('/api/v5/research/lane','/api/v5/research/wechat/materials')\n            heavy = heavy or research_path")
 anchor="            if heavy and not reader_slot.acquire(blocking=False):"
 s=once(s,anchor,"            if research_path:\n                reader_slot=m04_read_slot\n"+anchor)
 anchor="                if parsed.path == M18_ROUTE + '/pages':"
 s=once(s,anchor,"                if research_path:\n                    from .research_workbench_readonly import response\n                    status,payload=response(config,parsed.path,query)\n                    self.reply(status,payload,sha256_json(payload))\n                elif parsed.path == M18_ROUTE + '/pages':")
 s=once(s,"            except FileNotFoundError:self.error(503,'MODULE_RESULT_NOT_AVAILABLE')","            except TimeoutError:self.error(503,'RESEARCH_READER_TIMEOUT')\n            except FileNotFoundError:self.error(503,'MODULE_RESULT_NOT_AVAILABLE')")
 out[api]=s
 p='frontend/src/views/SavedManagerResultView.navigation.spec.ts'
 out[p]=once(out[p],"expect(screen.getByText('研报决策台 · 未接入')).toHaveProperty('disabled', true);", "expect(screen.getByRole('link',{name:'研报决策台'}).getAttribute('href')).toBe('?view=research');")
 p='frontend/src/views/SavedManagerResultView.spec.ts'
 out[p]=once(out[p],"expect(screen.queryByRole('link')).toBeNull();", "expect(screen.getByRole('link',{name:'研报决策台'}).getAttribute('href')).toBe('?view=research');")
 return out
PATHS=['frontend/src/main.ts','frontend/vite.config.ts','frontend/src/views/SavedManagerResultView.vue','V5/src/v5_shadow/module_api.py','frontend/src/views/SavedManagerResultView.navigation.spec.ts','frontend/src/views/SavedManagerResultView.spec.ts']
def validate_preimages(files,expected):
 for name,digest in expected.items():
  if name not in files or hashlib.sha256(files[name].encode()).hexdigest()!=digest:raise ValueError('UNKNOWN_MAC_PREIMAGE:'+name)

def apply(root):
 if (root/"frontend/src/research-workbench").exists():raise ValueError("RESEARCH_NAMESPACE_ALREADY_EXISTS")
 files={p:(root/p).read_bytes().decode('utf-8') for p in PATHS}
 validate_preimages(files,json.loads((HERE/'MAC_OBSERVED_PREIMAGE.json').read_bytes())['files'])
 out=transforms(files)
 # Prepare every transformation before writing. No reset, whole-tree copy or config mutation.
 receipt={p:{'before':hashlib.sha256(files[p].encode()).hexdigest(),'after':hashlib.sha256(out[p].encode()).hexdigest()} for p in PATHS}
 for p,text in out.items():(root/p).write_bytes(text.encode())
 dst=root/'frontend/src/research-workbench'
 if dst.exists():raise ValueError('RESEARCH_NAMESPACE_ALREADY_EXISTS')
 shutil.copytree(HERE/'frontend/src/research-workbench',dst)
 shutil.copy2(HERE/'bridge/research_workbench_readonly.py',root/'V5/src/v5_shadow/research_workbench_readonly.py')
 return receipt
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--isolated-checkout',required=True);args=parser.parse_args();print(json.dumps(apply(Path(args.isolated_checkout).resolve()),indent=2))
