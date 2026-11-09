"""Pure validators and early execution refusals; no collector/provider calls."""
import datetime as dt
import types
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
import capture
import bridge


class TimestampBoundary(unittest.TestCase):
    def case(self, node='hk-open'):
        stamp={'hk-open':'09:00:00','hk-continuous-close':'16:00:00','hk-auction-final':'16:09:00'}[node]
        value='2026-11-09T'+stamp+'+08:00'
        binding=types.SimpleNamespace(node=node,day='20261109',scope=('HK.00001',),source_reference='SYNTHETIC_ONLY',synthetic=True)
        doc=dict(schema='HK_OBSERVATION_V1',node=node,day='20261109',scope=['HK.00001'],source_reference='SYNTHETIC_ONLY',observed_at=value,available_at=value,actual_cas_end=value if node=='hk-auction-final' else None,rows=[dict(symbol='HK.00001',observation='SYNTHETIC ONLY')],data_kind='SYNTHETIC_TEST')
        now=dt.datetime(2026,11,9,17,tzinfo=dt.timezone(dt.timedelta(hours=8)))
        return binding,doc,now

    def test_late_submicrosecond_hk09_available_time_is_refused(self):
        b,x,now=self.case();x['available_at']='2026-11-09T09:00:00.0000001+08:00'
        with self.assertRaises(ValueError):capture.validate(b,x,now)

    def test_submicrosecond_observation_and_cas_are_refused(self):
        for node,field,value in [('hk-open','observed_at','09:00:00.0000001'),('hk-continuous-close','observed_at','16:00:00.0000001'),('hk-auction-final','actual_cas_end','16:10:00.0000001')]:
            with self.subTest(node=node,field=field):
                b,x,now=self.case(node);x[field]='2026-11-09T'+value+'+08:00'
                if node=='hk-auction-final':
                    x['observed_at']='2026-11-09T16:10:01+08:00';x['available_at']=x['observed_at']
                with self.assertRaises(ValueError):capture.validate(b,x,now)

    def test_fractional_zero_offset_must_not_be_silently_lost(self):
        for offset in ['+00:00:00.000001','-00:00:00.000001']:
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):capture.stamp('2026-11-09T01:00:00'+offset)

    def test_submicrosecond_offset_is_refused(self):
        for offset in ['+08:00:00.0000001','-00:00:00.0000001']:
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):capture.stamp('2026-11-09T09:00:00'+offset)

    def test_exact_hk09_boundary_and_three_nodes_still_validate(self):
        for node in ['hk-open','hk-continuous-close','hk-auction-final']:
            with self.subTest(node=node):self.assertEqual(capture.validate(*self.case(node)),[])

    def test_supported_microseconds_and_utc_offsets_preserve_instant(self):
        self.assertEqual(capture.stamp('2026-11-09T01:00:00.123456Z').isoformat(),'2026-11-09T09:00:00.123456+08:00')
        self.assertEqual(capture.stamp('2026-11-09T09:00:01+08:00:01').isoformat(),'2026-11-09T09:00:00+08:00')

    def test_one_microsecond_late_stays_refused(self):
        b,x,now=self.case();x['available_at']='2026-11-09T09:00:00.000001+08:00'
        with self.assertRaises(ValueError):capture.validate(b,x,now)

    def test_empty_registry_still_blocks(self):
        self.assertEqual(bridge.dispatch('hk-open','UNREGISTERED')['reason'],'TRUSTED_RUN_NOT_REGISTERED')

    def test_bridge_does_not_execute_an_ambient_capture_module(self):
        poison=types.ModuleType('capture');poison.execute=lambda b:dict(status='AMBIENT_MODULE_EXECUTED')
        binding=types.SimpleNamespace(node='hk-open',scope=())
        with patch.dict(sys.modules,{'capture':poison}),patch.object(bridge,'TRUSTED_RUNS',{'synthetic':binding}):
            result=bridge.dispatch('hk-open','synthetic')
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['reason'],'SCOPE_INVALID')

    def test_bridge_refuses_changed_capture_before_execution(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root)/'capture.py').write_text("raise RuntimeError('MUST_NOT_EXECUTE')\n")
            binding=types.SimpleNamespace(node='hk-open',scope=())
            with patch.object(bridge,'HERE',Path(root)),patch.object(bridge,'TRUSTED_RUNS',{'synthetic':binding}):
                result=bridge.dispatch('hk-open','synthetic')
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['reason'],'CAPTURE_CODE_CHANGED')


if __name__=='__main__':unittest.main()
