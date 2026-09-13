import json
from pathlib import Path
import pytest
from industry_bottleneck_scanner.research_agent_plan import build_plan, runnable

CONFIG = Path(__file__).resolve().parents[1] / 'research_agents/roles.json'

def plan():
    return build_plan(json.loads(CONFIG.read_text()), 'transformers', '2025-08-29T20:00:00Z')

def test_dependencies_and_no_automatic_publication():
    p = plan()
    assert p['waves'] == [['demand','supply'],['synthesis'],['review'],['report']]
    assert not p['publication_eligible']
    assert runnable(p, {'demand':{'status':'accepted'},'supply':{'status':'failed'}}) == []
    assert runnable(p, {'demand':{'status':'accepted'},'supply':{'status':'accepted'}}) == ['synthesis']

def test_cycle_rejected():
    c = json.loads(CONFIG.read_text())
    c['roles'][0]['depends_on'] = ['report']
    with pytest.raises(ValueError, match='cycle'):
        build_plan(c, 'test', '2025-08-29T20:00:00Z')

def test_naive_date_rejected():
    with pytest.raises(ValueError, match='timezone'):
        build_plan(json.loads(CONFIG.read_text()), 'test', '2025-08-29')
