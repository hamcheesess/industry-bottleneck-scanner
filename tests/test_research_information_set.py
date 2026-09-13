import copy
import unittest
from industry_bottleneck_scanner.research_information_set import validate_information_set


class InformationSetTest(unittest.TestCase):
    def setUp(self):
        self.packet={'schema_version':'research-information-set-v1','information_cutoff':'2025-08-29T20:00:00+00:00',
          'sources':[{'source_id':'a','url':'https://example.org/release','availability_basis':'dated original release',
            'available_from':'2025-08-01T00:00:00+00:00','available_no_later_than':'2025-08-02T00:00:00+00:00',
            'retrieved_at':'2026-09-07T00:00:00+00:00'}],
          'claims':[{'claim_id':'c','kind':'forecast','source_ids':['a'],'text_ko':'당시 발표한 미래 전망',
             'observation_end':'2030-12-31T00:00:00+00:00'}]}

    def test_future_forecast_is_not_future_evidence(self):
        self.assertTrue(validate_information_set(self.packet)['temporal_metadata_passed'])

    def test_future_actual_rejected(self):
        self.packet['claims'][0]['kind']='observed'
        with self.assertRaises(ValueError): validate_information_set(self.packet)

    def test_later_restatement_of_old_period_rejected(self):
        self.packet['claims'][0].update(kind='observed',observation_end='2025-06-30T00:00:00+00:00')
        self.packet['sources'][0]['available_no_later_than']='2026-07-23T00:00:00+00:00'
        with self.assertRaises(ValueError): validate_information_set(self.packet)

    def test_same_day_unknown_time_is_not_assumed_before_close(self):
        self.packet['sources'][0].update(available_from='2025-08-29T00:00:00+00:00',
                                        available_no_later_than='2025-08-30T00:00:00+00:00')
        with self.assertRaises(ValueError): validate_information_set(self.packet)

    def test_missing_source_and_duplicate_id(self):
        bad=copy.deepcopy(self.packet);bad['claims'][0]['source_ids']=['absent']
        with self.assertRaises(ValueError): validate_information_set(bad)
        self.packet['sources'].append(copy.deepcopy(self.packet['sources'][0]))
        with self.assertRaises(ValueError): validate_information_set(self.packet)

    def test_timezone_and_empty_packet_rejected(self):
        bad=copy.deepcopy(self.packet);bad['information_cutoff']='2025-08-29T20:00:00'
        with self.assertRaises(ValueError): validate_information_set(bad)
        self.packet['claims']=[]
        with self.assertRaises(ValueError): validate_information_set(self.packet)

    def test_metadata_is_not_publication_or_investment_approval(self):
        r=validate_information_set(self.packet)
        self.assertFalse(r['publication_eligible'])
        self.assertFalse(r['historical_availability_independently_certified'])
        self.assertEqual(r['investment_status'],'not_evaluable_missing_data')
