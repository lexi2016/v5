"""Immutable M11 commits using the byte-identical donor's descriptor-safe I/O.

A commit means persistence verified, never business READY or natural admission.
Pre-envelope legacy files are deliberately not accepted as committed artifacts.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from .owner_sources import safe_root_class

M11_SLOTS = ('09:25', '09:35', '10:00', '11:30', '14:00', '15:00')
_STATES = {'REQUEST_IN_FLIGHT','REQUEST_ATTEMPTED','ATTEMPT_UNKNOWN','FAILED_NO_REQUEST','SUCCEEDED'}


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


def _digest(value):return hashlib.sha256(_encoded(value)).hexdigest()


def _date(value):
    if not isinstance(value,str) or len(value)!=10:raise ValueError('target_date_invalid')
    return date.fromisoformat(value).isoformat()


def _root(root):
    p=Path(root)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('root_boundary_invalid')
    if any(item.is_symlink() for item in [p,*p.parents]):raise ValueError('root_symlink_rejected')
    return p


@dataclass(frozen=True)
class M11Slot:
    target_date: str
    slot: str
    cutoff: str
    trigger: str
    run_id: str
    input_sha: str = ''
    config_sha: str = ''
    code_sha: str = ''
    source_sha: str = ''

    def identity(self):
        _date(self.target_date)
        if self.slot not in M11_SLOTS:raise ValueError('slot_invalid')
        if not all(isinstance(v,str) for v in self.__dict__.values()):raise ValueError('identity_invalid')
        if not self.cutoff or not self.trigger or not self.run_id:raise ValueError('identity_incomplete')
        return _digest(self.__dict__)


class IntradayCapsuleStore:
    def __init__(self, root):
        self.root=_root(root)
        self.io=safe_root_class()(self.root)

    def _artifact_dir(self, slot):
        return self.root / _date(slot.target_date) / slot.slot.replace(':','') / slot.identity()

    def _stem(self, slot):return str(self._artifact_dir(slot).relative_to(self.root))

    def write_success(self, slot, payload, source_sha):
        if not isinstance(payload,dict) or not isinstance(source_sha,str) or not source_sha:raise ValueError('commit_payload_invalid')
        if slot.source_sha and slot.source_sha != source_sha:raise ValueError('source_identity_mismatch')
        stem=self._stem(slot)
        manifest={'schema':'v5.m11.manifest.v2','identity':slot.identity(),'slot':slot.__dict__,
                  'source_sha':source_sha,'payload_sha':_digest(payload),'created_at':datetime.now(timezone.utc).isoformat(),
                  'state':'COMMITTED','business_status':payload.get('status','CANNOT_CONFIRM')}
        receipt={'schema':'v5.m11.receipt.v2','identity':slot.identity(),'manifest_sha256':_digest(manifest),'payload_sha256':_digest(payload)}
        envelope={'manifest':manifest,'payload':payload,'receipt':receipt}
        with self.io.kernel_lock('locks/'+slot.identity()+'.lock'):
            # One atomically linked no-replace envelope; crashes cannot expose half a commit.
            self.io.write_bytes(stem+'/commit.json',_encoded(envelope),require_absent=True)
        if self.read_verified(slot)!=payload:raise ValueError('readback_mismatch')
        return manifest

    def write_attempt(self, slot, state, error_code=None):
        if state not in _STATES:raise ValueError('attempt_state_invalid')
        slot.identity()
        stem=_date(slot.target_date)+'/attempts/'+slot.slot.replace(':','')
        record={'slot':slot.__dict__,'state':state,'error_code':error_code}
        with self.io.kernel_lock('locks/'+slot.identity()+'.lock'):
            self.io.write_bytes(stem+'/events/'+uuid4().hex+'.json',_encoded(record),require_absent=True)
            self.io.write_bytes(stem+'/latest_attempt.json',_encoded(record))
        return record

    def read_verified(self, slot):
        envelope=json.loads(self.io.read_bytes(self._stem(slot)+'/commit.json'))
        if set(envelope)!={'manifest','payload','receipt'}:raise ValueError('commit_envelope_invalid')
        m=envelope['manifest']; p=envelope['payload']; r=envelope['receipt']
        if m.get('schema')!='v5.m11.manifest.v2' or m.get('state')!='COMMITTED':raise ValueError('manifest_invalid')
        if m.get('identity')!=slot.identity() or m.get('slot')!=slot.__dict__:raise ValueError('artifact_identity_mismatch')
        if slot.source_sha and m.get('source_sha')!=slot.source_sha:raise ValueError('source_identity_mismatch')
        if m.get('payload_sha')!=_digest(p):raise ValueError('payload_digest_mismatch')
        if r!={'schema':'v5.m11.receipt.v2','identity':slot.identity(),'manifest_sha256':_digest(m),'payload_sha256':_digest(p)}:
            raise ValueError('receipt_digest_mismatch')
        return p
