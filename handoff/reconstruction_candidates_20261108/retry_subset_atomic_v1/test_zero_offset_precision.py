"""Real-entry synthetic regression for the upstream fractional-offset guard."""
import copy
import dataclasses
import json
from pathlib import Path
import unittest

import test_entrypoint as entry_fixtures
from subset_plan import aware, canonical


class ZeroOffsetPrecisionTests(unittest.TestCase):
    def test_actual_pinned_entry_refuses_unavailable_source_before_owner_or_claim(self):
        fixture = entry_fixtures.EntryTests(); fixture.setUp()
        self.addCleanup(fixture.tearDown)
        original_path = Path(fixture.binding['original_binding']['contract_ref']['path'])
        original = json.loads(original_path.read_bytes())
        original['available_after'] = '2026-11-09T08:10:00-00:00:00.000001'
        new_original = fixture.put('original-contract.json', canonical(original))
        fixture.binding['original_binding']['contract_ref'] = new_original.as_dict()
        fixture.contract['binding'] = copy.deepcopy(fixture.binding)
        fixture.evidence['binding'] = copy.deepcopy(fixture.binding)
        new_contract = fixture.put('subset-contract.json', canonical(fixture.contract))
        fixture.approval['binding'] = copy.deepcopy(fixture.binding)
        fixture.approval['contract_ref'] = new_contract.as_dict()
        new_approval = fixture.put('approval.json', canonical(fixture.approval))
        new_review = fixture.put('review-1.json', canonical(fixture.evidence))
        fixture.registration = dataclasses.replace(
            fixture.registration, contract_ref=new_contract, approval_ref=new_approval,
            reconciliation_refs={'retry-1610': new_review, 'retry-1640': new_review})
        before = sorted(p.name for p in fixture.root.iterdir())
        result = fixture.dispatch(execute=True)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'ValueError:UNSUPPORTED_ZERO_FRACTIONAL_OFFSET')
        self.assertEqual(fixture.calls, [])
        self.assertEqual(fixture.events, [])
        self.assertEqual(sorted(p.name for p in fixture.root.iterdir()), before)
        self.assertFalse(result['production_allowed'])


if __name__ == '__main__':
    unittest.main()
