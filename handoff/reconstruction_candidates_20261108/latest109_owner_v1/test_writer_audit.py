import pathlib,tempfile,unittest,hashlib
import isolated_owner as owner
class WriterAuditTests(unittest.TestCase):
 def test_partial_objects_are_unknown_not_retryable(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'field_rows.parquet').write_bytes(b'partial')
   r=owner.inspect_writer_failure(p)
   self.assertEqual(r['state'],'UNKNOWN_RECONCILE_NO_RETRY')
   self.assertEqual(r['objects']['field_rows.parquet']['sha256'],hashlib.sha256(b'partial').hexdigest())
   self.assertEqual(r['objects']['row_metadata.parquet']['state'],'ABSENT')
 def test_receipt_does_not_prove_success(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)
   for n in ('field_rows.parquet','row_metadata.parquet','RECEIPT.json'):(p/n).write_bytes(b'x')
   self.assertEqual(owner.inspect_writer_failure(p)['state'],'UNKNOWN_RECONCILE_NO_RETRY')
 def test_symlink_not_read(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'RECEIPT.json').symlink_to('/not/available')
   self.assertEqual(owner.inspect_writer_failure(p)['objects']['RECEIPT.json']['state'],'UNKNOWN')
 def test_pending_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);q=p/'.row_metadata.parquet.pending';q.write_bytes(b'pending')
   r=owner.inspect_writer_failure(p)
   self.assertEqual(r['objects'][q.name]['bytes'],7);self.assertEqual(q.read_bytes(),b'pending')
if __name__=='__main__':unittest.main()
