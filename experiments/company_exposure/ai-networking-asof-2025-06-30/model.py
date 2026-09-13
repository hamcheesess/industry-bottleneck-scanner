"""Report-support FCFF scenarios. No provider calls; all forecasts are assumptions.
USD billions, billion diluted-share proxies; valuation date 2025-06-30.
SBC remains in EBIT. FCFF excludes financing flows. No trading recommendation.
"""
import json
from pathlib import Path
ROOT=Path(__file__).parent
INPUTS={
 'ANET':dict(price=102.31,shares=1.2792,cash=8.1496,debt=0,preferred=0,nci=0,tax=.21,da=.007,capex=.018,nwc=.015,wacc=.10,terminal=.03,scenarios={'bear':[8.6,.36,.10,.05],'base':[9.2,.41,.18,.09],'bull':[10,.43,.26,.12]}),
 'CSCO':dict(price=69.38,shares=4.002,cash=15.6,debt=29.279,preferred=0,nci=0,tax=.21,da=.035,capex=.017,nwc=.005,wacc=.09,terminal=.025,scenarios={'bear':[56,.22,.02,.02],'base':[59,.25,.05,.03],'bull':[62,.28,.08,.04]}),
 'COHR':dict(price=89.21,shares=.1591,cash=.8903,debt=3.7318,preferred=2.4616,nci=.3546,tax=.23,da=.05,capex=.06,nwc=.015,wacc=.10,terminal=.03,scenarios={'bear':[5.8,.08,.05,.03],'base':[6.5,.12,.12,.05],'bull':[7.2,.15,.20,.08]})}
def calculate(c,s,wacc=None,growth=None):
 r,m,g,late=s;g=g if growth is None else growth;w=c['wacc'] if wacc is None else wacc
 assert w>c['terminal']
 rows=[]
 for year in range(1,11):
  if year>1:r*=1+(g if year<=5 else late)
  ebit=r*m;tax=ebit*c['tax'];da=r*c['da'];capex=r*c['capex'];nwc=r*c['nwc']
  fcf=ebit-tax+da-capex-nwc
  rows.append(dict(year=year,revenue=r,ebit=ebit,tax=tax,da=da,capex=capex,delta_nwc=nwc,fcff=fcf,pv=fcf/(1+w)**year))
 terminal=rows[-1]['fcff']*(1+c['terminal'])/(w-c['terminal'])/(1+w)**10
 ev=sum(x['pv'] for x in rows)+terminal
 bridge=c['cash']-c['debt']-c['preferred']-c['nci'];raw_equity=ev+bridge;equity=max(0,raw_equity)
 return dict(unfloored_equity=raw_equity,value_per_share=equity/c['shares'],upside=equity/c['shares']/c['price']-1,ev=ev,equity=equity,terminal_share=terminal/ev,years=rows)
def reverse(c):
 target=c['price']*c['shares'];lo,hi=-.3,1.0
 for _ in range(120):
  mid=(lo+hi)/2
  if calculate(c,c['scenarios']['base'],growth=mid)['equity']>target:hi=mid
  else:lo=mid
 return (lo+hi)/2
if __name__=='__main__':
 out={}
 for ticker,c in INPUTS.items():
  vals={name:calculate(c,s) for name,s in c['scenarios'].items()}
  sensitivity={str(round(w,3)):calculate(c,c['scenarios']['base'],wacc=w)['value_per_share'] for w in [c['wacc']-.01,c['wacc'],c['wacc']+.01]}
  out[ticker]=dict(inputs=c,scenarios=vals,reverse_year2_to5_growth=reverse(c),wacc_sensitivity=sensitivity)
  assert abs(calculate(c,c['scenarios']['base'],growth=reverse(c))['value_per_share']-c['price'])<1e-7
  assert vals['bear']['value_per_share']<vals['base']['value_per_share']<vals['bull']['value_per_share']
 (ROOT/'valuation-results.json').write_text(json.dumps(out,indent=2)+'\n')
 (ROOT/'valuation-inputs.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
 for t,v in out.items():
  print(t,'reverse',round(v['reverse_year2_to5_growth']*100,1),'sensitivity',v['wacc_sensitivity'])
  for n,s in v['scenarios'].items():print(n,round(s['value_per_share'],2),round(s['upside']*100,1),'NTM FCFF',round(s['years'][0]['fcff'],3),'terminal%',round(s['terminal_share']*100,1))
