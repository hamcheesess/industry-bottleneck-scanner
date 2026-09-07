"""Research-only cash-flow sensitivities; never an investment publication gate.

Incremental FCFF is distinct from an issuer's reported CFO-minus-capex measure.
Reverse equity DCF accepts an explicitly assumed distributable-cash proxy, not
consensus. It does not assign the issuer's market value to one product.
"""
from __future__ import annotations

import math


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")
    return float(value)


def incremental_fcff(*, revenue: float, ebitda_margin: float, depreciation: float,
                     tax_rate: float, capex: float, working_capital_increase: float) -> dict:
    """All money uses the same unit and the same explicit forecast period.

    Working capital includes operating contract assets/liabilities. Negative
    working-capital increase is allowed (release/advance), but not normalized.
    No immediate tax benefit is assumed for operating losses.
    """
    values = {k: finite(v, k) for k, v in locals().copy().items()}
    if values['revenue'] < 0 or values['depreciation'] < 0 or values['capex'] < 0:
        raise ValueError('revenue, depreciation and capex must be nonnegative')
    if not 0 <= tax_rate <= 1 or not -1 <= ebitda_margin <= 1:
        raise ValueError('invalid margin or tax rate')
    ebitda = revenue * ebitda_margin
    ebit = ebitda - depreciation
    tax = max(ebit, 0) * tax_rate
    fcff = ebit - tax + depreciation - capex - working_capital_increase
    return {'ebitda': ebitda, 'ebit': ebit, 'cash_tax': tax,
            'depreciation_addback': depreciation, 'fcff': fcff,
            'publication_eligible': False, 'posture': 'conditional_sensitivity'}


def equity_dcf(*, initial_cash: float, growth: float, discount_rate: float,
               terminal_growth: float, years: int = 5) -> dict:
    """End-year cash: C_t = C_0*(1+growth)^t. No cash/debt bridge added.

    C_0 must be labeled a normalized forward annual equity cash-flow assumption.
    Using issuer guidance as C_0 is a proxy diagnostic, not a completed FCFE model.
    """
    for k, v in [('initial_cash', initial_cash), ('growth', growth),
                 ('discount_rate', discount_rate), ('terminal_growth', terminal_growth)]:
        finite(v, k)
    if initial_cash <= 0 or growth <= -1 or not 0 < discount_rate < 1:
        raise ValueError('invalid cash, growth or discount rate')
    if not -1 < terminal_growth < discount_rate:
        raise ValueError('terminal growth must be below discount rate')
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 50:
        raise ValueError('years must be an integer from 1 to 50')
    flows = [initial_cash * (1 + growth) ** t for t in range(1, years + 1)]
    explicit = sum(c / (1 + discount_rate) ** t for t, c in enumerate(flows, 1))
    terminal_pv = flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth) / (1 + discount_rate) ** years
    value = explicit + terminal_pv
    if not math.isfinite(value):
        raise ValueError('nonfinite valuation')
    return {'equity_value_proxy': value, 'year_end_cash': flows,
            'terminal_value_share': terminal_pv / value,
            'publication_eligible': False, 'posture': 'proxy_not_consensus'}


def reverse_equity_dcf(*, market_cap: float, initial_cash: float, discount_rate: float,
                       terminal_growth: float, years: int = 5) -> dict:
    finite(market_cap, 'market_cap')
    if market_cap <= 0:
        raise ValueError('market_cap must be positive')
    args = dict(initial_cash=initial_cash, discount_rate=discount_rate,
                terminal_growth=terminal_growth, years=years)
    low, high = -0.99, 3.0
    if not equity_dcf(growth=low, **args)['equity_value_proxy'] <= market_cap <= equity_dcf(growth=high, **args)['equity_value_proxy']:
        raise ValueError('required growth outside solver bounds')
    for _ in range(100):
        middle = (low + high) / 2
        if equity_dcf(growth=middle, **args)['equity_value_proxy'] < market_cap:
            low = middle
        else:
            high = middle
    growth = (low + high) / 2
    return {**equity_dcf(growth=growth, **args), 'required_growth': growth,
            'market_cap': market_cap}
