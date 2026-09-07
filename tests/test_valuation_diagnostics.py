import unittest
from industry_bottleneck_scanner.valuation_diagnostics import incremental_fcff, equity_dcf, reverse_equity_dcf


class ValuationDiagnosticsTests(unittest.TestCase):
    def test_depreciation_addback_and_loss_no_tax_credit(self):
        r = incremental_fcff(revenue=100, ebitda_margin=.2, depreciation=3,
                             tax_rate=.25, capex=5, working_capital_increase=8)
        self.assertAlmostEqual(r['fcff'], 2.75)
        loss = incremental_fcff(revenue=100, ebitda_margin=-.1, depreciation=3,
                                tax_rate=.25, capex=5, working_capital_increase=8)
        self.assertEqual(loss['cash_tax'], 0)
        self.assertEqual(loss['fcff'], -23)

    def test_release_not_silently_removed(self):
        r = incremental_fcff(revenue=100, ebitda_margin=.2, depreciation=3,
                             tax_rate=.25, capex=5, working_capital_increase=-8)
        self.assertAlmostEqual(r['fcff'], 18.75)
        self.assertFalse(r['publication_eligible'])

    def test_flat_perpetuity_and_reverse_tieout(self):
        r = equity_dcf(initial_cash=10, growth=0, discount_rate=.1, terminal_growth=0)
        self.assertAlmostEqual(r['equity_value_proxy'], 100)
        rev = reverse_equity_dcf(market_cap=100, initial_cash=10, discount_rate=.1, terminal_growth=0)
        self.assertAlmostEqual(rev['required_growth'], 0)
        self.assertFalse(rev['publication_eligible'])

    def test_nonfinite_and_invalid_terminal_rejected(self):
        for value in [float('nan'), float('inf'), True]:
            with self.assertRaises(ValueError):
                equity_dcf(initial_cash=value, growth=.1, discount_rate=.1, terminal_growth=.02)
        with self.assertRaises(ValueError):
            equity_dcf(initial_cash=10, growth=.1, discount_rate=.1, terminal_growth=.1)

    def test_more_reinvestment_reduces_cash(self):
        args = dict(revenue=100, ebitda_margin=.2, depreciation=3, tax_rate=.25, working_capital_increase=8)
        self.assertAlmostEqual(incremental_fcff(capex=15, **args)['fcff'] - incremental_fcff(capex=5, **args)['fcff'], -10)
