"""Educational scenario calculator. USD million; assumptions are NOT company guidance.
Whole operating-business EV only. No unsupported per-share target; Up-C/TRA gate remains.
"""
from pathlib import Path
import json
P=Path(__file__).parent
Q={'systems_revenue':670.952,'software_revenue':12.765,'operations_revenue':37.121,'systems_cost':523.607,'software_cost':3.486,'operations_cost':32.835,'revenue':720.838,'operating_income':32.895,'SBC':50.519,'CFO':-147.297,'capex_internal_software':17.333,'nine_month_CFO':305.584,'nine_month_capex':62.753,'cash':1746.446,'economic_share_proxy_m':603.863978,'price':42.13}
# No debt financing adjustment; operating leases remain within operating economics.
market_EV_proxy=Q['price']*Q['economic_share_proxy_m']-Q['cash']
def dcf(g,m5,sc,w=.11):
 prev=Q['revenue']*4;rows=[]
 for y in range(1,11):
  r=prev*(1+(g if y<=5 else .08));m=.0456+(m5-.0456)*min(y/5,1)
  nopat=r*m*.75;ri=(r-prev)/sc;fcff=nopat-ri
  rows.append({'year':y,'revenue':r,'margin':m,'NOPAT':nopat,'reinvestment':ri,'FCFF':fcff});prev=r
 tv=rows[-1]['NOPAT']*1.03*(1-.03/.15)/(w-.03)
 ev=sum(x['FCFF']/(1+w)**x['year'] for x in rows)+tv/(1+w)**10
 return {'years':rows,'EV':ev,'terminal_weight':tv/(1+w)**10/ev}
cases={n:dcf(g,m,sc) for n,g,m,sc in [('delay',.10,.09,3),('base',.20,.14,4),('execution',.30,.19,5)]}
lo,hi=0,1
for _ in range(100):
 mid=(lo+hi)/2
 if dcf(mid,.14,4)['EV']<market_EV_proxy:lo=mid
 else:hi=mid
roi={}
for name,annual in [('low',3),('base',4),('high',5)]:
 roi[name]={'annual_net_saving':annual,'simple_payback_years':20/annual,'NPV_8_year_10pct':-20+sum(annual/(1.1)**i for i in range(1,9))}
out={'reported_Q3_USD_m':Q,'derived_margins':{k:(Q[k+'_revenue']-Q[k+'_cost'])/Q[k+'_revenue'] for k in ['systems','software','operations']},'market_EV_proxy':market_EV_proxy,'cases':cases,'reverse_growth_first_5_years':(lo+hi)/2,'customer_example_USD_m':roi,'source':'https://ir.symbotic.com/news-releases/news-release-details/symbotic-reports-third-quarter-fiscal-year-2026-results','assumptions':['Latest quarter times four is starting scale, not annual forecast','SBC retained in operating margin; no blanket EBITDA-to-FCF conversion','Tax25%, years6-10 growth8%, terminalgrowth3%, terminalROIC15%, WACC11%','Incremental sales/capital includes net reinvestment; future Exol funding is NOT modeled','Economic share proxy sums disclosed A,V1,V3 paired units; NOT fully diluted legal valuation','Customer ROI numbers are hypothetical not vendor quote; no tax/salvage/inflation','No target price or trade approval']}
for x in cases.values():
 for r in x['years']:assert abs(r['NOPAT']-r['reinvestment']-r['FCFF'])<1e-8
assert abs(dcf(out['reverse_growth_first_5_years'],.14,4)['EV']-market_EV_proxy)<1e-5
(P/'economics.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k in ['derived_margins','market_EV_proxy','reverse_growth_first_5_years','customer_example_USD_m']},indent=2))
for n,c in cases.items():print(n,'EV',round(c['EV']), 'R5',round(c['years'][4]['revenue']),'FCF1',round(c['years'][0]['FCFF']),'FCF5',round(c['years'][4]['FCFF']),'TV',round(c['terminal_weight']*100))
