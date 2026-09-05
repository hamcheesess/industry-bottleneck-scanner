import copy
import json
from pathlib import Path
import unittest
from industry_bottleneck_scanner.company_exposure import assess_exposure


class ExposureTest(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((Path(__file__).parents[1] / 'experiments/company_exposure/transformers-current-research.json').read_text())

    def test_real_packet_remains_research_only(self):
        result = assess_exposure(self.packet)
        self.assertEqual(len(result['companies']), 3)
        self.assertTrue(all(not x['publication_eligible'] for x in result['companies']))
        self.assertEqual(result['companies'][2]['status'], 'needs_exposure_attribution')

    def test_rejects_future(self):
        self.packet['companies'][0]['evidence'][0]['published_at'] = '2026-09-06T00:00:00Z'
        with self.assertRaises(ValueError):
            assess_exposure(self.packet)

    def test_rejects_historical_reuse(self):
        self.packet['mode'] = 'historical_replay'
        with self.assertRaises(ValueError):
            assess_exposure(self.packet)

    def test_rejects_duplicate(self):
        self.packet['companies'].append(copy.deepcopy(self.packet['companies'][0]))
        with self.assertRaises(ValueError):
            assess_exposure(self.packet)

    def test_rejects_naive_time(self):
        self.packet['as_of'] = '2026-09-05'
        with self.assertRaises(ValueError):
            assess_exposure(self.packet)


if __name__ == '__main__':
    unittest.main()
