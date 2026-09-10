"""Provider-free agent contracts and dependency planning; does not call a model."""
from datetime import datetime
import argparse
import json
from pathlib import Path


def build_plan(config, topic, cutoff):
    date = datetime.fromisoformat(cutoff)
    if date.tzinfo is None:
        raise ValueError('cutoff must include timezone')
    roles = config['roles']
    ids = {r['id'] for r in roles}
    if len(ids) != len(roles) or not roles:
        raise ValueError('unique roles required')
    if config['max_parallel'] < 1:
        raise ValueError('positive concurrency required')
    for r in roles:
        if set(r['depends_on']) - ids or r['output_token_limit'] <= 0:
            raise ValueError('invalid dependencies or budget')
    done, waves = set(), []
    while done != ids:
        ready = [r['id'] for r in roles if r['id'] not in done and set(r['depends_on']) <= done]
        if not ready:
            raise ValueError('dependency cycle')
        wave = ready[:config['max_parallel']]
        waves.append(wave)
        done.update(wave)
    return dict(schema_version='research-agent-plan-v1', topic=topic,
                information_cutoff=cutoff, waves=waves, roles=roles,
                report_sections=config['report_sections'],
                status='planned_not_executed', publication_eligible=False,
                maximum_output_tokens_one_pass=sum(r['output_token_limit'] for r in roles),
                budget_note='Output caps only; input, reasoning, searches and retries add cost.',
                evidence_fields=['claim','source_url','source_entity','published_at','locator',
                                 'observation_period','fact_or_assumption','counterevidence'],
                telemetry_fields=['role','attempt','model','input_tokens','output_tokens',
                                  'cached_input_tokens','tool_calls','elapsed_seconds',
                                  'new_independent_evidence','blocking_issues'])


def runnable(plan, completed):
    """Only reviewed completion records satisfy a predecessor; failures do not."""
    accepted = {k for k,v in completed.items() if v.get('status') == 'accepted'}
    return [r['id'] for r in plan['roles'] if r['id'] not in completed
            and set(r['depends_on']) <= accepted]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--topic', required=True)
    p.add_argument('--cutoff', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    plan = build_plan(json.loads(a.config.read_text()), a.topic, a.cutoff)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
