"""Offline tests for update_rates.py. Run: python -m unittest discover scripts"""

import datetime as dt
import unittest

import update_rates as u

CORE_RATES = {c.lower(): 1.0 for c in u.CORE}
CORE_RATES['usd'] = 1


class CleanRates(unittest.TestCase):
    def test_uppercases_and_sorts(self):
        self.assertEqual(list(u.clean_rates({'jpy': 150, 'eur': 0.9})), ['EUR', 'JPY'])

    def test_drops_bad_codes_and_values(self):
        raw = {'btc': 0.00001, '1inch': 3.0, 'jpy': 0, 'krw': -1, 'thb': float('nan'),
               'eur': 'x', 'gbp': True, 'twd': 32}
        self.assertEqual(u.clean_rates(raw), {'BTC': 0.00001, 'TWD': 32})


class Parsers(unittest.TestCase):
    def test_fawaz(self):
        date, rates = u.parse_fawaz({'date': '2026-10-01', 'usd': {'usd': 1, 'jpy': 148.2}})
        self.assertEqual(date, '2026-10-01')
        self.assertEqual(rates, {'JPY': 148.2, 'USD': 1})

    def test_erapi_uses_utc_date(self):
        ts = int(dt.datetime(2026, 10, 1, 0, 2, tzinfo=dt.timezone.utc).timestamp())
        date, _ = u.parse_erapi({'result': 'success', 'time_last_update_unix': ts, 'rates': {'USD': 1}})
        self.assertEqual(date, '2026-10-01')

    def test_erapi_error_result_rejected(self):
        with self.assertRaises(ValueError):
            u.parse_erapi({'result': 'error', 'error-type': 'quota'})


class Validate(unittest.TestCase):
    def ok_rates(self):
        return u.clean_rates(dict(CORE_RATES))

    def test_complete_core_passes(self):
        self.assertEqual(u.validate('2026-10-01', self.ok_rates()), [])

    def test_missing_core_fails(self):
        rates = self.ok_rates()
        del rates['TWD']
        self.assertIn('missing core currency TWD', u.validate('2026-10-01', rates))

    def test_non_positive_core_is_dropped_then_fails(self):
        raw = dict(CORE_RATES)
        raw['jpy'] = 0
        self.assertIn('missing core currency JPY', u.validate('2026-10-01', u.clean_rates(raw)))

    def test_usd_must_be_base(self):
        rates = self.ok_rates()
        rates['USD'] = 1.01
        self.assertTrue(u.validate('2026-10-01', rates))

    def test_bad_date_fails(self):
        self.assertTrue(u.validate('yesterday', self.ok_rates()))


class Decide(unittest.TestCase):
    now = dt.datetime(2026, 10, 2, 1, 3, tzinfo=dt.timezone.utc)

    def make(self, date, jpy=150, at=None):
        return u.build(date, 'fawazahmed0', {'JPY': jpy, 'USD': 1}, at or self.now)

    def test_first_run_writes(self):
        self.assertEqual(u.decide(self.make('2026-10-02'), None), 'write')

    def test_only_generated_at_differs_is_unchanged(self):
        old = self.make('2026-10-02', at=dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc))
        self.assertEqual(u.decide(self.make('2026-10-02'), old), 'unchanged')

    def test_rate_change_writes(self):
        self.assertEqual(u.decide(self.make('2026-10-02', jpy=151), self.make('2026-10-02')), 'write')

    def test_older_upstream_never_overwrites(self):
        self.assertEqual(u.decide(self.make('2026-10-01', jpy=999), self.make('2026-10-02')), 'older')

    def test_output_shape_matches_spec(self):
        self.assertEqual(
            list(self.make('2026-10-02')),
            ['schemaVersion', 'date', 'generatedAt', 'base', 'source', 'rates'],
        )


if __name__ == '__main__':
    unittest.main()
