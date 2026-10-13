"""Explicit synthetic offline fixtures, never real HKEX evidence."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import time

DATE = '20260908'
CODE = 'HK.01191'


def observation():
    return {'target_trade_date': DATE, 'stage_id': 'STAGE_0935_0940', 'market': 'HK_CONNECT',
            'status': 'READY', 'rows': [{'code': CODE, 'name': 'SYNTHETIC TEST ISSUER',
            'stage_rank': 1, 'status': 'READY', 'stage_id': 'STAGE_0935_0940',
            'source_last_bar_time': '2026-09-08 09:40:00', 'last_price': 10,
            'support_price': 9, 'pressure_price': 11, 'volume': 100,
            'volume_ratio': 1.2, 'formal_eligible': False}]}


def write_input(root, value=None):
    p = Path(root) / 'observation.json'
    raw = json.dumps(observation() if value is None else value).encode()
    p.write_bytes(raw)
    return p, sha256(raw).hexdigest()


def pdf_bytes():
    lines = ['SYNTHETIC OFFLINE TEST ONLY', 'Year ended December 31, 2025',
             '2025 2024', '(HKD in millions)', 'Revenue 120 100', 'Profit for the year 20 10']
    stream = ('BT /F1 12 Tf 50 750 Td 18 TL ' + ' '.join(
        '(' + line + ') Tj T*' for line in lines) + ' ET').encode()
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    raw = b'%PDF-1.4\n'; offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(raw)); raw += str(i).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
    xref = len(raw)
    raw += b'xref\n0 6\n0000000000 65535 f \n' + b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets[1:])
    return raw + b'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n' + str(xref).encode() + b'\n%%EOF\n'


class OfflineTransport:
    def __init__(self):
        self.calls = []
        self.document = pdf_bytes()
        self.published = '08/09/2026 08:30'
        self.code = '01191'
        self.fail = False
        self.block_started = None
        self.release = None

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs.get('method', 'GET')))
        if self.block_started is not None:
            self.block_started.set()
            if not self.release.wait(5): raise RuntimeError('OFFLINE_TEST_BLOCK_TIMEOUT')
        if self.fail: raise RuntimeError('OFFLINE_TRANSPORT_FAILURE')
        ports = importlib.import_module('m16_owner_manager_research.ports')
        if 'activestock' in url:
            body = json.dumps([{'c': self.code, 'i': '123', 'n': 'SYNTHETIC TEST ISSUER'}]).encode()
        elif 'titlesearch' in url:
            body = f'''<table><tr><td class="release-time">{self.published}</td>
            <td class="stock-short-code">{self.code}</td><td class="stock-short-name">SYNTHETIC TEST ISSUER</td>
            <td><div class="doc-link"><a href="https://www.hkexnews.hk/synthetic-test.pdf">Annual results</a></div></td></tr></table>'''.encode()
        elif url.endswith('synthetic-test.pdf'): body = self.document
        else: raise AssertionError('UNEXPECTED_OFFLINE_URL')
        return ports.SourceResponse(url, 200, body, {}, '2026-09-08T10:00:00+08:00', url)


def offline_error(*args, **kwargs):
    raise RuntimeError('OFFLINE_OPTIONAL_SOURCE_UNAVAILABLE')


def wait_terminal(jobs, job_id, date=DATE):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        result = jobs.job(job_id, date)
        if result is not None and result['status'] not in {'QUEUED', 'RUNNING'}:
            # The original worker removes its active generation just after commit.
            future = jobs._service._active.get(job_id)
            if future is not None: future.result(timeout=5)
            return result
        time.sleep(.01)
    raise AssertionError('OFFLINE_JOB_DID_NOT_FINISH')


def file_snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}
