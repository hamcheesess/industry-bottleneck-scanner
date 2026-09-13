"""Reproduce reviewed research bundle without providers or model calls."""
import json
from pathlib import Path
from industry_bottleneck_scanner.two_axis_research import review_two_axes
HERE=Path(__file__).resolve().parent
p=json.loads((HERE/'input.json').read_text())
r=review_two_axes(p)
f=p['financial_facts'];h=f['HPS'];u=f['HUBB']
r['calculations']={'HPS_cfo_minus_capex_CADm':round(h['cfo']-h['capex'],3),
 'HPS_max_working_capital_use_for_cfo_capex_breakeven_CADm':round(h['working_capital_use']+h['cfo']-h['capex'],3),
 'HUBB_capex_USDm':u['cfo']-u['fcf'],
 'HUBB_guidance_fcf_per_diluted_share_proxy':[x*u['annual_guidance_conversion'] for x in u['annual_guidance_eps']],
 'HUBB_guidance_fcf_yield_proxy':[x*u['annual_guidance_conversion']/p['prices']['HUBB']['value'] for x in u['annual_guidance_eps']]}
r['calculation_posture']='Historical arithmetic and management-guidance proxy; not normalized FCFE or consensus.'
(HERE/'review.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
old=(HERE.parent/'transformers-asof-2025-08-29'/'report-source.md').read_text().split('---PAGE---')
market=next(x for x in old if x.strip().startswith('# 1. 시장 이상'))
names={'A':'Arcosa · 2025 Q2 실적','V':'Valmont · 2025 Q2 실적','C':'AEP · 2025-07-30 고객 부하 약정','L':'DOE · 데이터센터 전력 수요','D':'DOE · 대형 전력변압기 보고서','G':'GEV · 2025 Q2 원 실적','S':'Siemens Energy · FY2025 Q3','H':'Hitachi Energy · 2025-03 부품 투자','U':'Hubbell · 2025 Q2 실적','T':'HPS · 2025 Q2 보고서','Y':'Yash · 2025-05-28 실적발표 전사록'}
links='\n'.join(f"[{s['id']} · {names.get(s['id'],'원문')}]({s['url']})" for s in p['sources'] if s['id'] not in ['Q','P'])
links+='\n[M · 시장 이상 원 관측](https://github.com/hamcheesess/industry-bottleneck-scanner/blob/8e3d5922d5676c71cef4e7dc17c2e70171c7e633/experiments/company_exposure/transformers-asof-2025-08-29/market-origin.json)'
links+='\n'+'\n'.join(f"[{sid} · {ticker} 과거 종가]({p['prices'][ticker]['url']})" for sid,ticker in [('UP','HUBB'),('TP','HPS-A.TO')])
text=(HERE/'report-template.md').read_text().replace('{{MARKET_PAGE}}',market).replace('{{SOURCE_LINKS}}',links)
assert '{{' not in text
(HERE/'report-source.md').write_text(text)
print(json.dumps({'complete':r['research_complete'],'gaps':len(r['gaps']),'calculations':r['calculations']},ensure_ascii=False))
