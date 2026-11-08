import unittest
import latest109_rebuild as adapter


class CheckpointIdentityTests(unittest.TestCase):
    def verify(self, rows, context=None, state=None):
        context = context if context is not None else {'symbol': '000001.SZ', 'asof': rows[-1]['event_date']}
        state = state if state is not None else {'symbol': context['symbol'], 'count': len(rows) - 1, 'last_date': rows[-2]['event_date']}
        return adapter.validate_checkpoint(rows, context, state, adapter.digest(rows[:-1]))

    def test_boolean_count_rejected(self):
        rows = [{'symbol': '000001.SZ', 'event_date': d} for d in ('20261105', '20261106')]
        with self.assertRaises(ValueError):
            self.verify(rows, state={'symbol': '000001.SZ', 'count': True, 'last_date': '20261105'})

    def test_wrong_historical_symbol_rejected(self):
        rows = [{'symbol': '000002.SZ', 'event_date': '20261105'}, {'symbol': '000001.SZ', 'event_date': '20261106'}]
        with self.assertRaises(ValueError):
            self.verify(rows)

    def test_missing_symbol_rejected(self):
        rows = [{'event_date': d} for d in ('20261105', '20261106')]
        with self.assertRaises(ValueError):
            self.verify(rows, {'symbol': None, 'asof': '20261106'}, {'symbol': None, 'count': 1, 'last_date': '20261105'})

    def test_invalid_dates_rejected(self):
        for dates in [('20261106', '20261105'), ('20261106', '20261106'), ('20260230', '20261106'), ('2026-11-05', '20261106'), ('20261106', '２０２６１１０７')]:
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                self.verify([{'symbol': '000001.SZ', 'event_date': d} for d in dates])

    def test_earlier_history_order_checked(self):
        with self.assertRaises(ValueError):
            self.verify([{'symbol': '000001.SZ', 'event_date': d} for d in ('20261104', '20261103', '20261105', '20261106')])

    def test_leap_day_and_nonconsecutive_trading_dates_allowed(self):
        rows = [{'symbol': '000001.SZ', 'event_date': d} for d in ('20240229', '20261106')]
        self.assertIsInstance(self.verify(rows), str)

    def test_malformed_rows_raise_value_error(self):
        for rows in (None, [], [{}, None]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                adapter.validate_checkpoint(rows, {}, {}, '0' * 64)


if __name__ == '__main__':
    unittest.main()
