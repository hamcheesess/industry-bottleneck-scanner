"""Build a bounded, reviewed historical information set without provider calls.

PYTHONPATH=src python experiments/company_exposure/transformers-asof-2025-08-29/build_review.py --market-dir /path/to/calibration/output
"""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from industry_bottleneck_scanner.research_information_set import validate_information_set

ROOT=Path(__file__).resolve().parent
SOURCES=[
 ('A','2025-08-07','Arcosa','issuer_primary','https://s2.q4cdn.com/158938184/files/doc_financials/2025/q2/Arcosa-Inc-Announces-Second-Quarter-2025-Results.pdf','Dated original earnings release; PDF p1 publication, p3 claims'),
 ('V','2025-07-22','Valmont','issuer_primary','https://investors.valmont.com/news-releases/news-release-details/valmont-reports-second-quarter-2025-results-and-raises-full-year','Dated original earnings release and product-line table'),
 ('C','2025-07-30','AEP','customer_primary','https://www.aep.com/news/stories/view/10354/','Dated original customer earnings release'),
 ('L','2024-12-20','DOE / underlying LBNL study','government_research','https://www.energy.gov/articles/doe-releases-new-report-evaluating-increase-electricity-demand-data-centers','Dated DOE announcement; same underlying study as LBNL report, counted once'),
 ('D','2024-10-31','US DOE','government_technical','https://www.energy.gov/sites/default/files/2024-10/EXEC-2022-001242%20-%20Large%20Power%20Transformer%20Resilience%20Report%207-10-24.pdf','July 2024 report, October 2024 hosting path; conservative month-end bound, not exact publication day'),
 ('G','2025-07-23','GE Vernova','issuer_primary','https://www.gevernova.com/sites/default/files/gev_webcast_pressrelease_07232025.pdf','Dated original release PDF; use original segment presentation, not later restatement'),
 ('S','2025-08-06','Siemens Energy','issuer_primary','https://assets.siemens-energy.com/dam/a181bfed-4213-4a9e-8d6a-b331004a9a73/2025-08-06_ER_E_final-pdf_Original%20file.pdf','Dated original release PDF p3'),
 ('H','2025-03-10','Hitachi Energy','supplier_primary','https://www.hitachienergy.com/us/en/news-and-events/press-releases/2025/03/hitachi-energy-invests-additional-250-million-usd-to-address-global-transformer-shortage','Dated CERAWeek press announcement'),
]


def save(name,value):
    (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def build(market_dir):
    sources=[]
    for sid,date,entity,kind,url,basis in SOURCES:
        lower=datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        sources.append({'source_id':sid,'source_entity':entity,'source_class':kind,'url':url,
          'available_from':lower.isoformat(),'available_no_later_than':(lower+timedelta(days=1)).isoformat(),
          'retrieved_at':'2026-09-07T00:00:00+00:00','availability_basis':basis,
          'availability_precision':'conservative date bound; not original ingest timestamp'})
    # DOE date is a conservative range from document month through hosting month.
    next(s for s in sources if s['source_id']=='D')['available_from']='2024-07-01T00:00:00+00:00'
    claims=[]
    for cid,sids,kind,end,text in [
      ('structure_demand',['A','V'],'observed','2025-06-30','최초 바스켓 두 기업에서 전력망 수요 지지; 다른 네 기업 원인 미확정'),
      ('customer_load',['C'],'forecast','2030-12-31','당시 발표한 고객 약정 기반 신규 부하; 장비 발주와 다름'),
      ('dc_energy',['L'],'forecast','2028-12-31','당시 연구의 데이터센터 전력 사용 시나리오'),
      ('lpt_constraints',['D'],'observed','2024-07-31','제품별 설계·조달과 장기 납기 제약'),
      ('earnings_conversion',['G','S'],'observed','2025-06-30','당시 전력망 부문에서 실적·마진 전환 관측'),
      ('component_supply_response',['H'],'forecast','2027-12-31','핵심 부품 증산 투자 계획; 실제 가동량 미확정'),
      ('component_hypothesis',['H','D'],'inference','2025-08-29','부품 경로 조사 필요; 독립 병목·가치 격차 승인 아님'),
    ]:
        claims.append({'claim_id':cid,'source_ids':sids,'kind':kind,'observation_end':end+'T00:00:00+00:00','text_ko':text})
    packet={'schema_version':'research-information-set-v1','information_cutoff':'2025-08-29T20:00:00+00:00',
       'cutoff_timezone':'America/New_York','case_selection':'user_fixed_retrospective_exercise_not_blind_backtest',
       'sources':sources,'claims':claims}
    review=validate_information_set(packet)
    save('information-set.json',packet);save('information-set-review.json',review)
    rows=[]
    for date in ['2025-05-30','2025-06-30','2025-07-31','2025-08-29']:
        path=market_dir/('as_of='+date)/'industry_market_triggers.json'
        data=json.loads(path.read_text());entry=next(x for x in data['triggers'] if x['bucket'].startswith('SIC 3440'))
        rows.append({'as_of':date,'trigger':entry,'original_relative_path':str(path.relative_to(market_dir)),
                     'original_sha256':sha256(path.read_bytes()).hexdigest()})
    if [r['trigger']['triggered'] for r in rows] != [False,False,False,True]:
        raise ValueError('market history differs from reviewed report')
    save('market-origin.json',{'source_run':32717734277,'information_cutoff':packet['information_cutoff'],
         'rows':rows,'later_quality_or_persistence_used':False,'first_daily_detection_established':False})
    save('research-audit.json',{
      'canonical_source_sha256':sha256((ROOT/'report-source.md').read_bytes()).hexdigest(),
      'exclusions':[
        {'lead':'Arcosa Q2 2026; AEP Q2 2026; GEV Q2 2026','reason':'post-cutoff publications and actuals'},
        {'lead':'Hitachi 2025-09-04 manufacturing announcement','reason':'post-cutoff publication despite same calendar year'},
        {'lead':'Valmont 2025 Q2 transcript issuer URL','url':'https://investors.valmont.com/static-files/5d92dcf4-849d-43cf-8bc9-74f9d2657646','reason':'full text access failed; lead only, no claim admitted'},
        {'lead':'later comparative columns for 2025 GEV','reason':'later source vintage not used'},
        {'lead':'post-August29 persistence counts','reason':'future observations not initial selection evidence'}],
      'unresolved':['remaining four trigger constituents causal attribution','daily signal onset','national product-level deficit',
                    'company product cash flows','historical price and market expectations','nine numerical scenarios'],
      'calculations':[{'label':'Valmont Utility YoY sales growth','formula':'350416 / 332395 - 1','value':350416/332395-1,'source':'V'},
                      {'label':'Siemens observed incremental profit ratio','formula':'(448 - 237) / (2819 - 2299)',
                       'value':(448-237)/(2819-2299),'source':'S','forecast_unit_margin':False}],
      'actual_tokens':None,'token_measurement_note':'complete billable counts unavailable; do not invent',
      'historical_registry_write':False,'db_publication':False,
      'report_status':'historical_hypothesis_report_investment_valuation_not_evaluable'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--market-dir',type=Path,required=True)
    build(p.parse_args().market_dir)
