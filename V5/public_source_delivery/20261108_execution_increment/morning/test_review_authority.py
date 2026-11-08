import ast,inspect,unittest
import registered as r
class ReviewAuthority(unittest.TestCase):
 def test_freeze_return_flags_are_literal_false(self):
  tree=ast.parse(inspect.getsource(r.calculate));branch=tree.body[0].body[1]
  flags=[]
  for node in ast.walk(branch):
   if isinstance(node,ast.Dict):
    for k,v in zip(node.keys,node.values):
     if isinstance(k,ast.Constant) and k.value=='formal_freeze':flags.append(v)
  self.assertEqual(len(flags),2)
  self.assertTrue(all(isinstance(v,ast.Constant) and v.value is False for v in flags))
 def test_no_registration_or_production_job(self):
  self.assertEqual(r.TRUSTED_RUNS,());out=r.dispatch('freeze','production','production',None);self.assertEqual(out['status'],'BLOCKED_NO_TRUSTED_REGISTRATION');self.assertEqual(out['jobs_started'],0)
if __name__=='__main__':unittest.main()
