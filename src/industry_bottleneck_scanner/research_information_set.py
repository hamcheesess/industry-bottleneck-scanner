"""Validate reviewed availability metadata; never certify historical truth.

Publication and forecast periods are different clocks. Human-reviewed availability
bounds are required. This utility does not approve causal edges or publication.
"""
from datetime import datetime


def _time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed


def validate_information_set(packet):
    if packet.get('schema_version') != 'research-information-set-v1':
        raise ValueError('unsupported research information set')
    cutoff = _time(packet['information_cutoff'])
    sources = {}
    for source in packet['sources']:
        identity = source['source_id']
        if identity in sources:
            raise ValueError('duplicate source ID')
        if not source['url'].startswith('https://') or not source['availability_basis'].strip():
            raise ValueError('source and availability basis required')
        lower = _time(source['available_from'])
        upper = _time(source['available_no_later_than'])
        retrieved = _time(source['retrieved_at'])
        if lower > upper or upper > cutoff or upper > retrieved:
            raise ValueError('unresolved or post-cutoff availability')
        sources[identity] = source
    if not sources:
        raise ValueError('sources required')
    ids = set()
    for claim in packet['claims']:
        if claim['claim_id'] in ids:
            raise ValueError('duplicate claim ID')
        ids.add(claim['claim_id'])
        if not claim['source_ids'] or any(s not in sources for s in claim['source_ids']):
            raise ValueError('unknown or missing source')
        if claim['kind'] not in {'observed', 'forecast', 'inference'}:
            raise ValueError('unsupported claim kind')
        # Future forecast horizons are legal, future observations are not.
        if claim['kind'] == 'observed' and _time(claim['observation_end']) > cutoff:
            raise ValueError('post-cutoff observation')
        if not claim['text_ko'].strip():
            raise ValueError('claim text required')
    if not ids:
        raise ValueError('claims required')
    return {'schema_version':'research-information-set-review-v1',
            'information_cutoff':packet['information_cutoff'],
            'source_count':len(sources),'claim_count':len(ids),
            'temporal_metadata_passed':True,
            'historical_availability_independently_certified':False,
            'publication_eligible':False,
            'investment_status':'not_evaluable_missing_data'}
