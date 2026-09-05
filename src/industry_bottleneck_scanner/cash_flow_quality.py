"""Source-linked cash quality diagnostics, not normalized earnings or valuation."""
from datetime import date
from math import isfinite


def review_cash_quality(packet):
    if packet.get('schema_version') != 'cash-quality-input-v1':
        raise ValueError('unsupported schema')
    cutoff = date.fromisoformat(packet['as_of_date'])
    sources = packet['sources']
    if not sources:
        raise ValueError('sources required')
    for source in sources.values():
        if date.fromisoformat(source['published_date']) > cutoff:
            raise ValueError('future source')
        if not source['url'].startswith('https://'):
            raise ValueError('source URL required')
    metrics = packet['metrics']

    def metric(key):
        item = metrics[key]
        if item['source_id'] not in sources:
            raise ValueError('unknown source')
        value = item['value']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError('finite numeric value required')
        if item['unit'] != 'USD_million' or item['scope'] != 'consolidated':
            raise ValueError('incompatible scope or unit')
        if item['period'] != packet['period']:
            raise ValueError('period mismatch')
        return value

    fcf = metric('reported_fcf')
    working_capital = metric('working_capital_cash_benefit')
    result = {
        'schema_version': 'cash-quality-review-v1',
        'company_id': packet['company_id'],
        'period': packet['period'],
        'as_of_date': packet['as_of_date'],
        'unit': 'USD_million',
        'reported_fcf': fcf,
        'fcf_less_working_capital_benefit': round(fcf - working_capital, 3),
        'working_capital_to_reported_fcf': None if fcf <= 0 else round(working_capital / fcf, 6),
        'source_ids': sorted({metrics[k]['source_id'] for k in ('reported_fcf', 'working_capital_cash_benefit')}),
        'normalized_fcf': None,
        'transformer_attributed_fcf': None,
        'market_expectation_gap': None,
        'publication_eligible': False,
        'explanation_ko': '운전자본 효과를 단순 차감한 진단값이다. 정상 현금흐름·적정가치 또는 변압기 사업 현금흐름으로 사용할 수 없다. 선급금의 미래 비용, 다른 사업과 세금·설비투자를 추가 분리해야 한다.',
    }
    return result
