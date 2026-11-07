import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import material_pack as m
class Races(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name);self.root=self.base/'root';self.root.mkdir();self.secret=self.base/'outside';self.secret.write_bytes(b'OUTSIDE');(self.root/'safe').write_bytes(b'INSIDE')
 def test_v1_check_then_open_counterexample(self):
  # Reproduce V1's check/read split, retained here without importing V1.
  target=self.root/'safe';self.assertFalse(target.is_symlink());self.assertTrue(target.is_file());target.stat()
  target.unlink();target.symlink_to(self.secret)
  self.assertEqual(target.read_bytes(),b'OUTSIDE')
 def test_leaf_swap_before_open_is_rejected(self):
  original=os.open
  def racing(path,*a,**k):
   if path=='safe':
    p=self.root/'safe';p.unlink();p.symlink_to(self.secret)
   return original(path,*a,**k)
  with patch.object(m.os,'open',side_effect=racing):
   with self.assertRaises((OSError,ValueError)):m.local_bytes(self.root,'safe')
 def test_directory_swap_after_open_reads_original_fd(self):
  sub=self.root/'sub';sub.mkdir();(sub/'safe').write_bytes(b'INSIDE');outside=self.base/'other';outside.mkdir();(outside/'safe').write_bytes(b'OUTSIDE');original=os.open
  def racing(path,*a,**k):
   fd=original(path,*a,**k)
   if path=='sub':
    sub.rename(self.root/'kept');sub.symlink_to(outside,target_is_directory=True)
   return fd
  with patch.object(m.os,'open',side_effect=racing):self.assertEqual(m.local_bytes(self.root,'sub/safe'),b'INSIDE')
 def test_root_symlink_rejected(self):
  alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True)
  with self.assertRaises((OSError,ValueError)):m.local_bytes(alias,'safe')
 def test_fifo_rejected_without_block(self):
  os.mkfifo(self.root/'fifo')
  with self.assertRaises((OSError,ValueError)):m.local_bytes(self.root,'fifo')
 def test_size_cap(self):
  with patch.object(m,'MAX_BYTES',3):
   with self.assertRaises(ValueError):m.local_bytes(self.root,'safe')
 def test_directory_swap_before_open_is_rejected(self):
  sub=self.root/'sub';sub.mkdir();(sub/'safe').write_bytes(b'INSIDE');outside=self.base/'other';outside.mkdir();(outside/'safe').write_bytes(b'OUTSIDE');original=os.open
  def racing(path,*a,**k):
   if path=='sub':
    sub.rename(self.root/'kept');sub.symlink_to(outside,target_is_directory=True)
   return original(path,*a,**k)
  with patch.object(m.os,'open',side_effect=racing):
   with self.assertRaises((OSError,ValueError)):m.local_bytes(self.root,'sub/safe')
 def test_output_folder_swap_is_rejected(self):
  import datetime as dt
  report=m.assemble(self.root,'night','2026-11-07',[],dt.datetime(2026,11,7,tzinfo=dt.timezone.utc));out=self.base/'out';other=self.base/'other';other.mkdir();original=os.open
  def racing(path,*a,**k):
   if path==report['identity']:
    folder=out/path;folder.rename(out/'kept');folder.symlink_to(other,target_is_directory=True)
   return original(path,*a,**k)
  with patch.object(m.os,'open',side_effect=racing):
   with self.assertRaises((OSError,ValueError)):m.freeze(out,report)
  self.assertEqual(list(other.iterdir()),[])
 def test_growth_after_fstat_is_bounded(self):
  original=os.read;total=[];changed=[]
  def grow(fd,n):
   if not changed:
    with (self.root/'safe').open('ab') as f:f.write(b'X'*1000)
    changed.append(True)
   data=original(fd,n);total.append(len(data));return data
  with patch.object(m,'MAX_BYTES',8),patch.object(m.os,'read',side_effect=grow):
   with self.assertRaises(ValueError):m.local_bytes(self.root,'safe')
  self.assertLessEqual(sum(total),9)
 def test_growth_still_under_cap_is_not_stable(self):
  original=os.read;changed=[]
  def grow(fd,n):
   if not changed:
    with (self.root/'safe').open('ab') as f:f.write(b'X')
    changed.append(True)
   return original(fd,n)
  with patch.object(m.os,'read',side_effect=grow):
   with self.assertRaisesRegex(ValueError,'FILE_CHANGED_DURING_READ'):m.local_bytes(self.root,'safe')
if __name__=='__main__':unittest.main()
