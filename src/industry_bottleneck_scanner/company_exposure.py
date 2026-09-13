"""Research-only company exposure gate; never a publication or trading approval."""
from datetime import datetime
from hashlib import sha256
import json


def assess_exposure(packet):
    if packet.get('schema_version') != 'company-exposure-research-v1':
        raise ValueError('unsupported schema')
    cutoff = datetime.fromisoformat(packet['as_of'])
    if cutoff.tzinfo is None:
        raise ValueError('timezone required')
    if packet.get('mode') != 'current_research':
        raise ValueError('historical replay requires separately frozen evidence')
    seen = set()
    results = []
    for company in packet['companies']:
        identity = company['company_id']
        if identity in seen:
            raise ValueError('duplicate company')
        seen.add(identity)
        evidence = company['evidence']
        if not evidence:
            raise ValueError('evidence required')
        for source in evidence:
            if not source['url'].startswith('https://'):
                raise ValueError('source URL required')
            # Retrieval is not evidence of historical availability.
            for field in ('retrieved_at', 'published_at'):
                value = source.get(field)
                if value is None and field == 'published_at':
                    continue
                when = datetime.fromisoformat(value)
                if when.tzinfo is None or when > cutoff:
                    raise ValueError('invalid source timestamp')
        gaps = company['missing_inputs']
        if not gaps or not all(isinstance(x, str) and x.strip() for x in gaps):
            raise ValueError('research packet must disclose unresolved inputs')
        results.append({
            'company_id': identity,
            'status': 'needs_exposure_attribution' if company['node_match'] != 'direct' else 'needs_quantification',
            'reason_ko': company['reason_ko'],
            'missing_inputs': gaps,
            'historical_replay_eligible': False,
            'financial_scenario_ready': False,
            'publication_eligible': False,
        })
    return {'schema_version': 'company-exposure-review-v1', 'as_of': packet['as_of'],
            'input_sha256': sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'companies': results}
