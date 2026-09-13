import json
from pathlib import Path
import unittest
from industry_bottleneck_scanner.cash_flow_quality import review_cash_quality


class CashQualityTest(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((Path(__file__).parents[1] / 'experiments/company_exposure/ge-vernova-cash-quality.json').read_text())

    def test_real_source_bridge_is_not_normalized_fcf(self):
        r = review_cash_quality(self.p)
        self.assertEqual(r['fcf_less_working_capital_benefit'], -1293)
        self.assertIsNone(r['normalized_fcf'])
        self.assertIsNone(r['transformer_attributed_fcf'])
        self.assertFalse(r['publication_eligible'])

    def test_scope_mismatch(self):
        self.p['metrics']['reported_fcf']['scope'] = 'transformers'
        with self.assertRaises(ValueError): review_cash_quality(self.p)

    def test_period_mismatch(self):
        self.p['metrics']['reported_fcf']['period'] = '2026H1'
        with self.assertRaises(ValueError): review_cash_quality(self.p)

    def test_nan(self):
        self.p['metrics']['reported_fcf']['value'] = float('nan')
        with self.assertRaises(ValueError): review_cash_quality(self.p)

    def test_future(self):
        self.p['as_of_date'] = '2026-07-21'
        with self.assertRaises(ValueError): review_cash_quality(self.p)

    def test_unknown_source(self):
        self.p['metrics']['reported_fcf']['source_id'] = 'missing'
        with self.assertRaises(ValueError): review_cash_quality(self.p)

if __name__ == '__main__': unittest.main()
