import json
from pathlib import Path
import pytest
from industry_bottleneck_scanner.research_agent_plan import build_plan
from industry_bottleneck_scanner.research_agent_runtime import inspect_response, run_pilot

CUTOFF='2025-08-29T20:00:00Z'
def response(date='2025-07-01T00:00:00Z'):
    evidence=dict(claim='Orders increased',source_url='https://example.org/release',source_entity='issuer',published_at=date,locator='p1',observation_period='Q2',fact_or_assumption='fact',counterevidence='capacity expansion')
    return dict(id='test',status='completed',usage={'input_tokens':20,'output_tokens':30},output=[{'type':'web_search_call','action':{'sources':[{'url':evidence['source_url']}]}},{'type':'message','content':[{'type':'output_text','text':json.dumps({'evidence':[evidence],'unresolved_questions':[]})}]}])

def plan():
    config=json.loads((Path(__file__).resolve().parents[1]/'research_agents/roles.json').read_text())
    return build_plan(config,'transformers',CUTOFF)

def test_future_and_untraced_evidence_blocked():
    assert inspect_response(response('2026-01-01T00:00:00Z'),CUTOFF)['status']=='blocked'
    r=response();r['output'].pop(0)
    assert inspect_response(r,CUTOFF)['status']=='blocked'
    assert inspect_response(response(),CUTOFF)['status']=='needs_source_review'

def test_resume_never_repeats_paid_calls_and_preserves_usage(tmp_path):
    calls=[]
    def transport(payload):
        calls.append(payload);return response()
    result=run_pilot(plan(),'explicit-model',tmp_path,transport)
    assert len(calls)==2
    assert result['roles'][0]['usage']['input_tokens']==20
    run_pilot(plan(),'explicit-model',tmp_path,transport)
    assert len(calls)==2
    with pytest.raises(ValueError,match='identity'):
        run_pilot(plan(),'other-model',tmp_path,transport)

def test_uncertain_transport_not_automatically_retried(tmp_path):
    calls=[]
    def transport(payload):
        calls.append(1);raise RuntimeError('transport_outcome_unknown')
    run_pilot(plan(),'model',tmp_path,transport)
    result=run_pilot(plan(),'model',tmp_path,transport)
    assert len(calls)==2
    assert all(s['status']=='blocked' for s in result['roles'])
    assert not result['publication_eligible']

def test_incomplete_or_invalid_json_is_blocked():
    r=response();r['status']='incomplete'
    assert inspect_response(r,CUTOFF)['status']=='blocked'
    r['output'][1]['content'][0]['text']='not json'
    assert inspect_response(r,CUTOFF)['status']=='blocked'

@pytest.mark.parametrize('code,expected', [('insufficient_quota','insufficient_quota:429'),('rate_limit_exceeded','rate_limit_exceeded:429'),('secret-value','quota_or_rate_limit:429')])
def test_safe_http_classification(monkeypatch,code,expected):
    import io
    from urllib.error import HTTPError
    from industry_bottleneck_scanner import research_agent_runtime as runtime
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    def fail(*args,**kwargs):
        raise HTTPError('https://api.openai.com/v1/responses',429,'redacted',{},io.BytesIO(json.dumps({'error':{'code':code,'message':'never print this'}}).encode()))
    monkeypatch.setattr(runtime,'urlopen',fail)
    with pytest.raises(RuntimeError) as exc:
        runtime.call_api({})
    assert str(exc.value)==expected
