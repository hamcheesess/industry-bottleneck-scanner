"""Historical report-support model; all forecasts analyst assumptions.
USD bn, bn diluted-share proxies. Information cutoff June30 2025.
EBITA excludes acquired intangible amortization, retains SBC; physical D&A only.
Year1 explicit cash bridge; subsequent reinvestment=incremental sales/sales-capital.
No API, no forecast actuals. Price scenarios are conditional, not calibrated probabilities.
"""
from pathlib import Path
import json
P=Path(__file__).parent
C={
'ANET':dict(price=102.31,shares=1.2792,cash=8.1496,debt=0,pref=0,nci=0,tax=.21,da=.007,capex=.018,nwc=.15,wacc=.10,tg=.03,troic=.20,interest=0,div=0,pref_accretion=0,segments=[6.77,1.2492],labels=['product','service'],facts=['F_ANET'],cases={'bear':[[.05,.10],.36,.36,.08,.04,4],'base':[[.17,.20],.41,.40,.18,.08,5],'bull':[[.28,.25],.43,.43,.26,.12,6]}),
'CSCO':dict(price=69.38,shares=4.002,cash=15.6,debt=29.279,pref=0,nci=0,tax=.21,da=.01,capex=.017,nwc=.10,wacc=.09,tg=.025,troic=.12,interest=1.35,div=1.64*4.002,pref_accretion=0,segments=[41.496,15.10],labels=['product','service'],facts=['F_CSCO'],cases={'bear':[[-.02,.02],.24,.24,.02,.02,3],'base':[[.05,.04],.275,.275,.05,.03,4],'bull':[[.10,.06],.30,.30,.08,.04,5]}),
'COHR':dict(price=89.21,shares=.1591,cash=.8903,debt=3.7318,pref=2.4616,nci=.3546,tax=.23,da=.04,capex=.06,nwc=.20,wacc=.10,tg=.03,troic=.12,interest=.2292,div=0,pref_accretion=.1308,segments=[3.5892,2.4024],labels=['legacy_networking','other'],facts=['F_COHR','F_DAY'],cases={'bear':[[.05,-.08],.11,.12,.05,.03,2],'base':[[.20,0],.15,.18,.15,.06,2.5],'bull':[[.35,.05],.18,.21,.22,.09,3]})}
def calc(c,a,g_override=None,w_override=None):
 gr,m1,m5,g,late,sc=a;g=g if g_override is None else g_override;w=c['wacc'] if w_override is None else w_override
 assert w>c['tg'];prev=sum(c['segments']);seg=[b*(1+x) for b,x in zip(c['segments'],gr)];rev=sum(seg);rows=[]
 for y in range(1,11):
  if y>1:rev*=1+(g if y<=5 else late)
  m=m1+(m5-m1)*min((y-1)/4,1);ebita=rev*m;nopat=ebita*(1-c['tax']);delta=max(0,rev-prev)
  if y==1:
   da=rev*c['da'];cap=rev*c['capex'];nwc=delta*c['nwc'];ri=cap-da+nwc
  else:ri=delta/sc;da=cap=nwc=None
  fcff=nopat-ri;rows.append(dict(year=y,revenue=rev,margin=m,ebita=ebita,nopat=nopat,da=da,capex=cap,dnwc=nwc,reinvestment=ri,fcff=fcff));prev=rev
 tv=rows[-1]['nopat']*(1+c['tg'])*(1-c['tg']/c['troic'])/(w-c['tg']);pv=sum(r['fcff']/(1+w)**r['year'] for r in rows);ev=pv+tv/(1+w)**10
 bridge=c['cash']-c['debt']-c['pref']-c['nci'];v=max(0,ev+bridge)/c['shares']
 cash12=c['cash']+rows[0]['fcff']-c['interest']*(1-c['tax'])-c['div'];bridge12=cash12-c['debt']-c['pref']-c['pref_accretion']-c['nci']
 fair12=max(0,ev*(1+w)-rows[0]['fcff']+bridge12)/c['shares']
 multiple=(c['price']*c['shares']-bridge)/rows[0]['nopat'];steady12=max(0,multiple*rows[1]['nopat']+bridge12)/c['shares']
 return dict(segments_y1=seg,years=rows,ev=ev,dcf=v,fair12=fair12,return12=(fair12+c['div']/c['shares'])/c['price']-1,constant_multiple12=steady12,implied_ev_nopat=multiple,terminal_share=tv/(1+w)**10/ev)
def reverse(c):
 lo,hi=-.1,1
 for _ in range(100):
  m=(lo+hi)/2
  if calc(c,c['cases']['base'],m)['dcf']>c['price']:hi=m
  else:lo=m
 return (lo+hi)/2
out={}
for t,c in C.items():
 vs={k:calc(c,a) for k,a in c['cases'].items()};g=reverse(c)
 assert abs(calc(c,c['cases']['base'],g)['dcf']-c['price'])<1e-6
 assert vs['bear']['dcf']<vs['base']['dcf']<vs['bull']['dcf']
 for v in vs.values():
  for r in v['years']:assert abs(r['nopat']-r['reinvestment']-r['fcff'])<1e-10
 out[t]=dict(inputs=c,cases=vs,reverse_growth=g,sensitivity={str(round(w,3)):calc(c,c['cases']['base'],w_override=w)['dcf'] for w in [c['wacc']-.01,c['wacc'],c['wacc']+.01]})
(P/'valuation.json').write_text(json.dumps(out,indent=2)+'\n')
for t,r in out.items():
 print(t,'reverse',round(r['reverse_growth']*100,1),'sens',r['sensitivity'])
 for k,v in r['cases'].items():print(k,'Rev',round(v['years'][0]['revenue'],3),'FCF',round(v['years'][0]['fcff'],3),'DCF',round(v['dcf'],2),'12m',round(v['fair12'],2),'ret',round(v['return12']*100,1),'same multiple',round(v['constant_multiple12'],2),'TV',round(v['terminal_share']*100,1))
