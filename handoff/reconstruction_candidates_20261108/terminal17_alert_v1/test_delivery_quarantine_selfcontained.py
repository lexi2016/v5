"""Offline containment tests; synthetic identities, no connector or legacy test imports.
Run from repo terminal17_alert_v1 directory, or set V5_TEST_REPO to a local checkout.
No production pins are installed. Passing is NOT working delivery acceptance.
"""
import contextlib
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

REPO = Path(os.environ['V5_TEST_REPO']) if 'V5_TEST_REPO' in os.environ else Path(__file__).resolve().parents[3]
REL = Path('handoff/reconstruction_candidates_20261108/terminal17_alert_v1')
EXPECTED = 'a9369a26d5ca8f016f62d3484db543687b7afdc68de7ef1f14371fd7b0d38ca0'
ERROR = 'ANTI_ROLLBACK_AUTHORITY_UNBOUND_NO_SEND'

def load(path):
    spec = importlib.util.spec_from_file_location('fixture_local_module', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class QuarantineRegression(unittest.TestCase):
    def setUp(self):
        self.bridge = load(REPO / REL / 'controlled_delivery.py')
        self.assertEqual(self.bridge.sha((REPO / REL / 'controlled_delivery.py').read_bytes()), EXPECTED)
        self.assertEqual(self.bridge.OWNER_LEDGER_PINS, {})
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.ledger = self.root / 'ledger'; self.ledger.mkdir()
        ident = lambda p: dict(device=p.stat().st_dev, inode=p.stat().st_ino)
        self.calls = []; self.confirm = False
        def sender(**message):
            self.calls.append(message)
            self.fail('A sender was called')
        def reconciler(**kw):
            i = kw['identity']
            return dict(delivery_confirmed=self.confirm, channel=i['channel'], destination=i['destination'],
                payload_sha256=i['payload_sha256'], message_id='SYNTHETIC_PRIOR', evidence_ref='SYNTHETIC_PROOF')
        self.binding = dict(owner_id='fixture-owner', task_id='fixture-task', environment_id='fixture-env',
            run_id='fixture-run', run_date='20261109', domain='isolated_test',
            owner_context=contextlib.nullcontext, gate=lambda: True,
            clock=lambda: dt.datetime.fromisoformat('2026-11-09T19:00:00+08:00'),
            delivery=dict(authorized=True, authorization_ref='SYNTHETIC_ONLY', channel='chatgpt',
                destination='SYNTHETIC_NO_RECIPIENT', binding_version='fixture', output_root=self.root,
                root_identity=ident(self.root), sender=sender, reconciler=reconciler))
        authority = dict(schema='OWNER_DELIVERY_LEDGER_V1', authority_ref='SYNTHETIC_ONLY',
            owner_id='fixture-owner', task_id='fixture-task', environment_id='fixture-env',
            ledger_root=str(self.ledger), root_identity=ident(self.ledger), output_root=str(self.root),
            output_root_identity=ident(self.root))
        self.binding['resolve_delivery_authority'] = lambda **kw: dict(authority)
        # Patch only this independently loaded in-memory module, never project code.
        self.bridge.OWNER_LEDGER_PINS = {('fixture-owner','fixture-task','fixture-env'):self.bridge.sha(self.bridge.canonical(authority))}

    def call(self, node='1700', action='deliver'):
        return self.bridge.dispatch(self.binding, node=node, input_sha256='a'*64,
            code_version='synthetic', payload={'fixture':True}, preflight=lambda:None, action=action)

    def test_all_nodes_hard_block_and_prepare_reconcile(self):
        for node in ('0810','1700','1900'):
            with self.subTest(node=node):
                self.assertEqual(self.call(node,'prepare')['delivery_state'], 'PREPARED')
                with self.assertRaisesRegex(ValueError, ERROR): self.call(node)
                r=self.call(node,'reconcile')
                self.assertEqual(r['delivery_state'],'PREPARED'); self.assertFalse(r['delivery_verified'])
        self.assertEqual(self.calls,[])

    def test_inner_sender_hard_block(self):
        for node in ('0810','1700','1900'):
            c=self.bridge._delivery_config(self.binding,node,'a'*64,'synthetic',b'{}',lambda:None,'deliver')
            with self.assertRaisesRegex(ValueError, ERROR): c['sender'](text='synthetic')
        self.assertEqual(self.calls,[])

    def test_flags_and_project_domain_do_not_enable(self):
        self.binding.update(anti_rollback_verified=True, consume_once=lambda **kw: True)
        self.binding['delivery']['anti_rollback_verified']=True
        for node,domain,destination in [('0810','isolated_test','SYNTHETIC_NO_RECIPIENT'),('1900','reviewed_project','SYNTHETIC_NON_NETWORK')]:
            self.binding['domain']=domain; self.binding['delivery']['destination']=destination
            # Distinct logical node avoids an unrelated binding-change rejection.
            with self.assertRaisesRegex(ValueError,ERROR): self.call(node)
        self.assertEqual(self.calls,[])

    def test_both_stores_reset_or_legacy_missing_do_not_enable(self):
        self.call(action='prepare'); snapshot=(self.root/'outbox.sqlite3').read_bytes()
        for loss in (False,True):
            for p in self.ledger.glob('delivery-*'): p.rename(p.with_name('retained-'+p.name))
            db=self.root/'outbox.sqlite3'
            if loss: db.rename(self.root/'retained-outbox.sqlite3')
            else: db.write_bytes(snapshot)
            with self.assertRaisesRegex(ValueError,ERROR): self.call()
        self.assertEqual(self.calls,[])

    def test_unknown_reconcile_requires_positive_proof(self):
        r=self.call(action='prepare')
        c=self.bridge._delivery_config(self.binding,'1700','a'*64,'synthetic',self.bridge.canonical({'fixture':True}),lambda:None,'reconcile')
        module=self.bridge.pinned_module(REPO/REL/'outbox.py',self.bridge.OUTBOX_SHA)
        db=module._connection(c)
        try: module._transition(db,r['outbox_key'],'ATTEMPT_UNKNOWN',{'synthetic_prior':True})
        finally: db.close()
        r=self.call(action='reconcile')
        self.assertEqual(r['delivery_state'],'ATTEMPT_UNKNOWN');self.assertFalse(r['delivery_verified'])
        self.confirm=True
        r=self.call(action='reconcile')
        self.assertTrue(r['delivery_verified']);self.assertFalse(r['sent_in_this_call'])
        self.assertFalse(r['business_accepted']);self.assertFalse(r['natural_verified'])
        self.assertEqual(self.calls,[])

    def test_accepted_reconcile_never_calls_sender(self):
        r=self.call(action='prepare')
        c=self.bridge._delivery_config(self.binding,'1700','a'*64,'synthetic',self.bridge.canonical({'fixture':True}),lambda:None,'reconcile')
        module=self.bridge.pinned_module(REPO/REL/'outbox.py',self.bridge.OUTBOX_SHA)
        db=module._connection(c)
        try:
            module._transition(db,r['outbox_key'],'ACCEPTED',dict(message_id='SYNTHETIC_PRIOR',
                channel=c['channel'],destination=c['destination'],status='accepted',
                payload_sha256=self.bridge.sha(self.bridge.canonical({'fixture':True}))))
        finally: db.close()
        r=self.call()
        self.assertEqual(r['delivery_state'],'ACCEPTED');self.assertFalse(r['delivery_verified'])
        self.confirm=True
        self.assertTrue(self.call(action='reconcile')['delivery_verified'])
        self.assertEqual(self.calls,[])

    def test_authorization_still_required(self):
        self.binding['delivery']['authorized']=False
        with self.assertRaisesRegex(ValueError,'DELIVERY_NOT_EXPLICITLY_AUTHORIZED'):self.call(action='prepare')
        self.assertFalse((self.root/'outbox.sqlite3').exists());self.assertEqual(self.calls,[])

    def test_real_consumer_digest_wiring(self):
        alert=load(REPO/REL/'terminal_alert.py')
        self.assertEqual(alert.DELIVERY_BRIDGE_SHA,EXPECTED)
        self.assertEqual(alert._delivery_bridge().OWNER_LEDGER_PINS,{})
        evening=REPO/'V5/public_source_delivery/20261108_execution_increment/evening'
        execution=load(evening/'execution.py')
        chain=execution._controlled_chain()
        self.assertEqual(chain.DELIVERY_BRIDGE_SHA,EXPECTED)
        self.assertEqual(chain._bridge().OWNER_LEDGER_PINS,{})

if __name__=='__main__':unittest.main()
