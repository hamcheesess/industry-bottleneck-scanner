"""Insert deterministic valuation tables into the reviewed Korean narrative."""
from pathlib import Path
import json
P=Path(__file__).parent
v=json.loads((P/'valuation.json').read_text())
def table(headers, rows):
 return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in [headers]+rows)
fmt=lambda x:f'{x:,.2f}'
pc=lambda x:f'{x*100:.1f}%'
names={'ANET':'Arista','CSCO':'Cisco','COHR':'Coherent'}
cash=[]
for label,key in [('첫해 매출','revenue'),('세후 영업이익','nopat'),('순재투자','reinvestment'),('FCFF','fcff')]:
 cash.append([label]+[fmt(v[t]['cases']['base']['years'][0][key]) for t in v])
tokens={'CASH_TABLE':table(['기본 첫해 · 십억 달러','Arista','Cisco','Coherent'],cash)}
tokens['SCENARIO_CASH']=table(['첫해 FCFF · 십억 달러','약세','기본','강세'],[[names[t]]+[fmt(v[t]['cases'][k]['years'][0]['fcff']) for k in ['bear','base','bull']] for t in v])
tokens['VALUE_TABLE']=table(['회사 / 당시 가격','약세 DCF','기본 DCF','강세 DCF'],[[names[t]+' / $'+fmt(v[t]['inputs']['price'])]+['$'+fmt(v[t]['cases'][k]['dcf']) for k in ['bear','base','bull']] for t in v])
tokens['SENS_TABLE']=table(['기본 가치 민감도','WACC −1%p','기준 WACC','WACC +1%p'],[[names[t]]+['$'+fmt(x) for x in v[t]['sensitivity'].values()] for t in v])
tokens['REVERSE_TABLE']=table(['회사','기본 2~5년 성장','가격 일치 역산 성장'],[[names[t],pc(v[t]['inputs']['cases']['base'][3]),pc(v[t]['reverse_growth'])] for t in v])
tokens['PRICE_TABLE']=table(['12개월 가격 / 배당 포함 수익률','약세','기본','강세'],[[names[t]]+['$'+fmt(v[t]['cases'][k]['fair12'])+' / '+pc(v[t]['cases'][k]['return12']) for k in ['bear','base','bull']] for t in v])
tokens['MULTIPLE_TABLE']=table(['기본 시나리오만 비교','가치 완전 반영 가격','현재 선행 배수 유지 가격'],[[names[t],'$'+fmt(v[t]['cases']['base']['fair12']),'$'+fmt(v[t]['cases']['base']['constant_multiple12'])] for t in v])
s=(P/'report-source.md').read_text()
for k,val in tokens.items():
 assert s.count('{{'+k+'}}')==1,k
 s=s.replace('{{'+k+'}}',val)
assert '{{' not in s
(P/'report-ko.md').write_text(s)
print('assembled',len(s.split('---PAGE---')),'planned pages')
