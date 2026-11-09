"""Synthetic structural coverage only; this fixture is not an exchange calendar."""
import copy
import datetime as dt
import unittest

import registered as r
from test_panel_freshness import fixture, rebind_source, add_coverage




class Completeness(unittest.TestCase):
    def inputs(self):
        reg, policy, docs = fixture()
        add_coverage(docs)
        return reg, policy, docs

    def test_missing_coverage_refused(self):
        reg, policy, docs = self.inputs()
        docs.pop('calendar_coverage')
        with self.assertRaisesRegex(ValueError, '^PANEL_CALENDAR_COMPLETENESS_REQUIRED$'):
            r.validate_freeze_panel_freshness(reg, policy, docs)

    def test_sparse_sessions_cannot_hide_completed_friday(self):
        reg, policy, docs = self.inputs()
        rebind_source(reg, docs, '20261105')
        docs['panel_evidence'].update(observed_at='2026-11-06T15:01:00+08:00',
                                      available_at='2026-11-06T15:02:00+08:00')
        cal = docs['market_calendar']
        cal['sessions'] = [row for row in cal['sessions'] if row['trade_date'] != '20261106']
        # Even a recomputed self-hash must not remove the explicit OPEN day.
        docs['calendar_coverage']['calendar_identity'] = r.sha(r.canonical(cal))
        with self.assertRaisesRegex(ValueError, '^PANEL_CALENDAR_SESSION_COVERAGE_MISMATCH$'):
            r.validate_freeze_panel_freshness(reg, policy, docs)

    def test_missing_duplicate_and_unordered_civil_dates_refused(self):
        for mutation in ('missing', 'duplicate', 'reverse'):
            reg, policy, docs = self.inputs()
            rows = docs['calendar_coverage']['days']
            if mutation == 'missing':
                rows.pop(7)
            elif mutation == 'duplicate':
                rows.insert(7, copy.deepcopy(rows[7]))
            else:
                rows.reverse()
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'PANEL_CALENDAR_DAY_COVERAGE'):
                r.validate_freeze_panel_freshness(reg, policy, docs)

    def test_unknown_or_unreferenced_day_refused(self):
        for field, value in (('state', 'UNKNOWN'), ('state', True), ('source_reference', ''), ('source_reference', 'UNKNOWN')):
            reg, policy, docs = self.inputs()
            docs['calendar_coverage']['days'][1][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'PANEL_CALENDAR_DAY_UNRESOLVED'):
                r.validate_freeze_panel_freshness(reg, policy, docs)

    def test_coverage_exact_calendar_and_identity_binding(self):
        for field, value in (('calendar_identity', '0' * 64), ('version', 'OTHER'),
                             ('coverage_end', '20261109'), ('market', 'HK')):
            reg, policy, docs = self.inputs()
            docs['calendar_coverage'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'PANEL_CALENDAR_COMPLETENESS_BINDING'):
                r.validate_freeze_panel_freshness(reg, policy, docs)

    def test_explicit_temporary_closure_does_not_assume_weekdays_open(self):
        reg, policy, docs = self.inputs()
        rebind_source(reg, docs, '20261105')
        docs['panel_evidence'].update(observed_at='2026-11-06T15:01:00+08:00',
                                      available_at='2026-11-06T15:02:00+08:00')
        cal = docs['market_calendar']
        cal['sessions'] = [row for row in cal['sessions'] if row['trade_date'] != '20261106']
        add_coverage(docs)
        next(row for row in docs['calendar_coverage']['days'] if row['date'] == '20261106')['source_reference'] = 'SYNTHETIC_TEMPORARY_CLOSURE_NOT_REAL_NOTICE'
        result = r.validate_freeze_panel_freshness(reg, policy, docs)
        self.assertEqual(result['latest_completed_session'], '20261105')
        self.assertFalse(result['source_admission'])
        self.assertEqual(result['calendar_authority'], 'REQUIRES_EXISTING_INDEPENDENT_REVIEW')


if __name__ == '__main__':
    unittest.main()
