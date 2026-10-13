import copy, importlib.util, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
import unittest
import tempfile
P=Path(__file__).resolve().parents[1]/'prepare_history_batch.py'
spec=importlib.util.spec_from_file_location('prepare',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
HISTORY={'prior60':[f'202607{d:02}' for d in range(1,31)]+[f'202608{d:02}' for d in range(1,31)],'previous5':[f'202608{d:02}' for d in range(26,31)]}
# Deliberately fictional calendar passed to pure set tests, not actual market input.
class PreparationTests(unittest.TestCase):
 def artifact(self):return {'request':{'target_date':'20261014','signal_date':'20261013'},'research_observation':dict(strict=[],near=[],pending=[{'code':'HK.00001'},{'code':'HK.02825'}],excluded=[],screen_unresolved=[])}
 def test_pool_five_groups_exact_and_duplicates_rejected(self):
  a=self.artifact();self.assertEqual(m.members_from_saved(a),['HK.00001','HK.02825'])
  a['research_observation']['strict']=[{'code':'HK.00001'}]
  with self.assertRaises(ValueError):m.members_from_saved(a)
 def test_missing_exact_calendar_keys_not_last_available(self):
  members=['HK.00001','HK.02825'];rows=[(c,d) for c in members for d in HISTORY['prior60'] if (c,d)!=('HK.02825','20260830')]
  rows +=[(c,'20261013') for c in members]+[('HK.02825','20260630')]
  self.assertEqual(m.derive_missing_keys(rows,members,'20261013',HISTORY),[{'code':'HK.02825','date':'20260830'}])
 def test_target_omission_duplicate_and_extra_are_rejected(self):
  for rows in ([],[('HK.00001','20261013')]*2,[('HK.00001','20261013'),('HK.99999','20261013')]):
   with self.subTest(rows=rows),self.assertRaises(ValueError):m.derive_missing_keys(rows,['HK.00001'],'20261013',HISTORY)
 def test_duplicate_history_is_not_missing(self):
  rows=[('HK.00001','20261013'),('HK.00001','20260801'),('HK.00001','20260801')]
  with self.assertRaisesRegex(ValueError,'DUPLICATE_HISTORY'):m.derive_missing_keys(rows,['HK.00001'],'20261013',HISTORY)
 def test_calendar_requires_sixty_exact_dates(self):
  for h in ({'prior60':[],'previous5':[]},{'prior60':['20261013']*60,'previous5':['20261013']*5}):
   with self.assertRaises(ValueError):m.derive_missing_keys([],[],'20261013',h)
 def test_task_context_two_hour_expiry_and_canonical_keys(self):
  members=['HK.00001'];keys=[{'code':'HK.00001','date':'20260801'}];ref={'run_id':'a'*32};parent={'parent_panel_sha256':'b'*64}
  task,context=m.task_and_context(artifact=self.artifact(),reference=ref,parent=parent,members=members,keys=keys,files={},reuse=[],now=datetime(2026,10,13,18,tzinfo=timezone.utc))
  self.assertEqual(task['valid_until'],'2026-10-13T20:00:00.000000+00:00');self.assertEqual(context['keys'],keys)
  expected=hashlib.sha256(json.dumps(keys,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.assertEqual(task['keys_sha256'],expected)
 def test_output_must_be_separate_from_original_inputs(self):
  # macOS /tmp is normally a symlink; test physical paths without weakening
  # the production no-symlink rule or depending on a platform's temp alias.
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory).resolve();source=base/'source';good=base/'capture-preparation'
   self.assertEqual(m.require_separate_output(good,[source]),good)
   for p in (source,source/'new',base,Path('relative'),source/'..'/'new'):
    with self.subTest(path=str(p)),self.assertRaises(ValueError):m.require_separate_output(p,[source])
   link=base/'symlink-output';link.symlink_to(good)
   with self.assertRaisesRegex(ValueError,'OUTPUT_PATH'):m.require_separate_output(link,[source])
 def test_naive_preparation_clock_rejected(self):
  with self.assertRaises(ValueError):m.task_and_context(artifact=self.artifact(),reference={},parent={},members=[],keys=[],files={},reuse=[],now=datetime(2026,10,13))
if __name__=='__main__':unittest.main()
