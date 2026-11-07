import unittest,tempfile,subprocess,sys,json,hashlib
from pathlib import Path
from render import render

def fixture():
 return dict(natural_verified=False,business_accepted=False,new_selection=False,buy_decision=False,matched_symbols=1,unmatched_symbols=199,top200_denominator=200,mention_lines=1,title='SYNTHETIC <brief>',status='HISTORICAL SYNTHETIC ONLY',prepared_date='2000-01-03',timing_note='Published after cutoff cannot be backfilled; source timezone UNKNOWN.',themes=[dict(title='SYNTHETIC',summary='<not original text>',lines='1',source_file='synthetic.txt')],sources=[dict(file='synthetic.txt',url='https://example.invalid/synthetic',published_time_raw='2000-01-02T09:00:00')],preview_rule='Original rank retained, not new selection',matched_preview=[dict(name='SYNTHETIC',symbol='NOT_A_REAL_SYMBOL',original_top200_rank=1)],gaps=['identity UNKNOWN','natural NOT VERIFIED'])
class Tests(unittest.TestCase):
 def test_historical_escaping_and_time_preserved(self):
  md,ht=render(fixture());self.assertIn('HISTORICAL SYNTHETIC ONLY',md);self.assertIn('2000-01-02T09:00:00',md);self.assertIn('timezone UNKNOWN',md);self.assertIn('&lt;not original text&gt;',ht);self.assertIn('identity UNKNOWN',md)
 def test_no_acceptance_escalation(self):
  for key in ['natural_verified','business_accepted','new_selection','buy_decision']:
   d=fixture();d[key]=True
   with self.assertRaisesRegex(ValueError,'HISTORICAL_SCOPE_ONLY'):render(d)
 def test_denominator(self):
  d=fixture();d['unmatched_symbols']=198
  with self.assertRaisesRegex(ValueError,'DENOMINATOR'):render(d)
 def test_missing_source_ref(self):
  d=fixture();d['themes'][0]['source_file']='missing'
  with self.assertRaises(KeyError):render(d)
 def test_cli_hash_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);f=p/'synthetic.json';f.write_text(json.dumps(fixture()));out=p/'out';cmd=[sys.executable,str(Path(__file__).with_name('render.py')),'--input',str(f),'--sha256','0'*64,'--out',str(out)]
   r=subprocess.run(cmd,capture_output=True);self.assertEqual(r.returncode,2);self.assertFalse(out.exists())
   cmd=[sys.executable,str(Path(__file__).with_name('render.py')),'--input',str(f),'--sha256',hashlib.sha256(f.read_bytes()).hexdigest(),'--out',str(out)]
   r=subprocess.run(cmd,capture_output=True);self.assertEqual(r.returncode,0,r.stderr);before=(out/'BRIEF.md').read_bytes();r=subprocess.run(cmd,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertEqual(before,(out/'BRIEF.md').read_bytes())
 def test_no_default_private_input(self):
  r=subprocess.run([sys.executable,str(Path(__file__).with_name('render.py'))],capture_output=True);self.assertEqual(r.returncode,2)
if __name__=='__main__':unittest.main()
