"""Completeness of reviewed research, not automatic truth or investment approval."""
from datetime import datetime


def _date(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError('timezone required')
    return d


def review_two_axes(packet):
    cutoff = _date(packet['information_cutoff'])
    sources = {}
    for s in packet['sources']:
        if s['id'] in sources or _date(s['available_no_later_than']) > cutoff:
            raise ValueError('duplicate or post-cutoff source')
        sources[s['id']] = s
    gaps = [f"{s['id']}:source_availability_unverified" for s in sources.values()
            if s.get('availability_verified') is False]
    companies = packet['companies']
    if len({c['issuer'] for c in companies}) < 2:
        gaps.append('multi_issuer_purchase_research_missing')
    for c in companies:
        if not c['source_ids'] or set(c['source_ids']) - set(sources):
            raise ValueError('company source references missing')
        for field in ['purchase_evidence', 'cash_flow_mechanism', 'scenario_rationale', 'catalyst_window', 'falsifier']:
            if not c.get(field):
                gaps.append(f"{c['issuer']}:{field}")
        if not c.get('expectation_gap_supported'):
            gaps.append(f"{c['issuer']}:expectation_gap_unresolved")
    if not packet['paths']:
        gaps.append('downstream_research_missing')
    for p in packet['paths']:
        if not p['source_ids'] or set(p['source_ids']) - set(sources):
            raise ValueError('path source references missing')
        if p['status'] not in {'researching', 'candidate', 'validated_beneficiary', 'rejected'}:
            raise ValueError('unsupported path state')
        for field in ['purchase_dependency', 'supply_response', 'next_action', 'falsifier']:
            if not p.get(field):
                gaps.append(f"{p['id']}:{field}")
        required = ['independent_constraint_evidence', 'beneficiary_industry', 'issuer_capture_evidence']
        missing = [f for f in required if not p.get(f)]
        if p['status'] == 'validated_beneficiary' and missing:
            raise ValueError('route selection alone cannot validate a beneficiary')
        if p['status'] in {'researching', 'candidate'}:
            gaps.append(f"{p['id']}:downstream_validation_open")
        if p['status'] == 'rejected' and not p.get('rejection_evidence'):
            raise ValueError('rejection requires evidence, not missing data')
    return {'schema_version':'two-axis-review-v1','gaps':gaps,
            'research_complete':bool(companies) and bool(packet['paths']) and not gaps,
            'publication_eligible':False,
            'meaning':'Checks supplied research completeness; does not certify claims or approve investments.'}
