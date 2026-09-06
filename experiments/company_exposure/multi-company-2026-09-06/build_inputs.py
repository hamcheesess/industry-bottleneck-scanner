"""Reproduce the review packet and calculations from explicitly reviewed inputs.

Run with PYTHONPATH=src and --market-dir pointing at the extracted, original
provider-free-market-calibration output. No provider calls or historical writes.
Source metric definitions are retained; unavailable forecasts remain null.
"""
import argparse
import hashlib
import json
from pathlib import Path
from industry_bottleneck_scanner.company_exposure import assess_exposure

ROOT = Path(__file__).resolve().parent
AS_OF = '2026-09-06T23:59:59+00:00'
SOURCES = {
 'S1': ('Arcosa','2026-08-05','issuer_primary','https://www.sec.gov/Archives/edgar/data/1739445/000173944526000124/exh991earningsrelease63020.htm'),
 'S2': ('US DOE',None,'government_primary','https://www.energy.gov/sites/default/files/2024-10/EXEC-2022-001242%20-%20Large%20Power%20Transformer%20Resilience%20Report%207-10-24.pdf'),
 'S3': ('AEP','2026-07-30','customer_primary','https://docs.aep.com/docs/newsroom/resources/earnings/2026-07/2Q26EarningsReleasePresentation.pdf'),
 'S4': ('Texas Governor','2026-08-03','government_primary','https://gov.texas.gov/news/post/governor-abbott-directs-comprehensive-data-center-audit'),
 'S5': ('GE Vernova','2026-02-02','issuer_primary','https://www.gevernova.com/news/press-releases/ge-vernova-completes-prolec-ge-acquisition'),
 'S6': ('GE Vernova','2026-07-22','issuer_primary','https://www.sec.gov/Archives/edgar/data/1996810/000199681026000147/gevpressrelease2q26.htm'),
 'S7': ('Siemens Energy','2026-08-05','issuer_primary','https://www.siemens-energy.com/us/en/home/press-releases/earnings-release-q3-fy-2026.html'),
 'S8': ('Siemens Energy','2024-02-15','issuer_primary','https://www.siemens-energy.com/global/en/home/stories/transformer-manufacturing-and-service-expansion-in-us.html'),
 'S9': ('Hyosung Heavy Industries','2026-07-31','issuer_primary','https://www.hyosungheavyindustries.com/download/5815'),
 'S10': ('HD Hyundai Electric','2026-07-28','issuer_primary','https://www.hd-hyundaielectric.com/elect/en/IR/IRdata1.jsp'),
 'S11': ('Hitachi Energy','2026-06-29','issuer_primary','https://www.hitachienergy.com/news-and-events/press-releases/2026/06/hitachi-energy-breaks-ground-on-the-nation-s-largest-facility-for-the-production-of-large-power-transformers-in-south-boston-virginia'),
 'S12': ('GE Vernova','2026-07-22','issuer_primary','https://www.gevernova.com/sites/default/files/gev_webcast_transcript_07222026.pdf'),
 'S13': ('Eaton',None,'issuer_primary','https://www.eaton.com/us/en-us/company/news-insights/news-releases/2026/eaton-reports-record-second-quarter-2026-results.html'),
 'S14': ('Hammond Power Solutions',None,'issuer_primary','https://americas.hammondpowersolutions.com/products/medium-voltage-distribution/vpi-up-to-35kv-class'),
}


def dump(name,data):
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def build(market_dir):
    ledger={}
    for sid,(entity,date,kind,url) in SOURCES.items():
        ledger[sid]={'source_entity':entity,'published_at':date+'T23:59:59+00:00' if date else None,
                     'retrieved_at':'2026-09-06T00:00:00+00:00','source_class':kind,'url':url,
                     'timestamp_precision':'date_only; retrieved_date_only','historical_replay_eligible':False}
    ledger['S2']['date_note']='Report dated July 2024; URL hosted October 2024. No exact publication instant asserted.'
    ledger['S8']['date_note']='Page displays 2024-02-15; current retrieved version not independently archived as of that date.'
    ledger['S10']['download']={'url':'https://www.hd-hyundaielectric.com/elec/common/fileDown.jsp','method':'POST',
       'form':{'fileName':'2026_07_28_143006_1.pdf','filePath':'/home/app/hd_electric/upload/elec/presentation/',
               'fileOrgName':'HD Hyundai Electric_2Q26 Earning Release.pdf'},'locator':'IR list, 2Q2026; PDF pages 4-6'}
    ledger['S7']['document_url']='https://assets.siemens-energy.com/dam/d0147174-31a9-4a78-b062-b49d00428fc4/earnings-release-q3-fy2026-en-pdf_Original%20file.pdf'
    dump('source-ledger.json',ledger)
    specs=[
      ('ge-vernova','us_candidate','needs_product_attribution',['S5','S6','S12'],'인수 연결 효과와 대형 변압기 실적·현금흐름을 분리해야 한다.'),
      ('siemens-energy','non_us_supply_comparator','direct',['S7','S8'],'직접 제조는 확인했지만 공장별 출하·제품 실적·시장 기대는 미확정이다.'),
      ('hyosung-heavy-industries','non_us_supply_comparator','direct',['S9'],'미국 초고압 제품 실적에서 변압기·차단기 및 건설 현금흐름을 분리해야 한다.'),
      ('hd-hyundai-electric','non_us_supply_comparator','direct',['S10'],'제품 구분과 자회사 실적을 중복 없이 연결하고 납품 일정을 검증해야 한다.'),
      ('hitachi-energy','non_us_supply_comparator','direct',['S11'],'착공 단계의 공장을 단기 출하량으로 사용할 수 없고 투자 법인 연결이 필요하다.'),
      ('eaton','adjacent_product_comparator','adjacent_only',['S13'],'확인한 전기부문 실적만으로 대형 변압기 직접 노출을 승인할 수 없다.'),
      ('hammond-power-solutions','adjacent_product_comparator','adjacent_only',['S14'],'확인한 중전압 건식 제품만으로 대형 송전용 변압기 노출을 증명할 수 없다.'),
    ]
    packet={'schema_version':'company-exposure-research-v1','mode':'current_research','as_of':AS_OF,
            'historical_reference_only':'early-ai-electrical-2026-08-21-two-root-v2',
            'universe_note_ko':'한 산업 경로의 목적 표집 7개사. 미국 자동 선별 유니버스 확장이나 매수 순위가 아니다.',
            'companies':[]}
    for cid,role,match,sids,reason in specs:
        packet['companies'].append({'company_id':cid,'role':role,'node_match':match,'reason_ko':reason,
          'missing_inputs':['대형 변압기 제품별 유효 공급·단가·출하','동일 범위의 영업이익·FCF','같은 날짜의 가격·시장 기대'],
          'evidence':[{'source_id':sid,**ledger[sid]} for sid in sids]})
    dump('company-exposure-input.json',packet)
    review=assess_exposure(packet)
    if any(c['publication_eligible'] for c in review['companies']):
        raise ValueError('research-only packet must not publish')
    dump('company-exposure-review.json',review)
    trigger_path=market_dir/'as_of=2025-08-29/industry_market_triggers.json'
    quality_path=market_dir/'market_trigger_quality_review.json'
    t=json.loads(trigger_path.read_text()); q=json.loads(quality_path.read_text())
    bucket='SIC 3440 — FABRICATED STRUCTURAL METAL PRODUCTS'
    trigger=next(x for x in t['triggers'] if x['bucket']==bucket)
    stability=next(x for x in q['latest_bucket_stability'] if x['bucket']==bucket)
    if stability['first_triggered_as_of']!='2025-08-29' or trigger['score']!=59.17:
        raise ValueError('original trigger differs from reviewed report; stop and re-review')
    dump('market-selection-extract.json',{'schema_version':'research-market-extract-v1',
       'run_id':32717734277,'trigger':trigger,'stability':stability,'benchmark_ticker':t['benchmark_ticker'],
       'policy':t['policy'],'source':t['source'],'claim_scope':'first sampled detection; not exact daily onset',
       'files':[{'path':str(p.relative_to(market_dir)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [trigger_path,quality_path]]})
    metrics=[
      ('gev_electrification_revenue',3637,'USD_million','2026Q2','Electrification','revenue','S6'),
      ('gev_electrification_ebitda',671,'USD_million','2026Q2','Electrification','segment_EBITDA','S6'),
      ('siemens_grid_revenue',3624,'EUR_million','2026Q3_fiscal_Apr_Jun','Grid Technologies','revenue','S7'),
      ('siemens_grid_profit_before_special',722,'EUR_million','2026Q3_fiscal_Apr_Jun','Grid Technologies','profit_before_special_items','S7'),
      ('hyosung_heavy_revenue',1137.1,'KRW_billion','2026Q2','Heavy Industries','revenue','S9'),
      ('hyosung_heavy_op',229.8,'KRW_billion','2026Q2','Heavy Industries','operating_profit','S9'),
      ('hyundai_total_revenue',1141.8,'KRW_billion','2026Q2','consolidated','revenue','S10'),
      ('hyundai_total_op',287.0,'KRW_billion','2026Q2','consolidated','operating_profit','S10'),
      ('hyundai_power_revenue',535.9,'KRW_billion','2026Q2','Power category; subsidiaries separately presented','revenue','S10'),
      ('gev_reported_fcf',5107,'USD_million','2026Q2','consolidated','reported_FCF','S6'),
      ('gev_wc_benefit',6400,'USD_million','2026Q2','consolidated','rounded_working_capital_cash_benefit','S12'),
    ]
    dump('reviewed-financial-facts.json',{'schema_version':'reviewed-financial-facts-v1','as_of':AS_OF,
       'metrics':[dict(zip(['id','value','unit','period','scope','definition','source_id'],m)) for m in metrics],
       'calculations':[
          {'id':'siemens_observed_incremental_profit_ratio','value':round((722-448)/(3624-2819),6),
           'formula':'(722 - 448) / (3624 - 2819)','source_ids':['S7'],'use':'observed two-quarter change, not forecast transformer margin'},
          {'id':'gev_guidance_ebitda_bounds','value':[14500*.18,15000*.20],'unit':'USD_million',
           'period':'FY2026','scope':'Electrification','source_ids':['S6'],'use':'derived company-guidance envelope, not FCF or independent forecast'},
          {'id':'gev_fcf_minus_wc','value':5107-6400,'unit':'USD_million','source_ids':['S6','S12'],
           'use':'rounded diagnostic only; NOT normalized or transformer FCF'}],
       'financial_scenarios':None,'market_expectation_gap':None,'valuation':None,'publication_eligible':False})
    dump('evidence-gap-matrix.json',{'as_of':AS_OF,'research_scope':'seven-company comparison of one industry path',
       'closed':['first sampled anomaly metrics','manufacturer product-boundary comparison','segment actual profitability','customer contract and regulatory counterevidence'],
       'open':['daily anomaly onset and company contributions','national product-level supply deficit','company shipments, ASP, costs and FCF attribution','same-date prices and independent expectations','nine quantitative scenarios per finalist','regulatory audit resolution'],
       'rejected_source_uses':['OSTI 3363379: full text/publication not verified; not admitted','unverified Hyosung installed-share claim: omitted','Texas PUCT 59142_53 PDF inaccessible: replaced by governor primary release'],
       'token_feedback':{'input_tokens':None,'output_tokens':None,'cached_tokens':None,'reason':'tooling exposes no complete billable accounting; do not estimate',
         'improvement':'retain reviewed units, provenance and open questions; reuse issuer facts without re-generating final prose'},
       'historical_replay_mutation':False,'final_report_db_write':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--market-dir',type=Path,required=True)
    build(parser.parse_args().market_dir)
