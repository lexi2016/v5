"""Run the manifest-bound original factory, owner, provider, parser, store, APIs.
All documents and observations are synthetic; no business/PIT acceptance claimed.
"""
import asyncio
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import socket
import tempfile
from threading import Event
import unittest
from unittest.mock import patch
import urllib.request

import httpx
from v5_shadow.m16_runtime import closure, create_app, PinnedObservationReader
from v5_shadow.manager_loader import load_owner
from support import DATE, CODE, OfflineTransport, offline_error, observation, write_input, wait_terminal, file_snapshot, pdf_bytes


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_owner(closure())
        cls.hkex = importlib.import_module('m16_owner_manager_research.hkex_provider')
        cls.pdf = importlib.import_module('m16_owner_manager_research.pdf_parser')
        cls.contracts = importlib.import_module('m16_owner_manager_research.contracts')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.network_calls = []
        def forbid(*args, **kwargs):
            self.network_calls.append(True)
            raise AssertionError('NETWORK_FORBIDDEN')
        for target in ['socket.create_connection', 'socket.socket.connect', 'urllib.request.urlopen', 'urllib.request.OpenerDirector.open']:
            p = patch(target, forbid); p.start(); self.addCleanup(p.stop)
        self.transport = OfflineTransport()
        for name in ['_default_transport', '_default_eastmoney_hk_transport']:
            p = patch.object(self.hkex, name, return_value=self.transport); p.start(); self.addCleanup(p.stop)
        self.path, self.digest = write_input(self.root)
        self.app = self.make_app()
        self.jobs = self.app.state.manager_jobs

    def tearDown(self):
        self.assertEqual(self.network_calls, [])

    def make_app(self, *, producer=True, runtime=None, input_path='default', digest='default'):
        app = create_app(runtime_root=runtime or self.root / 'runtime',
                         input_path=self.path if input_path == 'default' else input_path,
                         input_sha256=self.digest if digest == 'default' else digest,
                         producer_enabled=producer)
        service = app.state.manager_jobs._service
        # Inject only original transport/reader ports, not a substitute owner/provider.
        event_source = importlib.import_module('m16_owner_manager_research.event_source')
        service.source_provider._event_media_transport = event_source.BoundedMediaTransport(transport=offline_error)
        service.reader_fetcher = offline_error
        self.addCleanup(service.close)
        self.addCleanup(lambda: [f.result(timeout=8) for f in list(service._active.values())])
        return app

    def request(self, method, path, *, app=None, **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app or self.app), base_url='http://test') as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(run())

    def produce(self):
        r = self.jobs.ensure(DATE)
        self.assertEqual(r['status'], 'QUEUED', r)
        job = wait_terminal(self.jobs, r['job']['job_id'])
        self.assertNotEqual(job['status'], 'FAILED', job)
        return self.jobs.get(DATE)

    def test_original_four_classes_are_used(self):
        s = self.jobs._service
        self.assertEqual(type(s).__module__, 'm16_owner_manager_research.service')
        self.assertEqual(type(s.source_provider).__module__, 'm16_owner_manager_research.hkex_provider')
        self.assertIs(s._material_store, s.source_provider._material_store)

    def test_get_never_submits_or_writes(self):
        before = file_snapshot(self.root)
        for route in ['', '/status']:
            r = self.request('GET', '/api/v4/manager/research' + route + '?date=' + DATE)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['status'], 'NOT_MATERIALIZED')
        self.assertEqual(before, file_snapshot(self.root))
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.jobs._service._active, {})

    def test_producer_defaults_read_only(self):
        app = self.make_app(producer=False, runtime=self.root / 'readonly')
        before = file_snapshot(self.root)
        r = self.request('POST', '/api/v4/manager/research/ensure?date=' + DATE, app=app)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()['detail'], 'M16_PRODUCER_DISABLED')
        self.assertEqual(before, file_snapshot(self.root))

    def test_actual_pdf_provider_job_commit_and_cold_read(self):
        result = self.produce()
        self.assertIsNotNone(result['product'], result)
        row = result['product']['rows'][0]
        self.assertTrue(row['facts'], row)
        self.assertEqual(row['source']['sha256'], sha256(self.transport.document).hexdigest())
        self.assertFalse(result['production_allowed'])
        self.assertFalse(result['orders_sent'])
        self.assertFalse(result['buy_gate_updated'])
        before = file_snapshot(self.root)
        cold = self.make_app()
        self.assertEqual(cold.state.manager_jobs.get(DATE)['product'], result['product'])
        self.assertEqual(before, file_snapshot(self.root))

    def test_exact_ensure_deduplicates_saved_result(self):
        first = self.produce(); count = len(self.transport.calls)
        again = self.jobs.ensure(DATE)
        self.assertEqual(again['job']['generation'], first['job']['generation'])
        self.assertEqual(len(self.transport.calls), count)

    def test_retry_uses_same_job_and_new_generation(self):
        first = self.produce(); r = self.jobs.retry(DATE)
        self.assertEqual(r['job']['job_id'], first['job']['job_id'])
        self.assertNotEqual(r['job']['generation'], first['job']['generation'])
        self.assertEqual(r['job']['attempt'], 2)
        self.assertNotEqual(wait_terminal(self.jobs, r['job']['job_id'])['status'], 'FAILED')

    def test_events_preserve_financial_document_and_do_not_fetch_pdf(self):
        first = self.produce(); count = sum(u.endswith('.pdf') for u, _ in self.transport.calls)
        refreshed = self.jobs.ensure_events(DATE, force=True)
        self.assertEqual(refreshed['status'], 'QUEUED')
        done = wait_terminal(self.jobs, refreshed['job']['job_id'])
        self.assertNotEqual(done['status'], 'FAILED', done)
        current = self.jobs.get(DATE)['product']
        self.assertEqual(current['rows'][0]['facts'], first['product']['rows'][0]['facts'])
        self.assertEqual(current['rows'][0]['source'], first['product']['rows'][0]['source'])
        self.assertEqual(sum(u.endswith('.pdf') for u, _ in self.transport.calls), count)

    def test_events_before_financial_result_do_not_create_job(self):
        before = file_snapshot(self.root)
        result = self.jobs.ensure_events(DATE, force=True)
        self.assertIn('FINANCIAL_PRODUCT_NOT_MATERIALIZED', result['cannot_confirm'])
        self.assertEqual(before, file_snapshot(self.root))

    def test_cancel_wins_over_late_transport(self):
        self.transport.block_started = Event(); self.transport.release = Event()
        self.addCleanup(self.transport.release.set)
        result = self.jobs.ensure(DATE); job_id = result['job']['job_id']
        self.assertTrue(self.transport.block_started.wait(2))
        self.assertEqual(self.jobs.cancel(job_id, DATE)['status'], 'CANCELLED')
        self.transport.release.set()
        self.assertEqual(wait_terminal(self.jobs, job_id)['status'], 'CANCELLED')
        self.assertIsNone(self.jobs.get(DATE)['product'])
        self.assertEqual(self.jobs.job(job_id, DATE)['status'], 'CANCELLED')

    def test_running_ensure_deduplicates_and_read_is_nonblocking(self):
        self.transport.block_started = Event(); self.transport.release = Event()
        self.addCleanup(self.transport.release.set)
        first = self.jobs.ensure(DATE)
        self.assertTrue(self.transport.block_started.wait(2))
        other = self.jobs.ensure(DATE)
        self.assertEqual(other['job']['generation'], first['job']['generation'])
        r = self.request('GET', '/api/v4/manager/research/status?date=' + DATE)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'RUNNING')
        self.transport.release.set(); wait_terminal(self.jobs, first['job']['job_id'])

    def test_failed_provider_is_visible_and_retry_recovers(self):
        self.transport.fail = True
        first = self.produce()
        self.assertEqual(first['product']['rows'][0]['status'], 'CANNOT_CONFIRM')
        self.transport.fail = False
        r = self.jobs.retry(DATE); wait_terminal(self.jobs, r['job']['job_id'])
        self.assertTrue(self.jobs.get(DATE)['product']['rows'][0]['facts'])

    def test_closed_service_refuses_new_jobs(self):
        self.jobs.close()
        self.assertIn('SERVICE_CLOSED', self.jobs.ensure(DATE)['cannot_confirm'])

    def test_changed_input_bytes_fail_closed_without_writes(self):
        self.path.write_text('{}')
        before = file_snapshot(self.root)
        r = self.jobs.ensure(DATE)
        self.assertEqual(r['status'], 'CANNOT_CONFIRM')
        self.assertIn('M16_INPUT_BYTES_CHANGED', r['cannot_confirm'])
        self.assertEqual(before, file_snapshot(self.root))

    def test_wrong_date_and_post_cutoff_input_fail_closed(self):
        self.assertEqual(self.jobs.ensure('20260909')['status'], 'CANNOT_CONFIRM')
        value = observation(); value['rows'][0]['source_last_bar_time'] = '2026-09-08 09:41:00'
        p, digest = write_input(self.root, value)
        app = self.make_app(runtime=self.root / 'late', input_path=p, digest=digest)
        self.assertEqual(app.state.manager_jobs.ensure(DATE)['status'], 'CANNOT_CONFIRM')
        self.assertEqual(self.transport.calls, [])

    def test_no_input_binding_cannot_create_job(self):
        app = self.make_app(runtime=self.root / 'unbound', input_path=None, digest=None)
        before = file_snapshot(self.root)
        result = app.state.manager_jobs.ensure(DATE)
        self.assertIn('STAGE_OBSERVATION_NOT_MATERIALIZED', result['cannot_confirm'])
        self.assertEqual(before, file_snapshot(self.root))

    def test_client_body_and_cross_origin_refused(self):
        for method in ['ensure', 'retry', 'events']:
            route = '/api/v4/manager/research/' + method + '?date=' + DATE
            self.assertEqual(self.request('POST', route, content=b'{"symbols":[]}').status_code, 422)
            self.assertEqual(self.request('POST', route, headers={'origin': 'https://evil.invalid'}).status_code, 403)
        self.assertEqual(self.transport.calls, [])

    def test_dates_required_and_real(self):
        for date in ['', '?date=2026-09-08', '?date=20260230']:
            self.assertEqual(self.request('GET', '/api/v4/manager/research' + date).status_code, 422)
        self.assertEqual(self.transport.calls, [])

    def test_no_other_module_routes_exposed(self):
        paths = set(self.app.openapi()['paths'])
        prefix = '/api/v4/manager/research'
        self.assertEqual(paths, {prefix + x for x in ['', '/status', '/ensure', '/retry', '/events', '/jobs/{job_id}', '/jobs/{job_id}/cancel']})

    def test_job_wrong_date_and_unknown_return_not_found(self):
        r = self.produce(); job = r['job']['job_id']
        self.assertIsNone(self.jobs.job(job, '20260909'))
        self.assertIsNone(self.jobs.cancel(job, '20260909'))
        response = self.request('GET', '/api/v4/manager/research/jobs/not-found?date=' + DATE)
        self.assertEqual(response.status_code, 404)

    def test_pdf_parser_extracts_actual_synthetic_bytes(self):
        facts, pages = self.pdf.extract_pdf_facts(pdf_bytes())
        self.assertTrue(pages)
        self.assertTrue(facts)
        self.assertEqual(facts[0]['page'], 1)
        self.assertIn('Revenue', facts[0]['source_excerpt'])

    def test_pdf_budget_and_invalid_bytes(self):
        self.assertEqual(self.pdf.extract_pdf_facts(b'not a PDF'), ([], []))
        with self.assertRaises(self.pdf.PdfParseError):
            self.pdf.extract_pdf_pages(pdf_bytes(), max_bytes=10)

    def test_provider_future_publication_refused(self):
        self.transport.published = '08/09/2026 09:41'
        r = self.jobs._service.source_provider.collect(target_trade_date=DATE,
              cutoff_at=self.contracts.cutoff_at(DATE), observation=observation()['rows'][0])
        self.assertEqual(r['reason'], 'NO_QUALIFYING_ANNOUNCEMENT')
        self.assertFalse(any(u.endswith('.pdf') for u, _ in self.transport.calls))

    def test_provider_wrong_cutoff_and_arbitrary_url_refused(self):
        with self.assertRaises(self.contracts.ContractError):
            self.jobs._service.source_provider.collect(target_trade_date=DATE, cutoff_at='wrong', observation=observation()['rows'][0])
        with self.assertRaises(self.hkex.ProviderError):
            self.jobs._service.source_provider._request('https://evil.invalid/p.pdf')
        self.assertEqual(self.transport.calls, [])


    def test_receipt_failure_keeps_previous_committed_product(self):
        first = self.produce()
        old = first['product']
        with patch.object(self.jobs._service.store, 'write_receipt', side_effect=OSError('fixture receipt failed')):
            r = self.jobs.retry(DATE)
            done = wait_terminal(self.jobs, r['job']['job_id'])
        self.assertEqual(done['status'], 'FAILED')
        current = self.jobs.get(DATE)
        self.assertEqual(current['status'], 'FAILED')
        self.assertEqual(current['product'], old)
        again = self.jobs.retry(DATE)
        self.assertNotEqual(wait_terminal(self.jobs, again['job']['job_id'])['status'], 'FAILED')

    def test_unowned_active_generation_is_not_silently_restarted(self):
        self.transport.block_started = Event(); self.transport.release = Event()
        self.addCleanup(self.transport.release.set)
        result = self.jobs.ensure(DATE); job_id = result['job']['job_id']
        self.assertTrue(self.transport.block_started.wait(2))
        other = self.make_app().state.manager_jobs
        before = file_snapshot(self.root)
        self.assertIn('JOB_OWNER_UNCONFIRMED', other.get(DATE)['cannot_confirm'])
        self.assertIn('JOB_OWNER_UNCONFIRMED', other.retry(DATE)['cannot_confirm'])
        self.assertEqual(before, file_snapshot(self.root))
        # Explicit cancel fences the old generation. A retry is then ordinary owner behavior.
        self.assertEqual(other.cancel(job_id, DATE)['status'], 'CANCELLED')
        self.transport.release.set(); wait_terminal(self.jobs, job_id)
        retry = other.retry(DATE)
        self.assertNotEqual(retry['job']['generation'], result['job']['generation'])
        self.assertNotEqual(wait_terminal(other, job_id)['status'], 'FAILED')

    def test_new_process_cold_reads_same_committed_product(self):
        import os, subprocess, sys
        first = self.produce()
        expected = sha256(json.dumps(first['product'], sort_keys=True).encode()).hexdigest()
        script = """import sys,json,hashlib,socket
from pathlib import Path
from v5_shadow.m16_runtime import create_app
def no_network(*a,**kw): raise AssertionError('NETWORK_FORBIDDEN')
socket.socket.connect=no_network
app=create_app(runtime_root=Path(sys.argv[1]),input_path=Path(sys.argv[2]),input_sha256=sys.argv[3])
try:
 print(hashlib.sha256(json.dumps(app.state.manager_jobs.get(sys.argv[4])['product'],sort_keys=True).encode()).hexdigest())
finally: app.state.manager_jobs.close()
"""
        before = file_snapshot(self.root)
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.root/'runtime'), str(self.path), self.digest, DATE], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)
        self.assertEqual(before, file_snapshot(self.root))

    def test_default_main_starts_single_loopback_app_without_submitting(self):
        from v5_shadow.m16_runtime import main
        with patch('uvicorn.run') as run:
            self.assertEqual(main(['--runtime-root', str(self.root/'cli')]), 0)
        app = run.call_args.args[0]
        self.assertFalse(app.state.producer_enabled)
        self.assertEqual(run.call_args.kwargs['host'], '127.0.0.1')
        self.assertTrue(app.state.manager_jobs._service._closed)
        self.assertEqual(self.transport.calls, [])

    def test_observation_path_validation(self):
        for path, digest in [(Path('relative'), self.digest), (self.path, None), (None, self.digest), (self.path, 'bad')]:
            with self.assertRaises(ValueError): PinnedObservationReader(path, digest)
        link = self.root/'link.json'; link.symlink_to(self.path)
        reader = PinnedObservationReader(link, self.digest)
        with self.assertRaises(self.contracts.ContractError): reader.read(DATE)

    def test_runtime_rejects_changed_dependency_manifest_pin(self):
        from v5_shadow import m16_runtime
        self.assertTrue(hasattr(m16_runtime, 'DEPENDENCY_MANIFEST_SHA256'), 'Dependency supplement is not pinned by startup')
        with patch.object(m16_runtime, 'DEPENDENCY_MANIFEST_SHA256', '0'*64):
            with self.assertRaisesRegex(ValueError, 'DEPENDENCY_MANIFEST_HASH'):
                m16_runtime.closure()


    def test_original_post_and_poll_interfaces_complete_offline(self):
        prefix = '/api/v4/manager/research'
        first = self.request('POST', prefix+'/ensure?date='+DATE)
        self.assertEqual(first.status_code, 200)
        job_id = first.json()['job']['job_id']
        wait_terminal(self.jobs, job_id)
        poll = self.request('GET', prefix+'/jobs/'+job_id+'?date='+DATE)
        self.assertEqual(poll.status_code, 200)
        self.assertTrue(poll.json()['product']['rows'][0]['facts'])
        first_generation = poll.json()['job']['generation']
        retry = self.request('POST', prefix+'/retry?date='+DATE)
        self.assertEqual(retry.status_code, 200)
        self.assertNotEqual(retry.json()['job']['generation'], first_generation)
        wait_terminal(self.jobs, job_id)
        events = self.request('POST', prefix+'/events?date='+DATE)
        self.assertEqual(events.status_code, 200)
        wait_terminal(self.jobs, events.json()['job']['job_id'])
        cancel = self.request('POST', prefix+'/jobs/'+job_id+'/cancel?date='+DATE)
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()['job']['job_id'], job_id)

if __name__ == '__main__': unittest.main()
