"""Explicit owned-buffer lifetime; no cache, weakened verification, or RSS override."""
import json
import unittest
from unittest.mock import patch
from test_m18_v2_disk_pages import fixture
from v5_shadow import m18_offline_v2 as m


class ReaderLifetimeTests(unittest.TestCase):
    def test_owned_encoded_content_is_released_before_full_json_parse(self):
        raw, identity, original = fixture()
        bundle = m.Bundle(original.manifest, dict(original.objects))
        meta = json.loads(bundle.manifest)
        content_keys = {row['object_sha256'] for row in meta['chunks']}
        index_keys = {row['object_sha256'] for row in meta['index_pages']}
        parse = m.parse
        phases = []
        def observe(data, scope, *args, **kwargs):
            if scope == 'object' and data in [original.objects[key] for key in content_keys]:
                # Keep the original chunk allocation order; do not interleave
                # deletion with ongoing content decode/assembly.
                self.assertTrue(content_keys <= set(bundle.objects))
            if scope == 'response':
                phases.append(scope)
                self.assertFalse(content_keys & set(bundle.objects))
                self.assertEqual(set(bundle.objects), index_keys)
            return parse(data, scope, *args, **kwargs)
        with patch.object(m, 'parse', side_effect=observe):
            reader = m.Reader(bundle,m.sha(bundle.manifest),identity,
                              expected_profile=m.PROFILE_SHA256,consume_content=True)
        self.assertEqual(phases,['response'])
        self.assertEqual(reader.full_response(),raw)
        self.assertEqual(set(bundle.objects),index_keys)
        self.assertEqual(set(original.objects),content_keys | index_keys)
        self.assertEqual(reader.overview()['identity'],identity)
        reader.verify_content(reader.content(0),expected_index=0)

    def test_default_reader_keeps_reusable_caller_bundle_and_same_counts(self):
        raw, identity, bundle = fixture()
        keys = set(bundle.objects)
        normal = m.Reader(bundle,m.sha(bundle.manifest),identity,expected_profile=m.PROFILE_SHA256)
        owned = m.Reader(m.Bundle(bundle.manifest,dict(bundle.objects)),m.sha(bundle.manifest),identity,
                         expected_profile=m.PROFILE_SHA256,consume_content=True)
        self.assertEqual(set(bundle.objects),keys)
        self.assertEqual(normal.counts,owned.counts)
        self.assertEqual(normal.overview(),owned.overview())
        self.assertEqual(normal.detail('gaps'),owned.detail('gaps'))
        self.assertEqual(normal.content(0),owned.content(0))

    def test_owned_mode_rejects_tampered_missing_and_extra_objects(self):
        _, identity, original = fixture()
        for kind in ('tampered','missing','extra'):
            bundle = m.Bundle(original.manifest,dict(original.objects))
            key = json.loads(bundle.manifest)['chunks'][0]['object_sha256']
            if kind == 'tampered': bundle.objects[key] = b'{}'
            elif kind == 'missing': del bundle.objects[key]
            else: bundle.objects['f'*64] = b'{}'
            with self.subTest(kind=kind), self.assertRaises(m.ContractError):
                m.Reader(bundle,m.sha(bundle.manifest),identity,expected_profile=m.PROFILE_SHA256,
                         consume_content=True)
