"""Provider-free reproduction of an explicitly conditional valuation diagnostic."""
import json
from pathlib import Path
from industry_bottleneck_scanner.valuation_diagnostics import incremental_fcff, equity_dcf, reverse_equity_dcf
from industry_bottleneck_scanner.research_information_set import validate_information_set

HERE = Path(__file__).resolve().parent

def build():
    inputs = json.loads((HERE / 'valuation-input.json').read_text())
    validate_information_set(json.loads((HERE / 'information-set.json').read_text()))
    # Market observations use unadjusted close, never today's total-return adjustment.
    if inputs['price']['basis'] != 'unadjusted_close' or inputs['price']['date'] != '2025-08-29':
        raise ValueError('price identity / basis mismatch')
    if inputs['shares']['period_end'] != '2025-06-30' or inputs['shares']['available_no_later_than'] > '2025-08-29T20:00:00Z':
        raise ValueError('share-count version mismatch')
    price, shares = inputs['price']['value_usd'], inputs['shares']['value_millions']
    market_cap = price * shares
    proxy = inputs['company_fcf_guidance_usd_millions']['midpoint']
    reverse = []
    for rate in [.08, .10, .12]:
        for terminal in [.02, .03]:
            reverse.append(dict(discount_rate=rate, terminal_growth=terminal,
                **reverse_equity_dcf(market_cap=market_cap, initial_cash=proxy, discount_rate=rate, terminal_growth=terminal)))
    scenarios = []
    for growth in [.10, .20, .30]:
        r = equity_dcf(initial_cash=proxy, growth=growth, discount_rate=.10, terminal_growth=.03)
        scenarios.append(dict(growth=growth, value_per_share=r['equity_value_proxy']/shares,
                             price_gap=r['equity_value_proxy']/market_cap-1, **r))
    bridges = []
    for case in inputs['incremental_product_sensitivities']:
        bridges.append(dict(case=case['case'], **case['inputs'], **incremental_fcff(**case['inputs'])))
    output = {'schema_version':'historical-valuation-diagnostic-v1', 'as_of': '2025-08-29T20:00:00Z',
              'market_cap_proxy_usd_millions':market_cap, 'share_count_lag_days':60,
              'guidance_fcf_yield_range':[3000/market_cap,3500/market_cap],
              'price_to_guidance_fcf_range':[market_cap/3500,market_cap/3000],
              'reverse_dcf':reverse, 'growth_sensitivities':scenarios, 'product_incremental_fcff':bridges,
              'required_annual_equity_cash_at_multiples':{str(m):market_cap/m for m in [20,25,30,40]},
              'investment_status':'not_evaluable_missing_data', 'publication_eligible':False,
              'limitations':['Product-level FCF is not disclosed; product cases are normalized sensitivities, not forecasts.',
                'FY2025 guidance midpoint is only an assumed forward annual equity cash proxy, not normalized FCFE or consensus.',
                'Quarter-end outstanding shares proxy is not same-day diluted shares.',
                'No surplus cash is added and no operating cash, minority interests or equity investments are separately valued.',
                'Five-year cash growth is a valuation variable, not a 6-18 month realized-return forecast.']}
    (HERE/'valuation-diagnostic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    template = (HERE/'report-template.md').read_text()
    tables = {}
    tables['MULTIPLE_ROWS'] = '\n'.join(f"| {m}배 가정 | {v/100:.1f}억 달러 | 회사 전망과 구분한 역산 |" for m,v in output['required_annual_equity_cash_at_multiples'].items())
    tables['REVERSE_ROWS'] = '\n'.join(f"| {r['discount_rate']:.0%} / {r['terminal_growth']:.0%} | {r['required_growth']:.1%} | {r['year_end_cash'][-1]/100:.1f}억 달러 |" for r in reverse)
    tables['GROWTH_ROWS'] = '\n'.join(f"| {r['growth']:.0%} 가정 | {r['value_per_share']:.2f}달러 | {r['price_gap']:.1%} |" for r in scenarios)
    fields = [('매출','revenue'),('EBITDA 마진','ebitda_margin'),('EBITDA','ebitda'),('감가상각','depreciation'),('영업이익','ebit'),('현금세금 / 세율 25%','cash_tax'),('설비투자','capex'),('운전자본 증가','working_capital_increase'),('증분 FCFF','fcff')]
    tables['BRIDGE_ROWS'] = '\n'.join('| '+label+' | '+' | '.join(f"{r[key]:.0%}" if key=='ebitda_margin' else f"{r[key]:.2f}" for r in bridges)+' |' for label,key in fields)
    for key, value in tables.items():
        template = template.replace('{{'+key+'}}',value)
    if '{{' in template:
        raise ValueError('unresolved report table')
    (HERE/'report-source.md').write_text(template)
    return output

if __name__ == '__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
