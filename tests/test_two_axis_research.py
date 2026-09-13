import unittest
from industry_bottleneck_scanner.two_axis_research import review_two_axes

class TwoAxisTests(unittest.TestCase):
    def packet(self):
        return {'information_cutoff':'2025-08-29T20:00:00Z','sources':[{'id':'a','available_no_later_than':'2025-07-01T00:00:00Z'}], 'companies':[], 'paths':[dict(id='p',source_ids=['a'],status='candidate',purchase_dependency='technical',supply_response='expansion',next_action='customer evidence',falsifier='capacity available')]}
    def test_route_only_is_incomplete(self):
        r=review_two_axes(self.packet());self.assertFalse(r['research_complete']);self.assertIn('p:downstream_validation_open',r['gaps'])
    def test_promotion_requires_actual_work(self):
        p=self.packet();p['paths'][0]['status']='validated_beneficiary'
        with self.assertRaises(ValueError):review_two_axes(p)
    def test_future_source_rejected(self):
        p=self.packet();p['sources'][0]['available_no_later_than']='2025-09-01T00:00:00Z'
        with self.assertRaises(ValueError):review_two_axes(p)
    def test_missing_not_negative(self):
        p=self.packet();p['paths'][0]['status']='rejected'
        with self.assertRaises(ValueError):review_two_axes(p)
    def test_event_date_is_not_verified_publication(self):
        p=self.packet();p['sources'][0]['availability_verified']=False
        r=review_two_axes(p)
        self.assertIn('a:source_availability_unverified',r['gaps'])
        self.assertFalse(r['research_complete'])
