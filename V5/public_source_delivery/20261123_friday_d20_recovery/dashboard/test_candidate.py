import hashlib
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
import candidate

class TestFriday(unittest.TestCase):
    def test_day_source_pinned_and_tamper_rejected(self):
        rows=candidate.friday_rows()
        self.assertEqual((len(rows),rows[0]['symbol'],rows[0]['change']),(200,'300812.SZ','20.00'))
        with TemporaryDirectory() as td:
            p=Path(td)/'bad.json';p.write_bytes(candidate.TOP.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'SOURCE_PIN'):
                candidate.friday_rows(p)
            p.unlink();p.symlink_to(candidate.TOP)
            with self.assertRaisesRegex(ValueError,'SOURCE_SYMLINK'):
                candidate.friday_rows(p)
    def test_http_exact_day_no_old_new_bleed(self):
        b=candidate.build_preview()
        with b.server(0) as s:
            th=threading.Thread(target=s.serve_forever,daemon=True);th.start()
            def get(path,method='GET'):
                c=http.client.HTTPConnection('127.0.0.1',s.server_port,timeout=4)
                try:
                    c.request(method,path);r=c.getresponse();return r.status,r.read()
                finally:c.close()
            try:
                endpoint='/api/reconstructed-board?business_date='
                st,data=get(endpoint+'20261120');v=json.loads(data)
                self.assertEqual((st,len(v['nodes']),v['historical_top200']),(200,21,candidate.friday_rows()))
                self.assertFalse(v['formal_admission']);self.assertFalse(v['live'])
                self.assertIsNone(v['chart']);self.assertIsNone(v['groups'])
                baseline={}
                baseline.update(__file__=str(candidate.BASE),__name__='pinned_board_baseline')
                exec(compile(candidate.pinned(candidate.BASE,candidate.BASE_SHA),str(candidate.BASE),'exec'),baseline)
                st,data=get(endpoint+'20261119');self.assertEqual((st,json.loads(data)),(200,baseline['project']('20261119')))
                self.assertEqual(get(endpoint+'20261123')[0],422)
                self.assertEqual(get(endpoint+'20261120&business_date=20261119')[0],422)
                self.assertEqual(get('/research-system/', 'POST')[0],405)
                st,html=get('/research-system/');self.assertEqual(st,200);self.assertIn(b'300812.SZ',html)
                self.assertEqual(hashlib.sha256(html).hexdigest(),hashlib.sha256(b.render()).hexdigest())
            finally:s.shutdown();th.join(3);self.assertFalse(th.is_alive())
        with self.assertRaises(ValueError): b.server(8785)
if __name__=='__main__': unittest.main()
